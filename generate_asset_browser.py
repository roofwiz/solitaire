import os
import json
import pygame
import shutil

# Initialize Pygame
pygame.init()
pygame.display.set_mode((100, 100), pygame.HIDDEN)

# Config
IMG_DIR = "guide_assets_v2"
if os.path.exists(IMG_DIR):
    shutil.rmtree(IMG_DIR)
os.makedirs(IMG_DIR)

# Load Data
with open('assets.json', 'r') as f:
    config = json.load(f)

IMAGES_PATH = "assets"
def load_sheet(name):
    filename = config['images'].get(name)
    if not filename: return None
    path = os.path.join(IMAGES_PATH, filename)
    if not os.path.exists(path): return None
    return pygame.image.load(path)

# Prepare Sheets
SHEETS = {}
for k, v in config['images'].items():
    s = load_sheet(k)
    if s: SHEETS[k] = s

# Helper: Luigi Tint
def tint_luigi(surf):
    if not surf: return None
    s = surf.copy()
    arr = pygame.PixelArray(s)
    with arr:
        for x in range(s.get_width()):
            for y in range(s.get_height()):
                c = s.unmap_rgb(arr[x, y])
                if c.a == 0: continue
                if c.r > 150 and c.g < 100 and c.b < 100:
                    arr[x, y] = (c.g, c.r, c.b, c.a)
    return s

# Data Collection
ENTITIES = []
cnt = 1

# Tags Logic
TAG_MAP = {
    'mario': ['Characters', 'Hero'],
    'luigi': ['Characters', 'Hero'],
    'koopa_green': ['Characters', 'Enemies', 'Turtle'],
    'koopa_red': ['Characters', 'Enemies', 'Turtle'],
    'spiny': ['Characters', 'Enemies'],
    'lakitu': ['Characters', 'Enemies'],
    'items': ['Items'],
    'blocks': ['Blocks', 'Environment'],
    'tetris_blocks': ['Tetris'],
    'rack_components': ['UI'],
    'cloud': ['Environment']
}

# Iterate Groups
for group_name, frames in config['sprite_coords'].items():
    entity = {
        'id': group_name,
        'number': cnt,
        'name': group_name.replace('_', ' ').replace('blocks', '').strip().title(),
        'tags': TAG_MAP.get(group_name, ['Uncategorized']),
        'animations': {}
    }
    cnt += 1
    
    # Process Frames
    for frame_key, data in frames.items():
        # Detect Sheet
        sheet_key = data.get('file', 'spritesheet') # Default to spritesheet for chars
        if group_name in ['mario', 'luigi', 'koopa_green', 'koopa_red', 'spiny', 'lakitu']:
            sheet_key = 'spritesheet'
        elif group_name == 'items': sheet_key = 'items'
        elif group_name == 'blocks': sheet_key = 'blocks'
        elif group_name == 'tetris_blocks': sheet_key = 'tetris'
        elif group_name == 'rack_components': sheet_key = 'rack'
        
        sheet = SHEETS.get(sheet_key)
        if not sheet: continue
        
        try:
            rect = pygame.Rect(data['x'], data['y'], data['w'], data['h'])
            sub = sheet.subsurface(rect).copy()
            
            # Apply Tint for Luigi
            if group_name == 'luigi':
                sub = tint_luigi(sub)
            
            # Save Image (Scaled)
            scale = 4
            scaled = pygame.transform.scale(sub, (data['w']*scale, data['h']*scale))
            
            # Identify Animation Group (e.g. 'walk_1' -> 'walk')
            if '_' in frame_key and frame_key.split('_')[-1].isdigit():
                anim_name = '_'.join(frame_key.split('_')[:-1])
            else:
                anim_name = frame_key # Single frame or named 'stand'
            
            if anim_name not in entity['animations']:
                entity['animations'][anim_name] = []
            
            # Filename
            fname = f"{group_name}_{frame_key}.png"
            pygame.image.save(scaled, os.path.join(IMG_DIR, fname))
            
            entity['animations'][anim_name].append(fname)
            
        except Exception as e:
            print(f"Error extracting {group_name}/{frame_key}: {e}")

    if entity['animations']:
        ENTITIES.append(entity)

# HTML Generation
html_assets = []

