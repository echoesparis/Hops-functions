"""Automatic Grasshopper group colouring by nickname prefix, with a viewport key.

File-synced companion of ``os_gh-template.gh``. Replaces the legacy C# Script
"AC" that used to carry this logic inline.

How it works
------------
A *schema* maps a nickname prefix to a label, a description and a colour. Any
group named ``<prefix>_<label>`` gets that colour and is renamed to ``<label>``,
so the colour carries the category and the name stays short.

The built-in schema (DEFAULT_SCHEMA below) covers twelve categories and needs
nothing on the canvas. Wire ``cs`` to override it.

The component watches the document ObjectsAdded / ObjectsDeleted events and
each group ObjectChanged event, so naming a group recolours it immediately.

Why the work is deferred: a rename done from inside the ObjectChanged handler
is overwritten by the edit that triggered it. Every event instead schedules a
pass that runs once the edit has landed. The pass is idempotent (a coloured
group has already lost its prefix), so it cannot loop.

Schema format
-------------
One row per category, as CSV::

    c_,#fdb462,"control: switches, toggles, gates"
    gi_,#b3de69,"GH input: sliders and values you author here"

Fields are ``prefix,colour,"label: description"`` - the text is one quoted
field, split on its first colon. Only ``prefix`` is required: a row with no
colour reuses that prefix's default colour when it is a known one, otherwise
the next free entry of the Set3 palette (and, once all twelve are spoken for,
cycles through them). Blank lines, ``#`` comments and ``...`` placeholders are
ignored; a leading ``//`` is tolerated but not emitted. The earlier
``prefix,label,description,#rrggbb`` and ``label:prefix:#rrggbb`` forms are
still accepted - the colour field is recognised by its leading ``#``.

When ``cs`` is wired it *replaces* the built-in schema: a prefix it does not
list stops being recognised. Unwire it to fall back to DEFAULT_SCHEMA. The
``s`` output always reports whichever schema is in force, in the CSV form
above - so it round-trips into a Panel you can edit and wire back in.

Viewport key
------------
While the component is previewed (not Hidden, not Locked) and its document is
the active one, two things are drawn over the active Rhino viewport: a key in
the top-left - one row per category, swatch + label + how many groups currently
carry it - and the ECHOES mark in the top-right. Toggle the component's preview
to show or hide both. Counting is by colour, not by name, because a coloured
group has already lost its prefix.

The mark comes from the ``l`` input - wire the ``Logo`` mesh param - and is
rasterised into a Bitmap with System.Drawing, then wrapped in a DisplayBitmap
sprite, following the AHD DrawEmbeddedSpriteBitmap pattern but without the
base64 payload, which corrupts silently when hand-copied into a .py. With ``l``
unwired it falls back to drawing the three circles of media/echoes.svg. The
sprite is 64 px: a non-power-of-two size renders nothing at all, with no error.
The raster is built once per solve and the DisplayBitmap per frame - a
DisplayBitmap cached across frames draws corrupted pixels.

Component ports (simple mode - a file-synced script never gets RunScript)
------------------------------------------------------------------------
in   script : path of this file (Input is path + Synchronize)
in   run    : master switch; False detaches every handler
in   cs     : custom schema, LIST access (optional)
in   l      : logo mesh drawn in the corner, LIST access (optional)
out  out    : log
out  s      : the active schema, as CSV rows
"""

import csv
import traceback

import System
import Rhino as rc
import Grasshopper as gh
import scriptcontext as sc
from Grasshopper.Kernel.Special import GH_Group
from System.Drawing import Color

KEY_SUFFIX = "_"
STICKY_ROOT = "os_gh-template::autocolor::"
LEGEND_ROOT = "os_gh-template::legend::"

# --------------------------------------------------------------------------
# tooltips - the .py is the single source of truth, never the GH UI.
# nickname -> (human name, description); a bare string sets the description only.
# --------------------------------------------------------------------------

