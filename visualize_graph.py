"""
Renders kuzu_db (built by load_into_kuzu.py) as a self-contained,
interactive HTML graph you open directly in a browser - no server, no
account, no Docker, matching this project's existing index.html/tables.html
pattern. Run `python load_into_kuzu.py` first, then:

    python visualize_graph.py

This produces graph_visualization.html. For the full interactive
query-and-visualize experience (type any Cypher, see results rendered live,
closer to Neo4j Browser), Kuzu also ships a web explorer you can run via
Docker instead: `docker run -p 8000:8000 -v <abs path to kuzu_db>:/database
kuzudb/explorer:latest` then open http://localhost:8000 - this script is the
lighter-weight, no-Docker alternative for a quick look.
"""

import kuzu
from pyvis.network import Network

db = kuzu.Database("kuzu_db")
conn = kuzu.Connection(db)

# Same accent colors as index.html's COLOR_PALETTE, so this fits the rest of
# the project visually.
NODE_COLORS = {
    "Word": "#8b7fe8",
    "Language": "#3fc9a0",
    "Category": "#e88a6a",
    "Scheme": "#5fa8e8",
    "Source": "#d46fc9",
}

net = Network(height="900px", width="100%", directed=True, bgcolor="#12141a", font_color="#e8e8ea")
net.barnes_hut(spring_length=120, spring_strength=0.02, damping=0.12)

seen_nodes = set()

# A category's scheme lives on its ResolvesInto edge, not on the category
# node itself - precompute category_id -> scheme name(s) so the *node*
# tooltip can show it too, not just the edge tooltip.
scheme_names_by_category_id = {}
result = conn.execute(
    "MATCH (c:Category)-[rel:ResolvesInto]->(target), (s:Scheme {scheme_id: rel.scheme_id}) "
    "RETURN c.category_id, s.name"
)
while result.has_next():
    category_id, scheme_name = result.get_next()
    scheme_names_by_category_id.setdefault(category_id, []).append(scheme_name)

# A word's citations live on its own incoming DEVELOPED_INTO edge - precompute
# word_id -> source name(s) so the *node* tooltip can show it too. A language
# node's own DEVELOPED_INTO edges (language-to-language lineage) carry no
# citations in this sample data, so aggregate its sources from its member
# words instead (the union of citations across every word tagged with that
# language).
source_names_by_word_id = {}
result = conn.execute("MATCH (a)-[rel:DevelopedInto]->(b:Word) RETURN b.word_id, rel.citations")
while result.has_next():
    word_id, citations = result.get_next()
    if citations:
        source_names_by_word_id[word_id] = [c["source_name"] for c in citations]

source_names_by_language_id = {}
result = conn.execute("MATCH (l:Language)-[:HasWord]->(w:Word) RETURN l.word_id, w.word_id")
while result.has_next():
    language_id, word_id = result.get_next()
    for name in source_names_by_word_id.get(word_id, []):
        source_names_by_language_id.setdefault(language_id, set()).add(name)


def node_key(node):
    return f"{node['_label']}:{node['_id']['offset']}"


def node_label(node):
    label = node["_label"]
    if label == "Word":
        return node["word"]
    if label == "Language":
        return node["name"]
    if label == "Category":
        return node["label"]
    if label == "Scheme":
        return node["name"]
    if label == "Source":
        return node["name"]
    return "?"


def node_title(node):
    label = node["_label"]
    if label == "Word":
        sources = source_names_by_word_id.get(node["word_id"], [])
        return (f"{node['word']} ({node['csv_id']})<br>meaning: {node['meaning']}<br>"
                f"category: {node['category']}<br>sources: {', '.join(sources) if sources else '(none)'}")
    if label == "Language":
        sources = sorted(source_names_by_language_id.get(node["word_id"], []))
        return f"Language: {node['name']}<br>sources (from its words): {', '.join(sources) if sources else '(none)'}"
    if label == "Category":
        schemes = scheme_names_by_category_id.get(node["category_id"], [])
        return f"Category: {node['label']}<br>scheme: {', '.join(schemes) if schemes else '(none)'}"
    if label == "Scheme":
        return f"Scheme: {node['name']}"
    if label == "Source":
        return f"Source: {node['name']} ({node['full_name']})"
    return ""


