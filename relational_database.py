import pandas as pd
import sqlite3

# 1. Load your existing flat dataset
# CSV columns: id, word, parent_id, meaning, category, tags
df = pd.read_csv("multilingual_tree_data.csv")

# 2. Build the Words table: one entity row per unique id (node_type=WORD),
# plus synthetic entity rows for each distinct language (tags). Semantic
# categories are not baked in here - they live in their own self-referential
# table (step 3) instead.
words_df = df[["id", "word", "meaning", "category", "tags"]].drop_duplicates().reset_index(drop=True)
words_df["node_type"] = "WORD"

languages_df = pd.DataFrame({"word": sorted(df["tags"].dropna().unique())})
languages_df["node_type"] = "LANGUAGE"

words_df = pd.concat([words_df, languages_df], ignore_index=True)
words_df["word_id"] = words_df.index + 1
words_df = words_df[["word_id", "node_type", "id", "word", "meaning", "category", "tags"]]

word_id_by_csv_id = dict(zip(df["id"], words_df.loc[words_df["node_type"] == "WORD", "word_id"]))
tags_by_csv_id = dict(zip(df["id"], df["tags"]))
language_word_id = dict(zip(
    words_df.loc[words_df["node_type"] == "LANGUAGE", "word"],
    words_df.loc[words_df["node_type"] == "LANGUAGE", "word_id"],
))

# 3. Semantic schemes: the classification system a semantic category belongs
# to. Three schemes are included so the scheme_id relation is actually
# exercised rather than always pointing at the same row - names are
# approximate labels (not verified against the real published schemes),
# and the assignment below (which category goes to which scheme) is
# illustrative for testing, not a scholarly mapping - placeholder until the
# professor confirms the exact tagging-scheme/tag entity shape.
semantic_schemes_df = pd.DataFrame([
    {"scheme_id": 1, "name": "Buck's Schema (approximate)"},
    {"scheme_id": 2, "name": "Swadesh List (approximate)"},
    {"scheme_id": 3, "name": "Concepticon (approximate)"},
])
BUCKS_SCHEME_ID = 1
SWADESH_SCHEME_ID = 2
CONCEPTICON_SCHEME_ID = 3

# 4. Semantic categories: a self-referential table (arbitrary depth) rather
# than baking a fixed CATEGORY/SUBCATEGORY pair into the words table. Tier 1
# is the broad category (e.g. Nature); tier 2 is each root-level concept's
# meaning (e.g. "wing / feather"). The category row itself carries no scheme
# information - which scheme classifies a category is a property of the
# RESOLVES_INTO edge between two category nodes (step 5), not of the
# category node, since the same category could in principle be nested
# differently under different schemes.
categories = []
category_id_by_label = {}
for label in sorted(df["category"].dropna().unique()):
    category_id = len(categories) + 1
    category_id_by_label[label] = category_id
    categories.append({"category_id": category_id, "label": label})

root_ids = set(df.loc[df["parent_id"].isna(), "id"])
root_concepts = df[df["parent_id"].isin(root_ids)]
subcategory_id_by_meaning = {}
for row in root_concepts.drop_duplicates(subset=["meaning", "category"]).itertuples():
    category_id = len(categories) + 1
    subcategory_id_by_meaning[row.meaning] = category_id
    categories.append({"category_id": category_id, "label": row.meaning})
semantic_categories_df = pd.DataFrame(categories)

# 5. category_edges: the RESOLVES_INTO hierarchy between category nodes,
# with scheme_id as an edge property (not a column on the category itself -
# see step 4). Tier-1 categories have no parent category, so their edge's
# parent_category_id is null and it resolves directly into the scheme
# instead - the scheme acts as the implicit root of its own category tree.
# Assigned to Buck's Schema for tier 1, except "Grammar" (a function-word
# grouping that doesn't fit a semantic-field scheme) which resolves into
# Concepticon instead, illustrating why more than one scheme is useful.
# Tier 2 resolves into the Swadesh List, since that scheme is specifically a
# list of basic/core concepts rather than broad fields.
category_edges = []
for label, category_id in category_id_by_label.items():
    category_edges.append({
        "category_edge_id": len(category_edges) + 1,
        "child_category_id": category_id,
        "parent_category_id": None,
        "relationship_type": "RESOLVES_INTO",
        "scheme_id": CONCEPTICON_SCHEME_ID if label == "Grammar" else BUCKS_SCHEME_ID,
    })