DESCRIPTION = ("Colours and renames canvas groups from their nickname prefix, and draws the "
               "schema as a key in the Rhino viewport. Name a group f_solar and it turns "
               "blue and renames itself to solar. Code: scripts/gh_template.py")
DOC_IN = {
    "script": ("Script", "Path of scripts/gh_template.py - relative to this .gh. "
                         "Input is path + Synchronize, so saving the file re-solves the canvas. "
                         "Do not edit the component text"),
    "run":    ("Run", "Master switch. False detaches every document and group handler "
                      "and hides the viewport key, leaving existing colours untouched"),
    "l":      ("Logo", "Flat mesh drawn as a sprite in the top-right of the viewport "
                       "(wire the Logo mesh param). Unwired, the ECHOES mark is drawn instead"),
    "cs":     ("Custom Schema", "Schema override, one CSV row per category: "
                                "prefix,#rrggbb,\"label: description\". Only prefix is required. "
                                "When wired it REPLACES the built-in schema; unwire to fall back"),
}
DOC_OUT = {
    "out":    ("Log", "Which schema is in force, how many prefixes and groups are watched, "
                      "how many were recoloured, plus any schema parse problem"),
    "s":      ("Schema", "The schema actually in force, as CSV rows in the same format cs "
                         "accepts - wire it to a Panel, edit, and feed it back into cs"),
}

# The schema, in dataflow reading order: steer -> take in -> compute -> give
# back -> housekeeping. Colours are ColorBrewer Set3 (n=12) - pastel by design,
# since a group fill sits *behind* components and must not fight them - but
# assigned by meaning rather than palette order, so families read at a glance:
#
#   amber   steering        greens/teal  the three ways data enters
#   red     secrets         purple       work that leaves this machine
#   blue    the actual work yellow       what comes back out
#   lilac/pink  what the human sees      loud yellow / grey  housekeeping
#
# prefix, label, description, colour
DEFAULT_SCHEMA = [
    ("c_",  "control",        "switches, toggles, gates",           "#fdb462"),
    ("gi_", "GH input",       "sliders and values you author here", "#b3de69"),
    ("ri_", "rhino input",    "geometry referenced from the 3dm",   "#8dd3c7"),
    ("ei_", "external input", "files, sheets, APIs",                "#ccebc5"),
    ("k_",  "keys",           "credentials - never commit these",   "#fb8072"),
    ("h_",  "remote",         "Hops / compute calls",               "#bc80bd"),
    ("f_",  "function",       "the actual logic",                   "#80b1d3"),
    ("o_",  "output",         "bake, write, export",                "#ffffb3"),
    ("v_",  "viz",            "preview, legends, colour ramps",     "#bebada"),
    ("ui_", "UI",             "interface widgets",                  "#fccde5"),
    ("t_",  "temp",           "scratch, work in progress",          "#ffed6f"),
    ("d_",  "dead",           "disabled, kept for reference",       "#d9d9d9"),
]

# ColorBrewer Set3, n=12 - fallback for schema rows that name no colour
PALETTE = ["#8dd3c7", "#ffffb3", "#bebada", "#fb8072", "#80b1d3", "#fdb462",
           "#b3de69", "#fccde5", "#d9d9d9", "#bc80bd", "#ccebc5", "#ffed6f"]

IGNORED_LINES = ("...", "…")


# --------------------------------------------------------------------------
# tooltips
# --------------------------------------------------------------------------

def annotate(comp, description, doc_in, doc_out):
    """Write the tooltips of a Script component from Python: the component
    Description, and the Name / Description of every input and output param
    (what Grasshopper shows on hover). Saved with the .gh like any param
    property. A doc value may be a ``(name, description)`` pair or a bare
    description string."""
    try:
        if comp.Description != description:
            comp.Description = description
        for params, docs in ((comp.Params.Input, doc_in), (comp.Params.Output, doc_out)):
            for p in params:
                doc = docs.get(p.NickName)
                if not doc:
                    continue
                name, desc = doc if isinstance(doc, tuple) else (None, doc)
                if name and p.Name != name:
                    p.Name = name
                if desc and p.Description != desc:
                    p.Description = desc
    except Exception:
        pass


