# Grasshopper

## Scripts

Grasshopper definitions

### Template

Auto-color groups based on prefix  

The logic lives in [`scripts/gh_template.py`](scripts/gh_template.py), loaded by the
`AC` Python 3 Script component in *input is path* + *Synchronize* mode: edit the `.py`
and the canvas re-solves on save. The path panel is relative to the `.gh`, so the
definition stays portable.  

Twelve categories, built into the script (`DEFAULT_SCHEMA`), in dataflow order -
colours are ColorBrewer Set3 assigned by meaning, so families read at a glance:  

| | | | |
|---|---|---|---|
| `c_` control | `gi_` GH input | `ri_` rhino input | `ei_` external input |
| `k_` keys | `h_` remote | `f_` function | `o_` output |
| `v_` viz | `ui_` UI | `t_` temp | `d_` dead |

Name a group `f_solar` and it turns blue and renames itself to `solar`. While the
component is previewed, the same schema is drawn as a key in the top-left of the
Rhino viewport, with a live count of the groups carrying each category (counted by
colour, since a coloured group has lost its prefix). Toggle the component preview to
show or hide it.  

Schema rows are CSV, `prefix,#rrggbb,"label: description"`:  

```
c_,#fdb462,"control: switches, toggles, gates"
gi_,#b3de69,"GH input: sliders and values you author here"
```

Only `prefix` is required. The `schema` output emits the schema in force in exactly
that form, so it round-trips: wire it to a Panel, edit, feed it back into `cs`.
Unwire `cs` to fall back to the built-in set.  

Port names and tooltips are written from the `.py` (`DESCRIPTION` / `DOC_IN` /
`DOC_OUT` + `annotate()`), never by hand on the canvas.  

The definition itself is the worked example: a floor-plate stacker that uses all twelve
categories for real — sliders (`gi_`) and a referenced point (`ri_`) drive a stack of
plates (`f_`), coloured by level (`v_`); a repo-relative CSV of floor uses is resolved and
read (`ei_`), a key path is carried but never committed (`k_`), the compute server is
health-checked (`h_`), a toggle (`c_`) gates writing the schedule to disk (`o_`), with a
mode list and readout (`ui_`), a scratch total (`t_`) and one locked leftover (`d_`).
Nothing outside core Grasshopper is required.  

![](https://github.com/echoesparis/scripts/blob/main/img/os_gh-template.gif)



## Remote functions

Using the [Hops component](https://developer.rhino3d.com/guides/compute/hops-component/) and running on our servers. 

Get in touch to get your key 

### Massing Typologies

Parametric urban typologies

![](https://github.com/echoesparis/scripts/blob/main/img/urb_massing-typologies.gif)

### Massing Analytics

Indicators for Bioclimatic Urban Design 

![](https://github.com/echoesparis/scripts/blob/main/img/ee_massing-analytics.gif)

### Procedural Urban Forestry

Parametric placement of trees in urban context 

![](https://github.com/echoesparis/Grasshopper-scripts/blob/main/img/vm_procedural-forestry_example.gif)

### Surface Temperatures

Computation of surface temperatures, adaptation of [Elioth’s ICE tool](https://github.com/Art-Ev/ICEtool) 

![](https://github.com/echoesparis/scripts/blob/main/img/ee_surface%20temperature_example.gif)

### Photovoltaics

Optimize the placement of solar PV systems

![](https://github.com/echoesparis/scripts/blob/main/img/ee_pv.jpg)

### Shading Typologies

Parametric shading strategies 

![](https://github.com/echoesparis/Grasshopper-scripts/blob/main/img/ad_shading-T1.gif)

### Clustering

One definition, `ds_clustering.gh`, covering both families:

**K-Means with silhouette coefficients** — sweep a range of `k`, read the silhouette per
value, pick the best. `point_scores` off plus a `silhouette_sample_size` around 1000 makes
the sweep roughly 10x faster on a few thousand points, without moving the reported score.

![](https://github.com/echoesparis/Grasshopper-scripts/blob/main/img/ds_kmeans-silhouette-clustering.jpg)

**Density clustering** — DBSCAN, HDBSCAN and OPTICS behind one component, for data where
the number of clusters is not known in advance and the shapes are not round. Set `Epsilon`
to 0 and the server estimates it from the knee of the k-distance curve; switch `Mode` to
`hdbscan` when density varies between clusters and there is no single radius that suits all
of them. Note `Epsilon` is expressed in standard deviations, not model units, while
`Normalize` is on.

The same file also carries a **validation harness** — eight reference datasets with known
answers (`blobs`, `moons`, `circles`, `iris`, …), scored by Adjusted Rand Index — so you can
check a setting against ground truth before trusting it on your own data.

Needs the clustering server in `compute - D/py` running locally
(`python app.py`, `http://127.0.0.1:5000`), plus **Hops** and **Ladybug Tools** installed —
Ladybug only for opening the server-rendered plot image. Full notes in
[`docs/gh-definitions.md`](docs/gh-definitions.md).
