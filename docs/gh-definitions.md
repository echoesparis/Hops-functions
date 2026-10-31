---
type: report
description: "Offline inventory and audit (2026-09-16) of every .gh of the repo: components, addons, Hops targets, and the fixes made to them."
applies_to:
  - "*.gh"
  - scripts/gh_template.py
---

# Grasshopper definitions — inventory & audit

Offline audit of every `.gh` in this repo (parsed with the `gh-graph` skill; no Rhino required), plus an in-Rhino pass over the clustering definition. Date: 2026-09-16.

## Inventory

| File | Comp. | Wires | Node types | Addon libs | Remote / Hops targets |
|---|---|---|---|---|---|
| `os_gh-template.gh` | 59 | 36 | 55 vanilla, 4 python (1 file-synced) | — (100% core) | `http://127.0.0.1:5000/` health check (h_ group) |
| `_viz_palettes_example.gh` | 12 | 9 | 11 vanilla, 1 Hops | Hops | `http://compute.echoes.paris/viz_colors.gh` |
| `viz_bivariate-choropleth_example.gh` | 19 | 24 | 18 vanilla, 1 Hops | Hops, Ladybug | local path → `appserver/src/files/viz_bivariate-choropleth.gh` |
| `googleAPI.gh` | 21 | 15 | 19 vanilla, 2 Hops | Hops | `http://127.0.0.1:5000/read_public_sheet`, `/read_sheet_oauth` |
| `ee_PV_example.gh` | 25 | 23 | 24 vanilla, 1 Hops | Hops, Ladybug | local path → `appserver/src/files/ee_PV.gh` |
| `vm_procedural-forestry_example.gh` | 38 | 34 | 35 vanilla, 3 Hops | Hops, WombatGH | `compute.echoes.paris/vm_procedural-urban-forestry.gh`, `/os_key-server.gh`, **`C:\Users\SP\OneDrive - ECHOES\secrets.gh`** |
| `ad_shading-typologies_example.gh` | 60 | 64 | 58 vanilla, 2 Hops | Hops, FroGH, TreeSloth, WombatGH, Human | local paths → `appserver/src/files/ad_shading-T1.gh`, `ad_shading-T3_angles.gh` |
| `urb_massing-typologies.gh` | 80 | 93 | 72 vanilla, 6 Hops, 1 C#, 1 cluster | Hops, Octopus, Weaverbird, Human | `compute.echoes.paris/urb_type-z_solar-envelope.gh`, `/urb_type-xy1.gh` + 4 local paths under the **old** `compute.rhino3d.appserver/` folder |
| `viz_seaborn.gh` | 85 | 63 | 77 vanilla, 5 Hops, 2 GHPython, 1 cluster | Hops, Human UI, Human, Ladybug | `https://seaborn-gh.herokuapp.com/histplot` (dead host), `127.0.0.1:5000/dt_to_df`, `/presets`, `/example_data`, `/seaborn/boxplot` |
| `ds_clustering.gh` | 140 | 146 | 135 vanilla, 5 Hops, 2 clusters | Hops, Volvox, HDTTreeUtils, Pufferfish, Human, Ladybug | `http://127.0.0.1:5000/clustering_datasets`, `/cluster_score`, `/dbscan` x2, `/kmeans` |
| `ee_massing-analytics_example.gh` | 191 | 186 | 178 vanilla, 10 Hops, 2 clusters, 1 C# | Hops, FroGH, jSwan, Human, Ladybug | 10 local paths → `appserver/src/files/`: `ee_PAR/VIEW/NRB/RAD/SUN/MSV/CBB/SKY`, `os_key-server`, `ad_shading-T3_angles` |

All 11 files parse cleanly: **0 unresolved components** anywhere. Orphans are all annotation (Sketch / Group / Scribble / Panel) or unwired UI inputs — normal for example files.