for ent in ENTITIES:
    current_card_html = f"""
    <div class="asset-card category-{' '.join(ent['tags']).lower()}" data-tags="{' '.join(ent['tags']).lower()}">
        <div class="header">
            <span class="number">#{ent['number']:03d}</span>
            <span class="title">{ent['name']}</span>
        </div>
        <div class="tags">
            {' '.join([f'<span class="tag">{t}</span>' for t in ent['tags']])}
        </div>
        
        <div class="animations-container">
    """
    
    for anim_name, frames in ent['animations'].items():
        # Clean name
        display_name = anim_name.title()
        frames_json = json.dumps(frames)
        
        current_card_html += f"""
            <div class="anim-box">
                <div class="preview-window">
                    <img src="{IMG_DIR}/{frames[0]}" class="anim-target" data-frames='{frames_json}' data-index="0" data-timer="0">
                </div>
                <div class="anim-label">{display_name}</div>
            </div>
        """
        
    current_card_html += f"""
        </div>
        <div class="actions" style="margin-top:auto; padding-top:10px; text-align:right;">
             <button onclick="launchEditor('{ent['id']}', '{list(ent['animations'].keys())[0]}')" class="filter-btn" style="font-size:12px;">EDIT</button>
        </div>
    </div>
    """
    html_assets.append(current_card_html)

    # Generate Options for Dropdown
    options_html = "<option value=''>-- Select New Asset --</option>"
    for ent in ENTITIES:
        # Only allow Items, Blocks, Enemies, Characters
        allowed = ['items', 'blocks', 'enemies', 'characters']
        if any(tag in allowed for tag in [t.lower() for t in ent['tags']]):
             # Use the first animation frame or idle as reference
             # We need to pass the ID (group name) and specific sprite name?
             # Actually ENTITIES are grouped.
             # Let's pass 'cat:name'.
             # ent['id'] is the category key usually... wait.
             # In data collection: id = group_name (e.g. 'mario', 'items')
             # animations keys are the sprite names.
             
             for anim in ent['animations']:
                 val = f"{ent['id']}:{anim}"
                 # Get representative image
                 frames = ent['animations'][anim]
                 img_path = f"{IMG_DIR}/{frames[0]}" if frames else ""
                 options_html += f"<option value='{val}' data-img='{img_path}'>{ent['id'].title()} - {anim}</option>"

    # --- SLOTS CATEGORY ---
    slot_symbols = {
        'mario': ('mario', 'stand'),
        'luigi': ('koopa_green', 'walk_1'), 
        'mushroom': ('items', 'mushroom_super'),
        'star': ('items', 'star_1'),
        'coin': ('items', 'coin_1'),
        'shell': ('koopa_red', 'shell_1'),
        'spiny': ('spiny', 'walk_1'),
        'flower': ('items', 'flower_fire'),
        'flyer': ('koopa_green', 'fly_1'),
        'jackpot': ('blocks', 'question_3'),
        'wild': ('blocks', 'question_1')
    }

    print("Generating Slot Assets...")
    for sym_name, (cat, sprite_name) in slot_symbols.items():
        # Get Sprite Data
        try:
             # Access config['sprite_coords']
             cat_data = config.get('sprite_coords', {}).get(cat, {})
             sprite_data = cat_data.get(sprite_name)
        except: sprite_data = None
        
        if not sprite_data: 
            print(f"Slot Asset Missing: {cat}/{sprite_name}")
            continue
        
        # Crop logic using Pygame
        x, y, w, h = sprite_data['x'], sprite_data['y'], sprite_data['w'], sprite_data['h']
        sheet_filename = sprite_data.get('file', 'spritesheet') 
        
        if sheet_filename not in SHEETS:
             print(f"Sheet missing: {sheet_filename}")
             continue
             
        sheet_surf = SHEETS[sheet_filename]
        
        # Create surface for the sprite
        sprite_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        sprite_surf.blit(sheet_surf, (0, 0), (x, y, w, h))
        
        # Scale (4x)
        final_surf = pygame.transform.scale(sprite_surf, (w*4, h*4))
        
        # Save
        out_name = f"slot_{sym_name}.png"
        pygame.image.save(final_surf, os.path.join(IMG_DIR, out_name))
        
        # HTML Card
        current_card_html = f"""
        <div class="asset-card category-slots" data-tags="slots {cat}">
            <div class="header">
                <span class="number">#SLOT</span>
                <span class="title">{sym_name.upper()}</span>
            </div>
            <div class="animations-container">
                <div class="anim-box">
                    <div class="preview-window">
                        <img src="{IMG_DIR}/{out_name}" class="anim-target" data-frames='["{out_name}"]' data-index="0" data-timer="0">
                    </div>
                    <div class="anim-label">Current: {cat}/{sprite_name}</div>
                </div>
            </div>
            <div class="actions" style="margin-top:auto; padding-top:10px; display:flex; flex-direction:column; gap:5px;">
                 <select id="sel_{sym_name}" onchange="previewSlotAsset(this)" style="background:#333; color:white; border:1px solid #555; padding:4px; font-size:11px; width:100%;">
                    {options_html}
                 </select>
                 <button onclick="updateSlotAsset('{sym_name}', document.getElementById('sel_{sym_name}').value)" class="filter-btn" style="background:#0078d4; width:100%; font-size:12px;">SET NEW ASSET</button>
            </div>
        </div>
        """
        html_assets.append(current_card_html)

