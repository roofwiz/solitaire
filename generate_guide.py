import os
import json
import pygame

# Initialize Pygame
pygame.init()
pygame.display.set_mode((100, 100), pygame.HIDDEN)

# Output Directory
IMG_DIR = "guide_assets"
if not os.path.exists(IMG_DIR):
    os.makedirs(IMG_DIR)

# Load Assets Config
with open('assets.json', 'r') as f:
    config = json.load(f)

IMAGES_PATH = "assets"

def load_sheet(name):
    filename = config['images'].get(name)
    if not filename: return None
    path = os.path.join(IMAGES_PATH, filename)
    if not os.path.exists(path):
        print(f"Warning: Image not found {path}")
        return None
    return pygame.image.load(path)

# Sheet Cache
SHEETS = {
    'spritesheet': load_sheet('spritesheet'),
    'items': load_sheet('items'),
    'blocks': load_sheet('blocks'),
    'tetris': load_sheet('tetris')
}

def get_sprite(sheet_key, coords_key, sub_key=None):
    sheet = SHEETS.get(sheet_key)
    if not sheet: return None
    
    # Resolve Coords
    data = config['sprite_coords'].get(coords_key)
    if sub_key and data:
        data = data.get(sub_key)
        
    if not data:
        print(f"Missing coords for {coords_key}/{sub_key}")
        return None
        
    rect = pygame.Rect(data['x'], data['y'], data['w'], data['h'])
    try:
        sub = sheet.subsurface(rect).copy()
        return sub
    except ValueError:
        print(f"Crop Error: {rect} outside surface size")
        return None

def make_luigi(surf):
    if not surf: return None
    s = surf.copy()
    arr = pygame.PixelArray(s)
    with arr:
        for x in range(s.get_width()):
            for y in range(s.get_height()):
                c = s.unmap_rgb(arr[x, y])
                r, g, b, a = c.r, c.g, c.b, c.a
                if a == 0: continue
                # Swap Red/Green for Luigi Palette
                if r > 150 and g < 100 and b < 100:
                    arr[x, y] = (g, r, b, a)
    return s

# Define Generation List
ALL_ENTITIES = [
    {
        "id": "mario",
        "name": "Mario",
        "type": "Hero",
        "desc": "The main character.",
        "extract": lambda: get_sprite('spritesheet', 'mario', 'walk')
    },
    {
        "id": "luigi",
        "name": "Luigi",
        "type": "Hero",
        "desc": "Mario's brother (Intro Only).",
        "extract": lambda: make_luigi(get_sprite('spritesheet', 'mario', 'walk'))
    },
    {
        "id": "koopa_green",
        "name": "Green Koopa",
        "type": "Enemy",
        "desc": "Basic enemy. Walks.",
        "extract": lambda: get_sprite('spritesheet', 'koopa_green', 'walk_1')
    },
    {
        "id": "koopa_red",
        "name": "Red Koopa",
        "type": "Enemy",
        "desc": "Flying enemy.",
        "extract": lambda: get_sprite('spritesheet', 'koopa_red', 'fly_1')
    },
    {
        "id": "spiny",
        "name": "Spiny",
        "type": "Enemy",
        "desc": "Spiky shell. Do not stomp!",
        "extract": lambda: get_sprite('spritesheet', 'spiny', 'walk_1')
    },
    {
        "id": "lakitu",
        "name": "Lakitu",
        "type": "Enemy",
        "desc": "Cloud rider.",
        "extract": lambda: get_sprite('spritesheet', 'lakitu', 'default')
    },
    {
        "id": "mushroom",
        "name": "Magic Mushroom",
        "type": "Item",
        "desc": "Grants 1-up / Bonus.",
        "extract": lambda: get_sprite('items', 'items', 'mushroom_super')
    },
    {
        "id": "coin",
        "name": "Coin",
        "type": "Item",
        "desc": "Collect for score.",
        "extract": lambda: get_sprite('items', 'items', 'coin_1')
    },
    {
        "id": "star",
        "name": "Star",
        "type": "Item",
        "desc": "Invincibility power.",
        "extract": lambda: get_sprite('items', 'items', 'star_1')
    },
    {
        "id": "brick",
        "name": "Brick Block",
        "type": "Block",
        "desc": "Standard building block.",
        "extract": lambda: get_sprite('blocks', 'blocks', 'brick')
    },
    {
        "id": "question",
        "name": "Question Block",
        "type": "Block",
        "desc": "Contains items.",
        "extract": lambda: get_sprite('blocks', 'blocks', 'question_1')
    }
]

# Generate Images and HTML
html_cards = ""

print("Generating images...")
for ent in ALL_ENTITIES:
    img = ent['extract']()
    if img:
        # Scale Up (4x)
        w, h = img.get_size()
        scaled = pygame.transform.scale(img, (w*4, h*4))
        path = f"{IMG_DIR}/{ent['id']}.png"
        pygame.image.save(scaled, path)
        print(f"Saved {path}")
        
        html_cards += f"""
        <div class="card">
            <span class="type">{ent['type']}</span><br>
            <img src="{path}" alt="{ent['name']}">
            <h4>{ent['name']}</h4>
            <p>{ent['desc']}</p>
        </div>
        """
    else:
        print(f"Failed to extract {ent['id']}")

# HTML Template
html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Mario Tetris - Visual Guide</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; background-color: #1a1a1a; color: #fff; padding: 20px; }}
        h1 {{ color: #fe1553; text-align: center; font-size: 48px; text-shadow: 2px 2px #000; margin-bottom: 40px; }}
        .card-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 20px; }}
        .card {{ background: #2b2b2b; border-radius: 12px; padding: 20px; text-align: center; border: 1px solid #333; transition: transform 0.2s; }}
        .card:hover {{ transform: translateY(-5px); border-color: #fe1553; box-shadow: 0 5px 15px rgba(254, 21, 83, 0.3); }}
        .card img {{ height: 80px; image-rendering: pixelated; margin: 15px 0; }}
        .card h4 {{ margin: 5px 0; color: #fff; font-size: 20px; }}
        .card .type {{ font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #aaa; background: #1a1a1a; padding: 4px 10px; border-radius: 20px; }}
        .card p {{ font-size: 14px; color: #bbb; line-height: 1.4; }}
    </style>
</head>
<body>
    <h1>MARIO TETRIS ASSETS</h1>
    <div class="card-grid">
        {html_cards}
    </div>
</body>
</html>
"""

with open("game_guide_visual.html", "w") as f:
    f.write(html_content)

print("Visual Guide Generated: game_guide_visual.html")
os.system("start game_guide_visual.html")