def add_node(node):
    key = node_key(node)
    if key not in seen_nodes:
        seen_nodes.add(key)
        label = node["_label"]
        # Structured (not just hover-text) properties, so the in-page filter
        # UI (added below) can filter on real data instead of parsing the
        # title's HTML string.
        extra = {}
        if label == "Word":
            extra["sources"] = source_names_by_word_id.get(node["word_id"], [])
        elif label == "Language":
            extra["sources"] = sorted(source_names_by_language_id.get(node["word_id"], []))
        elif label == "Category":
            extra["scheme"] = ", ".join(scheme_names_by_category_id.get(node["category_id"], []))
        net.add_node(key, label=node_label(node), title=node_title(node),
                     color=NODE_COLORS.get(label, "#888"), **extra)
    return key


# Add every node up front, even ones no edge happens to point at - e.g. the
# Swadesh List scheme, which tier-2 categories reference only via the
# scheme_id *edge property*, never as an edge target (their actual edge
# connects to their tier-1 parent category, whose own edge points at Buck's
# Schema instead). Without this, such nodes would silently vanish.
for label in ("Word", "Language", "Category", "Scheme", "Source"):
    result = conn.execute(f"MATCH (n:{label}) RETURN n")
    while result.has_next():
        (n,) = result.get_next()
        add_node(n)

# --- DEVELOPED_INTO: word-to-word and language-to-language lineage ---
result = conn.execute(
    "MATCH (a)-[rel:DevelopedInto]->(b) "
    "RETURN a, b, rel.is_diachronic, rel.citations"
)
while result.has_next():
    a, b, is_diachronic, citations = result.get_next()
    title = f"DEVELOPED_INTO (diachronic: {is_diachronic})"
    for cite in citations:
        title += f"<br>&bull; {cite['source_name']}: {cite['locus']}"
    net.add_edge(add_node(a), add_node(b), label="DEVELOPED_INTO", title=title,
                 color="#8a8d98", sources=[c["source_name"] for c in citations])

# --- HAS_WORD: language -> word; sources are the target word's own
# citations (citations attach to DEVELOPED_INTO edges, not to HAS_WORD
# directly, so this reuses source_names_by_word_id rather than new data). ---
result = conn.execute("MATCH (l:Language)-[:HasWord]->(w:Word) RETURN l, w")
while result.has_next():
    l, w = result.get_next()
    sources = source_names_by_word_id.get(w["word_id"], [])
    net.add_edge(add_node(l), add_node(w), label="HAS_WORD", color="#3fc9a0",
                 title=f"HAS_WORD<br>sources: {', '.join(sources) if sources else '(none)'}",
                 sources=sources)

# --- CONNECTED_TO: synchronic paradigm siblings (undirected convention - no
# arrow). No citation attaches to this relationship type in our schema
# (citations attest to DEVELOPED_INTO lineage claims specifically), so the
# tooltip says so explicitly rather than just being blank. ---
result = conn.execute("MATCH (a:Word)-[:ConnectedTo]->(b:Word) RETURN a, b")
while result.has_next():
    a, b = result.get_next()
    net.add_edge(add_node(a), add_node(b), label="CONNECTED_TO", color="#e85f7f", arrows="",
                 title="CONNECTED_TO<br>sources: (not tracked for this relationship type)")

# --- RESOLVES_INTO: category hierarchy, scheme as an edge property ---
result = conn.execute(
    "MATCH (c:Category)-[rel:ResolvesInto]->(target), (s:Scheme {scheme_id: rel.scheme_id}) "
    "RETURN c, target, s.name"
)
while result.has_next():
    c, target, scheme_name = result.get_next()
    net.add_edge(add_node(c), add_node(target), label="RESOLVES_INTO",
                 title=f"scheme: {scheme_name}", color="#e88a6a", scheme=scheme_name)