# --------------------------------------------------------------------------
# input coercion
# --------------------------------------------------------------------------

def as_bool(value):
    """Coerce a component input to bool.

    Inputs without a type hint arrive goo-wrapped, so a bare ``if value`` on a
    GH_Boolean is always True. Unwired inputs arrive as None.
    """
    if value is None:
        return False
    if hasattr(value, "Value"):
        value = value.Value
    if isinstance(value, str):
        return value.strip().lower() not in ("", "0", "false", "none")
    try:
        return bool(value)
    except Exception:
        return False


def as_lines(value):
    """Flatten a list-access text input into a list of lines.

    A Panel may deliver one item per line or a single multi-line string,
    and items arrive goo-wrapped.
    """
    if value is None:
        return []
    items = value if isinstance(value, (list, tuple)) else [value]
    lines = []
    for item in items:
        if item is None:
            continue
        if hasattr(item, "Value"):
            item = item.Value
        for line in str(item).replace("\r\n", "\n").replace("\r", "\n").split("\n"):
            lines.append(line)
    return lines


def to_color(text):
    """``#rrggbb`` / ``rrggbb`` / ``r,g,b`` -> Color, or None."""
    text = (text or "").strip().lstrip("#")
    if not text:
        return None
    if "," in text:
        try:
            r, g, b = [int(p) for p in text.split(",")[:3]]
        except ValueError:
            return None
        return Color.FromArgb(255, r, g, b)
    if len(text) == 3:
        text = "".join(c * 2 for c in text)
    if len(text) != 6:
        return None
    try:
        return Color.FromArgb(255, int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16))
    except ValueError:
        return None


def to_hex(colour):
    return "#%02x%02x%02x" % (colour.R, colour.G, colour.B)


def first_mesh(value):
    """First Rhino mesh out of a list-access input, unwrapping the goo."""
    if value is None:
        return None
    for item in (value if isinstance(value, (list, tuple)) else [value]):
        if item is None:
            continue
        m = item.Value if hasattr(item, "Value") else item
        if isinstance(m, rc.Geometry.Mesh):
            return m
    return None


# --------------------------------------------------------------------------
# schema
# --------------------------------------------------------------------------

def default_schema():
    """prefix -> (label, description, Color) for the built-in schema."""
    return dict((p, (lbl, desc, to_color(hexa))) for p, lbl, desc, hexa in DEFAULT_SCHEMA)


def split_row(line):
    """One schema line -> (prefix, label, description, colour_text), or None.

    Current form   ``[//]prefix,#rrggbb,"label: description"``
    Earlier form   ``[//]prefix,label,description,#rrggbb``
    Oldest form    ``label:prefix[:#rrggbb]``

    The colour field is identified by its leading ``#``, which is what tells
    the two CSV forms apart (a bare 6-char label such as "facade" is valid hex,
    so the marker is required rather than inferred).
    """
    if "," in line:
        try:
            row = next(csv.reader([line]))
        except Exception:
            return None
        row = [c.strip() for c in row] + ["", "", ""]
        if row[1].startswith("#"):
            label, _sep, desc = row[2].partition(":")
            return row[0], label.strip(), desc.strip(), row[1]
        return row[0], row[1], row[2], row[3]

    parts = [p.strip() for p in line.split(":")]
    if len(parts) < 2 or not parts[1]:
        return None
    return parts[1], parts[0], "", (parts[2] if len(parts) > 2 else "")


