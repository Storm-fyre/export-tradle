import json
import re

# --- CONFIGURATION ---
HTML_FILE = 'index.html'
JSON_FILE = 'exports.json'

def fix_countries():
    # 1. Load the Export Data Keys
    try:
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            json_keys = set(data.keys())
    except FileNotFoundError:
        print(f"Error: Could not find {JSON_FILE}")
        return

    # 2. Load the HTML Content
    try:
        with open(HTML_FILE, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except FileNotFoundError:
        print(f"Error: Could not find {HTML_FILE}")
        return

    # 3. Extract the COUNTRIES array
    pattern = r"const COUNTRIES = (\[.*?\]);"
    match = re.search(pattern, html_content, re.DOTALL)

    if not match:
        print("Error: Could not find 'const COUNTRIES' in index.html")
        return

    # Parse JS array to Python list
    js_array_str = match.group(1)
    # Remove trailing commas which are valid in JS but not JSON
    js_array_str = re.sub(r',\s*]', ']', js_array_str)
    try:
        countries_list = json.loads(js_array_str)
    except json.JSONDecodeError:
        print("Error parsing the COUNTRIES array. Check syntax.")
        return

    # 4. Process and Fix Mismatches
    fixed_countries = []

    # Common mappings found in trade data (UI Name -> Data Name)
    known_fixes = {
        "Czech Republic": "Czechia",
        "Turkey": "Türkiye",
        "Swaziland": "Eswatini",
        "Macedonia": "North Macedonia",
        "Bosnia and Herzegovina": "Bosnia Herzegovina"
    }

    for country in countries_list:
        name = country['name']
        cid = country['id']

        # 1. Try exact match
        if name in json_keys:
            fixed_countries.append(country)

        # 2. Try known fix
        elif name in known_fixes and known_fixes[name] in json_keys:
            country['name'] = known_fixes[name]
            fixed_countries.append(country)

        # 3. Try using ID as name (if data uses codes like "USA")
        elif cid in json_keys:
            country['name'] = cid
            fixed_countries.append(country)

        # 4. Keep original (will likely fail in game, but preserves list)
        else:
            fixed_countries.append(country)

    # 5. Generate Output in Single-Line Format
    print("const COUNTRIES = [")
    for i, country in enumerate(fixed_countries):
        # dump to string, ensure_ascii=False keeps accents like 'ü' in Türkiye
        line_str = json.dumps(country, ensure_ascii=False)

        # Add comma for all except the last item
        comma = "," if i < len(fixed_countries) - 1 else ""

        print(f"  {line_str}{comma}")
    print("];")

if __name__ == "__main__":
    fix_countries()