Caveat: "parses cleanly" is not "loads cleanly". The offline parse resolves a component by GUID against the file, not against the installed addons. The clustering definitions listed eleFront here and still opened with two **placeholder** components in Rhino 8, because eleFront is not installed on this machine; those two (`Bake Objects`, `Define Object Attributes`) have since been deleted, and no file in the repo needs eleFront any more. Cross-check the *Addon libs* column against what is actually installed before calling a file loadable.

## Findings

### 1. Hops endpoints are inconsistent — three different addressing styles
- **Published URL** (`compute.echoes.paris/...`) — only `_viz_palettes`, `vm_procedural-forestry`, `urb_massing-typologies`.
- **Absolute local path** into the appserver source tree — `ee_massing-analytics`, `ee_PV`, `ad_shading-typologies`, `viz_bivariate-choropleth`. These only solve on SP's machine; they will not work for anyone cloning the repo.
- **`http://127.0.0.1:5000/<route>`** — the Flask+Hops dev server (`compute - D/py`): `ds_clustering`, `googleAPI`, `viz_seaborn`.

Only the first style matches what the README promises ("running on our servers").

### 2. Stale / broken references
- `viz_seaborn.gh` still points at `https://seaborn-gh.herokuapp.com/histplot` — Heroku free dynos are gone; that endpoint is dead.
- `urb_massing-typologies.gh` uses the **old** repo name `compute.rhino3d.appserver/` while every other file uses `appserver/`.
- Missing referenced clusters (the source `.gh` was not found next to the file): `DBSCAN.gh` (ds_clustering), `ee_periods.gh` + `ee_SUN.gh` (ee_massing-analytics), `secrets.gh` (urb_massing-typologies), `box_plot_example.gh` (viz_seaborn).

### 3. Secrets handling
`vm_procedural-forestry_example.gh` Hops-references `C:\Users\SP\OneDrive - ECHOES\secrets.gh`, and `urb_massing-typologies.gh` embeds a `secrets.gh` cluster. Commit `f462ff1 "removed key"` shows keys have leaked here before. Both should go through `os_key-server.gh` like the other definitions.

### 4. README drift vs. working tree
README documents **Surface Temperatures** (`ee_surface temperature_example.gh`) and links `ee_massing-analytics.gif`, but the working tree has those files deleted and replaced by `ee_massing-analytics_example.gh`. Untracked: `ds_clustering.gh`, `googleAPI.gh`, `viz_seaborn.gh`, `viz_bivariate-choropleth_example.gh`, `_viz_palettes_example.gh` — of these only `ds_clustering.gh` is documented (README + this file). `os_gh-template.gh` is the only file with no remote dependency at all — its group auto-colouring now loads `scripts/gh_template.py` through a path relative to the `.gh`, which is repo-local, not remote.

### 5. Addon surface
12 third-party libraries across the repo. Heaviest consumers are `ds_clustering.gh` (Volvox, HDTTreeUtils, Pufferfish) and `viz_seaborn` (Human UI). Ladybug appears in 4 files. `ee_massing-analytics_example.gh` (4.6 MB, 191 components, 10 Hops calls) is the most complex and the most machine-bound definition in the repo.

## Reproduce

```bash
python "$CLAUDE_PLUGIN_ROOT/skills/gh-graph/analyze.py" <file>.gh --all
```

---

# Clustering definition — state as of 2026-09-16

`ds_clustering.gh` is now the **single** clustering definition: the working definition and the validation harness that used to live in `ds_clustering-advanced_example.gh` were merged into it, and the separate `ds_clustering-advanced_example.gh` and `ds_silhouette clustering_example.gh` files were deleted. `git` is the durable record of what they contained.

**140 objects, 146 wires, 5 Hops components, 0 unresolved components.** It needs the clustering server in `compute - D/py` running on `http://127.0.0.1:5000` (`python app.py`), plus **Hops** and **Ladybug Tools** installed — Ladybug only to open the server-rendered plot image.

