import json

def extract_hs4_codes(input_filename, output_filename):
    try:
        # Open and load the input JSON file
        with open(input_filename, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Dictionary to store the final key-value pairs
        hs4_map = {}

        # Check if 'results' key exists (based on your snippet)
        if 'results' not in data:
            print("Error: Input JSON does not contain a 'results' key.")
            return

        for item in data['results']:
            # We only want HS-4 entities.
            # In your snippet, these have "aggrlevel": 4
            if item.get('aggrlevel') == 4:

                code = item.get('id')
                raw_text = item.get('text', '')

                # CLEANING THE NAME
                # The text usually comes as "0101 - Live horses..."
                # We want to remove the code and the " - " separator.

                description = raw_text

                # If the description starts with the code, cut it off
                if description.startswith(code):
                    description = description[len(code):]

                # Strip leading hyphens, spaces, and dots
                description = description.lstrip(' -.')

                # Add to dictionary
                hs4_map[code] = description

        # Save to output file
        # indent=4 ensures "one entity per row" as requested
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(hs4_map, f, indent=4)

        print(f"Success! Extracted {len(hs4_map)} HS-4 entities.")
        print(f"File saved as: {output_filename}")

    except FileNotFoundError:
        print(f"Error: The file '{input_filename}' was not found.")
    except json.JSONDecodeError:
        print(f"Error: Failed to decode JSON. Please check input file format.")

# Run the function
# Assumes your file is named 'input.json'
if __name__ == "__main__":
    extract_hs4_codes('input.json', 'hs4_output.json')
