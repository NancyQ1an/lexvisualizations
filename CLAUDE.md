# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

A single-file, client-side visualization tool for etymological/lexical trees ("CSV layer graph"). There is no build system, package manager, or test suite — the entire application lives in [index.html](index.html), which loads D3.js and PapaParse from CDNs.

## Running / developing

There is no build step. Open [index.html](index.html) directly in a browser (or serve the directory with any static file server) to run the app. Changes take effect on page reload.

There are no lint or test commands configured for this project.

## Data files

- [multilingual_tree_data.csv](multilingual_tree_data.csv) — a flat etymology dataset (`id, word, parent_id, meaning, category, tags`) used as source data for the relational model below. Not consumed directly by `index.html`.
- [relational_database.py](relational_database.py) — a one-off migration script that normalizes `multilingual_tree_data.csv` into a `words` / `edges` relational schema and writes it to a local SQLite file (`etymology.db`) via pandas. Run with `python relational_database.py` (requires `pandas`). This is exploratory/offline tooling, separate from the browser visualization.

## Architecture of index.html

The app expects two CSV inputs (uploaded via file pickers, or generated from the built-in "Load Sample Dataset" button using the `SAMPLE_NODES_CSV`/`SAMPLE_EDGES_CSV` constants):

- **Nodes CSV**: `id, label, layer, layer_name` — `layer` is a numeric rank used to group nodes into horizontal bands (e.g. language family → language → word → gloss).
- **Edges CSV**: `source, target, type, sources` — `sources` is a semicolon-separated list of citation sources (e.g. `LIV`, `Pokorny`, `Consensus`) used for edge coloring/filtering; `type` distinguishes relationship kinds (e.g. `DERIVED_FROM`, `HAS_MEANING`, `BELONGS_TO`).

Data flow: file input change handlers parse CSVs with PapaParse into `rawNodeRows`/`rawEdgeRows` → `tryBuild()` → `buildAndRender()`, which builds the D3 force simulation, layer bands, and adjacency maps, then calls `render()` on every interaction (click/hover/breadcrumb navigation) to recompute visibility and styling without rebuilding the simulation.

Key concepts to understand before modifying rendering logic:

- **Layers as focus depth, not literal 3D**: nodes are laid out per-layer band (`d3.forceY` pinned to `layerBandY`), but `projectTo3D()` fakes a pseudo-3D depth effect by scaling node/edge positions outward or inward based on `layerIndex - focusIndex` (`zScale`). Despite the name, this is a 2D visual effect (see the "back to 2d" commit history), not a WebGL/three.js scene.
- **Focus/drill-down navigation**: `focusIndex` and `activeParentId` track which layer and parent node the user has drilled into; clicking a node re-centers the view, and `renderBreadcrumb()` reflects the current path. `resetAll()` (triggered by clicking empty canvas) clears this state.
- **Word-inspection tree mode**: clicking a word node sets `selectedInspectedNodeId` and calls `computeTreeLayoutPositions()`, which walks `diachronicAncestors`/`diachronicDescendants` maps (built from `DERIVED_FROM` edges) to lay out a 4-lane pedigree tree (ancestors / node / descendants / meanings) at fixed X positions, overriding the force simulation via `node.treeX`/`node.treeY`.
- **Highlighting vs. visibility are separate passes**: `highlight()` (hover) toggles opacity based on the adjacency map; `render()` (click/state changes) recomputes which nodes/edges are structurally visible for the current focus/inspection state. Both run independently on top of the same DOM selection.
- **Source filtering**: `sources` values are normalized via `SOURCE_NORMALIZATION_MAP` (handles typos/case variants like `picorni` → `Pokorny`) before being matched against the `selectedSources` set driven by the sidebar checkboxes.
