"""
Loads etymology.db (built by relational_database.py) into Kuzu, an embedded
(file-based, no server/account) graph database with a Cypher-like query
language. Run `python relational_database.py` first to (re)build
etymology.db, then `python load_into_kuzu.py` to (re)build the kuzu_db
directory. Query it afterward with the `kuzu` Python package:

    import kuzu
    db = kuzu.Database("kuzu_db")
    conn = kuzu.Connection(db)
    result = conn.execute("MATCH (w:Word)-[r:DevelopedInto]->(w2:Word) "
                          "WHERE size(r.citations) > 1 RETURN w.word, w2.word")

Unlike the Neo4j export (export_to_neo4j.py), citations do NOT need to be
reified as their own node here: Kuzu supports LIST<STRUCT<...>> as a native
relationship property type (Neo4j only allows flat scalars/arrays of
scalars), so every DEVELOPED_INTO relationship just carries its own
`citations` list directly - no :Etymology workaround needed.

Uses sqlite3 + parameterized queries throughout (no pandas DataFrame
scanning) - as of kuzu 0.11.3, COPY FROM a pandas DataFrame crashes against
pandas 3.0's new default PyArrow-backed string dtype (confirmed locally);
parameterized conn.execute(query, parameters=...) calls sidestep that
entirely and also make nested list/struct properties trivial to pass as
native Python values.
"""

import shutil
import sqlite3

import kuzu

DB_PATH = "kuzu_db"
shutil.rmtree(DB_PATH, ignore_errors=True)

sq = sqlite3.connect("etymology.db")
cur = sq.cursor()

db = kuzu.Database(DB_PATH)
conn = kuzu.Connection(db)

# --- Schema ---
conn.execute("CREATE NODE TABLE Word(word_id INT64, csv_id STRING, word STRING, "
             "meaning STRING, category STRING, PRIMARY KEY(word_id))")
conn.execute("CREATE NODE TABLE Language(word_id INT64, name STRING, PRIMARY KEY(word_id))")
conn.execute("CREATE NODE TABLE Category(category_id INT64, label STRING, PRIMARY KEY(category_id))")
conn.execute("CREATE NODE TABLE Scheme(scheme_id INT64, name STRING, PRIMARY KEY(scheme_id))")
conn.execute("CREATE NODE TABLE Source(source_id INT64, name STRING, full_name STRING, "
             "PRIMARY KEY(source_id))")

conn.execute("""
    CREATE REL TABLE DevelopedInto(
        FROM Word TO Word,
        FROM Language TO Language,
        edge_id INT64,
        is_diachronic BOOLEAN,
        citations STRUCT(source_id INT64, source_name STRING, locus STRING, note STRING)[]
    )
""")
conn.execute("CREATE REL TABLE HasWord(FROM Language TO Word, edge_id INT64)")
conn.execute("CREATE REL TABLE ConnectedTo(FROM Word TO Word, edge_id INT64)")
conn.execute("""
    CREATE REL TABLE ResolvesInto(
        FROM Category TO Category,
        FROM Category TO Scheme,
        category_edge_id INT64,
        scheme_id INT64
    )
""")
conn.execute("CREATE REL TABLE HasCategory(FROM Word TO Category)")

# --- Word / Language nodes ---
word_node_ids = set()
for word_id, node_type, csv_id, word, meaning, category, tags in cur.execute(
    "SELECT word_id, node_type, id, word, meaning, category, tags FROM words"
):
    if node_type == "WORD":
        word_node_ids.add(word_id)
        conn.execute(
            "CREATE (w:Word {word_id: $word_id, csv_id: $csv_id, word: $word, "
            "meaning: $meaning, category: $category})",
            {"word_id": word_id, "csv_id": csv_id, "word": word,
             "meaning": meaning, "category": category},
        )
    else:
        conn.execute("CREATE (l:Language {word_id: $word_id, name: $name})",
                      {"word_id": word_id, "name": word})

# --- Category / Scheme / Source nodes ---
for category_id, label in cur.execute("SELECT category_id, label FROM semantic_categories"):
    conn.execute("CREATE (c:Category {category_id: $id, label: $label})",
                 {"id": category_id, "label": label})
for scheme_id, name in cur.execute("SELECT scheme_id, name FROM semantic_schemes"):
    conn.execute("CREATE (s:Scheme {scheme_id: $id, name: $name})", {"id": scheme_id, "name": name})
for source_id, name, full_name in cur.execute("SELECT source_id, name, full_name FROM sources"):
    conn.execute("CREATE (so:Source {source_id: $id, name: $name, full_name: $full_name})",
                 {"id": source_id, "name": name, "full_name": full_name})