def parse_schema(lines):
    """Parse schema lines into prefix -> (label, description, Color).

    Returns ``(schema, problems)``. A row with no colour falls back to that
    prefix's default colour, then to the next unused palette entry.
    """
    defaults = default_schema()
    used = set(to_hex(v[2]) for v in defaults.values())
    spare = [c for c in (to_color(h) for h in PALETTE) if to_hex(c) not in used]
    schema, problems = {}, []

    for raw in lines:
        line = (raw or "").strip()
        if line.startswith("//"):
            line = line[2:].strip()
        if not line or line.startswith("#") or line in IGNORED_LINES:
            continue

        row = split_row(line)
        if row is None or not row[0]:
            problems.append("cannot parse %r (expected prefix,label,description,#colour)" % raw)
            continue

        prefix, label, desc, colour_text = row
        if not prefix.endswith(KEY_SUFFIX):
            prefix += KEY_SUFFIX

        colour = to_color(colour_text)
        if colour is None:
            if colour_text:
                problems.append("unreadable colour %r, using a default" % colour_text)
            if prefix in defaults:
                colour = defaults[prefix][2]
            elif spare:
                colour = spare.pop(0)
            else:
                colour = to_color(PALETTE[len(schema) % len(PALETTE)])

        if not label and prefix in defaults:
            label = defaults[prefix][0]
        if not desc and prefix in defaults:
            desc = defaults[prefix][1]
        schema[prefix] = (label or prefix, desc, colour)

    return schema, problems


def build_schema(schema_input):
    """The active schema: the wired input replaces the defaults, else defaults."""
    lines = as_lines(schema_input)
    if not lines:
        return default_schema(), [], False
    schema, problems = parse_schema(lines)
    if not schema:
        problems.append("cs held no usable row - using the built-in schema")
        return default_schema(), problems, False
    return schema, problems, True


def schema_order(schema):
    """Built-in prefixes first, in dataflow order, then anything new."""
    order = [p for p, _l, _d, _h in DEFAULT_SCHEMA if p in schema]
    return order + sorted(p for p in schema if p not in order)


def format_schema(schema):
    """The active schema as CSV rows, in the form ``cs`` accepts."""
    rows = []
    for p in schema_order(schema):
        label, desc, colour = schema[p]
        text = "%s: %s" % (label, desc) if desc else label
        rows.append('%s,%s,"%s"' % (p, to_hex(colour), text.replace('"', "'")))
    return rows


# --------------------------------------------------------------------------
# colouring
# --------------------------------------------------------------------------

def resolve(grp, schema):
    """Return ``(colour, new_name)`` for *grp*, or None when it is not ours.

    Port of the C# ``colorGroup``: a nickname without an underscore is skipped,
    a bare prefix is skipped (it would rename the group to nothing), and the
    prefix is removed with a plain ``replace`` (every occurrence).
    """
    if not isinstance(grp, GH_Group):
        return None

    name = grp.NickName or ""
    if name.endswith(KEY_SUFFIX):       # a bare prefix names no group
        return None

    splits = name.split("_")
    if len(splits) == 1:
        return None

    prefix = splits[0] + "_"
    if prefix not in schema:
        return None

    return schema[prefix][2], name.replace(prefix, "")


def color_group(grp, schema):
    """Colour and rename one group. Returns True when it was changed."""
    hit = resolve(grp, schema)
    if hit is None:
        return False
    grp.Colour, grp.NickName = hit
    return True


def color_all(doc, schema):
    """One idempotent pass over every group. Returns the names it changed."""
    done = []
    for grp in [o for o in list(doc.Objects) if isinstance(o, GH_Group)]:
        if color_group(grp, schema):
            done.append(grp.NickName)
    if done:
        refresh()
    return done


def tally(doc, schema):
    """prefix -> number of groups currently carrying that colour.

    Counted by colour, not by name: a coloured group has lost its prefix.
    """
    counts = dict((p, 0) for p in schema)
    by_argb = dict((schema[p][2].ToArgb(), p) for p in schema)
    for grp in [o for o in list(doc.Objects) if isinstance(o, GH_Group)]:
        p = by_argb.get(grp.Colour.ToArgb())
        if p is not None:
            counts[p] += 1
    return counts


