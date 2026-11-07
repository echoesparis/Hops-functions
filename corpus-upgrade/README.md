# Corpus upgrade: a synthetic sample

A small corpus of Grasshopper definitions with typical faults, before and after an automated upgrade, by ECHOES.PARIS.

Every file was written by a script. Nothing comes from a project, no file holds a person's name, and every key is made up (`FAKE-KEY-...`): it opens nothing.

```
before/     the corpus as a team might have it: a folder per rule, a file named by what it holds, one fault per file
  modular/    clusters pasted into several definitions
  safe/       a key in a panel, in a pasted cluster, in a script
  readable/   old versions of components
  sound/      a file read where no machine has it, a missing font, Python 2 scripts, retired plugins
  legible/    groups in one colour, heaped canvases
  findable/   definitions with no description
  callable/   a definition Hops can call
  library/    a cluster file and a user object
after/      the same corpus after the upgrade
  library/          each shared cluster made one file, referenced by the definitions
  secrets.txt       the keys moved out of the panels (made up)
  keys-to-rotate.txt  every key found, moved or left
  change-record.*   what was changed in each file, and what was left for a person
_staging/   the two definitions of the sun cluster before it was made a reference
layout/     the canvas positions the layout pass applied
projects.json  each definition of before/, by its path
```

What the upgrade did: shared clusters made one library, old components upgraded, lost files re-pointed, keys moved to `secrets.txt`, missing fonts swapped, descriptions written, groups coloured by role, heaped canvases laid out. What it left on purpose: the edited copy of a cluster, the key in a script, the Python 2 scripts and the plugins.

`after/` names the files it reads relative to itself (`../../before/sound/data/...`, `secrets.txt`), so it names no folder of the machine that made it. Grasshopper reads such a path from Rhino's working folder: set the full path in the File panels to run those definitions.

Paste the link of this folder into [cc.maiastra.xyz](https://cc.maiastra.xyz) to see its audit, before and after.

Licence: [CC BY 4.0](LICENSE).
