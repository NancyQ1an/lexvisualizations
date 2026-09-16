import pandas as pd
import sqlite3

# 1. Load your existing flat dataset
# CSV columns: id, word, parent_id, meaning, category, tags
df = pd.read_csv("multilingual_tree_data.csv")

# 2. Build the Words table: one entity row per unique id (node_type=WORD),
# plus synthetic entity rows for each distinct language (tags), semantic
# category (category), and semantic subcategory (the meaning of each
# root-level concept, i.e. a direct child of a root/blank-parent row).
# All entity kinds share one word_id space so edges can point at any of them.
words_df = df[["id", "word", "meaning", "category", "tags"]].drop_duplicates().reset_index(drop=True)
words_df["node_type"] = "WORD"

languages_df = pd.DataFrame({"word": sorted(df["tags"].dropna().unique())})
languages_df["node_type"] = "LANGUAGE"

categories_df = pd.DataFrame({"word": sorted(df["category"].dropna().unique())})
categories_df["node_type"] = "CATEGORY"

root_ids = set(df.loc[df["parent_id"].isna(), "id"])
root_concepts = df[df["parent_id"].isin(root_ids)]
subcategories_df = root_concepts[["meaning", "category"]].drop_duplicates().rename(columns={"meaning": "word"})
subcategories_df["node_type"] = "SUBCATEGORY"

words_df = pd.concat(
    [words_df, languages_df, categories_df, subcategories_df], ignore_index=True
)
words_df["word_id"] = words_df.index + 1
words_df = words_df[["word_id", "node_type", "id", "word", "meaning", "category", "tags"]]

word_id_by_csv_id = dict(zip(df["id"], words_df.loc[words_df["node_type"] == "WORD", "word_id"]))
tags_by_csv_id = dict(zip(df["id"], df["tags"]))
language_word_id = dict(zip(
    words_df.loc[words_df["node_type"] == "LANGUAGE", "word"],
    words_df.loc[words_df["node_type"] == "LANGUAGE", "word_id"],
))
category_word_id = dict(zip(
    words_df.loc[words_df["node_type"] == "CATEGORY", "word"],
    words_df.loc[words_df["node_type"] == "CATEGORY", "word_id"],
))
subcategory_word_id = dict(zip(
    words_df.loc[words_df["node_type"] == "SUBCATEGORY", "word"],
    words_df.loc[words_df["node_type"] == "SUBCATEGORY", "word_id"],
))

edges = []

# 3a. DEVELOPED_INTO - word-to-word (and, if the CSV encoded them,
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

# 3b. HAS_WORD (language -> word) and TAGGED_AS (word -> language), derived
# from each word's tags value.
for row in df.itertuples():
    lang_id = language_word_id[row.tags]
    word_id = word_id_by_csv_id[row.id]
    edges.append({"source_word_id": lang_id, "target_word_id": word_id,
                   "relationship_type": "HAS_WORD", "is_diachronic": None})
    edges.append({"source_word_id": word_id, "target_word_id": lang_id,
                   "relationship_type": "TAGGED_AS", "is_diachronic": None})

# 3c. RESOLVES_INTO (semantic category -> subcategory), derived from each
# root-level concept's category and meaning.
for row in root_concepts.drop_duplicates(subset=["meaning", "category"]).itertuples():
    edges.append({
        "source_word_id": category_word_id[row.category],
        "target_word_id": subcategory_word_id[row.meaning],
        "relationship_type": "RESOLVES_INTO",
        "is_diachronic": None,
    })

# 3d. CONNECTED_TO (synchronic word-to-word) - sibling words that share both
# a parent and a language, i.e. they coexist rather than one having
# developed into the other.
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

# 4. Connect to a local SQLite database (creates 'etymology.db' automatically)
con = sqlite3.connect("etymology.db")

# Export tables to the database
words_df.to_sql("words", con, if_exists="replace", index=False)
edges_df.to_sql("edges", con, if_exists="replace", index=False)

# Close the connection
con.close()
print("Migration complete! Tables 'words' and 'edges' created successfully in etymology.db.")
