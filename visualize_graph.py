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
    return "?"


def node_title(node):
    label = node["_label"]
    if label == "Word":
        sources = source_names_by_word_id.get(node["word_id"], [])
        doubtful_note = "<br><i>Pokorny treats membership as doubtful</i>" if node.get("is_doubtful") else ""
        return (f"{node['word']} ({node['csv_id']})<br>meaning: {node['meaning']}<br>"
                f"category: {node['category']}<br>sources: {', '.join(sources) if sources else '(none)'}"
                f"{doubtful_note}")
    if label == "Language":
        sources = sorted(source_names_by_language_id.get(node["word_id"], []))
        return f"Language: {node['name']}<br>sources (from its words): {', '.join(sources) if sources else '(none)'}"
    if label == "Category":
        schemes = scheme_names_by_category_id.get(node["category_id"], [])
        return f"Category: {node['label']}<br>scheme: {', '.join(schemes) if schemes else '(none)'}"
    if label == "Scheme":
        return f"Scheme: {node['name']}"
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
            if node.get("is_doubtful"):
                # Dashed border, not a different color, so doubtful words are
                # visually distinct while staying recognizably Word-purple.
                extra["shapeProperties"] = {"borderDashes": True}
        elif label == "Language":
            extra["sources"] = sorted(source_names_by_language_id.get(node["word_id"], []))
        elif label == "Category":
            extra["scheme"] = ", ".join(scheme_names_by_category_id.get(node["category_id"], []))
        elif label == "Scheme":
            # A Scheme node is itself "of" its own scheme, so the scheme
            # filter hides unselected Scheme nodes too, not just the
            # categories pointing at them - without this, picking one scheme
            # left every Scheme node (including unselected ones) visible
            # regardless, which is the inconsistency that prompted this fix.
            extra["scheme"] = node["name"]
        net.add_node(key, label=node_label(node), title=node_title(node),
                     color=NODE_COLORS.get(label, "#888"), **extra)
    return key


# Add every node up front, even ones no edge happens to point at - e.g. the
# Swadesh List scheme, which tier-2 categories reference only via the
# scheme_id *edge property*, never as an edge target (their actual edge
# connects to their tier-1 parent category, whose own edge points at Buck's
# Schema instead). Without this, such nodes would silently vanish.
for label in ("Word", "Language", "Category", "Scheme"):
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
# Source names come from inside the citations lists (no :Source node exists
# to query directly - see the note above the DevelopedInto schema in
# load_into_kuzu.py).
source_names = set()
result = conn.execute("MATCH ()-[rel:DevelopedInto]->() RETURN rel.citations")
while result.has_next():
    (citations,) = result.get_next()
    for cite in citations:
        source_names.add(cite["source_name"])
source_names = sorted(source_names)

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
<div id="search-panel" style="position:fixed; top:10px; left:10px; z-index:1000;
     background:#1a1d25; border:1px solid #2a2e38; border-radius:8px; padding:12px;
     font-family:sans-serif; font-size:12px; color:#e8e8ea; width:240px;">
  <div style="font-weight:600; margin-bottom:6px;">Search</div>
  <input id="search-box" type="text" placeholder="word, meaning, language..."
         style="width:100%; box-sizing:border-box; padding:6px; border-radius:4px;
                border:1px solid #2a2e38; background:#12141a; color:#e8e8ea;">
  <div id="search-status" style="margin-top:6px; color:#8a8d98;"></div>
  <button id="reset-view" style="margin-top:10px; width:100%; cursor:pointer;">Reset view</button>
</div>
<div id="inspector-panel" style="position:fixed; bottom:10px; left:10px; z-index:1000;
     background:#1a1d25; border:1px solid #2a2e38; border-radius:8px; padding:12px;
     font-family:sans-serif; font-size:12px; color:#e8e8ea; width:280px; max-height:320px;
     overflow-y:auto; display:none;">
  <div id="inspector-title" style="font-weight:600; margin-bottom:6px;"></div>
  <div id="inspector-hint" style="color:#8a8d98; margin-bottom:6px;">Click an edge below to isolate just that relationship.</div>
  <div id="inspector-edges"></div>