# --- Citations, pre-aggregated per edge_id into the list this relationship
# property expects (one DEVELOPED_INTO edge can carry multiple citations,
# e.g. both Pokorny and LIV citing the same claim). ---
citations_by_edge = {}
for edge_id, source_id, source_name, locus, note in cur.execute(
    "SELECT c.edge_id, c.source_id, s.name, c.locus, c.note "
    "FROM citations c JOIN sources s ON c.source_id = s.source_id"
):
    citations_by_edge.setdefault(edge_id, []).append(
        {"source_id": source_id, "source_name": source_name, "locus": locus, "note": note}
    )

# --- DEVELOPED_INTO (word-to-word and language-to-language) ---
for edge_id, source_word_id, target_word_id, is_diachronic in cur.execute(
    "SELECT edge_id, source_word_id, target_word_id, is_diachronic "
    "FROM edges WHERE relationship_type = 'DEVELOPED_INTO'"
):
    source_label = "Word" if source_word_id in word_node_ids else "Language"
    target_label = "Word" if target_word_id in word_node_ids else "Language"
    conn.execute(
        f"MATCH (a:{source_label} {{word_id: $src}}), (b:{target_label} {{word_id: $tgt}}) "
        f"CREATE (a)-[:DevelopedInto {{edge_id: $edge_id, is_diachronic: $diac, "
        f"citations: $cites}}]->(b)",
        {"src": source_word_id, "tgt": target_word_id, "edge_id": edge_id,
         "diac": bool(is_diachronic) if is_diachronic is not None else None,
         "cites": citations_by_edge.get(edge_id, [])},
    )

# --- HAS_WORD (language -> word) ---
for edge_id, source_word_id, target_word_id in cur.execute(
    "SELECT edge_id, source_word_id, target_word_id FROM edges WHERE relationship_type = 'HAS_WORD'"
):
    conn.execute(
        "MATCH (l:Language {word_id: $src}), (w:Word {word_id: $tgt}) "
        "CREATE (l)-[:HasWord {edge_id: $edge_id}]->(w)",
        {"src": source_word_id, "tgt": target_word_id, "edge_id": edge_id},
    )

# --- CONNECTED_TO (synchronic paradigm siblings; one row per pair, not two) ---
for edge_id, source_word_id, target_word_id in cur.execute(
    "SELECT edge_id, source_word_id, target_word_id FROM edges WHERE relationship_type = 'CONNECTED_TO'"
):
    conn.execute(
        "MATCH (a:Word {word_id: $src}), (b:Word {word_id: $tgt}) "
        "CREATE (a)-[:ConnectedTo {edge_id: $edge_id}]->(b)",
        {"src": source_word_id, "tgt": target_word_id, "edge_id": edge_id},
    )

# --- RESOLVES_INTO (category hierarchy, scheme as an edge property; tier-1
# categories resolve directly into their scheme instead of a parent category) ---
for category_edge_id, child_category_id, parent_category_id, scheme_id in cur.execute(
    "SELECT category_edge_id, child_category_id, parent_category_id, scheme_id FROM category_edges"
):
    if parent_category_id is None:
        conn.execute(
            "MATCH (c:Category {category_id: $child}), (s:Scheme {scheme_id: $scheme}) "
            "CREATE (c)-[:ResolvesInto {category_edge_id: $ce_id, scheme_id: $scheme}]->(s)",
            {"child": child_category_id, "scheme": scheme_id, "ce_id": category_edge_id},
        )
    else:
        conn.execute(
            "MATCH (c:Category {category_id: $child}), (p:Category {category_id: $parent}) "
            "CREATE (c)-[:ResolvesInto {category_edge_id: $ce_id, scheme_id: $scheme}]->(p)",
            {"child": child_category_id, "parent": int(parent_category_id),
             "ce_id": category_edge_id, "scheme": scheme_id},
        )

# --- HAS_CATEGORY (word -> category membership) ---
for word_id, category_id in cur.execute("SELECT word_id, category_id FROM word_categories"):
    conn.execute(
        "MATCH (w:Word {word_id: $word}), (c:Category {category_id: $cat}) "
        "CREATE (w)-[:HasCategory]->(c)",
        {"word": word_id, "cat": category_id},
    )

sq.close()

counts = {
    label: conn.execute(f"MATCH (n:{label}) RETURN count(n)").get_next()[0]
    for label in ("Word", "Language", "Category", "Scheme", "Source")
}
print(f"Loaded into {DB_PATH}/: {counts}")
