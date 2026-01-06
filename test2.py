import json

with open("logtest.json", "r", encoding="utf-8") as f:
    raw = f.read()

print("First 50 chars:", repr(raw[:50]))

# Remove UTF-8 BOM if present
raw = raw.lstrip("\ufeff").strip()

# Find the real JSON start
start = raw.find("[")
if start == -1:
    raise ValueError("No JSON array found in file!")

raw = raw[start:]

# Now parse
outer = json.loads(raw)

# Decode the "log" string
for item in outer:
    if item[0] == "log":
        item[1] = json.loads(item[1])

# Save clean output
with open("output.json", "w", encoding="utf-8") as f:
    json.dump(outer, f, indent=2)

print("✅ Fixed and saved to output.json")