for meaning, category_id in subcategory_id_by_meaning.items():
    parent_label = root_concepts.loc[root_concepts["meaning"] == meaning, "category"].iloc[0]
    category_edges.append({
        "category_edge_id": len(category_edges) + 1,
        "child_category_id": category_id,
        "parent_category_id": category_id_by_label[parent_label],
        "relationship_type": "RESOLVES_INTO",
        "scheme_id": SWADESH_SCHEME_ID,
    })
category_edges_df = pd.DataFrame(category_edges)

# 6. word_categories bridge table (many-to-many): every word links to its
# broad (tier-1) category; root-level concepts additionally link to their
# own (tier-2) subcategory.
word_category_links = []
for row in df.itertuples():
    if pd.isna(row.category):
        continue
    word_category_links.append({
        "word_id": word_id_by_csv_id[row.id],
        "category_id": category_id_by_label[row.category],
    })
for row in root_concepts.itertuples():
    word_category_links.append({
        "word_id": word_id_by_csv_id[row.id],
        "category_id": subcategory_id_by_meaning[row.meaning],
    })
word_categories_df = pd.DataFrame(word_category_links).drop_duplicates().reset_index(drop=True)

edges = []

# 7a. DEVELOPED_INTO - word-to-word (and, if the CSV encoded them,
# language-to-language) lineage: every parent_id -> id link in the tree.
for row in df.itertuples():
    if pd.isna(row.parent_id):
        continue
    edges.append({
        "source_word_id": word_id_by_csv_id[row.parent_id],
        "target_word_id": word_id_by_csv_id[row.id],
        "relationship_type": "DEVELOPED_INTO",
        "is_diachronic": tags_by_csv_id[row.parent_id] != row.tags,
    })

# 7a2. DEVELOPED_INTO - language-to-language: aggregated from the word-level
# evidence above. Every diachronic word transition (tags changed from parent
# to child) is itself evidence that the parent's language developed into the
# child's language, so collect the distinct (parent_tag, child_tag) pairs and
# emit one language-level edge per pair.
language_pairs = set()
for row in df.itertuples():
    if pd.isna(row.parent_id):
        continue
    parent_tag = tags_by_csv_id[row.parent_id]
    if parent_tag != row.tags:
        language_pairs.add((parent_tag, row.tags))

for parent_tag, child_tag in sorted(language_pairs):
    edges.append({
        "source_word_id": language_word_id[parent_tag],
        "target_word_id": language_word_id[child_tag],
        "relationship_type": "DEVELOPED_INTO",
        "is_diachronic": True,
    })

# 7b. HAS_WORD (language -> word), derived from each word's tags value.
# TAGGED_AS (word -> language) is its inverse and is exposed as a SQL view
# (step 7) instead of being stored as a duplicate physical row.
for row in df.itertuples():
    edges.append({
        "source_word_id": language_word_id[row.tags],
        "target_word_id": word_id_by_csv_id[row.id],
        "relationship_type": "HAS_WORD",
        "is_diachronic": None,
    })

# 7c. CONNECTED_TO (synchronic word-to-word) - words explicitly curated as
# belonging to the same paradigm (paradigm_id), e.g. English "to be"
# (am/is/are, was/were, be/been), each tracing back to a *different* PIE
# root (*h1es-, *h2wes-, *bhuH-). This relation cannot be inferred from
# parent_id/tags - suppletive paradigm members share no ancestor and often
# no language-internal derivation, so it requires its own curated data.
# Stored once per pair (undirected), not twice.
for paradigm_id, group in df.dropna(subset=["paradigm_id"]).groupby("paradigm_id"):
    ids = group["id"].tolist()
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            edges.append({
                "source_word_id": word_id_by_csv_id[ids[i]],
                "target_word_id": word_id_by_csv_id[ids[j]],
                "relationship_type": "CONNECTED_TO",
                "is_diachronic": False,
            })

edges_df = pd.DataFrame(edges).drop_duplicates().reset_index(drop=True)
edges_df.insert(0, "edge_id", edges_df.index + 1)

