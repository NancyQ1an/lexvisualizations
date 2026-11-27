# lexvisualizations

A toy etymological dataset (Proto-Indo-European roots → descendant word forms across Greek, Latin, Spanish, Old High German, German, Tocharian, and English) used to prototype a few different ways of representing and querying the same linguistic relationships: a hand-built D3 force-graph, a normalized relational schema, and an embedded graph database.

## What's here

- **`index.html`** — a standalone D3.js visualization of the etymological word tree (languages → words → meanings), with focus/drill-down navigation and citation-source filtering. Open directly in a browser.
- **`tables.html`** — a standalone browser page: upload the flat CSV (or load the sample) and see the same relational schema (words, edges, categories, schemes, sources, citations) rendered as HTML tables — no Python/server needed.
- **`multilingual_tree_data.csv`** — the source dataset, including a few curated suppletive word paradigms (e.g. English "to be": am/is/are, was/were, be/been, each from a *different* PIE root) to test synchronic-vs-diachronic relationships.
- **`relational_database.py`** — normalizes the CSV into an 8-table relational schema (SQLite): words, typed edges (`DEVELOPED_INTO`, `HAS_WORD`, `CONNECTED_TO`), semantic category hierarchy, classification schemes, and sources/citations.
- **`load_into_kuzu.py`** / **`visualize_graph.py`** — load that relational schema into [Kùzu](https://kuzudb.com) (an embedded, file-based graph database) and render it as an interactive, filterable HTML graph.
- **`export_to_neo4j.py`** — an alternate path that exports the same data as a Cypher script for Neo4j.

See [`CLAUDE.md`](CLAUDE.md) for the full schema documentation and design rationale behind each table and relationship type.

## Quickstart

### View the word-tree visualization
Open `index.html` in a browser, click "Load Sample Dataset."

### View the relational tables
Open `tables.html` in a browser, click "Load Sample Dataset."

### Build and explore the graph database
```
pip install pandas kuzu pyvis
python relational_database.py   # CSV -> relational SQLite (etymology.db)
python load_into_kuzu.py        # relational SQLite -> embedded graph (kuzu_db)
python visualize_graph.py       # graph -> interactive HTML (graph_visualization.html)
```
Then open `graph_visualization.html` in a browser: drag/zoom the graph, hover any node or edge for details, and use the filter panel (top-right) to filter by citation source (LIV/Pokorny/OED) or classification scheme (Buck's/Swadesh/Concepticon).
