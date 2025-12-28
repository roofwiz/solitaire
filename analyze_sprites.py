"""
Auto-labeling sprite scanner for Super Mario Bros sprites.
Based on common NES sprite sheet patterns.
"""
import pygame
import json

# Common Super Mario Bros sprite categories and their typical sizes
MARIO_SPRITE_INFO = {
    # Format: "name": (width, height, description)
    "koopa_green_walk": (16, 27, "Green Koopa walking (no wings)"),
    "koopa_green_fly": (16, 27, "Green Paratroopa with wings"),
    "koopa_red_walk": (16, 27, "Red Koopa walking (no wings)"),
    "koopa_red_fly": (16, 24, "Red Paratroopa with wings"),
    "spiny": (16, 16, "Spiny enemy"),
    "shell": (16, 14, "Koopa shell"),
    "piranha_plant": (16, 24, "Piranha plant"),
    "goomba": (16, 16, "Goomba enemy"),
    "mario_stand": (16, 32, "Mario standing"),
    "mario_walk": (16, 32, "Mario walking"),
    "lakitu": (24, 32, "Lakitu with cloud"),
    "coin": (16, 16, "Coin"),
    "mushroom": (16, 16, "Mushroom power-up"),
    "star": (16, 16, "Star power-up"),
    "flower": (16, 16, "Fire flower"),
}

def scan_spritesheet(filepath):
    """Scan sprite sheet and suggest identifications based on size and location."""
    
    sheet = pygame.image.load(filepath)
    w, h = sheet.get_size()
    
    print("=" * 80)
    print(f"SCANNING: {filepath}")
    print(f"Sheet Size: {w}x{h} pixels")
    print("=" * 80)
    
    # Load existing assets.json to see what's already defined
    try:
        with open('assets.json', 'r') as f:
            assets = json.load(f)
            existing_sprites = assets.get('sprite_coords', {})
    except:
        existing_sprites = {}
    
    print("\n📋 EXISTING SPRITE DEFINITIONS:")
    print("-" * 80)
    
    categories = ['koopa_green', 'koopa_red', 'spiny', 'mario', 'lakitu']
    
    for category in categories:
        if category in existing_sprites:
            print(f"\n{category.upper()}:")
            for sprite_name, coords in existing_sprites[category].items():
                x, y = coords.get('x', 0), coords.get('y', 0)
                sprite_w, sprite_h = coords.get('w', 0), coords.get('h', 0)
                
                # Try to identify what this might be based on size
                suggestions = []
                for info_name, (expected_w, expected_h, desc) in MARIO_SPRITE_INFO.items():
                    if sprite_w == expected_w and sprite_h == expected_h:
                        if category in info_name:
                            suggestions.append(desc)
                
                suggestion_str = f" → Likely: {', '.join(suggestions)}" if suggestions else ""
                print(f"  {sprite_name}: ({x}, {y}) {sprite_w}x{sprite_h}{suggestion_str}")
    
    print("\n" + "=" * 80)
    print("🔍 SUGGESTED FIXES FOR COMMON MARIO SPRITES:")
    print("=" * 80)
    
    # Known typical locations on standard Mario sprite sheets
    print("\n📌 RECOMMENDED SPRITE LOCATIONS (standard NES layout):")
    print("-" * 80)
    print("\nGREEN KOOPA (Paratroopa with wings):")
    print('  fly_1: Usually around x:288-304, y:243, size: 16x27')
    print('  fly_2: Usually around x:328-344, y:243, size: 16x27')
    
    print("\nRED KOOPA (Paratroopa with wings):")
    print('  fly_1: Usually around x:287-303, y:323-325, size: 16x24')
    print('  fly_2: Usually around x:328-344, y:323-325, size: 16x24')
    
    print("\nSPINY:")
    print('  walk_1: Usually around x:8, y:325, size: 16x16')
    print('  walk_2: Usually around x:48, y:325, size: 16x16')
    print('  NOTE: If these show a plant, they\'re mapped to the wrong coordinates!')
    
    print("\nPIRANHA PLANT (if present):")
    print('  Should be 16x24 pixels, typically around y:240-280 range')
    
    print("\n" + "=" * 80)
    print("💡 HOW TO FIX:")
    print("=" * 80)
    print("1. Run: py sprite_scanner_tool.py")
    print("2. Use the visual tool to select the CORRECT sprite locations")
    print("3. Copy the coordinates it prints")
    print("4. Tell me which sprite to update (e.g., 'koopa_red fly_1')")
    print("=" * 80)

if __name__ == "__main__":
    pygame.init()
    scan_spritesheet('assets/marioallsprite.png')
    print("\nScan complete! Use sprite_scanner_tool.py to visually select sprites.")
