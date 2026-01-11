import pandas as pd
import json
import sys

# ==========================================
# 1. FILE CONFIGURATION
# ==========================================
BACI_FILENAME = "BACI_HS22_Y2023.csv"
COUNTRY_CODES_FILENAME = "country_codes.csv"
OUTPUT_FILENAME = "final_exports.json"

# ==========================================
# 2. SECTION MAPPING (ID 1-22)
# ==========================================
SECTION_DEFINITIONS = [
    {"id": "1", "chapters": [1,2,3,4,5]},
    {"id": "2", "chapters": range(6, 15)},
    {"id": "3", "chapters": [15]},
    {"id": "4", "chapters": range(16, 25)},
    {"id": "5", "chapters": [25,26,27]},
    {"id": "6", "chapters": range(28, 39)},
    {"id": "7", "chapters": [39,40]},
    {"id": "8", "chapters": [41,42,43]},
    {"id": "9", "chapters": [44,45,46]},
    {"id": "10", "chapters": [47,48,49]},
    {"id": "11", "chapters": range(50, 64)},
    {"id": "12", "chapters": [64,65,66,67]},
    {"id": "13", "chapters": [68,69,70]},
    {"id": "14", "chapters": [71]},
    {"id": "15", "chapters": range(72, 84)},
    {"id": "16", "chapters": [84,85]},
    {"id": "17", "chapters": [86,87,88,89]},
    {"id": "18", "chapters": [90,91,92]},
    {"id": "19", "chapters": [93]},
    {"id": "20", "chapters": [94,95,96]},
    {"id": "21", "chapters": [97,98,99]},
    {"id": "22", "chapters": [] }
]

# Create fast lookup: Chapter Int -> Section ID String (e.g., 1 -> "1")
CHAPTER_TO_SECTION_ID = {}
for sec in SECTION_DEFINITIONS:
    for ch in sec["chapters"]:
        CHAPTER_TO_SECTION_ID[ch] = sec["id"]

def main():
    print("--- Starting Full Global Export Generator ---")

    # --- Step A: Load Country Codes ---
    print(f"Loading {COUNTRY_CODES_FILENAME}...")
    try:
        df_geo = pd.read_csv(COUNTRY_CODES_FILENAME, encoding='utf-8')
        df_geo.columns = [c.strip().lower() for c in df_geo.columns]

        # Detect Columns
        code_col = next((c for c in ['country_code', 'code', 'id', 'numeric'] if c in df_geo.columns), None)
        iso_col = next((c for c in ['country_iso3', 'iso_3digit_alpha', 'iso3', 'iso', 'iso_code'] if c in df_geo.columns), None)
        name_col = next((c for c in ['country_name', 'name', 'country', 'country_name_full'] if c in df_geo.columns), None)

        if not code_col or not iso_col or not name_col:
            print("ERROR: Could not detect columns. Need ID, ISO3, and Name.")
            print(f"Found: {df_geo.columns.tolist()}")
            return

        # Create Lookup Dicts
        # We need: ID -> Name (for Root Key) and ID -> ISO (for Meta ID)
        id_to_name = pd.Series(df_geo[name_col].values, index=df_geo[code_col]).to_dict()
        id_to_iso = pd.Series(df_geo[iso_col].values, index=df_geo[code_col]).to_dict()

        target_ids = list(id_to_name.keys())
        total_countries = len(target_ids)
        print(f"   -> Loaded {total_countries} countries to process.")

    except Exception as e:
        print(f"CRITICAL ERROR loading country codes: {e}")
        return

    # --- Step B: Load Trade Data ---
    print(f"Loading {BACI_FILENAME}... (This is the heavy step)")
    try:
        df = pd.read_csv(BACI_FILENAME, usecols=['t', 'i', 'k', 'v'])
    except ValueError:
        print("   -> Standard columns not found, attempting to sanitize...")
        df = pd.read_csv(BACI_FILENAME)
        df.columns = [c.strip().lower() for c in df.columns]
        df = df[['t', 'i', 'k', 'v']]

    # Filter for valid countries only
    df = df[df['i'].isin(target_ids)].copy()

    # Pre-calculate Data
    df['v'] = (df['v'] * 1000).astype(int) # Convert to integer units
    df['hs4'] = df['k'] // 100
    df['hs2'] = df['k'] // 10000

    print(f"   -> Data loaded and filtered ({len(df)} rows).")

    # --- Step C: Main Loop ---
    final_output = {}

    for idx, numeric_id in enumerate(target_ids):
        # Progress Bar Logic
        country_name = id_to_name.get(numeric_id, "Unknown")
        iso_code = id_to_iso.get(numeric_id, "UNK")

        # Update progress on same line
        sys.stdout.write(f"\r[{idx+1} / {total_countries}] Processing {country_name} ({iso_code})...           ")
        sys.stdout.flush()

        # Subset data
        country_data = df[df['i'] == numeric_id]

        if country_data.empty:
            continue

        # 1. Total Exports
        total_val = int(country_data['v'].sum())

        if total_val == 0:
            continue

        # 2. Sections (Ensure all 22 keys exist)
        chapter_totals = country_data.groupby('hs2')['v'].sum().to_dict()
        sections_map = {str(i): 0 for i in range(1, 23)} # Initialize "1"..."22" with 0

        for ch, val in chapter_totals.items():
            sec_id = CHAPTER_TO_SECTION_ID.get(ch, "22") # Default to Unspecified
            sections_map[sec_id] += int(val)

        # 3. Top Products (HS4)
        hs4_grouped = country_data.groupby('hs4')['v'].sum().reset_index()
        hs4_grouped['share'] = (hs4_grouped['v'] / total_val) * 100

        # Filter > 0.01%
        sig_products = hs4_grouped[hs4_grouped['share'] > 0.01].copy()
        sig_products.sort_values(by='v', ascending=False, inplace=True)

        prod_count = len(sig_products)

        # Build Optimized List
        products_list = []
        for _, row in sig_products.iterrows():
            products_list.append({
                "id": str(int(row['hs4'])),
                "v": int(row['v']),
                "s": round(row['share'], 2)
            })

        # Final Object Construction
        final_output[country_name] = {
            "meta": {
                "id": iso_code,
                "total_exports": total_val,
                "product_count": prod_count
            },
            "sections": sections_map,
            "top_products": products_list
        }

    # --- Step D: Save ---
    print(f"\n\nProcessing complete. Writing to {OUTPUT_FILENAME}...")
    with open(OUTPUT_FILENAME, 'w', encoding='utf-8') as f:
        json.dump(final_output, f, separators=(',', ':')) # Minified JSON

    print("Success!")

if __name__ == "__main__":
    main()
