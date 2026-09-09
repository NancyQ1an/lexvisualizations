import pandas as pd
import sqlite3

# 1. Load your existing flat dataset
# Replace 'etymological_data.csv' with your actual file name
df = pd.read_csv("multilingual_tree_data.csv")

# 2. Build the normalized Words table
words_df = df[["head_word", "language", "semantic_category", "source"]].drop_duplicates().reset_index(drop=True)
words_df["word_id"] = words_df.index + 1

# 3. Build the Edges table by mapping parents to children
merged = df.merge(words_df, left_on="head_word", right_on="head_word", suffixes=("", "_target"))
merged = merged.merge(words_df, left_on="parent_word", right_on="head_word", suffixes=("_child", "_parent"))

edges_df = pd.DataFrame({
    "source_word_id": merged["word_id_parent"],
    "target_word_id": merged["word_id_child"],
    "relationship_type": "DEVELOPED_INTO",
    "is_diachronic": merged["language_parent"] != merged["language_child"]
}).drop_duplicates().reset_index(drop=True)
edges_df["edge_id"] = edges_df.index + 1

# 4. Connect to a local SQLite database (creates 'etymology.db' automatically)
con = sqlite3.connect("etymology.db")

# Export tables to the database
words_df.to_sql("words", con, if_exists="replace", index=False)
edges_df.to_sql("edges", con, if_exists="replace", index=False)

# Close the connection
con.close()
print("Migration complete! Tables 'words' and 'edges' created successfully in etymology.db.")