"""
Convert local_name (Latin transliteration) to Thaana script via Claude API.
Saves result to local_name_dv field in data/fishes.json.

Usage:
    python3 generate_dhivehi_names.py
"""

import json
import anthropic
from pathlib import Path

client = anthropic.Anthropic()

data_path = Path(__file__).parent / "data" / "fishes.json"

with open(data_path, encoding="utf-8") as f:
    fish_list = json.load(f)

updated = 0
for fish in fish_list:
    name = fish.get("local_name", "").strip()
    if not name or fish.get("local_name_dv"):
        continue

    msg = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=100,
        messages=[{
            "role": "user",
            "content": (
                f'Convert this Dhivehi fish name from Latin transliteration to Thaana script: '
                f'"{name}". Reply with ONLY the Thaana script, nothing else.'
            ),
        }],
    )
    fish["local_name_dv"] = msg.content[0].text.strip()
    print(f"  {name} → {fish['local_name_dv']}")
    updated += 1

with open(data_path, "w", encoding="utf-8") as f:
    json.dump(fish_list, f, indent=2, ensure_ascii=False)

print(f"\nDone. {updated} names converted. fishes.json updated with local_name_dv field.")