# --- HAS_CATEGORY: word -> category membership. No citation attaches to
# this relationship type either (plain membership, not an etymological
# claim). ---
result = conn.execute("MATCH (w:Word)-[:HasCategory]->(c:Category) RETURN w, c")
while result.has_next():
    w, c = result.get_next()
    net.add_edge(add_node(w), add_node(c), label="HAS_CATEGORY", color="#5fa8e8",
                 title="HAS_CATEGORY<br>sources: (not tracked for this relationship type)")

net.write_html("graph_visualization.html")

# --- In-page filter panel (checkboxes), so filtering by source/scheme is a
# click instead of writing a separate Python/Cypher script every time.
# Reads the structured `sources`/`scheme` properties set above via
# nodes.update()/edges.update() on the already-rendered vis.js DataSets -
# pyvis's drawGraph() runs synchronously at the bottom of its own <script>
# tag (not deferred to window.onload), so by the time this appended script
# runs, the global `nodes`/`edges` variables it created are already populated.
source_names = []
result = conn.execute("MATCH (s:Source) RETURN s.name ORDER BY s.name")
while result.has_next():
    (name,) = result.get_next()
    source_names.append(name)

scheme_names = []
result = conn.execute("MATCH (s:Scheme) RETURN s.name ORDER BY s.name")
while result.has_next():
    (name,) = result.get_next()
    scheme_names.append(name)

source_checkboxes = "".join(
    f'<label style="display:block;"><input type="checkbox" class="source-filter" value="{name}"> {name}</label>'
    for name in source_names
)
scheme_checkboxes = "".join(
    f'<label style="display:block;"><input type="checkbox" class="scheme-filter" value="{name}"> {name}</label>'
    for name in scheme_names
)

filter_panel_html = f"""
<div id="filter-panel" style="position:fixed; top:10px; right:10px; z-index:1000;
     background:#1a1d25; border:1px solid #2a2e38; border-radius:8px; padding:12px;
     font-family:sans-serif; font-size:12px; color:#e8e8ea; max-width:220px;">
  <div style="font-weight:600; margin-bottom:6px;">Filter by source</div>
  {source_checkboxes}
  <div style="font-weight:600; margin:10px 0 6px;">Filter by scheme</div>
  {scheme_checkboxes}
  <button id="reset-filters" style="margin-top:10px; width:100%; cursor:pointer;">Reset</button>
</div>
<script>
(function(){{
  function selectedValues(cls){{
    return Array.from(document.querySelectorAll('.' + cls + ':checked')).map(function(el){{ return el.value; }});
  }}
  function applyFilters(){{
    var selectedSources = selectedValues('source-filter');
    var selectedSchemes = selectedValues('scheme-filter');

    function isHidden(item){{
      var hidden = false;
      if (selectedSources.length && item.sources !== undefined) {{
        hidden = !item.sources.some(function(s){{ return selectedSources.indexOf(s) !== -1; }});
      }}
      if (!hidden && selectedSchemes.length && item.scheme !== undefined) {{
        hidden = selectedSchemes.indexOf(item.scheme) === -1;
      }}
      return hidden;
    }}

    var edgeUpdates = [];
    edges.forEach(function(edge){{ edgeUpdates.push({{id: edge.id, hidden: isHidden(edge)}}); }});
    edges.update(edgeUpdates);

    var nodeUpdates = [];
    nodes.forEach(function(node){{ nodeUpdates.push({{id: node.id, hidden: isHidden(node)}}); }});
    nodes.update(nodeUpdates);
  }}
  document.querySelectorAll('.source-filter, .scheme-filter').forEach(function(el){{
    el.addEventListener('change', applyFilters);
  }});
  document.getElementById('reset-filters').addEventListener('click', function(){{
    document.querySelectorAll('.source-filter, .scheme-filter').forEach(function(el){{ el.checked = false; }});
    applyFilters();
  }});
}})();
</script>
"""

with open("graph_visualization.html", "r", encoding="utf-8") as f:
    html = f.read()
html = html.replace("</body>", filter_panel_html + "</body>")
with open("graph_visualization.html", "w", encoding="utf-8") as f:
    f.write(html)

print(f"Wrote graph_visualization.html ({len(seen_nodes)} nodes)")
