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

# 3. Semantic categories: a self-referential table (arbitrary depth) rather
# than baking a fixed CATEGORY/SUBCATEGORY pair into the words table. Tier 1
# is the broad category (e.g. Nature); tier 2 is each root-level concept's
# meaning (e.g. "wing / feather"), parented under its tier-1 category.
categories = []
category_id_by_label = {}
for label in sorted(df["category"].dropna().unique()):
    category_id = len(categories) + 1
    category_id_by_label[label] = category_id
    categories.append({"category_id": category_id, "label": label, "parent_category_id": None})

root_ids = set(df.loc[df["parent_id"].isna(), "id"])
root_concepts = df[df["parent_id"].isin(root_ids)]
subcategory_id_by_meaning = {}
for row in root_concepts.drop_duplicates(subset=["meaning", "category"]).itertuples():
    category_id = len(categories) + 1
    subcategory_id_by_meaning[row.meaning] = category_id
    categories.append({
        "category_id": category_id,
        "label": row.meaning,
        "parent_category_id": category_id_by_label[row.category],
    })
semantic_categories_df = pd.DataFrame(categories)

# 4. word_categories bridge table (many-to-many): every word links to its
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

# 5a. DEVELOPED_INTO - word-to-word (and, if the CSV encoded them,
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

# 5b. HAS_WORD (language -> word), derived from each word's tags value.
# TAGGED_AS (word -> language) is its inverse and is exposed as a SQL view
# (step 7) instead of being stored as a duplicate physical row.
for row in df.itertuples():
    edges.append({
        "source_word_id": language_word_id[row.tags],
        "target_word_id": word_id_by_csv_id[row.id],
        "relationship_type": "HAS_WORD",
        "is_diachronic": None,
    })

# 5c. CONNECTED_TO (synchronic word-to-word) - sibling words that share both
# a parent and a language, i.e. they coexist rather than one having
# developed into the other. Stored once per pair (undirected), not twice.
for parent_id, group in df.groupby("parent_id"):
    for tag, same_tag_group in group.groupby("tags"):
        ids = same_tag_group["id"].tolist()
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

# 6. Sources and citations (LIV, Pokorny, OED). multilingual_tree_data.csv
# carries no citation data of its own, so these are illustrative sample
# citations for demonstrating the schema - loci/notes are not verified
# against the physical dictionaries and should be replaced with real
# citations when available.
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

citations_df = pd.DataFrame([
    {
        "citation_id": i + 1,
        "word_id": word_id_by_csv_id[csv_id],
        "source_id": source_id_by_name[source_name],
        "locus": locus,
        "note": note,
    }
    for i, (csv_id, source_name, locus, note) in enumerate(SAMPLE_CITATIONS)
])

# 7. Connect to a local SQLite database (creates 'etymology.db' automatically)
con = sqlite3.connect("etymology.db")

words_df.to_sql("words", con, if_exists="replace", index=False)
edges_df.to_sql("edges", con, if_exists="replace", index=False)
semantic_categories_df.to_sql("semantic_categories", con, if_exists="replace", index=False)
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
    "Migration complete! Tables 'words', 'edges', 'semantic_categories', "
    "'word_categories', 'sources', 'citations' (and view 'tagged_as') "
    "created in etymology.db."
)