def refresh():
    """Repaint the canvas without expiring the solution we are inside of."""
    canvas = gh.Instances.ActiveCanvas
    if canvas is not None:
        canvas.Refresh()


# --------------------------------------------------------------------------
# viewport key (AHD DrawForeground design pattern)
# --------------------------------------------------------------------------

PAD, SWATCH_W, SWATCH_H, ROW_H, TEXT_H = 18, 22, 14, 21, 13
FONT = "Consolas"
LOGO_PX = 128         # sprite size in px - MUST be a power of two (see module docs)


def logo_bitmap(size, colour):
    """The ECHOES mark - three concentric circles, as in media/echoes.svg -
    rasterised at *size* px. Rebuilt per frame on purpose (see module docs)."""
    bmp = System.Drawing.Bitmap(size, size)
    g = System.Drawing.Graphics.FromImage(bmp)
    try:
        g.SmoothingMode = System.Drawing.Drawing2D.SmoothingMode.AntiAlias
        g.Clear(System.Drawing.Color.Transparent)
        unit = size / 24.0                       # the svg viewBox is 0 0 24 24
        pen = System.Drawing.Pen(colour, float(2.0 * unit))
        brush = System.Drawing.SolidBrush(colour)
        for r in (10.0, 6.0):                    # the two stroked rings
            d = 2.0 * r * unit
            off = (size - d) / 2.0
            g.DrawEllipse(pen, float(off), float(off), float(d), float(d))
        d = 4.0 * unit                           # the filled centre, r = 2
        off = (size - d) / 2.0
        g.FillEllipse(brush, float(off), float(off), float(d), float(d))
        pen.Dispose()
        brush.Dispose()
    finally:
        g.Dispose()
    return bmp


def mesh_bitmap(mesh, size, colour):
    """Rasterise a flat mesh into a *size* px bitmap, fitted and centred.

    Faces are filled and outlined in the same colour: filling alone leaves
    hairline seams between adjacent triangles when antialiasing is on.
    """
    try:
        bb = mesh.GetBoundingBox(True)
    except Exception:
        return None
    w, h = bb.Max.X - bb.Min.X, bb.Max.Y - bb.Min.Y
    if w <= 0 or h <= 0:
        return None

    pad = size * 0.06
    scale = (size - 2.0 * pad) / max(w, h)
    ox = pad + (size - 2.0 * pad - w * scale) / 2.0
    oy = pad + (size - 2.0 * pad - h * scale) / 2.0

    bmp = System.Drawing.Bitmap(size, size)
    g = System.Drawing.Graphics.FromImage(bmp)
    try:
        g.SmoothingMode = System.Drawing.Drawing2D.SmoothingMode.AntiAlias
        g.Clear(System.Drawing.Color.Transparent)
        brush = System.Drawing.SolidBrush(colour)
        pen = System.Drawing.Pen(colour, 1.0)
        verts = mesh.Vertices

        def screen(i):
            v = verts[i]
            return System.Drawing.PointF(
                float(ox + (v.X - bb.Min.X) * scale),
                float(size - (oy + (v.Y - bb.Min.Y) * scale)))   # screen y grows down

        for f in mesh.Faces:
            idx = [f.A, f.B, f.C] + ([f.D] if f.IsQuad else [])
            poly = System.Array[System.Drawing.PointF]([screen(i) for i in idx])
            g.FillPolygon(brush, poly)
            g.DrawPolygon(pen, poly)
        brush.Dispose()
        pen.Dispose()
    finally:
        g.Dispose()
    return bmp


