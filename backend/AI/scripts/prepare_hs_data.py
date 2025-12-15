import pandas as pd
import os

def normalize_text(s):
    if pd.isna(s):
        return ""
    return str(s).strip().lower()

BASE_DIR = os.path.join(os.path.dirname(__file__), '..')
DATA_DIR = os.path.join(BASE_DIR, 'datasets')
MODELS_DIR = os.path.join(BASE_DIR, 'models')
os.makedirs(MODELS_DIR, exist_ok=True)

hs_csv = os.path.join(DATA_DIR, 'harmonized-system.csv')
sections_csv = os.path.join(DATA_DIR, 'sections.csv')

if not os.path.exists(hs_csv):
    raise FileNotFoundError(f"Missing {hs_csv}")

if not os.path.exists(sections_csv):
    raise FileNotFoundError(f"Missing {sections_csv}")

# Load datasets
hs = pd.read_csv(hs_csv, dtype=str, keep_default_na=False)
sections = pd.read_csv(sections_csv, dtype=str, keep_default_na=False)

# Normalize column names
hs.columns = [c.strip() for c in hs.columns]
sections.columns = [c.strip() for c in sections.columns]

# Expect harmonized-system.csv to have columns like 'hscode','description','parent','level' etc.
# Normalize keys
if 'hscode' not in hs.columns:
    # try common alternatives
    possible = [c for c in hs.columns if 'code' in c.lower()]
    if possible:
        hs = hs.rename(columns={possible[0]: 'hscode'})

if 'description' not in hs.columns:
    possible = [c for c in hs.columns if 'desc' in c.lower()]
    if possible:
        hs = hs.rename(columns={possible[0]: 'description'})

# Ensure essential columns
required = ['hscode', 'description']
for r in required:
    if r not in hs.columns:
        hs[r] = ''

# Sections may have columns like 'section','title' or similar
sec_name_col = None
for col in sections.columns:
    if 'section' in col.lower() or 'roman' in col.lower():
        sec_name_col = col
        break
# Try to identify mapping between hs and sections
# Assume sections.csv has columns: code (1-21) and title/full_name
if 'code' in sections.columns and ('title' in sections.columns or 'name' in sections.columns):
    sections = sections.rename(columns={ 'code': 'section_code' })

# Build section lookup by either section_code or some key
sections_lookup = {}
if 'section_code' in sections.columns:
    name_col = 'title' if 'title' in sections.columns else ('name' if 'name' in sections.columns else sections.columns[1])
    for _, row in sections.iterrows():
        sections_lookup[str(row['section_code']).strip()] = str(row[name_col]).strip()
else:
    # fallback: use all rows concatenated
    for i, row in sections.iterrows():
        sections_lookup[str(i+1)] = ' '.join([str(v) for v in row.tolist()])

# Attempt to map HS to section via hscode prefix (first 2 digits -> section mapping not direct).
# If harmonized-system.csv has a 'section' column, use it.
if 'section' in hs.columns:
    hs['section_code'] = hs['section'].astype(str)
else:
    # leave empty; user can supply sections.csv mapping later
    hs['section_code'] = ''

# Map section full name
hs['section'] = hs['section_code'].map(sections_lookup).fillna('')

# Parent and level columns handling
if 'parent' not in hs.columns:
    hs['parent'] = ''
if 'level' not in hs.columns:
    hs['level'] = ''

# Create normalized text: hscode + description + section
hs['text'] = (hs['hscode'].astype(str).fillna('') + ' ' + hs['description'].astype(str).fillna('') + ' ' + hs['section'].astype(str).fillna('')).str.strip().str.lower()

# Drop duplicates and empty
hs = hs[hs['text'].str.strip() != '']
hs = hs.drop_duplicates(subset=['hscode', 'text'])

# Save outputs
out_parquet = os.path.join(MODELS_DIR, 'hs_meta.parquet')
out_csv = os.path.join(MODELS_DIR, 'hs_meta.csv')
hs.to_parquet(out_parquet, index=False)
hs.to_csv(out_csv, index=False)

print(f"Prepared HS data: {len(hs)} rows")
print(f"Saved: {out_parquet}")
print(f"Saved: {out_csv}")
