# Parallels Snapshotter

Snapshots of parallels per command line; quick create by template


## Installation

```bash
pip3 install prlsnapshotter
```

Create a template parallel machine. Then make a shortcut for it:

```bash
prl-snap -t <template-machine> -p <machine_prefix> shortcut <path>
prl-snap -t postgres_template -p postgres_ shortcut pgsnap
```