def make_legend(component, doc, schema, logo=None):
    """Build the DrawForeground handler that draws the schema key."""
    rows = [(p, schema[p][0], schema[p][2]) for p in schema_order(schema)]
    ink = Color.FromArgb(255, 30, 30, 30)
    # rasterised once per solve, not per frame
    raster = mesh_bitmap(logo, LOGO_PX, ink) if logo is not None else None
    if raster is None:
        raster = logo_bitmap(LOGO_PX, ink)
    edge = Color.FromArgb(120, 30, 30, 30)
    back = Color.FromArgb(215, 252, 252, 252)

    def active(arg):
        # component previewed, our document focused, active viewport only -
        # DrawForeground otherwise fires once per viewport
        rhino_doc = rc.RhinoDoc.ActiveDoc
        canvas = gh.Instances.ActiveCanvas
        return (not component.Hidden and not component.Locked
                and canvas is not None and rhino_doc is not None
                and component.OnPingDocument() == canvas.Document
                and arg.Viewport.Id == rhino_doc.Views.ActiveView.ActiveViewportID)

    def draw(sender, arg):
        try:
            if not active(arg):
                return
            counts = tally(doc, schema)
            labels = ["%-3s %-15s %d" % (p, lbl, counts.get(p, 0)) for p, lbl, _c in rows]
            width = SWATCH_W + 12 + int(TEXT_H * 0.62 * max(len(t) for t in labels)) + PAD
            height = ROW_H * len(rows) + PAD

            arg.Display.Draw2dRectangle(
                System.Drawing.Rectangle(PAD - 8, PAD - 8, width, height), edge, 1, back)
            for i, (_p, _lbl, colour) in enumerate(rows):
                y = PAD + i * ROW_H
                arg.Display.Draw2dRectangle(
                    System.Drawing.Rectangle(PAD, y, SWATCH_W, SWATCH_H), edge, 1, colour)
                arg.Display.Draw2dText(
                    labels[i], ink,
                    rc.Geometry.Point2d(PAD + SWATCH_W + 12, y), False, TEXT_H, FONT)

            # the mark, top-right. DrawSprite centres on the point, hence the
            # half-size offset. LOGO_PX must stay a power of two: at 56 the
            # sprite silently drew nothing, with no exception raised.
            sprite = rc.Display.DisplayBitmap(raster)
            centre = rc.Geometry.Point2d(
                arg.Viewport.Size.Width - LOGO_PX / 2.0 - PAD, LOGO_PX / 2.0 + PAD)
            arg.Display.DrawSprite(sprite, centre, LOGO_PX, LOGO_PX)
        except Exception:
            pass

    return draw


def set_legend(component, doc, schema, on, logo=None):
    """(Re)subscribe the key handler, or drop it.

    Unsubscribing the cached delegate first is mandatory: a file-synced module
    re-executes on every solve and on every disk save, so a freshly defined
    function would stack handlers instead of replacing them.
    """
    key = LEGEND_ROOT + str(component.InstanceGuid)
    old = sc.sticky.get(key)
    if old is not None:
        try:
            rc.Display.DisplayPipeline.DrawForeground -= old
        except Exception:
            pass
        sc.sticky[key] = None

    if on:
        handler = make_legend(component, doc, schema, logo)
        rc.Display.DisplayPipeline.DrawForeground += handler
        sc.sticky[key] = handler

    rhino_doc = rc.RhinoDoc.ActiveDoc
    if rhino_doc is not None:
        rhino_doc.Views.Redraw()


# --------------------------------------------------------------------------
# handler bookkeeping
# --------------------------------------------------------------------------

def state(component):
    """Per-component state parked in sticky.

    A file-synced script re-executes on every solve, so the handlers defined
    below are brand new function objects each time and ``-=`` against a fresh
    one silently fails to unsubscribe the previous one. The live delegates are
    therefore cached here (which also keeps them alive against GC) and detached
    before new ones are attached.
    """
    key = STICKY_ROOT + str(component.InstanceGuid)
    st = sc.sticky.get(key)
    if st is None:
        st = {"on_changed": None, "on_added": None, "on_removed": None,
              "groups": [], "pending": False}
        sc.sticky[key] = st
    return st