# 8. Sources and citations (LIV, Pokorny, OED). A citation attaches to the
# specific DEVELOPED_INTO edge it attests to (e.g. "Pokorny asserts this
# word derived from that root"), not to the word in isolation - mirroring
# how scheme is an edge property above, rather than a node property.
# multilingual_tree_data.csv carries no citation data of its own, so these
# are illustrative sample citations for demonstrating the schema - loci/
# notes are not verified against the physical dictionaries and should be
# replaced with real citations when available.
sources_df = pd.DataFrame([
    {"source_id": 1, "name": "LIV", "full_name": "Lexikon der indogermanischen Verben"},
    {"source_id": 2, "name": "Pokorny", "full_name": "Indogermanisches etymologisches Woerterbuch"},
    {"source_id": 3, "name": "OED", "full_name": "Oxford English Dictionary"},
])
source_id_by_name = dict(zip(sources_df["name"], sources_df["source_id"]))

SAMPLE_CITATIONS = [
    ("PIE_PTER", "Pokorny", "Pokorny 1959, p. 825, s.v. *pet-",
     "Root meaning 'to fly, fall'; source for the 'wing/feather' word family."),
    ("PIE_PTER", "LIV", "LIV, s.v. *peth2-",
     "Verbal root 'to fly'; laryngeal-inclusive notation differs from Pokorny's older *pet-."),
    ("PIE_AKW", "Pokorny", "Pokorny 1959, p. 775, s.v. *okw-",
     "Root for 'to see, eye'."),
    ("GER_AUGE", "OED", "OED, s.v. eye, n., Etymology",
     "Cross-linguistic cognate note including Germanic *augo and PIE *h3ekw-."),
    ("PIE_KWON", "Pokorny", "Pokorny 1959, p. 632, s.v. *kwon-",
     "Root for 'dog'."),
    ("LAT_CANIS", "OED", "OED, s.v. canine, adj., Etymology",
     "Traces Latin canis to its PIE root."),
    ("PIE_MATR", "Pokorny", "Pokorny 1959, p. 700, s.v. *mater-",
     "Kinship term 'mother'."),
    ("PIE_ED", "LIV", "LIV, s.v. *h1ed-",
     "Verbal root 'to eat'."),
    ("LAT_EDERE", "OED", "OED, s.v. edible, adj., Etymology",
     "Traces Latin edere to PIE *h1ed-."),
    ("PIE_NEBH", "Pokorny", "Pokorny 1959, p. 315, s.v. *nebh-",
     "Root for 'cloud, mist, sky'."),
]

# Every word (other than ROOT) has exactly one incoming DEVELOPED_INTO edge
# (from its parent), so a citation about that word attaches to that edge.
develop_into_edge_id_by_target = dict(zip(
    edges_df.loc[edges_df["relationship_type"] == "DEVELOPED_INTO", "target_word_id"],
    edges_df.loc[edges_df["relationship_type"] == "DEVELOPED_INTO", "edge_id"],
))

citations_df = pd.DataFrame([
    {
        "citation_id": i + 1,
        "edge_id": develop_into_edge_id_by_target[word_id_by_csv_id[csv_id]],
        "source_id": source_id_by_name[source_name],
        "locus": locus,
        "note": note,
    }
    for i, (csv_id, source_name, locus, note) in enumerate(SAMPLE_CITATIONS)
])

# 9. Connect to a local SQLite database (creates 'etymology.db' automatically)
con = sqlite3.connect("etymology.db")

words_df.to_sql("words", con, if_exists="replace", index=False)
edges_df.to_sql("edges", con, if_exists="replace", index=False)
semantic_schemes_df.to_sql("semantic_schemes", con, if_exists="replace", index=False)
semantic_categories_df.to_sql("semantic_categories", con, if_exists="replace", index=False)
category_edges_df.to_sql("category_edges", con, if_exists="replace", index=False)
word_categories_df.to_sql("word_categories", con, if_exists="replace", index=False)
sources_df.to_sql("sources", con, if_exists="replace", index=False)
citations_df.to_sql("citations", con, if_exists="replace", index=False)

# TAGGED_AS (word -> language) is the inverse of HAS_WORD - expose it as a
# view instead of storing duplicate rows.
con.execute("DROP VIEW IF EXISTS tagged_as")
con.execute("""
    CREATE VIEW tagged_as AS
    SELECT target_word_id AS source_word_id,
           source_word_id AS target_word_id,
           'TAGGED_AS' AS relationship_type
    FROM edges
    WHERE relationship_type = 'HAS_WORD'
""")

con.close()
print(
    "Migration complete! Tables 'words', 'edges', 'semantic_schemes', "
    "'semantic_categories', 'category_edges', 'word_categories', 'sources', "
    "'citations' (and view 'tagged_as') created in etymology.db."
)