| Hops | Pivot | Role |
|---|---|---|
| `/clustering_datasets` | (329, 466) | harness — reference data with ground truth |
| `/dbscan` | (1120, 507) | harness — clusters the reference data |
| `/cluster_score` | (1389, 432) | harness — scores the result against the known answer |
| `/dbscan` | (2060, 1415) | main definition |
| `/kmeans` | (1384, 2367) | main definition |

Positions are component **pivots** (`Attributes.Pivot`), not bounding-box corners.

## Server-side changes this file depends on

The Hops components gained inputs and outputs on 2026-09-16. Everything is **additive** — no existing parameter was renamed, retyped or reordered — so the old wiring survives. New parameters:

| Route | New inputs | New outputs |
|---|---|---|
| `/kmeans` | `ps` (point_scores), `ssn` (silhouette_sample_size) | — |
| `/dbscan` | `Normalize`, `Mode`, `MinClusterSize`, `Xi` | `SuggestedEps` |
| `/cluster_score` | *(new component)* `Labels`, `TrueLabels` | `ARI`, `AMI`, `Homogeneity`, `Completeness`, `VMeasure`, `Report` |
| `/clustering_datasets` | *(new component)* `Dataset`, `NSamples`, `Noise`, `Seed` | `Data`, `TrueLabels`, `NumClustersTrue`, `Points`, `Info` |

**Grasshopper caches remote definitions.** Expiring the solution is *not* enough to pick these up — nor is `HopsComponent.OnRemoteDefinitionChanged()`. Force a re-fetch by clearing the component's path and setting it back:

```python
url = obj.RemoteDefinitionLocation
obj.RemoteDefinitionLocation = ""
obj.RemoteDefinitionLocation = url
```

## The main definition

Two Hops components against a real dataset: **12 branches x 12,662 items**, read as 12,662 points in 12 dimensions. Both are fully driven from canvas controls — `/dbscan` from `Normalize`, `Mode`, `MinClusterSize` and `Xi (optics)`; `/kmeans` from `k_values`, `point_scores` and `silhouette_sample_size`.

Inputs left unwired (`Met`, `Alg`, `LS` on `/dbscan`; `max_iter`, `tol`, `Random_seed`, `normalize`, `initialization`, `n_init`, `verbose` on `/kmeans`) are all `access=item` with persistent defaults, so they satisfy the "every declared input must be present in the request" rule and are ordinary tuning knobs. Unwired **outputs** (`CM` on `/dbscan`; `Inertia_scores`, `Centroids`, `Iterations` on `/kmeans`) are simply unused readouts.

### What the 2026-09-16 rewiring fixed

The DBSCAN half of the definition was **dead**. A complete colour-by-cluster pipeline had been built — `Equality` comparing against `-1`, its `Inequality` output feeding two `Cull Pattern` components, then `Bounds` -> `Gradient` -> `Construct Cloud` — but `Equality.First Number` and `Cull Pattern.List` had no source. Every DBSCAN output dead-ended.

Connecting `Labels` to those two inputs restored the whole chain:

```
Labels (12,662) -> Equality (!= -1) -> Cull Pattern x2 -> 8,208 clustered points
                                    -> Gradient -> Construct Cloud
```

8,208 = 12,662 - 4,454 noise, matching the `NoisePoints` readout. The same fix had to be applied a second time to the copy of this pipeline that arrived with the merged harness file, where it had never been ported.

### Controls added

Three groups, two scribbles, twelve new wires.

- **new DBSCAN controls** — `Normalize` (toggle), `Mode` (value list:
  `dbscan` / `hdbscan` / `optics`), `MinClusterSize` (2..500), `Xi (optics)` (0.01..0.5)
- **KMeans performance** — `point_scores` (toggle), `silhouette_sample_size` (0..5000)
- **DBSCAN readouts** — panels on `SuggestedEps`, `NumClusters`, `NoisePoints`,
  `Silhouette`, `ProcessingTime`; plus a panel on the KMeans `Stats` output

The `Epsilon` slider's minimum was lowered from 0.5 to **0**, because 0 is the sentinel that makes the server use its automatic k-distance suggestion.

### Measured on this dataset

