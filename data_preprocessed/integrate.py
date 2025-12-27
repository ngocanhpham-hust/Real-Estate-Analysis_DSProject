import pandas as pd
import os

# Paths
path_bds = "data/preprocessed/batdongsancomvn_preprocessed.csv"
path_muaban = "data/preprocessed/muabannet_preprocessed.csv"
output_path = "data/preprocessed/full.csv"

print("Loading datasets...")

df_bds = pd.read_csv(path_bds)
df_muaban = pd.read_csv(path_muaban)

print(f"batdongsancomvn: {df_bds.shape}")
print(f"muabannet: {df_muaban.shape}")

# Chuẩn hoá tên cột
df_bds.columns = df_bds.columns.str.strip().str.lower()
df_muaban.columns = df_muaban.columns.str.strip().str.lower()

# Align columns (union of columns)
common_cols = sorted(set(df_bds.columns) | set(df_muaban.columns))

df_bds = df_bds.reindex(columns=common_cols)
df_muaban = df_muaban.reindex(columns=common_cols)

# Add source column
df_bds["source"] = "batdongsancomvn"
df_muaban["source"] = "muabannet"

# Concatenate
df_full = pd.concat([df_bds, df_muaban], ignore_index = True)

print(f"Full dataset shape: {df_full.shape}")

# Ensure output directory exists
output_dir = os.path.dirname(output_path)
os.makedirs(output_dir, exist_ok = True)

if os.path.exists(output_path):
    os.remove(output_path)

df_full.to_csv(output_path, index = False, encoding = "utf-8-sig")

print(f"SUCCESS! Integrated dataset saved to: {output_path}")