# Full HTML (Replaced with new structure)
full_html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Mario Tetris Asset Browser</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #121212; color: #eee; padding: 20px; }}
        h1 {{ color: #fe1553; text-align: center; font-variant: small-caps; letter-spacing: 2px; }}
        
        .controls {{ text-align: center; margin-bottom: 30px; }}
        .filter-btn {{ background: #333; border: 1px solid #444; color: #fff; padding: 8px 16px; margin: 0 5px; cursor: pointer; border-radius: 20px; transition: 0.2s; }}
        .filter-btn:hover, .filter-btn.active {{ background: #fe1553; border-color: #fe1553; }}
        
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 25px; }}
        
        .asset-card {{ background: #1e1e1e; border-radius: 8px; border: 1px solid #333; padding: 15px; display: flex; flex-direction: column; }}
        .asset-card:hover {{ border-color: #555; box-shadow: 0 4px 12px rgba(0,0,0,0.3); }}
        
        .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #2a2a2a; padding-bottom: 10px; margin-bottom: 10px; }}
        .number {{ color: #666; font-family: monospace; font-size: 14px; }}
        .title {{ font-weight: bold; font-size: 18px; color: #fff; }}
        
        .tags {{ margin-bottom: 15px; }}
        .tag {{ font-size: 10px; background: #2a2a2a; padding: 3px 8px; border-radius: 4px; color: #aaa; margin-right: 5px; text-transform: uppercase; }}
        
        .animations-container {{ display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; }}
        
        .anim-box {{ text-align: center; background: #1a1a1a; padding: 10px; border-radius: 6px; border: 1px solid #2a2a2a; }}
        .preview-window {{ width: 80px; height: 80px; display: flex; align-items: center; justify-content: center; margin-bottom: 5px; overflow: hidden; }}
        .preview-window img {{ max-width: 100%; max-height: 100%; image-rendering: pixelated; }}
        .anim-label {{ font-size: 11px; color: #888; }}
        
    </style>
</head>
<body>
    <h1>Mario Tetris Assets</h1>
    
    <div class="controls">
        <button class="filter-btn active" onclick="filter('all')">All</button>
        <button class="filter-btn" onclick="filter('slots')">Slots</button>
        <button class="filter-btn" onclick="filter('characters')">Characters</button>
        <button class="filter-btn" onclick="filter('enemies')">Enemies</button>
        <button class="filter-btn" onclick="filter('items')">Items</button>
        <button class="filter-btn" onclick="filter('blocks')">Blocks</button>
        <button class="filter-btn" onclick="filter('ui')">UI</button>
        <button class="filter-btn" onclick="filter('tetris')">Tetris</button>
        <button class="filter-btn" onclick="filter('environment')">Environment</button>
    </div>

    <div class="grid">
        {''.join(html_assets)}
    </div>

    <script>
        // Check protocol
        if (window.location.protocol === 'file:') {{
            const msg = "WARNING: You are opening this file directly. The 'EDIT' buttons will NOT work.\\n\\nPlease run 'serve_guide.py' and open http://localhost:8080";
            alert(msg);
            document.body.insertAdjacentHTML('afterbegin', '<div style="background:red;color:white;padding:10px;text-align:center;font-weight:bold;">' + msg + '</div>');
        }}

        function launchEditor(cat, spr) {{
            fetch('/edit?cat=' + cat + '&spr=' + spr).then(() => {{
                console.log('Editor launched for ' + cat + '/' + spr);
            }}).catch(e => console.error(e));
        }}

        function updateSlotAsset(slot_sym, new_val) {{
            if (!new_val) return;
            // new_val is "category:sprite_name"
            const [cat, spr] = new_val.split(':');
            fetch('/update_slot?sym=' + slot_sym + '&cat=' + cat + '&spr=' + spr).then(() => {{
                alert('Slot Asset Updated! Restarting Slot Machine...');
            }}).catch(e => {{
                console.error(e);
                alert('Failed to update asset');
            }});
        }}

        function previewSlotAsset(selectEl) {{
            const option = selectEl.options[selectEl.selectedIndex];
            const imgPath = option.dataset.img;
            if (!imgPath) return;
            
            // Find card
            const card = selectEl.closest('.asset-card');
            const img = card.querySelector('.anim-target');
            const label = card.querySelector('.anim-label');
            
            img.src = imgPath;
            // disabling animation loop for this one temporarily or just let it be replaced?
            // The animation loop updates 'src' based on 'data-frames'.
            // We should update 'data-frames' to contain just this single image to stop it jumping back.
            img.dataset.frames = JSON.stringify([imgPath.split('/').pop()]);
            img.dataset.index = 0;
            
            label.innerText = "Selected: " + option.text;
        }}

        // filtering
        function filter(tag) {{
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            event.target.classList.add('active');
            
            document.querySelectorAll('.asset-card').forEach(c => {{
                if (tag === 'all' || c.dataset.tags.includes(tag)) {{
                    c.style.display = 'flex';
                }} else {{
                    c.style.display = 'none';
                }}
            }});
        }}
        
        // Animation Loop
        setInterval(() => {{
            document.querySelectorAll('.anim-target').forEach(img => {{
                const frames = JSON.parse(img.dataset.frames);
                if (frames.length > 1) {{
                    let idx = parseInt(img.dataset.index);
                    idx = (idx + 1) % frames.length;
                    img.dataset.index = idx;
                    img.src = "{IMG_DIR}/" + frames[idx];
                }}
            }});
        }}, 200); // 200ms frame time
    </script>
</body>
</html>
"""

with open("asset_browser.html", "w") as f:
    f.write(full_html)

print("Generated asset_browser.html")
os.system("start asset_browser.html")