| Setting | Clusters | Noise | Silhouette |
|---|---|---|---|
| `dbscan`, Epsilon 0.5 *(as previously saved)* | 346 | 1,403 | **-0.17** |
| `dbscan`, Epsilon 0 -> auto (1.013), MinSamples 12 | 23 | 510 | -0.14 |
| `hdbscan`, MinClusterSize 100 | 19 | 4,454 | **+0.36** |

The stored `Epsilon = 0.5` was far too tight for 12 dimensions: 346 clusters at a negative silhouette is not a meaningful partition. Automatic epsilon cuts that to 23 clusters, and HDBSCAN — which infers its own density scale and needs no epsilon — is the only setting that reaches a positive silhouette here.

**Epsilon is in z-score units while `Normalize` is on**, not model units.

## The harness

Pick a dataset from the `dataset` value list, pick a mode from `mode`, read `ARI` — Adjusted Rand Index, where 1.0 is perfect agreement with the known answer and 0.0 is chance. The `Epsilon (0 = auto)` slider at 0 uses the server's suggestion.

Eight datasets: `blobs`, `aniso`, `varied`, `moons`, `circles`, `no_structure`, `iris`, `wine`. Measured through the harness:

| Dataset | `dbscan` | `hdbscan` |
|---|---|---|
| blobs | 0.868 | 0.936 |
| moons | 0.967 | **1.000** |
| circles | 0.576 (11 clusters) | **1.000** (2 clusters) |
| iris | 0.550 | 0.564 |

`circles` is the instructive case: automatic epsilon **under-estimates on rings**, because density is near-uniform *along* each ring so the k-distance curve bends early — DBSCAN shatters two rings into about eleven fragments. HDBSCAN recovers both exactly. `iris` sits near 0.55 for everything because two of its three species genuinely overlap; that is the honest ceiling, not a defect.

## Things that look like defects and are not

Each of these was mis-read as a fault during the audit; check here before "fixing" one.

- A `Construct Cloud` with **no recipients is the display endpoint**, not an orphan — a
  point cloud previews from the component itself. `Cloud.N` (normals) unwired is likewise
  normal.
- The locked image cluster is the **plot-display chain**: `/kmeans` `Visualizations` →
  `Deserialize Image from String` → image plane, with `Data Dam` → `LB Open File` to open
  the rendered plot. The `Import Image`-on-a-rectangle half is deliberately disabled — its
  group is named *heavy*. This is why the file depends on Ladybug Tools.
- The `dev` / `prod` value list feeds two string-concat components, **not** any Hops URL —
  Hops stores its endpoint internally and has no input port for it. All five components are
  hardcoded to `http://127.0.0.1:5000`; the switch does not repoint them.
- A Hops component's unwired `item` inputs carry persistent data and are fine. Only an
  unwired **list**-access input breaks a solve (this is why ARI scoring lives in its own
  `/cluster_score` component rather than as a `true_labels` input on `/kmeans`).

## Auditing this file

The offline `gh-graph` parse cannot see placeholder components, pivots or persistent data. For those, open the file headlessly in a running Rhino — this does not touch the canvas:

```python
from Grasshopper.Kernel import GH_DocumentIO
io = GH_DocumentIO(); io.Open(path); doc = io.Document
```

Two components (`Bake Objects`, `Define Object Attributes`) loaded as **placeholders** this way because eleFront is not installed here; they were disconnected and have been deleted. The offline parse had reported them as resolved.

Note a GH document carrying a `FilePath` is **not necessarily on disk** — check `os.path.exists` before trusting a document's path as a backup, and save explicitly with `io.Save()` / `GH_DocumentIO.SaveQuiet`.

## Performance note

Per-point silhouette is O(n^2) and is recomputed for every k value. On the `/kmeans` component, `point_scores = False` plus `silhouette_sample_size = 1000` measured a **10.3x** speedup at n=5000 with the reported silhouette unchanged to four decimal places. Defaults (`point_scores` on, sample size 0) reproduce the previous exact behaviour.