def detach_all(doc, st):
    on_changed = st.get("on_changed")
    if on_changed is not None:
        for grp in st.get("groups") or []:
            try:
                grp.ObjectChanged -= on_changed
            except Exception:
                pass
    if st.get("on_added") is not None:
        try:
            doc.ObjectsAdded -= st["on_added"]
        except Exception:
            pass
    if st.get("on_removed") is not None:
        try:
            doc.ObjectsDeleted -= st["on_removed"]
        except Exception:
            pass
    st["groups"] = []
    st["on_changed"] = None
    st["on_added"] = None
    st["on_removed"] = None
    st["pending"] = False


# --------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------

def main(component, run, schema_input=None, logo_input=None):
    annotate(component, DESCRIPTION, DOC_IN, DOC_OUT)

    log = []
    doc = component.OnPingDocument()
    if doc is None:
        return ["no Grasshopper document"], []

    st = state(component)
    detach_all(doc, st)                 # always first, so the pass is idempotent

    schema, problems, custom = build_schema(schema_input)

    if not run:
        set_legend(component, doc, schema, False)
        return ["run = False - handlers detached"], format_schema(schema)

    log.extend(problems)
    groups = [o for o in list(doc.Objects) if isinstance(o, GH_Group)]

    def deferred(_doc):
        st["pending"] = False
        try:
            color_all(_doc, schema)
            rhino_doc = rc.RhinoDoc.ActiveDoc
            if rhino_doc is not None:
                rhino_doc.Views.Redraw()    # the key shows live counts
        except Exception:
            pass

    def schedule():
        """Run the pass once the event that triggered it has unwound."""
        if st["pending"]:
            return
        st["pending"] = True
        doc.ScheduleSolution(5, gh.Kernel.GH_Document.GH_ScheduleDelegate(deferred))

    def on_group_changed(sender, e):
        # No filtering here: the event fires while the rename is still in
        # flight, so sender.NickName is the OLD name and any resolve() check
        # would skip the very rename that triggered us. The deferred pass is
        # idempotent, so scheduling unconditionally is both correct and cheap.
        try:
            schedule()
        except Exception:
            pass

    def on_objects_added(sender, e):
        added = [o for o in e.Objects if isinstance(o, GH_Group)]
        for obj in added:
            obj.ObjectChanged += on_group_changed
            st["groups"].append(obj)
        if added:
            schedule()

    def on_objects_removed(sender, e):
        for obj in e.Objects:
            if isinstance(obj, GH_Group):
                try:
                    obj.ObjectChanged -= on_group_changed
                except Exception:
                    pass
                if obj in st["groups"]:
                    st["groups"].remove(obj)

    for grp in groups:
        grp.ObjectChanged += on_group_changed
    st["groups"] = list(groups)
    st["on_changed"] = on_group_changed

    changed = color_all(doc, schema)

    doc.ObjectsAdded += on_objects_added
    doc.ObjectsDeleted += on_objects_removed
    st["on_added"] = on_objects_added
    st["on_removed"] = on_objects_removed

    set_legend(component, doc, schema, True, first_mesh(logo_input))

    if changed:
        log.append("coloured: " + ", ".join(changed))
    log.append("%s schema, %d prefix(es), watching %d group(s), %d recoloured" % (
        "custom" if custom else "built-in", len(schema), len(groups), len(changed)))
    return log, format_schema(schema)


# --------------------------------------------------------------------------
# component tail - skipped when the file is imported as a module
# --------------------------------------------------------------------------

try:
    _run = run
except NameError:
    pass
else:
    try:
        _cs = cs
    except NameError:
        _cs = None
    try:
        _l = l
    except NameError:
        _l = None
    try:
        # runtime errors are swallowed on file-synced components, so the only
        # reliable error channel is stdout
        _log, s = main(ghenv.Component, as_bool(_run), _cs, _l)
        for _line in _log:
            print(_line)
    except Exception:
        s = []
        print(traceback.format_exc())