</div>
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
  // Freeze the force layout once it settles instead of letting vis-network
  // keep recalculating physics for all 344 nodes on every frame - that
  // continuous recalculation is what was causing the zoom/pan lag, since it
  // competes with rendering during interaction. Dragging a node still
  // re-enables physics briefly to resettle, which is the normal vis-network
  // behavior and fine at this graph size.
  network.once("stabilizationIterationsDone", function(){{
    network.setOptions({{ physics: false }});
  }});

  // Search's highlight: fades non-matches (doesn't hide them) since a
  // search can match many nodes at once and context around them is still
  // useful - a different intent, and a cheaper operation, than the
  // inspector's expandFocus below, which fully hides whatever isn't
  // (yet) part of the focused set and can afford to be much more
  // aggressive.
  function highlightMatches(nodeIds){{
    var nodeSet = new Set(nodeIds || []);
    var highlighting = nodeSet.size > 0;

    var nodeUpdates = [];
    nodes.forEach(function(node){{
      nodeUpdates.push({{id: node.id, opacity: highlighting ? (nodeSet.has(node.id) ? 1 : 0.1) : 1}});
    }});
    nodes.update(nodeUpdates);

    var edgeUpdates = [];
    edges.forEach(function(edge){{
      var touches = nodeSet.has(edge.from) || nodeSet.has(edge.to);
      edgeUpdates.push({{id: edge.id, opacity: highlighting ? (touches ? 1 : 0.05) : 1}});
    }});
    edges.update(edgeUpdates);
  }}

  var searchBox = document.getElementById("search-box");
  var searchStatus = document.getElementById("search-status");
  searchBox.addEventListener("input", function(){{
    var query = searchBox.value.trim().toLowerCase();
    var matchIds = [];
    if (query){{
      nodes.forEach(function(node){{
        var haystack = (String(node.label || "") + " " + String(node.title || "")).toLowerCase();
        if (haystack.indexOf(query) !== -1) matchIds.push(node.id);
      }});
    }}
    highlightMatches(matchIds);
    if (!query) {{ searchStatus.textContent = ""; return; }}
    if (matchIds.length){{
      network.fit({{nodes: matchIds, animation: {{duration: 400}}}});
      searchStatus.textContent = matchIds.length + " match" + (matchIds.length === 1 ? "" : "es");
    }} else {{
      searchStatus.textContent = "no matches";
    }}
  }});

  // Inspector focus: fully HIDES everything except the chosen node pair and
  // edge (no faded noise at all, unlike search), then briefly re-enables
  // physics so just the visible subset - hidden nodes don't participate in
  // physics, so this stays cheap regardless of total graph size - settles
  // into a tidy close cluster instead of staying wherever it happened to
  // land in the full layout, before freezing again.
  //
  // expandFocus() is additive (unions with whatever's already focused)
  // rather than replacing it, so clicking outward from a node you just
  // expanded into keeps the earlier trail visible instead of discarding it -
  // you can keep drilling through node after node and build up a connected
  // exploration subgraph. resetFocus() is the only thing that clears it,
  // un-hiding everything; since hidden nodes don't move, the full graph
  // reappears exactly as it was, no re-stabilization needed.
  var focused = false;
  var focusedNodeIds = new Set();
  var focusedEdgeIds = new Set();

  // lastExpandTime guards against a stray click landing on empty canvas
  // right after an expand (the view re-clusters and re-zooms, so a node's
  // dot can end up smaller or slightly moved - a click during or just after
  // that transition can miss it and fall through to the "background click"
  // branch below, which would otherwise wipe out everything you just built
  // up). Background clicks are ignored for a short window after any expand.
  var lastExpandTime = 0;
  function expandFocus(nodeIds, edgeIds){{
    // Only nodes newly entering the focus this call get to move - anything
    // already focused (including anything you've directly clicked, pinned
    // below) is fixed in place first, so expanding further never drags the
    // existing cluster around. That's what was causing "drift": every
    // expand re-ran physics across the *whole* visible set, not just the
    // new part.
    var newNodeIds = nodeIds.filter(function(id){{ return !focusedNodeIds.has(id); }});

    nodeIds.forEach(function(id){{ focusedNodeIds.add(id); }});
    edgeIds.forEach(function(id){{ focusedEdgeIds.add(id); }});
    focused = true;
    lastExpandTime = Date.now();

    var newNodeSet = new Set(newNodeIds);
    var nodeUpdates = [];
    nodes.forEach(function(node){{
      var isFocused = focusedNodeIds.has(node.id);
      var update = {{ id: node.id, hidden: !isFocused }};
      if (isFocused) update.fixed = {{ x: !newNodeSet.has(node.id), y: !newNodeSet.has(node.id) }};
      nodeUpdates.push(update);
    }});
    nodes.update(nodeUpdates);

    var edgeUpdates = [];
    edges.forEach(function(edge){{ edgeUpdates.push({{id: edge.id, hidden: !focusedEdgeIds.has(edge.id)}}); }});
    edges.update(edgeUpdates);

    if (!newNodeIds.length){{
      network.fit({{nodes: Array.from(focusedNodeIds), animation: {{duration: 300}}}});
      return;
    }}
    network.setOptions({{ physics: true }});
    network.once("stabilizationIterationsDone", function(){{
      network.setOptions({{ physics: false }});
      network.fit({{nodes: Array.from(focusedNodeIds), animation: {{duration: 300}}}});
      lastExpandTime = Date.now();
    }});
  }}
  function resetFocus(){{
    if (!focused) return;
    focused = false;
    focusedNodeIds.clear();
    focusedEdgeIds.clear();
    nodes.update(nodes.getIds().map(function(id){{ return {{id: id, hidden: false, fixed: {{x: false, y: false}}}}; }}));
    edges.update(edges.getIds().map(function(id){{ return {{id: id, hidden: false}}; }}));
    network.setOptions({{ physics: false }});
  }}

  // Explicit reset button - a reliable alternative to clicking empty
  // canvas, which requires precisely missing every node/edge and can be
  // fiddly once the view is zoomed into a small cluster.
  document.getElementById("reset-view").addEventListener("click", function(){{
    resetFocus();
    highlightMatches([]);
    document.getElementById("search-box").value = "";
    document.getElementById("search-status").textContent = "";
    document.getElementById("inspector-panel").style.display = "none";
  }});

  // Node/edge inspector: click a node to list every edge touching it,
  // grouped by (direction + relationship_type) - a high-degree node like a
  // category can have hundreds of HAS_CATEGORY edges (every word in that
  // category is its own row in word_categories, which is correct data, just
  // too many to usefully list one-by-one). Each group header shows the
  // count; clicking the header text expands that whole group immediately,
  // small groups (<=6) also list individual members you can click the same
  // way. Checkboxes let you pick several groups/items first and expand them
  // all together in one "Focus selected" action, instead of one at a time.
  var inspectorPanel = document.getElementById("inspector-panel");
  var inspectorTitle = document.getElementById("inspector-title");
  var inspectorEdges = document.getElementById("inspector-edges");

  function showInspector(nodeId){{
    var node = nodes.get(nodeId);
    inspectorTitle.textContent = node.label;
    inspectorEdges.innerHTML = "";

    var groups = new Map();
    edges.get().filter(function(e){{ return e.from === nodeId || e.to === nodeId; }}).forEach(function(e){{
      var outgoing = e.from === nodeId;
      var key = (outgoing ? "out" : "in") + "|" + e.label;
      if (!groups.has(key)) groups.set(key, {{ outgoing: outgoing, type: e.label, items: [] }});
      groups.get(key).items.push(e);
    }});

    var selections = []; // {{checkbox, nodeIds, edgeIds}}

    function addRow(container, checkboxNodeIds, checkboxEdgeIds, labelText, onLabelClick, indent){{
      var row = document.createElement("div");
      row.style.cssText = "display:flex; align-items:center; gap:6px; padding:" +
        (indent ? "2px 0 2px 14px" : "4px 0") + "; border-bottom:" + (indent ? "none" : "1px solid #2a2e38") + ";";
      var checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      selections.push({{ checkbox: checkbox, nodeIds: checkboxNodeIds, edgeIds: checkboxEdgeIds }});
      var label = document.createElement("span");
      label.style.cssText = "cursor:pointer; flex:1;" + (indent ? " color:#8a8d98;" : " font-weight:600;");
      label.textContent = labelText;
      label.title = "Click to expand just this";
      label.addEventListener("click", function(ev){{ ev.stopPropagation(); onLabelClick(); }});
      row.appendChild(checkbox);
      row.appendChild(label);
      container.appendChild(row);
    }}

    groups.forEach(function(group){{
      var otherIds = group.items.map(function(e){{ return group.outgoing ? e.to : e.from; }});
      var edgeIds = group.items.map(function(e){{ return e.id; }});
      var headerText = (group.outgoing ? "-> " : "<- ") + group.type + "  (" + group.items.length + ")";
      addRow(inspectorEdges, [nodeId].concat(otherIds), edgeIds, headerText, function(){{
        expandFocus([nodeId].concat(otherIds), edgeIds);
      }}, false);

      if (group.items.length <= 6){{
        group.items.forEach(function(e){{
          var otherId = group.outgoing ? e.to : e.from;
          var other = nodes.get(otherId);
          addRow(inspectorEdges, [nodeId, otherId], [e.id], other.label, function(){{
            expandFocus([nodeId, otherId], [e.id]);
          }}, true);
        }});
      }}
    }});

    var focusSelectedBtn = document.createElement("button");
    focusSelectedBtn.textContent = "Focus selected";
    focusSelectedBtn.style.cssText = "margin-top:8px; width:100%; cursor:pointer;";
    focusSelectedBtn.addEventListener("click", function(){{
      var nodeIdSet = new Set([nodeId]);
      var edgeIdSet = new Set();
      var any = false;
      selections.forEach(function(sel){{
        if (sel.checkbox.checked){{
          any = true;
          sel.nodeIds.forEach(function(id){{ nodeIdSet.add(id); }});
          sel.edgeIds.forEach(function(id){{ edgeIdSet.add(id); }});
        }}
      }});
      if (any) expandFocus(Array.from(nodeIdSet), Array.from(edgeIdSet));
    }});
    inspectorEdges.appendChild(focusSelectedBtn);

    inspectorPanel.style.display = "block";
  }}

  network.on("click", function(params){{
    if (params.nodes.length === 1){{
      // Freeze on press: any node you click is pinned immediately, on top
      // of expandFocus's own pinning of previously-focused nodes - so even
      // a node you're just inspecting (not yet expanding into) stops
      // drifting the moment you press it.
      nodes.update({{id: params.nodes[0], fixed: {{x: true, y: true}}}});
      showInspector(params.nodes[0]);
    }} else if (params.nodes.length === 0 && params.edges.length === 1){{
      var e = edges.get(params.edges[0]);
      expandFocus([e.from, e.to], [e.id]);
      inspectorPanel.style.display = "none";
    }} else if (params.nodes.length === 0 && params.edges.length === 0){{
      if (Date.now() - lastExpandTime < 600) return; // see lastExpandTime comment above
      resetFocus();
      highlightMatches([]);
      inspectorPanel.style.display = "none";
    }}
  }});

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
