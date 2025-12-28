"""
Sprite Analysis Tool
Cross-references detected sprites with assets.json to find missing/unused sprites
"""

import json
import re

# Parse found sprites
found_sprites = []
with open('found_sprites.txt', 'r') as f:
    for line in f:
        match = re.match(r'Sprite: x=(\d+), y=(\d+), w=(\d+), h=(\d+)', line)
        if match:
            found_sprites.append({
                'x': int(match.group(1)),
                'y': int(match.group(2)),
                'w': int(match.group(3)),
                'h': int(match.group(4))
            })

# Load assets.json
with open('assets.json', 'r') as f:
    assets = json.load(f)

# Extract all sprites from spritesheet (marioallsprite.png)
defined_sprites = []
for category, sprites in assets.get('sprite_coords', {}).items():
    for name, coords in sprites.items():
        # Only include sprites from the main spritesheet (no 'file' key or file='spritesheet')
        if coords.get('file', 'spritesheet') == 'spritesheet' or 'file' not in coords:
            defined_sprites.append({
                'category': category,
                'name': name,
                'x': coords['x'],
                'y': coords['y'],
                'w': coords['w'],
                'h': coords['h']
            })

print("=" * 70)
print("SPRITE ANALYSIS REPORT - marioallsprite.png")
print("=" * 70)

print(f"\n📊 SUMMARY:")
print(f"   Found by scanner: {len(found_sprites)} sprite regions")
print(f"   Defined in assets.json (main spritesheet): {len(defined_sprites)} sprites")

# Check which found sprites match defined ones (with tolerance)
def sprites_match(found, defined, tolerance=5):
    """Check if sprites approximately match"""
    return (abs(found['x'] - defined['x']) <= tolerance and
            abs(found['y'] - defined['y']) <= tolerance and
            abs(found['w'] - defined['w']) <= tolerance and
            abs(found['h'] - defined['h']) <= tolerance)

def sprites_overlap(a, b):
    """Check if two sprite regions overlap"""
    return not (a['x'] + a['w'] < b['x'] or 
                b['x'] + b['w'] < a['x'] or
                a['y'] + a['h'] < b['y'] or 
                b['y'] + b['h'] < a['y'])

# Find matched and unmatched
matched_found = []
unmatched_found = []

for found in found_sprites:
    matched = False
    for defined in defined_sprites:
        if sprites_match(found, defined) or sprites_overlap(found, defined):
            matched = True
            matched_found.append((found, defined))
            break
    if not matched:
        unmatched_found.append(found)

# Check if any defined sprites aren't matched by scanner
unmatched_defined = []
for defined in defined_sprites:
    matched = False
    for found in found_sprites:
        if sprites_match(found, defined) or sprites_overlap(found, defined):
            matched = True
            break
    if not matched:
        unmatched_defined.append(defined)

print(f"\n✅ MATCHED SPRITES: {len(matched_found)}")
print(f"❓ UNDEFINED (found but not in assets.json): {len(unmatched_found)}")
print(f"⚠️  POTENTIALLY MISSING (in assets.json but not found by scanner): {len(unmatched_defined)}")

# Group unmatched by Y-position (row)
print("\n" + "=" * 70)
print("🔍 UNDEFINED SPRITES (Potential new assets to add)")
print("=" * 70)

# Sort by y then x
unmatched_found.sort(key=lambda s: (s['y'], s['x']))

# Group by approximate rows
current_row = None
for sprite in unmatched_found:
    row = sprite['y'] // 40  # Group by ~40px rows
    if row != current_row:
        current_row = row
        print(f"\n--- Row y≈{row * 40}-{row * 40 + 39} ---")
    
    print(f"   x={sprite['x']:3d}, y={sprite['y']:3d}, w={sprite['w']:2d}, h={sprite['h']:2d}", end="")
    
    # Try to guess what it might be based on position/size
    if sprite['w'] <= 16 and sprite['h'] <= 16 and sprite['y'] < 70:
        print("  [Likely: Small Mario/item]")
    elif 24 <= sprite['w'] <= 32 and 24 <= sprite['h'] <= 32 and sprite['y'] < 100:
        print("  [Likely: Large character/Goomba]")
    elif sprite['w'] >= 30 and sprite['y'] > 390:
        print("  [Likely: Title/Logo sprite]")
    elif 14 <= sprite['h'] <= 16 and 200 <= sprite['y'] <= 250:
        print("  [Likely: Shell sprite]")
    elif sprite['y'] > 300 and sprite['h'] >= 30:
        print("  [Likely: Tall character (Para-Koopa, Lakitu)]")
    else:
        print("")

print("\n" + "=" * 70)
print("⚠️  SPRITES IN assets.json THAT WEREN'T AUTO-DETECTED")
print("=" * 70)
print("(These might have wrong coordinates or be from different sheets)")

for defined in unmatched_defined:
    print(f"   {defined['category']}/{defined['name']}: "
          f"x={defined['x']}, y={defined['y']}, w={defined['w']}, h={defined['h']}")

# Generate suggested additions
print("\n" + "=" * 70)
print("💡 SUGGESTED ADDITIONS FOR assets.json")
print("=" * 70)

suggested = []
for i, sprite in enumerate(unmatched_found):
    # Try to categorize
    y = sprite['y']
    h = sprite['h']
    w = sprite['w']
    
    if y < 30 and w > 20:
        category = "effects"
        name = f"explosion_{i+1}"
    elif y < 70 and h <= 16:
        category = "mario_small"
        name = f"frame_{i+1}"
    elif 80 <= y <= 200 and h >= 26:
        category = "mario_big"
        name = f"frame_{i+1}"
    elif 240 <= y <= 310:
        category = "koopa_unknown"
        name = f"frame_{i+1}"
    elif y > 390 and w >= 30:
        category = "title_sprites"
        name = f"logo_{i+1}"
    else:
        category = "unknown"
        name = f"sprite_{i+1}"
    
    suggested.append({
        'category': category,
        'name': name,
        'coords': sprite
    })

# Group suggestions by category
from collections import defaultdict
by_category = defaultdict(list)
for s in suggested:
    by_category[s['category']].append(s)

for category, sprites in by_category.items():
    print(f"\n\"{category}\": {{")
    for s in sprites:
        c = s['coords']
        print(f'    "{s["name"]}": {{"x": {c["x"]}, "y": {c["y"]}, "w": {c["w"]}, "h": {c["h"]}}},')
    print("}")

# Save detailed report
with open('sprite_analysis_report.txt', 'w') as f:
    f.write("SPRITE ANALYSIS REPORT\n")
    f.write("=" * 70 + "\n\n")
    f.write(f"Found by scanner: {len(found_sprites)} sprites\n")
    f.write(f"Defined in assets.json: {len(defined_sprites)} sprites\n")
    f.write(f"Matched: {len(matched_found)}\n")
    f.write(f"Undefined (found but not mapped): {len(unmatched_found)}\n")
    f.write(f"Potentially wrong coords: {len(unmatched_defined)}\n\n")
    
    f.write("UNDEFINED SPRITES:\n")
    for s in unmatched_found:
        f.write(f"  x={s['x']}, y={s['y']}, w={s['w']}, h={s['h']}\n")
    
    f.write("\nPOTENTIALLY WRONG COORDS:\n")
    for d in unmatched_defined:
        f.write(f"  {d['category']}/{d['name']}: x={d['x']}, y={d['y']}, w={d['w']}, h={d['h']}\n")

print("\n\n📄 Detailed report saved to: sprite_analysis_report.txt")
