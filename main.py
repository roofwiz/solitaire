
import sys
import os

# Ensure game root is in path for web/pygbag
game_root = os.path.dirname(os.path.abspath(__file__))
if game_root not in sys.path:
    sys.path.append(game_root)

# FORCE REBUILD 6:23PM
import pygame
import random
import json
import asyncio
import math
import sys
from level_layouts import get_layout
import time # Added by user

# Early Mixer Hint for Pygbag/Web
try:
    if not pygame.mixer.get_init():
        pygame.mixer.pre_init(44100, -16, 2, 1024)
except: pass

from settings import game_settings
from asset_loader import init_asset_loader, AssetLoader
from asset_editor import AssetEditor
from src.config import *
from src.ai_player import TetrisBot
from src.luigi_generator import generate_luigi_sprites
from src.bonus_level import BonusLevel
from src.scene_dark_world import Scene_DarkWorld
from src.scene_intro import IntroScene


# --- Game Configuration ---


# --- DAS Configuration ---
DAS_DELAY = 0.3  # Initial delay before auto-repeat
DAS_REPEAT = 0.12 # Speed of auto-repeat

# --- Colors & Style ---
C_BLACK = (10, 10, 10)
C_DARK_BLUE = (20, 20, 40)
C_GRID_BG = (30, 30, 50)
C_NEON_PINK = (255, 20, 147)
C_NEON_BLUE = (100, 200, 255)
C_WHITE = (240, 240, 240)
C_RED = (255, 50, 50)
C_GREEN = (50, 255, 50)
C_GOLD = (255, 215, 0)
C_ORANGE = (255, 100, 30)
C_GHOST = (128, 128, 128, 100) 

# --- Levels ---
LINES_TO_CLEAR_LEVEL = 10

# Tetromino shapes and colors
TETROMINO_DATA = {
    'I': {'shape': [[1, 1, 1, 1]], 'color': (0, 255, 255)},
    'O': {'shape': [[1, 1], [1, 1]], 'color': (255, 255, 0)},
    'T': {'shape': [[0, 1, 0], [1, 1, 1]], 'color': (128, 0, 128)},
    'L': {'shape': [[0, 0, 1], [1, 1, 1]], 'color': (255, 165, 0)},
    'J': {'shape': [[1, 0, 0], [1, 1, 1]], 'color': (0, 0, 255)},
    'S': {'shape': [[0, 1, 1], [1, 1, 0]], 'color': (0, 255, 0)},
    'Z': {'shape': [[1, 1, 0], [0, 1, 1]], 'color': (255, 0, 0)}
}

COLOR_TO_SPRITE = {
    (0, 255, 255): 'cyan',
    (255, 255, 0): 'yellow',
    (128, 0, 128): 'purple',
    (255, 165, 0): 'orange',
    (0, 0, 255): 'blue',
    (0, 255, 0): 'green',
    (255, 0, 0): 'red'
}

# Wall Kick Data (SRS-like)
WALL_KICK_DATA = {
    'JLSTZ': [
        [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)],
        [(0, 0), (1, 0), (1, -1), (0, 2), (1, 2)],
        [(0, 0), (1, 0), (1, -1), (0, 2), (1, 2)],
        [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)],
        [(0, 0), (1, 0), (1, 1), (0, -2), (1, -2)],
        [(0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)],
        [(0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)],
        [(0, 0), (1, 0), (1, 1), (0, -2), (1, -2)],
    ],
    'I': [
        [(0, 0), (-2, 0), (1, 0), (-2, -1), (1, 2)],
        [(0, 0), (2, 0), (-1, 0), (2, 1), (-1, -2)],
        [(0, 0), (-1, 0), (2, 0), (-1, 2), (2, -1)],
        [(0, 0), (1, 0), (-2, 0), (1, -2), (-2, 1)],
        [(0, 0), (2, 0), (-1, 0), (2, 1), (-1, -2)],
        [(0, 0), (-2, 0), (1, 0), (-2, -1), (1, 2)],
        [(0, 0), (1, 0), (-2, 0), (1, -2), (-2, 1)],
        [(0, 0), (-1, 0), (2, 0), (-1, 2), (2, -1)],
    ]
}

# --- Global Helper Functions ---

# --- Level Themes (Mario Style) ---
LEVEL_THEMES = [
    # 1. OVERWORLD (Sky Blue / Brown)
    {'name': 'OVERWORLD', 'bg': (92, 148, 252), 'accent': (181, 101, 29), 'grid_alpha': 180},
    # 2. UNDERGROUND (Black / Blue-Teal)
    {'name': 'UNDERGROUND', 'bg': (15, 15, 15), 'accent': (0, 128, 136), 'grid_alpha': 120},
    # 3. WATER WORLD (Deep Blue / Sea Green)
    {'name': 'WATER WORLD', 'bg': (32, 56, 236), 'accent': (0, 168, 0), 'grid_alpha': 150},
    # 4. CASTLE (Dark Grey / Fire Red)
    {'name': 'CASTLE', 'bg': (32, 32, 32), 'accent': (216, 40, 0), 'grid_alpha': 200},
    # 5. MUSHROOM (Dark Red / Peach)
    {'name': 'MUSHROOM', 'bg': (139, 0, 0), 'accent': (255, 218, 185), 'grid_alpha': 160},
    # 6. SNOW LAND (White-ish / Ice Blue)
    {'name': 'SNOW LAND', 'bg': (240, 248, 255), 'accent': (0, 191, 255), 'grid_alpha': 140},
    # 7. HAUNTED (Deep Purple / Ghost White)
    {'name': 'HAUNTED', 'bg': (48, 25, 52), 'accent': (248, 248, 255), 'grid_alpha': 190},
    # 8. SKY LAND (Cloud Blue / Vine Green)
    {'name': 'SKY LAND', 'bg': (135, 206, 235), 'accent': (34, 139, 34), 'grid_alpha': 170},
    # 9. DESERT (Sand / Pyramid Brown)
    {'name': 'DESERT', 'bg': (244, 164, 96), 'accent': (139, 69, 19), 'grid_alpha': 160},
    # 10. HYPERSPACE (Dark Space / Star Yellow)
    {'name': 'HYPERSPACE', 'bg': (10, 0, 20), 'accent': (255, 215, 0), 'grid_alpha': 130},
]
def draw_block(screen, x, y, color):
    """Draws a single Tetris block on the grid."""
    px = PLAYFIELD_X + x * BLOCK_SIZE
    py = PLAYFIELD_Y + y * BLOCK_SIZE
    pygame.draw.rect(screen, color, (px, py, BLOCK_SIZE, BLOCK_SIZE))
    # Bevel effect
    pygame.draw.rect(screen, (255, 255, 255), (px, py, BLOCK_SIZE, BLOCK_SIZE), 1)

def draw_heart(surface, x, y, size, active=True):
    """Draws a polished Mario-style heart."""
    rect = pygame.Rect(x, y, size, size)
    if not active:
        # Draw empty heart tray (darker circle with outline)
        pygame.draw.circle(surface, (40, 0, 0), (x + size//2, y + size//2), size//2 - 2)
        pygame.draw.circle(surface, (100, 40, 40), (x + size//2, y + size//2), size//2 - 2, 2)
        return

    # Draw active heart
    color = C_RED
    shadow = (150, 0, 0)
    highlight = (255, 150, 150)
    
    # Rounded heart shapes
    r = size // 2
    pygame.draw.circle(surface, color, (x + r//2 + 2, y + r//2 + 2), r//2 + 1)
    pygame.draw.circle(surface, color, (x + size - r//2 - 2, y + r//2 + 2), r//2 + 1)
    
    points = [
        (x + 2, y + r + 2),
        (x + size - 2, y + r + 2),
        (x + size//2, y + size - 2)
    ]
    pygame.draw.polygon(surface, color, points)
    
    # Subtle highlight for "Premium" look
    pygame.draw.circle(surface, highlight, (x + r//2 + 1, y + r//2 + 1), 2)

class Polyomino:
    # SHAPE DEFINITIONS
    SHAPES = {
        'I': [(-1, 0), (0, 0), (1, 0), (2, 0)],
        'O': [(0, 0), (1, 0), (0, 1), (1, 1)],
        'T': [(-1, 0), (0, 0), (1, 0), (0, 1)],
        'S': [(-1, 0), (0, 0), (0, 1), (1, 1)],
        'Z': [(-1, 1), (0, 1), (0, 0), (1, 0)],
        'J': [(-1, 0), (0, 0), (1, 0), (1, -1)],
        'L': [(-1, 0), (0, 0), (1, 0), (-1, -1)]
    }
    COLORS = {
        'I': (0, 255, 255), 'O': (255, 255, 0), 'T': (128, 0, 128),
        'S': (0, 255, 0), 'Z': (255, 0, 0), 'J': (0, 0, 255), 'L': (255, 165, 0)
    }

    def __init__(self, shape_key):
        self.x = GRID_WIDTH // 2 - 1
        self.y = 0  
        self.shape_key = shape_key
        self.name = shape_key # Added for sprite mapping support
        self.blocks = list(self.SHAPES[shape_key])
        self.color = self.COLORS[shape_key]
        self.rotation_index = 0

    def rotate(self, direction=1):
        if self.shape_key == 'O': return
        new_blocks = []
        for block in self.blocks:
            bx, by = block
            if direction == 1: new_x, new_y = -by, bx
            else: new_x, new_y = by, -bx
            new_blocks.append((new_x, new_y))
        self.blocks = new_blocks

class Spawner:
    def __init__(self):
        self.bag = []
        self.fill_bag()

    def fill_bag(self):
        self.bag = ['I', 'O', 'T', 'S', 'Z', 'J', 'L']
        random.shuffle(self.bag)

    def get_next_piece(self):
        if len(self.bag) == 0: self.fill_bag()
        return Polyomino(self.bag.pop(0))

class SpriteManager:
    def __init__(self):
        self.images = {}
        images_config = game_settings.config.get('images', {})
        for name, filename in images_config.items():
            try:
                path = os.path.join('assets', filename)
                if os.path.exists(path):
                    self.images[name] = pygame.image.load(path).convert_alpha()
                    print(f"Loaded spritesheet: {name} ({filename})")
                else:
                    print(f"Spritesheet NOT found: {name} ({path})")
            except Exception as e:
                print(f"Error loading spritesheet {name}: {e}")
        
        # Legacy support for self.spritesheet
        self.spritesheet = self.images.get('spritesheet')
        self.sprite_data = game_settings.config.get('sprite_coords', {})
            
        # Load Waterworld BG
        self.waterworld_bg = None
        try:
            path = game_settings.get_asset_path('images', 'waterworld')
            if path and os.path.exists(path):
                img = pygame.image.load(path).convert()
                self.waterworld_bg = pygame.transform.scale(img, (WINDOW_WIDTH, WINDOW_HEIGHT))
        except: pass
    def get_waterworld_bg(self):
        return self.waterworld_bg

    def get_sprite(self, char_name, frame_name, scale_factor=2.0):
        try:
            coords = self.sprite_data[char_name][frame_name]
            sheet_name = coords.get('file', 'spritesheet')
            sheet = self.images.get(sheet_name)
            if not sheet: return None
            
            rect = pygame.Rect(coords['x'], coords['y'], coords['w'], coords['h'])
            if not sheet.get_rect().contains(rect): return None
            image = sheet.subsurface(rect)
            new_height = int(BLOCK_SIZE * scale_factor)
            aspect = image.get_width() / image.get_height()
            new_width = int(new_height * aspect)
            return pygame.transform.scale(image, (new_width, new_height))
        except KeyError: return None

    def get_animation_frames(self, char_name, scale_factor=1.5, prefix=None): # Tuned scale factor
        if not self.spritesheet: return []
        frames = []
        if char_name in self.sprite_data:
            # Sort keys to ensure order (e.g. fly_1 before fly_2)
            keys = sorted(self.sprite_data[char_name].keys())
            for frame_name in keys:
                if prefix and not frame_name.startswith(prefix): continue
                
                frame = self.get_sprite(char_name, frame_name, scale_factor)
                if frame: frames.append(frame)
        return frames

    def get_cloud_image(self, size=(32, 24)):
        # Use sprite sheet cloud if possible
        if self.spritesheet:
            cloud = self.get_sprite("cloud", "walk_1", scale_factor=1.0)
            if cloud: return pygame.transform.scale(cloud, size)
            
        # Fallback to single file if sheet fails
        try:
            path = game_settings.get_asset_path('images', 'cloud_fallback')
            if path and os.path.exists(path):
                img = pygame.image.load(path).convert_alpha()
                return pygame.transform.scale(img, size)
        except: return None

class BackgroundElement:
    def __init__(self, theme_type, sprite_manager=None):
        self.type = theme_type
        self.x = random.randint(0, WINDOW_WIDTH)
        self.y = random.randint(0, WINDOW_HEIGHT)
        self.vx = random.uniform(-20, 20)
        self.vy = random.uniform(10, 40)
        self.size = random.randint(4, 12)
        self.color = (255, 255, 255, 100)
        self.angle = random.uniform(0, 360)
        self.rotate_speed = random.uniform(-2, 2)
        self.image = None
        
        # Sprite Logic
        if sprite_manager:
            if theme_type == 'OVERWORLD':
                 # Clouds
                 self.image = sprite_manager.get_sprite('cloud', 'walk_1')
                 if self.image: 
                     self.vy = random.uniform(-5, 5)
                     self.vx = random.uniform(5, 15)
                     
            elif theme_type == 'UNDERGROUND':
                 # Brick Shards
                 self.image = sprite_manager.get_sprite('blocks', 'brick_piece_1')
                 if self.image: 
                     self.vy = random.uniform(20, 60)
                     
            elif theme_type == 'WATER':
                 # Bubbles -> use simple circle or specific bubble sprite if exists
                 self.vy = random.uniform(-30, -10)
                 self.color = (150, 220, 255, 80)
                 
            elif theme_type == 'CASTLE':
                 # Embers
                 self.color = (255, 100, 30, 150)
                 self.vy = random.uniform(-40, -10)
                 
            elif theme_type == 'MUSHROOM':
                 # Mushroom spots / tiny mushrooms
                 self.image = sprite_manager.get_sprite('items', 'mushroom_1up')
                 if self.image:
                     self.image = pygame.transform.scale(self.image, (16, 16))
                     
        # Fallback physics per theme if no sprite
        if not self.image:
            if theme_type == 'OCEAN':
                self.color = (150, 220, 255, 80)
                self.vy = random.uniform(-30, -10)
            elif theme_type == 'FIRE':
                self.color = (255, 100, 30, 150)
                self.vy = random.uniform(-60, -20)
            elif theme_type == 'FOREST':
                self.color = (100, 200, 100, 120)
                self.vy = random.uniform(20, 50)
            elif theme_type == 'CRYSTAL':
                self.color = (180, 240, 255, 180)
                self.vy = random.uniform(5, 15)

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.angle += self.rotate_speed
        
        if self.y < -50: self.y = WINDOW_HEIGHT + 50
        if self.y > WINDOW_HEIGHT + 50: self.y = -50
        if self.x < -50: self.x = WINDOW_WIDTH + 50
        if self.x > WINDOW_WIDTH + 50: self.x = -50

    def draw(self, surface):
        if self.image:
            # Draw sprite
            h_w = self.image.get_width() // 2
            h_h = self.image.get_height() // 2
            # Simple rotation
            if abs(self.rotate_speed) > 0.1:
                rot_img = pygame.transform.rotate(self.image, self.angle)
                surface.blit(rot_img, (int(self.x) - rot_img.get_width()//2, int(self.y) - rot_img.get_height()//2))
            else:
                surface.blit(self.image, (int(self.x) - h_w, int(self.y) - h_h))
        else:
            # Fallback shapes
            if self.type in ['OCEAN', 'WATER']:
                pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.size, 1)
            elif self.type in ['FIRE', 'CASTLE']:
                glow = self.size * 2
                s = pygame.Surface((glow*2, glow*2), pygame.SRCALPHA)
                pygame.draw.circle(s, (*self.color[:3], 100), (glow, glow), glow)
                surface.blit(s, (int(self.x-glow), int(self.y-glow)))
            elif self.type == 'FOREST':
                points = [
                    (self.x, self.y - self.size),
                    (self.x + self.size, self.y),
                    (self.x, self.y + self.size),
                    (self.x - self.size, self.y)
                ]
                pygame.draw.polygon(surface, self.color, points)
            else:
                pygame.draw.rect(surface, self.color, (int(self.x), int(self.y), self.size, self.size))

class Turtle:
    ENEMY_TYPE = 'green'
    def __init__(self, is_golden=False, enemy_type=None, tetris=None):
        self.x = random.randint(0, GRID_WIDTH - 1)
        self.y = -2.0
        self.speed = 1.5 
        self.state = 'active'
        self.direction = random.choice([-1, 1])
        self.is_golden = is_golden
        self.enemy_type = enemy_type if enemy_type else self.ENEMY_TYPE
        self.tetris = tetris
        self.vx = 0
        self.vy = self.speed # Initial fall speed
        
        # Frame Loading Logic
        raw_frames = self.get_frames()
        if isinstance(raw_frames, dict):
             self.fly_frames = raw_frames.get('fly', [])
             self.walk_frames = raw_frames.get('walk', [])
             self.shell_frames = raw_frames.get('shell', [])
        else:
             self.fly_frames = []
             self.walk_frames = raw_frames
             self.shell_frames = []

        # Generate directional frames
        # All enemies face LEFT in sprite sheet - flip to create RIGHT
        self.walk_frames_left = self.walk_frames
        self.walk_frames_right = [pygame.transform.flip(f, True, False) for f in self.walk_frames_left]
        
        self.fly_frames_left = self.fly_frames
        self.fly_frames_right = [pygame.transform.flip(f, True, False) for f in self.fly_frames_left]
        
        self.shell_frames_left = self.shell_frames
        self.shell_frames_right = [pygame.transform.flip(f, True, False) for f in self.shell_frames_left]
        
        # Golden Tint (Apply to all if generic method used or just handle separately)
        # Using pre-generated GOLDEN_TURTLE_FRAMES which is just a list (walk only for now)
        if self.is_golden and not self.walk_frames:
             pass # Golden frames are likely just walk frames in list format
             
        self.current_frame = 0
        self.last_update = pygame.time.get_ticks()
        self.move_timer = 0
        self.move_interval = 0.5 
        self.landed_timer = 0
        self.max_lifetime = 15.0 
        self.animation_speed = 200 
        self.dying_timer = 0 
        
        # Turn counter for smart turtles
        self.turns_at_edge = 0

    def get_frames(self):
        if self.is_golden: return Tetris.GOLDEN_TURTLE_FRAMES
        if self.enemy_type == 'red': return Tetris.RED_TURTLE_FRAMES
        if self.enemy_type == 'spiny': return Tetris.SPINY_FRAMES
        if self.enemy_type == 'blooper': return Tetris.BLOOPER_FRAMES
        if self.enemy_type == 'piranha': return Tetris.PIRANHA_FRAMES
        if self.enemy_type == 'magic_mushroom':
            return [self.tetris.sprite_manager.get_sprite('items', 'mushroom_super', scale_factor=1.5)]
        return Tetris.TURTLE_FRAMES

    def update_animation(self):
        now = pygame.time.get_ticks()
        frames = []
        anim_speed = self.animation_speed
        
        if self.state == 'dying': 
            # Use specific shell frames for the spin
            frames = self.shell_frames_left if self.direction == -1 else self.shell_frames_right
            if not frames: frames = self.shell_frames
            
            # Spin is fast
            anim_speed = 60 # 60ms between frames
            
        elif self.state == 'flying':
            frames = self.fly_frames_right if self.direction == 1 else self.fly_frames_left
            
        elif self.state in ['active', 'landed']:
            frames = self.walk_frames_right if self.direction == 1 else self.walk_frames_left
        
        if frames and len(frames) > 0 and now - self.last_update > anim_speed:
            self.last_update = now
            self.current_frame = (self.current_frame + 1) % len(frames)

    def update_movement(self, delta_time, game_grid):
        # Anti-Stuck / Squish Logic: If inside a block, DIE INSTANTLY
        ix, iy = int(self.x + 0.5), int(self.y + 0.5)
        if 0 <= ix < GRID_WIDTH and 0 <= iy < GRID_HEIGHT:
            if game_grid.grid[iy][ix] is not None:
                # If they are at the very bottom, let them "jump out" to be fair
                if iy >= GRID_HEIGHT - 2 and not hasattr(self, 'jump_lock'):
                    self.state = 'active'
                    self.vy = -12.0 # REAL jump up!
                    self.jump_lock = True
                else:
                    # SQUISH!
                    self.state = 'dead' 
                    if game_grid.tetris:
                        game_grid.tetris.spawn_particles(PLAYFIELD_X + self.x * BLOCK_SIZE, 
                                                       PLAYFIELD_Y + self.y * BLOCK_SIZE, 
                                                       (255, 255, 255), count=5)
                    return 'SQUISHED'
        if self.state == 'dying':
            self.dying_timer += delta_time
            
            # Simple shake effect - no arc needed
            self.shake_offset_x = random.uniform(-0.15, 0.15)
            self.shake_offset_y = random.uniform(-0.1, 0.1)
            
            # Quick death - 0.4 seconds
            return self.dying_timer > 0.4

        if self.state == 'falling_out':
            self.y += 10 * delta_time 
            return self.y > GRID_HEIGHT + 2
        
        # THROWN state - arc trajectory (used by Lakitu's Spinies)
        if self.state == 'thrown':
            self.x += getattr(self, 'vx', 0) * delta_time
            self.y += self.vy * delta_time
            self.vy += 20.0 * delta_time  # Gravity
            
            # Land on floor or blocks
            if self.y >= GRID_HEIGHT - 1:
                self.y = GRID_HEIGHT - 1
                self.state = 'landed'
                self.vy = 0
                self.vx = 0
            elif int(self.y + 1) < GRID_HEIGHT and int(self.x) >= 0 and int(self.x) < GRID_WIDTH:
                if game_grid.grid[int(self.y + 1)][int(self.x)] is not None:
                    self.y = int(self.y)
                    self.state = 'landed'
                    self.vy = 0
                    self.vx = 0
            return False

        if self.state == 'flying':
             # Flying Logic (Horizontal with slight descent or hover)
             self.x += self.direction * self.speed * delta_time
             self.y += 0.5 * delta_time # Very slow descent
             
             # Bounce Walls
             if self.x <= 0: self.direction = 1; self.x = 0
             if self.x >= GRID_WIDTH - 1: self.direction = -1; self.x = GRID_WIDTH - 1
             
             # Check Collision (Grid or Floor - broad check for wings clipping)
             # Check corners to ensure we clip wings if we touch ANYTHING
             collision = False
             check_points = [(self.x + 0.1, self.y + 0.1), (self.x + 0.9, self.y + 0.1), 
                             (self.x + 0.1, self.y + 0.9), (self.x + 0.9, self.y + 0.9)]
             
             for cx, cy in check_points:
                 icx, icy = int(cx), int(cy)
                 if icy >= GRID_HEIGHT or (0 <= icx < GRID_WIDTH and 0 <= icy < GRID_HEIGHT and game_grid.grid[icy][icx] is not None):
                     collision = True
                     break
             
             if collision:
                  self.state = 'active'
                  self.vy = self.speed  # Start falling with gravity
                  # Pop up slightly to avoid being stuck in the block
                  self.y = max(0, int(self.y) - 0.1)
             return False

        if self.state == 'active':
            # Use velocity and gravity
            self.y += self.vy * delta_time
            self.vy += 25.0 * delta_time # Standard Gravity
            
            # Handle horizontal velocity (for thrown enemies like Spinies)
            if hasattr(self, 'vx') and self.vx != 0:
                self.x += self.vx * delta_time
                self.vx *= 0.98  # Friction to slow down
                if abs(self.vx) < 0.1: self.vx = 0
            
            landed_y = int(self.y + 1)
            landed_x = int(self.x)
            
            # 1. Land on floor (Bottom of grid)
            if landed_y >= GRID_HEIGHT:
                # Play landing sound based on fall speed
                if hasattr(self, 'tetris') and self.tetris:
                    if self.vy > 8:  # Fast fall = long drop
                        self.tetris.sound_manager.play('impact_heavy')
                    else:  # Short fall
                        self.tetris.sound_manager.play('enemy_land')
                self.y = GRID_HEIGHT - 1
                self.vy = 0
                self.state = 'landed'
                self.move_timer = 0
                self.landed_timer = 0
                return False
                
            # 2. Land on blocks (Check CENTER of turtle for reliable landing)
            check_x = int(self.x + 0.5)
            if self.vy >= 0 and 0 <= check_x < GRID_WIDTH and 0 <= landed_y < GRID_HEIGHT and game_grid.grid[landed_y][check_x] is not None:
                # Play landing sound based on fall speed
                if hasattr(self, 'tetris') and self.tetris:
                    if self.vy > 8:  # Fast fall = long drop
                        self.tetris.sound_manager.play('impact_heavy')
                    else:  # Short fall
                        self.tetris.sound_manager.play('enemy_land')
                self.y = landed_y - 1 
                self.vy = 0
                self.state = 'landed'
                self.move_timer = 0
                self.landed_timer = 0
                return False
            
            # If we fall past the screen entirely
            if self.y > GRID_HEIGHT + 2:
                self.state = 'falling_out'
                return True # Signal removal if needed

        elif self.state == 'landed':
            self.landed_timer += delta_time
            if self.landed_timer > self.max_lifetime:
                self.state = 'falling_out'
                return False

            self.move_timer += delta_time
            if self.move_timer >= self.move_interval:
                self.move_timer -= self.move_interval
                next_x = int(self.x + self.direction)
                
                if 0 <= next_x < GRID_WIDTH:
                    # Logic to check walls and holes
                    block_below_next = int(self.y) + 1
                    block_in_front = 0 <= next_x < GRID_WIDTH and game_grid.grid[int(self.y)][next_x] is not None
                    has_ground = (block_below_next < GRID_HEIGHT and game_grid.grid[block_below_next][next_x] is not None) or (block_below_next == GRID_HEIGHT)
                    
                    if self.enemy_type == 'red':
                         # SMART TURN LOGIC
                         if block_in_front or not has_ground: 
                             if self.turns_at_edge < 3: # Turn around 3 times max
                                 self.direction *= -1
                                 self.turns_at_edge += 1
                             else:
                                 # Allowed to fall
                                 self.x = next_x
                                 self.state = 'active'
                         else: 
                             self.x = next_x
                             self.state = 'landed'
                    else: 
                        # Green / Spiny fall off edges blindly
                        if not has_ground and not block_in_front:
                            self.state = 'active'; self.x = next_x
                        elif block_in_front: self.direction *= -1
                        else: self.x = next_x
                else:
                    self.direction *= -1 
        return False

    def draw(self, surface):
        frames = []
        if self.state == 'flying': frames = self.fly_frames_right if self.direction == 1 else self.fly_frames_left
        elif self.state in ['active', 'landed']: frames = self.walk_frames_right if self.direction == 1 else self.walk_frames_left
        elif self.state == 'dying': frames = getattr(self, 'shell_frames_left', [])
        
        if not frames and hasattr(self, 'walk_frames'): frames = self.walk_frames
        
        img = None
        if frames:
            img = frames[int(self.current_frame) % len(frames)]
            
        if img:
            scale = 1.0
            game = getattr(self, 'tetris', None)
            if game and getattr(game, 'mega_mode', False):
                scale = 2.0
            
            if scale != 1.0:
                w, h = img.get_size()
                img = pygame.transform.scale(img, (int(w*scale), int(h*scale)))
            
            px = PLAYFIELD_X + self.x * BLOCK_SIZE
            py = PLAYFIELD_Y + self.y * BLOCK_SIZE
            
            # Apply shake offset when dying
            if self.state == 'dying':
                px += getattr(self, 'shake_offset_x', 0) * BLOCK_SIZE
                py += getattr(self, 'shake_offset_y', 0) * BLOCK_SIZE
            
            if scale != 1.0:
                 offset = (scale - 1.0) * BLOCK_SIZE
                 px -= offset / 2
                 py -= offset 
            
            surface.blit(img, (px, py))

    def handle_stomp(self, game):
        game.sound_manager.play('stomp')
        self.state = 'dying'
        self.dying_timer = 0
        
        # Spawn particles for visual feedback
        game.spawn_particles(PLAYFIELD_X + self.x * BLOCK_SIZE, 
                           PLAYFIELD_Y + self.y * BLOCK_SIZE, 
                           (255, 255, 255), count=12)
        
        # Also add a popup as backup visual
        game.popups.append(PopupText(PLAYFIELD_X + self.x * BLOCK_SIZE, 
                                    PLAYFIELD_Y + self.y * BLOCK_SIZE, 
                                    "STOMP!", (255, 200, 0)))
        
        score = 500
        if self.is_golden:
            game.lives = min(game.lives + 1, 5)
            game.sound_manager.play('life')
            score = 2500
        else:
            game.turtles_stomped += 1
            if game.turtles_stomped % 5 == 0:
                game.lives = min(game.lives + 1, 5)
                game.sound_manager.play('life')
                
        if getattr(game, 'mega_mode', False):
             score *= 5
        return score

    def update(self, delta_time, game_grid):
        self.update_animation()
        return self.update_movement(delta_time, game_grid)

class RedTurtle(Turtle): 
    ENEMY_TYPE = 'red'
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.state = 'flying' # Start flying
class Spiny(Turtle):
    ENEMY_TYPE = 'spiny'
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure we have proper shell frames (use walk frames as fallback)
        if not self.shell_frames:
            self.shell_frames = self.walk_frames[:] if self.walk_frames else []
            self.shell_frames_left = self.walk_frames_left[:] if self.walk_frames_left else []
            self.shell_frames_right = self.walk_frames_right[:] if self.walk_frames_right else []
            
    def handle_stomp(self, game):
        # In Tetris mode, crushing a Spiny with a block should just kill it normally
        # No damage to player!
        return super().handle_stomp(game)

class Hammer:
    def __init__(self, x, y, dx, dy, sprite_manager):
        self.x = x
        self.y = y
        self.vx = dx * 5.0
        self.vy = dy * -8.0  # Initial jump up
        self.sprite_manager = sprite_manager
        self.timer = 0
        self.angle = 0
        self.sprite = sprite_manager.get_sprite('hammer', 'default', scale_factor=2.0)
        
    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 25.0 * dt # Gravity
        self.angle += 360 * dt * 2 # Spin
        
    def draw(self, surface):
        if self.sprite:
            px = PLAYFIELD_X + self.x * BLOCK_SIZE
            py = PLAYFIELD_Y + self.y * BLOCK_SIZE
            rot_img = pygame.transform.rotate(self.sprite, self.angle)
            surface.blit(rot_img, rot_img.get_rect(center=(px, py)))

class HammerBro(Turtle):
    ENEMY_TYPE = 'hammerbro'
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.throw_timer = 2.0
        self.jump_timer = 3.0
        self.speed = 1.0
        self.y = GRID_HEIGHT - 1
        self.state = 'landed'
        self.vy = 0
        
    def update_movement(self, dt, grid):
        # Walk back and forth in a small area
        self.x += self.direction * self.speed * dt
        if self.x < 0: self.direction = 1
        elif self.x > GRID_WIDTH - 1: self.direction = -1
        
        # Jumping logic
        self.jump_timer -= dt
        if self.jump_timer <= 0:
            self.jump_timer = 3.0 + random.random() * 2
            self.vy = -12.0 # Big jump
            self.state = 'jumping'
            
        if self.state == 'jumping':
            self.y += self.vy * dt
            self.vy += 30 * dt # Gravity
            if self.y >= GRID_HEIGHT - 1:
                self.y = GRID_HEIGHT - 1
                self.state = 'landed'
                self.vy = 0
                
        # Throwing logic
        self.throw_timer -= dt
        if self.throw_timer <= 0:
            self.throw_timer = 2.5
            # Spawn Hammer
            if self.tetris:
                h = Hammer(self.x, self.y, self.direction, 1.0, self.tetris.sprite_manager)
                self.tetris.effects.append(h)
        return False

class Blooper(Turtle):
    ENEMY_TYPE = 'blooper'
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.swim_timer = 0
        self.speed = 2.0
        
    def update_movement(self, dt, grid):
        """Swim up diagonally, then sink slowly"""
        self.swim_timer += dt
        
        # 2-second cycle
        cycle = self.swim_timer % 2.0
        if cycle < 0.5:
            # Burst swim up
            self.y -= self.speed * dt * 2
            self.x += self.direction * self.speed * dt
        else:
            # Sink down
            self.y += self.speed * dt * 0.5
            
        # Screen wrap x
        if self.x < 0: self.direction = 1
        if self.x > GRID_WIDTH - 1: self.direction = -1
        
        # Kill if off bottom
        if self.y > GRID_HEIGHT: return True
        return False

class Piranha(Turtle):
    ENEMY_TYPE = 'piranha'
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.offset = 0
        
    def update_movement(self, dt, grid):
        """Bob up and down like a piranha plant in a pipe"""
        self.swim_timer += dt
        self.offset = math.sin(self.swim_timer * 4) * 0.8
        self.y = self.base_y + self.offset
        return False # Doesn't die by falling off screen normally

class MagicMushroom(Turtle): 
    """Randomly becomes Life (Green), Poison (Purple), or Mega (Orange) Mushroom."""
    ENEMY_TYPE = 'magic_mushroom'
    
    def __init__(self, tetris_ref):
        self.tetris = tetris_ref
        super().__init__(enemy_type='magic_mushroom', tetris=tetris_ref)
        self.speed = 1.5
        self.max_lifetime = 25.0
        self.state = 'active'
        self.move_timer = 0
        self.move_interval = 0.4
        
        # Determine Type: 10% Mega, 30% Poison, 60% Life
        roll = random.random()
        if roll < 0.1: self.m_type = 'mega'
        elif roll < 0.4: self.m_type = 'poison'
        else: self.m_type = 'life'
        
        # Load Correct Sprite
        sprite_name = 'mushroom_1up' # Default Green
        if self.m_type == 'poison': sprite_name = 'mushroom_poison'
        elif self.m_type == 'mega': sprite_name = 'mushroom_mega'
        
        img = self.tetris.sprite_manager.get_sprite('items', sprite_name, scale_factor=2.0)
        
        # Fallback Tints if specific sprites missing
        if not img and self.m_type == 'poison':
             img = self.tetris.sprite_manager.get_sprite('items', 'mushroom_1up', scale_factor=2.0)
             if img:
                 img = img.copy()
                 img.fill((150, 0, 150), special_flags=pygame.BLEND_MULT) # Purple Tint
                 
        if not img and self.m_type == 'mega':
             img = self.tetris.sprite_manager.get_sprite('items', 'mushroom_super', scale_factor=3.0) # Larger!
        
        if not img: # Ultimate fallback
             img = self.tetris.sprite_manager.get_sprite('items', 'mushroom_1up', scale_factor=2.0)

        if img:
            # Fix transparency Manual (set_colorkey ignored on alpha surfaces)
            img = img.copy() # Ensure unique copy
            img.lock()
            for x in range(img.get_width()):
                for y in range(img.get_height()):
                    c = img.get_at((x, y))
                    if c[0] < 10 and c[1] < 10 and c[2] < 10: # Near black
                        img.set_at((x, y), (0, 0, 0, 0))
            img.unlock()
            
            self.walk_frames = [img]
            self.walk_frames_left = [img]
            self.walk_frames_right = [img]
        else:
             fallback = pygame.Surface((BLOCK_SIZE, BLOCK_SIZE))
             fallback.fill((0,255,0))
             self.walk_frames = [fallback]
             self.walk_frames_left = [fallback]
             self.walk_frames_right = [fallback]
             
        self.fly_frames_left = []
        self.fly_frames_right = []
        self.shell_frames_left = []
        self.shell_frames_right = []
        
    def handle_stomp(self, game):
        if self.state == 'dying': return 0
        self.state = 'dying'
        
        # ARC INITIALIZATION: Start exactly where we are
        self.dying_timer = 0
        self.dying_vx = random.choice([-6.0, 6.0])
        self.dying_vy = -8.0 
        
        # Visual Juice: Smoke Poof
        if game:
            game.spawn_particles(PLAYFIELD_X + self.x * BLOCK_SIZE, 
                               PLAYFIELD_Y + self.y * BLOCK_SIZE, 
                               (255, 255, 255), count=10)
        
        if self.m_type == 'poison':
            game.lives -= 1
            game.sound_manager.play('lifelost')
            game.popups.append(PopupText(PLAYFIELD_X + self.x*BLOCK_SIZE, PLAYFIELD_Y + self.y*BLOCK_SIZE, "POISON! -1 LIFE", C_RED))
            return 0
        elif self.m_type == 'mega':
            if hasattr(game, 'trigger_mega_mode'): game.trigger_mega_mode(20.0)
            return 1000
        else:
             # Life - Verify it works!
             game.lives = min(game.lives + 1, 5)
             game.sound_manager.play('life')
             game.popups.append(PopupText(PLAYFIELD_X + self.x*BLOCK_SIZE, PLAYFIELD_Y + self.y*BLOCK_SIZE, "1UP! +1 LIFE", C_GREEN))
             print(f"[BONUS] 1UP Awarded! Current Lives: {game.lives}")
             return 1000
        
    def get_frames(self):
        return []

    def update_movement(self, delta_time, game_grid):
        """Turtle-like physics: fall with gravity, walk back and forth when landed."""
        
        if self.state == 'dying':
            self.dying_timer += delta_time
            self.y += 8 * delta_time  # Fall when dying
            return self.dying_timer > 1.5
        
        if self.state == 'falling_out':
            self.y += 8 * delta_time
            return self.y > GRID_HEIGHT + 2
        
        # Active/Falling state - gravity pulls down
        if self.state == 'active':
            self.y += self.speed * delta_time
            
            # Check for landing
            landed_y = int(self.y + 1)
            landed_x = int(self.x)
            
            # Land on floor or blocks
            if landed_y >= GRID_HEIGHT:
                self.y = GRID_HEIGHT - 1
                self.state = 'landed'
                self.move_timer = 0
            elif 0 <= landed_x < GRID_WIDTH and 0 <= landed_y < GRID_HEIGHT:
                if game_grid.grid[landed_y][landed_x] is not None:
                    self.y = landed_y - 1
                    self.state = 'landed'
                    self.move_timer = 0
        
        # Landed state - walk back and forth like turtles
        elif self.state == 'landed':
            self.landed_timer += delta_time
            if self.landed_timer > self.max_lifetime:
                self.state = 'falling_out'
                return False
            
            self.move_timer += delta_time
            if self.move_timer >= self.move_interval:
                self.move_timer -= self.move_interval
                next_x = int(self.x + self.direction)
                
                if 0 <= next_x < GRID_WIDTH:
                    # Check if there's a wall in front
                    block_in_front = game_grid.grid[int(self.y)][next_x] is not None if 0 <= int(self.y) < GRID_HEIGHT else False
                    
                    # Check if there's ground below the next position
                    block_below_next = int(self.y) + 1
                    has_ground = (block_below_next >= GRID_HEIGHT or 
                                  (0 <= next_x < GRID_WIDTH and 0 <= block_below_next < GRID_HEIGHT and 
                                   game_grid.grid[block_below_next][next_x] is not None))
                    
                    if block_in_front:
                        # Hit a wall, turn around
                        self.direction *= -1
                    elif not has_ground:
                        # No ground ahead - fall or turn around
                        self.x = next_x
                        self.state = 'active'  # Start falling
                    else:
                        # Safe to move
                        self.x = next_x
                else:
                    # Hit edge of playfield, turn around
                    self.direction *= -1
        
        return False

    def handle_stomp(self, game):
        """Collecting the mushroom gives 1UP!"""
        game.sound_manager.play('life')
        game.lives = min(game.lives + 1, 5)
        game.popups.append(PopupText(PLAYFIELD_X + self.x*BLOCK_SIZE, PLAYFIELD_Y + self.y*BLOCK_SIZE, "1UP!", (255, 215, 0)))
        self.state = 'dying'
        return 1000


class MagicStar(Turtle):
    """Bouncing star power-up that grants 30 seconds of invincibility."""
    ENEMY_TYPE = 'magic_star'
    
    def __init__(self, tetris_ref):
        self.tetris = tetris_ref
        super().__init__(enemy_type='magic_star')
        self.speed = 2.5  # Stars move faster
        self.max_lifetime = 20.0
        self.state = 'active'
        self.vy = 0  # Vertical velocity for bouncing
        self.bounce_force = -8.0  # How high it bounces
        
        # Load animated star sprites (cycles through colors)
        self.star_frames = []
        for i in range(1, 5):
            frame = self.tetris.sprite_manager.get_sprite('items', f'star_{i}', scale_factor=2.0)
            if frame:
                # Fix using Manual Alpha Clearing
                frame = frame.copy()
                frame.lock()
                for x in range(frame.get_width()):
                    for y in range(frame.get_height()):
                        c = frame.get_at((x, y))
                        if c[0] < 10 and c[1] < 10 and c[2] < 10:
                            frame.set_at((x, y), (0, 0, 0, 0))
                frame.unlock()
                self.star_frames.append(frame)
        
        if self.star_frames:
            self.walk_frames = self.star_frames
            self.walk_frames_left = self.star_frames
            self.walk_frames_right = self.star_frames
        else:
            # Fallback - yellow star
            fallback = pygame.Surface((BLOCK_SIZE, BLOCK_SIZE), pygame.SRCALPHA)
            pygame.draw.polygon(fallback, (255, 255, 0), [
                (BLOCK_SIZE//2, 0), (BLOCK_SIZE*0.6, BLOCK_SIZE*0.4),
                (BLOCK_SIZE, BLOCK_SIZE*0.4), (BLOCK_SIZE*0.7, BLOCK_SIZE*0.6),
                (BLOCK_SIZE*0.8, BLOCK_SIZE), (BLOCK_SIZE//2, BLOCK_SIZE*0.75),
                (BLOCK_SIZE*0.2, BLOCK_SIZE), (BLOCK_SIZE*0.3, BLOCK_SIZE*0.6),
                (0, BLOCK_SIZE*0.4), (BLOCK_SIZE*0.4, BLOCK_SIZE*0.4)
            ])
            self.walk_frames = [fallback]
            self.walk_frames_left = [fallback]
            self.walk_frames_right = [fallback]
        
        self.fly_frames_left = []
        self.fly_frames_right = []
        self.shell_frames_left = []
        self.shell_frames_right = []
        self.animation_speed = 100  # Faster animation for rainbow effect
        
    def get_frames(self):
        return []

    def update_movement(self, delta_time, game_grid):
        """Bouncing star physics - bounces high and fast!"""
        
        if self.state == 'dying':
            self.dying_timer += delta_time
            return self.dying_timer > 0.5
        
        if self.state == 'falling_out':
            self.y += 10 * delta_time
            return self.y > GRID_HEIGHT + 2
            
        # WALK & JUMP LOGIC
        # Defaults to Turtle walking behavior? 
        # But we want to bounce continuously or Jump over holes.
        
        # 1. Apply Gravity if in air
        block_below = int(self.y + 1)
        center_x = int(self.x + 0.5)
        on_ground = False
        
        if block_below >= GRID_HEIGHT:
            on_ground = True
            self.y = GRID_HEIGHT - 1
            self.vy = 0
        elif 0 <= center_x < GRID_WIDTH and 0 <= block_below < GRID_HEIGHT and game_grid.grid[block_below][center_x] is not None:
            on_ground = True
            self.y = block_below - 1
            self.vy = 0
        else:
            # In Air
            self.vy += 30.0 * delta_time # Heavy gravity
            self.y += self.vy * delta_time
            
        # 2. Move Horizontal
        next_x = self.x + self.direction * self.speed * delta_time
        
        # 3. Check for Walls or Holes to JUMP
        if on_ground:
            # Wall ahead?
            wall_x = int(next_x + (0.5 if self.direction > 0 else -0.5))
            wall_hit = False
            if not (0 <= wall_x < GRID_WIDTH): wall_hit = True # Edge of screen
            elif game_grid.grid[int(self.y)][wall_x] is not None: wall_hit = True # Block
            
            # Hole ahead? (Check block below next step)
            hole_ahead = False
            if 0 <= wall_x < GRID_WIDTH:
                 if block_below < GRID_HEIGHT and game_grid.grid[block_below][wall_x] is None:
                     hole_ahead = True
            
            if wall_hit:
                # Bounce/Jump back?
                self.direction *= -1
                self.vy = -12.0 # Jump!
                self.y -= 0.1 # Lift off
            elif hole_ahead:
                # JUMP over hole!
                self.vy = -15.0
                self.y -= 0.1
                
        # Apply move
        self.x += self.direction * self.speed * delta_time
        
        # Bounds check
        if self.x < 0: self.x = 0; self.direction = 1
        if self.x > GRID_WIDTH - 1: self.x = GRID_WIDTH - 1; self.direction = -1

        return False
        
        landed = False
        if iy >= GRID_HEIGHT:
            self.y = GRID_HEIGHT - 1
            landed = True
        elif 0 <= ix < GRID_WIDTH and 0 <= iy < GRID_HEIGHT:
            if game_grid.grid[iy][ix] is not None:
                self.y = iy - 1
                landed = True
        
        if landed:
            self.vy = self.bounce_force  # BOUNCE high!
        
        # Wall bouncing
        if self.x < 0:
            self.x = 0
            self.direction = 1
        if self.x > GRID_WIDTH - 1:
            self.x = GRID_WIDTH - 1
            self.direction = -1
        
        # Lifetime check
        self.landed_timer += delta_time
        if self.landed_timer > self.max_lifetime:
            self.state = 'falling_out'
        
        return False

    def handle_stomp(self, game):
        """Collecting the star gives 30 seconds of invincibility!"""
        game.sound_manager.play('life')
        game.star_active = True
        game.star_timer = 30.0  # 30 seconds of invincibility!
        game.popups.append(PopupText(PLAYFIELD_X + self.x*BLOCK_SIZE, PLAYFIELD_Y + self.y*BLOCK_SIZE, "STAR POWER!", (255, 255, 0)))
        self.state = 'dying'
        return 2000

class Cloud:
    def __init__(self, sprite_manager):
        self.image = sprite_manager.get_cloud_image((64, 48))
        
        self.x = random.randint(0, WINDOW_WIDTH)
        self.y = random.randint(0, 200)
        self.speed = random.uniform(10, 30)
        self.direction = 1
        
    def update(self, delta_time):
        self.x += self.speed * delta_time
        if self.x > WINDOW_WIDTH + 50: 
            self.x = -100
            self.y = random.randint(0, 200)

    def draw(self, surface):
        if self.image:
            surface.blit(self.image, (self.x, self.y))

class PopupText:
    def __init__(self, x, y, text, color=(255, 255, 255), size='small'):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.size = size # 'small', 'med', 'big'
        self.life = 1.0 # Seconds
        self.dy = -40 if size == 'big' else -30
        
    def update(self, dt):
        self.life -= dt
        self.y += self.dy * dt
        
    def draw(self, surface, font_map):
        if self.life > 0:
            font = font_map.get(self.size, font_map['small'])
            surf = font.render(self.text, True, self.color)
            rect = surf.get_rect(center=(self.x, self.y))
            surface.blit(surf, rect)

class SparkleEffect:
    def __init__(self, x, y, sprite_manager):
        self.x = x
        self.y = y
        self.sprite_manager = sprite_manager
        self.frame = 1
        self.timer = 0
        self.life = 0.5 
        
    def update(self, dt):
        self.timer += dt
        self.frame = min(8, int((self.timer / self.life) * 8) + 1)
        return self.timer < self.life
        
    def draw(self, surface):
        img = self.sprite_manager.get_sprite('items', f'sparkle_{self.frame}', scale_factor=BLOCK_SIZE/16/2.0)
        if img:
            surface.blit(img, (self.x, self.y))

class BonusPlayer:
    def __init__(self, x, y, sprite_manager):
        self.x = x
        self.y = y
        self.vx = 0
        self.vy = 0
        self.on_ground = False
        self.facing_right = True
        self.width = 16
        self.height = 16
        self.sprite_manager = sprite_manager
        
    def update(self, dt, blocks, world_type='WATER'):
        # Physics Constants
        if world_type == 'WATER':
            GRAVITY = 200
            MOVE_SPEED = 120
            SWIM_FORCE = -200
            MAX_FALL_SPEED = 150
            JUMP_FORCE = SWIM_FORCE
        else: # CLOUD WORLD
            GRAVITY = 800
            MOVE_SPEED = 180
            JUMP_FORCE = -400
            MAX_FALL_SPEED = 500
            
        keys = pygame.key.get_pressed()
        
        # Horizontal Movement
        self.vx = 0
        if keys[pygame.K_LEFT]:
            self.vx = -MOVE_SPEED
            self.facing_right = False
        if keys[pygame.K_RIGHT]:
            self.vx = MOVE_SPEED
            self.facing_right = True
            
        # Apply X move
        self.x += self.vx * dt
        
        # Collision X
        player_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        for b in blocks:
            if player_rect.colliderect(b):
                if self.vx > 0: self.x = b.left - self.width
                elif self.vx < 0: self.x = b.right
        
        # Vertical Movement
        self.vy += GRAVITY * dt
        
        # Jump / Swim
        if keys[pygame.K_UP]:
            if world_type == 'WATER':
                 self.vy = SWIM_FORCE
            elif self.on_ground:
                 self.vy = JUMP_FORCE
            
        # Cap falling speed
        if self.vy > MAX_FALL_SPEED: self.vy = MAX_FALL_SPEED
        
        self.y += self.vy * dt
        
        # Collision Y
        self.on_ground = False
        player_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        for b in blocks:
            if player_rect.colliderect(b):
                if self.vy > 0: 
                    self.y = b.top - self.height
                    self.vy = 0
                    self.on_ground = True
                elif self.vy < 0:
                    self.y = b.bottom
                    self.vy = 0
        
        # Screen Bounds
        if self.x < 0: self.x = 0
        if self.x > WINDOW_WIDTH - self.width: self.x = WINDOW_WIDTH - self.width
        if self.y > WINDOW_HEIGHT: # Fall off checks
            if world_type == 'WATER':
                 self.y = WINDOW_HEIGHT - self.height
            else:
                 # In cloud world, falling means respawn at top?
                 self.y = 0
                 self.x = 100
            self.vy = 0
        if self.y < 0: self.y = 0 # Ceiling


    def draw(self, surface):
        color = (255, 0, 0)
        sprite = None
        
        if self.sprite_manager:
            # Water World uses swim frames
            if self.vy != 0: # Moving vertically (swimming)
                 swim_frames = self.sprite_manager.get_animation_frames("mario", scale_factor=1.0, prefix="swim")
                 if swim_frames:
                     # Use vy to determine frame or just cycle
                     idx = int(pygame.time.get_ticks() / 150) % len(swim_frames)
                     sprite = swim_frames[idx]
            
            if not sprite:
                sprite = self.sprite_manager.get_sprite("mario", "stand", scale_factor=1.0)
            
        if sprite:
            if not self.facing_right:
                sprite = pygame.transform.flip(sprite, True, False)
            surface.blit(sprite, (self.x, self.y))
        else:
            pygame.draw.rect(surface, color, (self.x, self.y, self.width, self.height))

class SquidEnemy:
    def __init__(self, sprite_manager):
        self.x = random.choice([-20, WINDOW_WIDTH + 20])
        self.y = random.randint(100, WINDOW_HEIGHT - 50)
        self.speed = random.uniform(50, 80)
        self.vx = 0
        self.vy = 0
        self.move_timer = 0
        self.width = 16
        self.height = 24
        
        self.sprite_manager = sprite_manager
        self.frames = sprite_manager.get_animation_frames('squid', scale_factor=1.0)
        self.frame_index = 0
        self.anim_timer = 0
        self.state = 'sink' # sink or lunge
        
    def update(self, dt, player_x, player_y):
        self.move_timer -= dt
        
        # Blooper Logic: Sink slowly, then lunge up and towards player
        if self.state == 'sink':
            self.vy = 20 # Sink speed
            self.vx *= 0.95 # Drag
            
            if self.move_timer <= 0:
                self.state = 'lunge'
                self.move_timer = 0.8 # Lunge duration
                
                # Calculate lunge direction
                dx = player_x - self.x
                dy = (player_y - 20) - self.y # Aim slightly above player
                
                # Bloopers go UP when they move
                if dy > -20: dy = -50
                if dy < -100: dy = -100
                
                # Set Lunge velocity
                self.vx = 40 if dx > 0 else -40 # Fixed horizontal speed burst
                if abs(dx) < 10: self.vx = 0
                
                self.vy = -60 # Upward thrust
                
        elif self.state == 'lunge':
            if self.move_timer <= 0:
                self.state = 'sink'
                self.move_timer = 2.0 # Sink duration
                
        self.x += self.vx * dt
        self.y += self.vy * dt
        
        # Animation
        self.anim_timer += dt
        if self.state == 'lunge': self.frame_index = 1 # Closed/Thrust frame
        else: self.frame_index = 0 # Open/Sink frame
        
    def draw(self, surface):
        if self.frames:
            sprite = self.frames[self.frame_index % len(self.frames)]
            surface.blit(sprite, (self.x, self.y))
        else:
            # Fallback
            points = [
                (self.x + self.width//2, self.y),
                (self.x, self.y + self.height),
                (self.x + self.width, self.y + self.height)
            ]
            pygame.draw.polygon(surface, (255, 255, 255), points)

class CheepCheepEnemy:
    def __init__(self, sprite_manager):
        self.direction = random.choice([-1, 1])
        self.x = -20 if self.direction == 1 else WINDOW_WIDTH + 20
        self.y = random.randint(100, WINDOW_HEIGHT - 100)
        self.speed = random.uniform(60, 100)
        self.width = 16
        self.height = 16
        
        self.sprite_manager = sprite_manager
        self.frames = sprite_manager.get_animation_frames('cheepcheep_green', scale_factor=1.0)
        self.frame_index = 0
        self.anim_timer = 0
        
    def update(self, dt):
        self.x += self.speed * self.direction * dt
        
        # Animation
        self.anim_timer += dt
        if self.anim_timer > 0.15:
            self.anim_timer = 0
            self.frame_index += 1
            
    def draw(self, surface):
        if self.frames:
            sprite = self.frames[self.frame_index % len(self.frames)]
            if self.direction == 1:
                sprite = pygame.transform.flip(sprite, True, False) # Flip if swimming right
            surface.blit(sprite, (self.x, self.y))
        else:
            pygame.draw.rect(surface, (0, 255, 0), (self.x, self.y, self.width, self.height))



class BonusGame:
    def __init__(self, tetris_ref):
        self.tetris = tetris_ref
        self.active = False
        self.timer = 15.0
        self.score = 0
        self.world_type = 'WATER' # 'WATER' or 'CLOUD'
        
        self.blocks = []
        self.block_dirs = [] # For moving platforms
        self.coins = []
        self.squids = []
        self.squid_spawn_timer = 0
        
        self.player = BonusPlayer(50, 300, tetris_ref.sprite_manager)
        
    def start(self):
        self.active = True
        self.timer = 20.0
        self.score = 0
        
        # Level Generation
        self.blocks = []
        self.block_dirs = []
        self.coins = []
        
        if self.world_type == 'WATER':
            # Floor
            for i in range(0, WINDOW_WIDTH, 20):
                 self.blocks.append(pygame.Rect(i, WINDOW_HEIGHT - 20, 20, 20))
                 self.block_dirs.append(0)
            # Floating Platforms
            self.blocks.append(pygame.Rect(100, 300, 100, 20))
            self.block_dirs.append(0)
            self.blocks.append(pygame.Rect(300, 250, 100, 20))
            self.block_dirs.append(0)
            # Coins
            for _ in range(10):
                self.coins.append(pygame.Rect(random.randint(50, WINDOW_WIDTH-50), random.randint(50, WINDOW_HEIGHT-100), 10, 10))
                
        else: # CLOUD WORLD
            # No Floor
            # Starting platform
            self.blocks.append(pygame.Rect(50, 350, 100, 20))
            self.block_dirs.append(0)
            
            # Moving cloud platforms
            for i in range(5):
                y = 100 + i * 50
                x = random.randint(50, WINDOW_WIDTH - 150)
                self.blocks.append(pygame.Rect(x, y, 48, 16)) # Use cloud width
                self.block_dirs.append(random.choice([-1, 1]))
                self.coins.append(pygame.Rect(x + 20, y - 30, 10, 10))

        self.player.x, self.player.y = 100, 300
        self.player.vy = 0
        self.player.vx = 0
        
    def update(self, dt):
        if not self.active: return
        
        # Moving Platforms logic for Cloud World
        if self.world_type == 'CLOUD':
            for i, b in enumerate(self.blocks):
                if self.block_dirs[i] != 0:
                    b.x += self.block_dirs[i] * 50 * dt
                    if b.right > WINDOW_WIDTH: self.block_dirs[i] = -1
                    if b.left < 0: self.block_dirs[i] = 1
        
        # Spawn Squids
        if self.world_type == 'WATER':
            self.squid_spawn_timer += dt
            if self.squid_spawn_timer > 3.0:
                 if random.random() < 0.6:
                     self.squids.append(SquidEnemy(self.tetris.sprite_manager))
                 else:
                     self.squids.append(CheepCheepEnemy(self.tetris.sprite_manager))
                 self.squid_spawn_timer = 0
             
        # Update Squids
        player_rect = pygame.Rect(self.player.x, self.player.y, self.player.width, self.player.height)
        for s in self.squids[:]:
            if isinstance(s, SquidEnemy): s.update(dt, self.player.x, self.player.y)
            else: s.update(dt)
            
            s_rect = pygame.Rect(s.x, s.y, s.width, s.height)
            if s_rect.colliderect(player_rect):
                self.tetris.lives -= 1
                self.tetris.sound_manager.play('damage')
                self.squids.remove(s)
                if self.tetris.lives <= 0:
                    self.active = False
                    self.tetris.game_state = 'GAMEOVER'
                    return

        self.timer -= dt
        if self.timer <= 0:
            self.active = False
            if self.tetris.level_in_world == 1:
                self.tetris.game_state = 'WORLD_CLEAR'
                self.tetris.world_clear_timer = 3.0
                self.tetris.sound_manager.play('world_clear')
            else:
                self.tetris.game_state = 'PLAYING'
            return
            
        # Update Player Physics based on world
        # We need to tell BonusPlayer which physics to use
        self.player.update(dt, self.blocks, self.world_type)
        
        # Coin Collection
        player_rect = pygame.Rect(self.player.x, self.player.y, self.player.width, self.player.height)
        for c in self.coins[:]:
            if player_rect.colliderect(c):
                self.coins.remove(c)
                self.score += 100
                self.tetris.score += 100
                self.tetris.coins += 1
                if self.tetris.coins >= 100:
                    self.tetris.coins -= 100
                    self.tetris.lives = min(self.tetris.lives + 1, 5)
                    self.tetris.sound_manager.play('life')
                    self.tetris.popups.append(PopupText(WINDOW_WIDTH//2, 50, "1UP! 100 COINS", (255, 215, 0)))
                
    def draw(self, surface):
        # BG
        bg_key = 'waterworld' if self.world_type == 'WATER' else 'cloudworld'
        bg = None
        # Get from SpriteManager
        if self.world_type == 'WATER':
            bg = self.tetris.sprite_manager.get_waterworld_bg()
        else:
            # We need a getter for cloudworld or just use waterworld logic
            path = game_settings.get_asset_path('images', 'cloudworld')
            if path and os.path.exists(path):
                img = pygame.image.load(path).convert()
                bg = pygame.transform.scale(img, (WINDOW_WIDTH, WINDOW_HEIGHT))
        
        if bg:
            surface.blit(bg, (0, 0))
        else:
            surface.fill((100, 100, 255))
        
        # Blocks / Platforms
        cloud_sprite = self.tetris.sprite_manager.get_sprite('cloud_platform', 'idle', scale_factor=1.0)
        
        for b in self.blocks:
            if self.world_type == 'CLOUD' and cloud_sprite:
                surface.blit(cloud_sprite, (b.x, b.y))
            else:
                pygame.draw.rect(surface, (139, 69, 19), b)
                pygame.draw.rect(surface, (0,0,0), b, 1)
            
        # Coins
        for c in self.coins:
            pygame.draw.circle(surface, (255, 215, 0), c.center, 5)

        # Squids
        for s in self.squids:
            s.draw(surface)
            
        self.player.draw(surface)
        
        font = self.tetris.font_small
        timer_surf = font.render(f"BONUS {self.world_type}: {int(self.timer)}", True, (255, 255, 255))
        surface.blit(timer_surf, (WINDOW_WIDTH//2 - 80, 20))

class Lakitu(Turtle):
    def __init__(self, tetris_ref):
        super().__init__(tetris=tetris_ref)
        self.tetris = tetris_ref
        self.enemy_type = 'lakitu'  # Make Lakitu identifiable
        self.y = 1
        self.x = -5
        self.speed = 3.0
        self.direction = 1
        self.throw_timer = 0
        self.state = 'active'
        self.hover_offset = 0
        
        # Load sprites - Make Lakitu bigger (was 2.0)
        self.sprite_default = tetris_ref.sprite_manager.get_sprite('lakitu', 'default', scale_factor=3.5)
        self.sprite_throw = tetris_ref.sprite_manager.get_sprite('lakitu', 'throw', scale_factor=3.5)
        self.is_throwing = False
        self.pending_spinies = []  # Queue to avoid modifying turtles during iteration
        
    def update(self, dt):
        self.hover_offset += dt * 5
        self.y = 1 + math.sin(self.hover_offset) * 0.5
        
        # Chase the player x slightly
        target_x = self.x
        if self.tetris and self.tetris.current_piece:
            target_x = self.tetris.current_piece.x
        
        if self.x < target_x: self.x += self.speed * dt * 0.5
        elif self.x > target_x: self.x -= self.speed * dt * 0.5
            
        self.throw_timer += dt
        if self.throw_timer > 4.0:
            # THROW ANIMATION pulse
            self.throw_timer = 0
            self.is_throwing = True
            
            if self.tetris:
                try:
                    # Queue Spiny spawn - don't add directly to avoid iteration issues
                    s = Spiny(tetris=self.tetris)
                    s.x = self.x
                    s.y = self.y + 1
                    s.state = 'thrown'  # Special state for arc movement
                    s.vy = -5.0 # Pop up slightly
                    s.vx = max(-3, min(3, (target_x - self.x)))  # Reduced momentum
                    self.pending_spinies.append(s)
                    self.tetris.popups.append(PopupText(PLAYFIELD_X + self.x*BLOCK_SIZE, PLAYFIELD_Y + self.y*BLOCK_SIZE, "SPINY!", C_RED))
                except Exception as e:
                    print(f"Lakitu Spiny spawn error: {e}")
        
        if self.is_throwing and self.throw_timer > 0.5:
            self.is_throwing = False
            
        # Flush pending spinies to the main turtle list (safe, after Lakitu's update)
        if self.pending_spinies and self.tetris:
            for s in self.pending_spinies:
                self.tetris.turtles.append(s)
            self.pending_spinies.clear()

    def draw(self, surface):
        px = PLAYFIELD_X + self.x * BLOCK_SIZE
        py = PLAYFIELD_Y + self.y * BLOCK_SIZE
        
        img = self.sprite_throw if self.is_throwing else self.sprite_default
        if img:
            surface.blit(img, (px, py))
        else:
             pygame.draw.rect(surface, (200, 200, 200), (px, py, 32, 24))


class BossFireball:
    def __init__(self, x, y, sprite_manager):
        self.x = x
        self.y = y
        self.vy = -4.0  # Slower fireballs (was -6)
        self.sprite_manager = sprite_manager
        self.width = 1.0
        self.height = 1.0
        self.timer = 0
        
    def update(self, dt):
        self.y += self.vy * dt
        self.timer += dt
        
    def draw(self, surface):
        px = PLAYFIELD_X + (self.x - 0.5) * BLOCK_SIZE
        py = PLAYFIELD_Y + (self.y - 0.5) * BLOCK_SIZE
        # Use fireball animation or fallback
        frames = self.sprite_manager.get_animation_frames('bowser', prefix='fire')
        if not frames:
            pygame.draw.circle(surface, (255, 100, 0), (int(px + BLOCK_SIZE//2), int(py + BLOCK_SIZE//2)), 12)
        else:
            idx = int(self.timer * 10) % len(frames)
            surface.blit(frames[idx], (px, py))

class BigBoss:
    def __init__(self, tetris_ref):
        self.tetris = tetris_ref
        self.x = GRID_WIDTH // 2 - 1.5
        self.y = GRID_HEIGHT - 1.0
        self.width = 3.0
        self.height = 3.0
        self.speed = 2.0
        self.direction = 1
        self.hp = 100
        self.max_hp = 100
        self.hit_timer = 0
        
        # Load Bowser Animation from spritesheet
        self.frames = tetris_ref.sprite_manager.get_animation_frames('bowser', scale_factor=3.0, prefix='walk')
        if not self.frames:
            # Fallback to big turtle if bowser missing in assets.json
            self.frames = tetris_ref.sprite_manager.get_animation_frames('koopa_red', scale_factor=6.0, prefix='walk')
            
        self.frame_index = 0
        self.anim_timer = 0
        self.attack_timer = 5.0
        self.fireballs = []
        
    def update(self, dt):
        # Move back and forth
        # Speed up as HP drops
        health_pct = max(0.2, self.hp / self.max_hp)
        current_speed = self.speed * (1.0 + (1.0 - health_pct) * 2.0)
        self.x += self.direction * current_speed * dt
        
        # Boundary check
        if self.x < 0:
            self.x = 0
            self.direction = 1
        elif self.x > GRID_WIDTH - self.width:
            self.x = GRID_WIDTH - self.width
            self.direction = -1
            
        # Animation
        self.anim_timer += dt
        if self.anim_timer > 0.15:
            self.anim_timer = 0
            if self.frames:
                self.frame_index = (self.frame_index + 1) % len(self.frames)
            
        if self.hit_timer > 0:
            self.hit_timer -= dt
            
        # Attack Logic - More forgiving
        self.attack_timer -= dt
        if self.attack_timer <= 0:
            # SHOOT FIREBALL
            self.attack_timer = 6.0 * health_pct + 2.5 # Slower attacks, more time to react
            fb = BossFireball(self.x + 1.5, self.y - 2.0, self.tetris.sprite_manager)
            self.fireballs.append(fb)
            self.tetris.sound_manager.play('fireball')
            
        # Update Fireballs
        for fb in self.fireballs[:]:
            fb.update(dt)
            if fb.y < -2:
                 self.fireballs.remove(fb)
                 
            # Hit check with current piece
            if self.tetris.current_piece:
                p = self.tetris.current_piece
                for bx, by in p.blocks:
                    gx, gy = p.x + bx, p.y + by
                    if abs(gx - fb.x) < 1.0 and abs(gy - fb.y) < 1.0:
                         # Hit! - Break the piece or add garbage?
                         # For now, just cancel the piece and add a penalty
                         self.tetris.sound_manager.play('damage')
                         self.tetris.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, "PIECE DESTROYED!", C_RED))
                         self.tetris.current_piece = self.tetris.next_piece
                         self.tetris.next_piece = self.tetris.spawner.get_next_piece()
                         if fb in self.fireballs: self.fireballs.remove(fb)
                         break
            
    def draw(self, surface):
        px = PLAYFIELD_X + self.x * BLOCK_SIZE
        # Boss is at the bottom of the grid
        py = PLAYFIELD_Y + (self.y - 2.5) * BLOCK_SIZE
        
        if not self.frames:
            # Fallback rect
            color = (255, 100, 100) if self.hit_timer > 0 else (200, 0, 0)
            rect = (px, py, self.width * BLOCK_SIZE, self.height * BLOCK_SIZE)
            pygame.draw.rect(surface, color, rect)
        else:
            img = self.frames[self.frame_index]
            if self.direction < 0:
                img = pygame.transform.flip(img, True, False)
                
            if self.hit_timer > 0:
                # Flash effect
                mask = pygame.mask.from_surface(img)
                flash_surf = mask.to_surface(setcolor=(255, 255, 255, 200), unsetcolor=(0, 0, 0, 0))
                surface.blit(img, (px, py))
                surface.blit(flash_surf, (px, py), special_flags=pygame.BLEND_RGBA_ADD)
            else:
                surface.blit(img, (px, py))

        # Draw Fireballs
        for fb in self.fireballs:
            fb.draw(surface)
        
        # Draw HP bar
        hp_bar_width = self.width * BLOCK_SIZE
        hp_rect = (px, py - 20, hp_bar_width, 8)
        pygame.draw.rect(surface, (50, 0, 0), hp_rect) # BG
        if self.hp > 0:
            curr_hp_width = (self.hp / self.max_hp) * hp_bar_width
            pygame.draw.rect(surface, (255, 0, 0), (px, py - 20, curr_hp_width, 8))
        pygame.draw.rect(surface, (255, 255, 255), hp_rect, 1) # Border



class Tetromino:
    def __init__(self, shape_name):
        self.name = shape_name
        self.shape = TETROMINO_DATA[shape_name]['shape']
        self.color = TETROMINO_DATA[shape_name]['color']
        self.rotation = 0
        self.x = GRID_WIDTH // 2 - len(self.shape[0]) // 2
        self.y = 0

    def get_rotated_shape(self):
        return [list(row) for row in zip(*self.shape[::-1])]


def draw_3d_block(surface, color, x, y, size):
    # Premium "Gem" Style Block
    # 1. Base Gradient (Darker at bottom)
    r, g, b = color[:3]
    h, s, v = pygame.Color(r, g, b).hsla[:3]
    
    # Create gradient effect
    for i in range(size):
        # Darken as we go down
        shade = max(0, 1.0 - (i / size) * 0.4) 
        row_color = (int(r * shade), int(g * shade), int(b * shade))
        pygame.draw.line(surface, row_color, (x, y + i), (x + size, y + i))
        
    # 2. Glassy Highlight (Top Left Triangle)
    s_high = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.polygon(s_high, (255, 255, 255, 60), [(0,0), (size, 0), (0, size)])
    surface.blit(s_high, (x, y))

    # 3. Inner Shine (Top Left Dot)
    pygame.draw.circle(surface, (255, 255, 255, 180), (x + 4, y + 4), 2)
    
    # 4. Refined Border
    pygame.draw.rect(surface, (255, 255, 255), (x, y, size, size), 1) # Outer thin light outline
    pygame.draw.rect(surface, (0, 0, 0, 100), (x, y, size, size), 2) # Inner dark definition

class Block:
    def __init__(self, color, block_type='normal', sprite_data=None):
        self.color = color
        self.type = block_type
        self.anim_offset = random.random() * 10 
        self.hit = False
        self.sprite_data = sprite_data # {'sprite': '...', 'category': '...'}

    def get_image(self, sprite_manager, timer):
        # 1. New Sprite Mapping System
        if self.sprite_data:
            cat = self.sprite_data.get('category')
            name = self.sprite_data.get('sprite')
            
            # Support pre-loaded/modified Surfaces (e.g. tinted blocks)
            if isinstance(name, pygame.Surface):
                return name

            
            # 2. Animated Enemies
            if cat in ['koopa_green', 'koopa_red', 'spiny']:
                # Use frames. Note: we need to handle "walk" prefix or not
                frames = sprite_manager.get_animation_frames(cat, prefix='walk', scale_factor=2.0)
                if not frames and 'walk_1' in name: # Fallback if specific sprite name given
                     pass 
                
                if frames:
                    # Animation speed
                    idx = int((timer + self.anim_offset) * 6) % len(frames)
                    return frames[idx]
            
            # 3. Static Items / Blocks
            # Map category to sheet name in assets.json keys
            # 'blocks', 'items' are direct keys.
            img = sprite_manager.get_sprite(cat, name, scale_factor=2.0)
            if img: return img

        # Fallbacks for legacy types
        if self.type == 'question':
            if self.hit:
                return sprite_manager.get_sprite('blocks', 'empty', scale_factor=2.0)
            f_idx = int((timer * 2 + self.anim_offset) % 3) + 1
            return sprite_manager.get_sprite('blocks', f'question_{f_idx}', scale_factor=2.0)
            
        if self.type == 'brick':
            return sprite_manager.get_sprite('blocks', 'brick', scale_factor=2.0)
            
        if self.type == 'coin':
            frames = [1, 2, 3, 2]
            f_idx = frames[int((timer * 8 + self.anim_offset) % 4)]
            return sprite_manager.get_sprite('items', f'coin_{f_idx}', scale_factor=2.0)
            
        return None

class Grid:
    def __init__(self, sprite_manager):
        self.sprite_manager = sprite_manager
        # Dual World Data
        self.grid_neon = [[None for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.grid_shadow = [[None for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        
        self.active_world = 'NEON'
        self.grid = self.grid_neon # Active Grid Pointer
        self.animation_timer = 0
    
    def set_world(self, world_name):
        self.active_world = world_name
        if world_name == 'SHADOW': self.grid = self.grid_shadow
        else: self.grid = self.grid_neon

    def check_collision_in_world(self, piece, world_name):
        target_grid = self.grid_shadow if world_name == 'SHADOW' else self.grid_neon
        for bx, by in piece.blocks:
            gx, gy = int(piece.x + bx), int(piece.y + by)
            if gx < 0 or gx >= GRID_WIDTH or gy >= GRID_HEIGHT: return True
            if gy >= 0 and target_grid[gy][gx] is not None: return True
        return False

    def check_collision(self, piece, inverted_gravity=False):
        if not hasattr(piece, 'blocks'):
             return False
             
        for bx, by in piece.blocks:
            gx, gy = int(piece.x + bx), int(piece.y + by)
            
            # Wall Collision (Left/Right)
            if gx < 0 or gx >= GRID_WIDTH: return True
            
            # Floor Collision (Normal)
            if not inverted_gravity and gy >= GRID_HEIGHT: return True
            
            # Ceiling Collision (Antigravity)
            if inverted_gravity and gy < 0: return True
            
            # Block Collision
            # Note: valid Y range is 0 to GRID_HEIGHT-1
            if 0 <= gy < GRID_HEIGHT:
                 if self.grid[gy][gx] is not None: return True
                 
        return False

    def lock_piece(self, piece):
        # Retrieve sprite data from config based on piece name
        t_data = TETROMINO_DATA.get(piece.name, {})
        sprite_data = None
        if 'sprite' in t_data:
            sprite_data = {'sprite': t_data['sprite'], 'category': t_data['category']}
            
        for bx, by in piece.blocks:
            gx, gy = int(piece.x + bx), int(piece.y + by)
            if 0 <= gy < GRID_HEIGHT and 0 <= gx < GRID_WIDTH:
                self.grid[gy][gx] = Block(piece.color, sprite_data=sprite_data)

    def clear_lines(self):
        lines_cleared = 0
        special_events = [] # For coins, items etc
        completed_line_indices = []  # Track which lines are complete for animation
        
        rows_to_keep = []
        for y in range(GRID_HEIGHT):
            cols = [self.grid[y][x] for x in range(GRID_WIDTH)]
            if None in cols:
                rows_to_keep.append(cols)
            else:
                # Check for unclearable blocks
                unclearable = False
                for block in cols:
                    if block and getattr(block, 'type', '') in ['solid', 'ground']:
                        unclearable = True
                        break
                
                if unclearable:
                     rows_to_keep.append(cols)
                else:
                    lines_cleared += 1
                    completed_line_indices.append(y)  # Save line index for animation
                # Check for special blocks in this line
                has_garbage = False
                for block in cols:
                    if block and getattr(block, 'type', '') == 'brick': has_garbage = True
                    if block and block.type == 'coin': special_events.append('COIN')
                    if block and block.type == 'question': special_events.append('ITEM')
                if has_garbage: special_events.append('BRICK_CLEAR')
        
        while len(rows_to_keep) < GRID_HEIGHT:
            rows_to_keep.insert(0, [None] * GRID_WIDTH)
            
        # Update references
        if self.active_world == 'SHADOW': self.grid_shadow = rows_to_keep
        else: self.grid_neon = rows_to_keep
        self.grid = rows_to_keep # Update Pointer
        
        return lines_cleared, special_events, completed_line_indices

    def draw(self, screen, total_time, draw_bg=True, alpha=255, level=1, bg_color=None, accent_color=None):
        # Draw Background 
        if draw_bg:
            bg_rect = (PLAYFIELD_X, PLAYFIELD_Y, PLAYFIELD_WIDTH, PLAYFIELD_HEIGHT)
            
            # Use passed color or default
            bg_col = bg_color if bg_color else (20, 20, 40)
            
            # Darken the background color slightly for the playfield
            dark_bg = [max(0, c - 40) for c in bg_col]
            
            # Premium Background: Vertical Gradient
            r, g, b = dark_bg
            # Fill with solid first for safety
            pygame.draw.rect(screen, dark_bg, bg_rect)
            
            # OVERLAY Gradient
            # for i in range(PLAYFIELD_HEIGHT):
            #     # Gradient factor (darker at bottom)
            #     f = 1.0 - (i / PLAYFIELD_HEIGHT) * 0.3
            #     col = (int(r * f), int(g * f), int(b * f))
            #     pygame.draw.line(screen, col, (PLAYFIELD_X, PLAYFIELD_Y + i), (PLAYFIELD_X + PLAYFIELD_WIDTH, PLAYFIELD_Y + i))
            
            # Pattern Overlay: Subtle Grid
            grid_surf = pygame.Surface((PLAYFIELD_WIDTH, PLAYFIELD_HEIGHT), pygame.SRCALPHA)
            for x in range(0, PLAYFIELD_WIDTH, BLOCK_SIZE):
                pygame.draw.line(grid_surf, (0, 0, 0, 20), (x, 0), (x, PLAYFIELD_HEIGHT))
            for y in range(0, PLAYFIELD_HEIGHT, BLOCK_SIZE):
                pygame.draw.line(grid_surf, (0, 0, 0, 20), (0, y), (PLAYFIELD_WIDTH, y))
            screen.blit(grid_surf, (PLAYFIELD_X, PLAYFIELD_Y))
            
            # Border Glow
            glow_color = accent_color if accent_color else ((100, 100, 255) if level % 2 == 0 else (255, 100, 100))
            
            # Glow Effect
            for i in range(5):
                alpha = 100 - i * 20
                s_glow = pygame.Surface((PLAYFIELD_WIDTH + i*4, PLAYFIELD_HEIGHT + i*4), pygame.SRCALPHA)
                msg_col = glow_color + (alpha,)
                pygame.draw.rect(s_glow, msg_col, (0, 0, s_glow.get_width(), s_glow.get_height()), 2)
                screen.blit(s_glow, (PLAYFIELD_X - i*2, PLAYFIELD_Y - i*2))
            # Inner line
            pygame.draw.rect(screen, (50, 50, 50), bg_rect, 1)

            
        # 1. Draw Inactive World (Ghost) - 15% Opacity
        ghost_grid = self.grid_shadow if self.active_world == 'NEON' else self.grid_neon
        self._render_layer(screen, ghost_grid, total_time, alpha=40)
        
        # 2. Draw Active World - 100% Opacity
        self._render_layer(screen, self.grid, total_time, alpha=255)

        # 3. Draw Ground Row (Decorative)
        if alpha == 255 and hasattr(self, 'ground_row') and self.ground_row:
             py = PLAYFIELD_Y + GRID_HEIGHT * BLOCK_SIZE
             for x, sprite in enumerate(self.ground_row):
                 if sprite:
                     px = PLAYFIELD_X + x * BLOCK_SIZE
                     screen.blit(sprite, (px, py))
                     
    def _render_layer(self, screen, grid_data, total_time, alpha=255):
        target_surf = screen
        ox, oy = PLAYFIELD_X, PLAYFIELD_Y
        
        if alpha < 255:
            target_surf = pygame.Surface((PLAYFIELD_WIDTH, PLAYFIELD_HEIGHT), pygame.SRCALPHA)
            target_surf.fill((0,0,0,0))
            ox, oy = 0, 0
            
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                block = grid_data[y][x]
                if block:
                     px, py = ox + x * BLOCK_SIZE, oy + y * BLOCK_SIZE
                     img = block.get_image(self.sprite_manager, total_time)
                     if img: target_surf.blit(img, (px, py))
                     else: draw_3d_block(target_surf, block.color, px, py, BLOCK_SIZE)
                     # Grid Lines
                     pygame.draw.rect(target_surf, (40, 40, 60), (px, py, BLOCK_SIZE, BLOCK_SIZE), 1)

        if alpha < 255:
            target_surf.set_alpha(alpha)
            screen.blit(target_surf, (PLAYFIELD_X, PLAYFIELD_Y))

class SoundManager:
    """
    Rethought SoundManager for high stability.
    Uses dedicated channels instead of mixer.music singleton to prevent double-playback.
    """
    def __init__(self):
        self.sounds = {}
        self.music_channel = None
        self.current_track_name = None
        self.master_volume = 0.7  # Standard background music level
        self.muted = False
        self.manual_stop = False
        
        # Audio System Setup
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.pre_init(44100, -16, 2, 1024)
                pygame.mixer.init()
            pygame.mixer.set_num_channels(32)
            # Reserve Channel 0 for Music
            self.music_channel = pygame.mixer.Channel(0)
        except Exception as e:
            print(f"[SoundManager] Mixer setup failed: {e}")

        # Playlists
        self.neon_playlist = [
            '2. Bring The Noise.mp3',
            '01. The James Bond Theme.mp3',
            '05. Ten in 2010.mp3',
            '06. Them and Us.mp3',
            '07. One Fine Day.mp3',
            'intro_theme.mp3',
            '02. undergroundtheme.mp3'
        ]
        self.neon_track_index = 0
        self.current_mode = 'intro'
        
        # Pre-load sounds via asset_loader logic
        self._load_sfx()

    def _load_sfx(self):
        sfx_files = {
            'rotate': 'rotate.wav',
            'lock': 'lock.wav',
            'clear': 'clear.wav',
            'stomp': 'stomp.wav',  # Single stomp
            'stomp_combo': 'impactGeneric_light_003.ogg',  # 2x stomp combo
            'enemy_land': 'impactGeneric_light_002.ogg',  # Enemy lands
            'enemy_spawn': 'impactGeneric_light_004.ogg',  # Enemy spawns/appears
            'impact_heavy': 'impactBell_heavy_004.ogg',  # Heavy impact (boss hit, etc)
            'life': 'life.wav',
            'damage': 'stomp.wav',
            'gameover': 'gameover.wav',
            'move': 'move.wav',  # Now distinct from rotate
            'coin': 'life.wav',
            'level_up': 'life.wav',
            'drop': 'lock.wav',
            'fireball': 'rotate.wav'
        }
        for name, fname in sfx_files.items():
            p = self._get_path(fname)
            if os.path.exists(p):
                try: self.sounds[name] = pygame.mixer.Sound(p)
                except: pass
        
        # Standard Game Balance Levels
        if 'enemy_land' in self.sounds:
            self.sounds['enemy_land'].set_volume(0.6)  # Audible but soft
        if 'enemy_spawn' in self.sounds:
            self.sounds['enemy_spawn'].set_volume(0.7)  # Noticeable
        if 'rotate' in self.sounds:
            self.sounds['rotate'].set_volume(0.5)  # Standard feedback level
        if 'move' in self.sounds:
            self.sounds['move'].set_volume(0.4)  # Slightly quieter than rotate

    def _get_path(self, f):
        base = globals().get('game_root', os.getcwd())
        paths = [
            os.path.join(base, 'assets', 'sounds', f),
            os.path.join(base, 'sounds', f),
            os.path.join(base, f)
        ]
        for p in paths:
            if sys.platform == 'emscripten': p = p.replace('\\', '/')
            if os.path.exists(p): return p
        return f

    def play(self, name):
        """Play a standard one-shot SFX"""
        if self.muted or name not in self.sounds: return
        try:
            # Use higher channels for SFX to not cut off music on Ch 0
            self.sounds[name].set_volume(self.master_volume)
            self.sounds[name].play()
        except: pass

    def play_track(self, track_name, force=False):
        """
        The GOLD STANDARD music play method.
        Only reloads if the track is actually different.
        """
        if not self.music_channel: return
        if self.current_track_name == track_name and not force:
            if self.music_channel.get_busy(): return

        p = self._get_path(track_name)
        if not os.path.exists(p):
            print(f"[SoundManager] Music file missing: {p}")
            return

        print(f"[SoundManager] Switching Music -> {track_name}")
        try:
            # Stop existing music immediately
            self.music_channel.stop()
            
            # Load as Sound object forWASMB/Web stability
            new_sound = pygame.mixer.Sound(p)
            new_sound.set_volume(0 if self.muted else self.master_volume)
            
            # Start fresh on reserved channel
            self.music_channel.play(new_sound, loops=-1, fade_ms=500)
            self.current_track_name = track_name
            self.manual_stop = False
        except Exception as e:
            print(f"[SoundManager] PlayTrack Error: {e}")

    def stop_music(self):
        self.manual_stop = True
        self.current_track_name = None
        if self.music_channel:
            self.music_channel.stop()
        print("[SoundManager] Music Stopped.")

    def play_music_gameplay(self):
        self.current_mode = 'gameplay'
        track = self.neon_playlist[self.neon_track_index]
        self.play_track(track)

    def next_track(self):
        self.neon_track_index = (self.neon_track_index + 1) % len(self.neon_playlist)
        self.play_music_gameplay()

    def update(self, dt):
        """Lightweight maintenance: only handle volume and basic state sync"""
        if self.muted:
            if self.music_channel and self.music_channel.get_volume() > 0:
                self.music_channel.set_volume(0)
        else:
            if self.music_channel and self.music_channel.get_volume() != self.master_volume:
                self.music_channel.set_volume(self.master_volume)

    def toggle_mute(self):
        self.muted = not self.muted
        return self.muted

    def set_volume(self, v):
        self.master_volume = max(0.0, min(1.0, v))

    def get_track_display_name(self):
        """Returns a clean name for the UI"""
        track = self.current_track_name or "Muted"
        name = track.split('/')[-1].split('\\')[-1].replace('.mp3', '')
        
        # Clean up specific tracks
        name_map = {
            '01. The James Bond Theme': 'James Bond',
            '02. undergroundtheme': 'Underground',
            '2. Bring The Noise': 'Bring The Noise',
            'intro_theme': 'Intro'
        }
        return name_map.get(name, name[:20])

    def next_song(self):
        """Alias for next_track"""
        self.next_track()

    def play_music_intro(self):
        """Play the dedicated intro theme"""
        self.current_mode = 'intro'
        self.play_track('intro_theme.mp3')

    def play_music(self):
        """Generic alias for playing gameplay music"""
        self.play_music_gameplay()
    
    def get_track_position(self):
        """Returns current track number and total tracks"""
        if self.current_mode == 'intro':
            return (1, 1) # Intro is single track
        return (self.neon_track_index + 1, len(self.neon_playlist))

    @property
    def volume(self):
        return self.master_volume
    
    @volume.setter
    def volume(self, v):
        self.set_volume(v)

class MobileControls:
    """Enhanced mobile touch controls with DAS, zones, and visual feedback"""
    
    # Zone layout (percentages of screen width)
    ZONE_LEFT = 0.30       # Left 30% = move left
    ZONE_RIGHT = 0.70      # Right 30% = move right  
    ZONE_CENTER = (0.30, 0.70)  # Middle 40% = rotate
    ZONE_BOTTOM = 0.85     # Bottom 15% = soft drop area
    
    # DAS (Delayed Auto Shift) settings
    DAS_DELAY = 0.18       # Initial delay before auto-repeat (seconds)
    DAS_REPEAT = 0.05      # Speed of auto-repeat (seconds)
    
    # Swipe settings
    SWIPE_THRESHOLD = 40   # Minimum pixels for swipe detection
    TAP_TIME_MAX = 0.25    # Maximum time for tap (seconds)
    
    def __init__(self, screen_dimensions):
        self.screen_w, self.screen_h = screen_dimensions
        self.reset()
        
        # Visual feedback
        self.touch_ripples = []  # [(x, y, start_time, type), ...]
        self.zone_highlight = None  # ('LEFT'/'RIGHT'/'CENTER'/'DOWN', start_time)
        
    def reset(self):
        """Reset all touch state"""
        self.touch_start = None
        self.touch_start_time = 0
        self.touch_current = None
        self.is_holding = False
        self.hold_zone = None  # 'LEFT', 'RIGHT', 'DOWN', or None
        self.das_timer = 0
        self.das_triggered = False
        self.last_das_move = 0
        
    def handle_touch_down(self, pos, game_time):
        """Called when touch starts. Returns immediate action or None."""
        self.touch_start = pos
        self.touch_start_time = game_time
        self.touch_current = pos
        self.is_holding = True
        self.das_timer = 0
        self.das_triggered = False
        
        # Add touch ripple effect
        self.touch_ripples.append((pos[0], pos[1], game_time, 'start'))
        
        # Determine which zone was touched for DAS
        x_pct = pos[0] / self.screen_w
        y_pct = pos[1] / self.screen_h
        
        if y_pct > self.ZONE_BOTTOM:
            self.hold_zone = 'DOWN'
        elif x_pct < self.ZONE_LEFT:
            self.hold_zone = 'LEFT'
        elif x_pct > self.ZONE_RIGHT:
            self.hold_zone = 'RIGHT'
        else:
            self.hold_zone = 'CENTER'
            
        self.zone_highlight = (self.hold_zone, game_time)
        
        return None  # No immediate action on touch down
    
    def handle_touch_move(self, pos):
        """Called during touch drag"""
        self.touch_current = pos
        
    def handle_touch_up(self, pos, game_time):
        """Called when touch ends. Returns action based on gesture."""
        if not self.touch_start:
            return None
            
        # Calculate gesture metrics
        dx = pos[0] - self.touch_start[0]
        dy = pos[1] - self.touch_start[1]
        distance = (dx**2 + dy**2) ** 0.5
        time_elapsed = game_time - self.touch_start_time
        
        action = None
        
        # If DAS was already triggered, don't do another action
        if self.das_triggered:
            self.reset()
            return None
        
        # SWIPE detection (takes priority over taps if distance is significant)
        if distance >= self.SWIPE_THRESHOLD:
            if abs(dx) > abs(dy):
                # Horizontal swipe
                if dx > 0:
                    action = 'MOVE_RIGHT'
                    self.touch_ripples.append((pos[0], pos[1], game_time, 'swipe_right'))
                else:
                    action = 'MOVE_LEFT'
                    self.touch_ripples.append((pos[0], pos[1], game_time, 'swipe_left'))
            else:
                # Vertical swipe
                if dy > 0:
                    action = 'HARD_DROP'  # Swipe down = hard drop
                    self.touch_ripples.append((pos[0], pos[1], game_time, 'swipe_down'))
                else:
                    action = 'ROTATE'  # Swipe up = rotate
                    self.touch_ripples.append((pos[0], pos[1], game_time, 'swipe_up'))
        
        # TAP detection (quick touch with minimal movement)
        elif time_elapsed < self.TAP_TIME_MAX:
            x_pct = pos[0] / self.screen_w
            y_pct = pos[1] / self.screen_h
            
            if y_pct > self.ZONE_BOTTOM:
                action = 'SOFT_DROP'
                self.touch_ripples.append((pos[0], pos[1], game_time, 'tap'))
            elif x_pct < self.ZONE_LEFT:
                action = 'MOVE_LEFT'
                self.touch_ripples.append((pos[0], pos[1], game_time, 'tap'))
            elif x_pct > self.ZONE_RIGHT:
                action = 'MOVE_RIGHT'
                self.touch_ripples.append((pos[0], pos[1], game_time, 'tap'))
            else:
                action = 'ROTATE'
                self.touch_ripples.append((pos[0], pos[1], game_time, 'tap'))
        
        self.reset()
        return action
    
    def update(self, dt, game_time):
        """Update DAS timer. Returns action if DAS triggers, else None."""
        action = None
        
        if self.is_holding and self.hold_zone in ('LEFT', 'RIGHT', 'DOWN'):
            self.das_timer += dt
            
            # Initial DAS delay
            if not self.das_triggered and self.das_timer >= self.DAS_DELAY:
                self.das_triggered = True
                self.last_das_move = game_time
                if self.hold_zone == 'LEFT':
                    action = 'MOVE_LEFT'
                elif self.hold_zone == 'RIGHT':
                    action = 'MOVE_RIGHT'
                elif self.hold_zone == 'DOWN':
                    action = 'SOFT_DROP'
            
            # DAS repeat
            elif self.das_triggered and (game_time - self.last_das_move) >= self.DAS_REPEAT:
                self.last_das_move = game_time
                if self.hold_zone == 'LEFT':
                    action = 'MOVE_LEFT'
                elif self.hold_zone == 'RIGHT':
                    action = 'MOVE_RIGHT'
                elif self.hold_zone == 'DOWN':
                    action = 'SOFT_DROP'
        
        # Clean up old ripples (older than 0.5 seconds)
        self.touch_ripples = [(x, y, t, typ) for x, y, t, typ in self.touch_ripples 
                               if game_time - t < 0.5]
        
        # Clear zone highlight after 0.3 seconds
        if self.zone_highlight and game_time - self.zone_highlight[1] > 0.3:
            self.zone_highlight = None
            
        return action
    
    def draw(self, surface, game_time):
        """Draw touch feedback overlays"""
        # Draw zone highlights when touching
        if self.zone_highlight:
            zone, start_time = self.zone_highlight
            alpha = max(0, int(80 * (1 - (game_time - start_time) / 0.3)))
            
            if alpha > 0:
                overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
                
                if zone == 'LEFT':
                    pygame.draw.rect(overlay, (100, 200, 255, alpha), 
                                   (0, 0, int(self.screen_w * self.ZONE_LEFT), self.screen_h))
                elif zone == 'RIGHT':
                    pygame.draw.rect(overlay, (100, 200, 255, alpha),
                                   (int(self.screen_w * self.ZONE_RIGHT), 0, 
                                    int(self.screen_w * (1 - self.ZONE_RIGHT)), self.screen_h))
                elif zone == 'CENTER':
                    pygame.draw.rect(overlay, (255, 200, 100, alpha),
                                   (int(self.screen_w * self.ZONE_LEFT), 0,
                                    int(self.screen_w * (self.ZONE_RIGHT - self.ZONE_LEFT)), 
                                    int(self.screen_h * self.ZONE_BOTTOM)))
                elif zone == 'DOWN':
                    pygame.draw.rect(overlay, (100, 255, 100, alpha),
                                   (0, int(self.screen_h * self.ZONE_BOTTOM),
                                    self.screen_w, int(self.screen_h * (1 - self.ZONE_BOTTOM))))
                
                surface.blit(overlay, (0, 0))
        
        # Draw touch ripples
        for x, y, start_time, ripple_type in self.touch_ripples:
            age = game_time - start_time
            progress = age / 0.4  # 0.4 second animation
            
            if progress < 1.0:
                radius = int(20 + 40 * progress)
                alpha = int(200 * (1 - progress))
                
                # Color based on type
                if ripple_type == 'tap':
                    color = (255, 255, 255, alpha)
                elif 'swipe' in ripple_type:
                    color = (255, 200, 100, alpha)
                else:
                    color = (100, 200, 255, alpha)
                
                # Draw expanding ring
                ripple_surf = pygame.Surface((radius*2 + 4, radius*2 + 4), pygame.SRCALPHA)
                pygame.draw.circle(ripple_surf, color, (radius + 2, radius + 2), radius, 3)
                surface.blit(ripple_surf, (int(x - radius - 2), int(y - radius - 2)))
    
    def draw_zone_hints(self, surface, font=None):
        """Draw subtle zone indicator lines (call during pause or tutorial)"""
        # Vertical zone dividers
        left_x = int(self.screen_w * self.ZONE_LEFT)
        right_x = int(self.screen_w * self.ZONE_RIGHT)
        bottom_y = int(self.screen_h * self.ZONE_BOTTOM)
        
        # Dashed lines
        dash_color = (150, 150, 150, 150)
        for y in range(0, self.screen_h, 20):
            pygame.draw.line(surface, dash_color, (left_x, y), (left_x, min(y+10, self.screen_h)), 2)
            pygame.draw.line(surface, dash_color, (right_x, y), (right_x, min(y+10, self.screen_h)), 2)
        for x in range(0, self.screen_w, 20):
            pygame.draw.line(surface, dash_color, (x, bottom_y), (min(x+10, self.screen_w), bottom_y), 2)
        
        # Zone labels
        small_font = font if font else pygame.font.SysFont('Arial', 16, bold=True)
        labels = [
            ("← MOVE", left_x // 2, self.screen_h // 2),
            ("ROTATE / TAP", (left_x + right_x) // 2, self.screen_h // 2),
            ("MOVE →", (right_x + self.screen_w) // 2, self.screen_h // 2),
            ("↓ SOFT DROP ↓", self.screen_w // 2, (bottom_y + self.screen_h) // 2 + 10),
            ("SWIPE DOWN = HARD DROP", self.screen_w // 2, 80)
        ]
        for text, x, y in labels:
            # Shadow
            s_surf = small_font.render(text, True, (0, 0, 0))
            surface.blit(s_surf, s_surf.get_rect(center=(x+2, y+2)))
            # Main
            txt_surf = small_font.render(text, True, (255, 255, 255))
            surface.blit(txt_surf, txt_surf.get_rect(center=(x, y)))

    def draw_tutorial(self, surface, font=None):
        """Alias for draw_zone_hints with a dark overlay"""
        overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))
        self.draw_zone_hints(surface, font)


# Keep old name for backwards compatibility
GestureControls = MobileControls


class Tetris:
    TURTLE_FRAMES = []
    RED_TURTLE_FRAMES = []
    SPINY_FRAMES = []
    GOLDEN_TURTLE_FRAMES = []
    CLOUD_FRAMES = []
    TURTLE_LIFE_ICON = None
    MUSHROOM_FRAMES = []
    BLOOPER_FRAMES = {}
    PIRANHA_FRAMES = {}

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)
        pygame.display.set_caption("Mario Tetris Redux")
        self.clock = pygame.time.Clock()
        self.game_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        
        # --- Init Assets ---
        
        self.mario_life_icon = None
        # Initialize Bonus Level (New System)
        self.bonus_level = None # Defer creation until assets loaded options
        
        # --- Init Assets ---
        self.sprite_manager = init_asset_loader()
        self.grid = Grid(self.sprite_manager)
        
        # Initialize Bonus Level now that loader is ready
        self.bonus_level = BonusLevel(self.sprite_manager)
        self.dark_world = Scene_DarkWorld(self.sprite_manager)
        self.intro_scene = IntroScene(self.sprite_manager)
        
        # PRODUCTION FIX: Generate Green Luigi Sprites once at startup
        generate_luigi_sprites(self.sprite_manager)
        
        self.camera_zoom = 1.0 # Init Camera
        self.camera_x = 0 # Init Camera Pan
        
        # Load Complex Frames (Dicts)
        # Load Complex Frames (Dicts) with debug logging
        Tetris.TURTLE_FRAMES = {
            'fly': self.sprite_manager.get_animation_frames('koopa_green', scale_factor=2.5, prefix='fly'),
            'walk': self.sprite_manager.get_animation_frames('koopa_green', scale_factor=2.5, prefix='walk'),
            'shell': self.sprite_manager.get_animation_frames('koopa_green', scale_factor=2.5, prefix='shell')
        }
        print(f"[DEBUG] Green Koopa frames - fly: {len(Tetris.TURTLE_FRAMES['fly'])}, walk: {len(Tetris.TURTLE_FRAMES['walk'])}, shell: {len(Tetris.TURTLE_FRAMES['shell'])}")
        
        Tetris.RED_TURTLE_FRAMES = {
            'fly': self.sprite_manager.get_animation_frames('koopa_red', scale_factor=2.5, prefix='fly'),
            'walk': self.sprite_manager.get_animation_frames('koopa_red', scale_factor=2.5, prefix='walk'),
            'shell': self.sprite_manager.get_animation_frames('koopa_red', scale_factor=2.5, prefix='shell')
        }
        print(f"[DEBUG] Red Koopa frames - fly: {len(Tetris.RED_TURTLE_FRAMES['fly'])}, walk: {len(Tetris.RED_TURTLE_FRAMES['walk'])}, shell: {len(Tetris.RED_TURTLE_FRAMES['shell'])}")
        
        # Load Spiny frames as dict for consistency with other turtles
        spiny_walk = self.sprite_manager.get_animation_frames('spiny', scale_factor=2.5)
        Tetris.SPINY_FRAMES = {
            'fly': [],  # Spinies don't fly
            'walk': spiny_walk if spiny_walk else [],
            'shell': []  # Spinies don't have shell animation
        }
        print(f"[DEBUG] Spiny frames - walk: {len(Tetris.SPINY_FRAMES['walk'])}")
        Tetris.MUSHROOM_FRAMES = self.sprite_manager.get_animation_frames('mushroom', prefix='walk')
        
        # Load Blooper
        blooper_walk = self.sprite_manager.get_animation_frames('blooper', scale_factor=2.5)
        Tetris.BLOOPER_FRAMES = {
            'fly': blooper_walk,
            'walk': blooper_walk,
            'shell': blooper_walk
        }
        
        # Load Piranha
        piranha_walk = self.sprite_manager.get_animation_frames('piranha', scale_factor=2.5)
        Tetris.PIRANHA_FRAMES = {
            'fly': piranha_walk,
            'walk': piranha_walk,
            'shell': piranha_walk
        }
        
        # Tint Golden (Based on Walk frames)
        for f in Tetris.TURTLE_FRAMES['walk']:
            gf = f.copy()
            gf.fill((255, 215, 0, 100), special_flags=pygame.BLEND_RGBA_MULT)
            Tetris.GOLDEN_TURTLE_FRAMES.append(gf)

        self.mario_life_icon = self.sprite_manager.get_sprite('mario', 'stand', scale_factor=1.5)
        self.mario_sprite = self.mario_life_icon
        if self.mario_life_icon:
            Tetris.TURTLE_LIFE_ICON = self.mario_life_icon
        elif Tetris.TURTLE_FRAMES and 'walk' in Tetris.TURTLE_FRAMES and Tetris.TURTLE_FRAMES['walk']:
            Tetris.TURTLE_LIFE_ICON = pygame.transform.scale(Tetris.TURTLE_FRAMES['walk'][0], (20, 20))

        self.sound_manager = SoundManager()
        
        self.clouds = [] # Disabled clouds (user reported as fire sprite)
        # self.bonus_game = BonusGame(self) # Removed old bonus game
        
        # Modern Gesture Controls
        self.gesture_controls = GestureControls((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.show_gesture_tutorial = False  # Set to True to show tutorial on first launch
        
        # Load Font
        self.font_path = game_settings.get_asset_path('fonts', 'main')
        if not self.font_path: self.font_path = os.path.join('assets', 'PressStart2P-Regular.ttf') # Fallback
        
        self.font_big = pygame.font.Font(self.font_path, 30) if os.path.exists(self.font_path) else pygame.font.SysFont('Arial', 40, bold=True)
        self.font_med = pygame.font.Font(self.font_path, 20) if os.path.exists(self.font_path) else pygame.font.SysFont('Arial', 24, bold=True)
        self.font_small = pygame.font.Font(self.font_path, 12) if os.path.exists(self.font_path) else pygame.font.SysFont('Arial', 16)
        
        self.highscore = 0
        self.highscore_file = "highscore.json"
        self.load_highscore()
        
        # Scaling & Mobile Response Init
        self.fullscreen = False
        self.is_mobile = False 
        self.is_portrait = False
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        
        self.reset_game()
        self.game_state = 'INTRO'
        
        # DEFER MUSIC START - Let the main loop handle it after full init
        # This prevents double-audio race conditions
        self._music_started = False
              
        self.ui_bg = None

        self.update_scaling()
        
    def update_scaling(self):
        sw, sh = self.screen.get_size()
        self.is_portrait = sh > sw
        self.is_mobile = sw < 800 or self.is_portrait
        
        # Calculate Letterbox Scaling
        scale_w = sw / WINDOW_WIDTH
        scale_h = sh / WINDOW_HEIGHT
        self.scale = min(scale_w, scale_h)
        self.offset_x = (sw - (WINDOW_WIDTH * self.scale)) // 2
        self.offset_y = (sh - (WINDOW_HEIGHT * self.scale)) // 2
        
    def get_game_coords(self, pos):
        """Convert screen pixels to virtual game pixels (1280x720)"""
        gx = (pos[0] - self.offset_x) / self.scale
        gy = (pos[1] - self.offset_y) / self.scale
        return (gx, gy)

    def reset_game(self):
        # Basic Stats (Init first to prevent draw crashes)
        self.auto_play = False 
        self.ai_bot = TetrisBot(self) # Initialize Bot
        self.shift_cooldown = 0
        self.shadow_multiplier = 1
        
        self.score = 0
        self.displayed_score = 0 # For coin adding animation
        self.lives = 3
        self.hearts = 5 # SMB2 Health system
        self.max_hearts = 5
        self.coins = 0
        self.turtles_stomped = 0
        self.lines_since_mushroom = 0
        self.level = 1
        self.world = 1
        self.level_in_world = 1
        self.lines_this_level = 0
        self.lines_cleared_total = 0
        self.total_time = 0
        self.match_timer = 400.0 # SMB2 Countdown
        self.transition_timer = 0
        self.kills_this_level = 0 # Track for bonus spins
        
        # Antigravity & FX Defaults
        self.antigravity_active = False
        self.antigravity_timer = 0
        self.screen_shake_timer = 0
        self.shake_offset = (0, 0)
        
        # Start Music Logic REMOVED from reset_game
        # Music is now handled explicitly by game state transitions
        # if hasattr(self, 'sound_manager'):
        #     self.sound_manager.play_music_gameplay()
            
        # Init Spawner & Pieces
        self.spawner = Spawner()
        self.current_piece = self.spawner.get_next_piece()
        self.next_piece = self.spawner.get_next_piece()
        self.turtles = []
        self.turtles_stomped = 0
        self.turtle_spawn_timer = 5.0
        self.stomp_combo = 0
        self.frame_stomps = 0 
        self.b2b_chain = 0
        
        self.line_flash_timer = 0
        self.flash_lines = []
        
        # Level Progress
        self.lines_required = 10
        self.boss_hp = 0
        self.max_boss_hp = 0
        self.boss_garbage_timer = 0
        self.is_boss_level = False
        self.big_boss = None
        
        self.falling_hearts = []
        self.popups = []
        self.effects = []
        
        # VISUAL POLISH: Scanlines & Particles
        self.scanline_overlay = None
        sl_path = os.path.join('assets', 'scanline_overlay.png')
        if os.path.exists(sl_path):
             self.scanline_overlay = pygame.image.load(sl_path).convert_alpha()
             self.scanline_overlay = pygame.transform.scale(self.scanline_overlay, (WINDOW_WIDTH, WINDOW_HEIGHT))
             self.scanline_overlay.set_alpha(30) # Subtle
            

        # Antigravity & Specials
        self.antigravity_active = False 
        self.antigravity_timer = 0.0
        self.lakitu = None
        self.lakitu_timer = 0
        self.p_wing_active = False
        self.p_wing_timer = 0
        self.star_active = False
        self.star_timer = 0
        self.damage_flash_timer = 0
        # Shared Grid
        self.grid = Grid(self.sprite_manager)
        
        self.fall_timer = 0
        self.is_losing_life = False
        self.world_clear_timer = 0
        
        self.das_timer = 0
        self.das_direction = 0
        self.key_down_held = False
        
        # New Gameplay Timers
        self.match_timer = 400.0 # SMB2 style countdown
        self.lock_timer = 0
        self.max_lock_delay = 0.5 
        self.lock_move_count = 0 
        self.max_lock_moves = 10
        
        self.fall_speed = 0.8 # Initial fall speed
        
        # Mario Helper System
        self.mario_helper_active = False
        self.mario_helper_x = -100
        self.mario_helper_timer = 0
        self.mario_helper_cooldown = 60.0  # Can trigger every 60 seconds
        self.lines_since_helper = 0  # Track lines cleared since last helper

        self.reset_level()

    def reset_level(self):
        self.sprite_manager = self.sprite_manager # This line is redundant if sprite_manager is already self.sprite_manager
        self.grid.grid_neon = [[None for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.grid.grid_shadow = [[None for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.grid.grid = self.grid.grid_neon # Pointer to current world
        self.grid.ground_row = [] # For decorative bottom row
        
        self.flash_lines = []
        self.line_flash_timer = 0
        self.lines_this_level = 0
        if self.world == 1 and self.level_in_world == 1:
            self.lines_required = 5  # Easy first level
        else:
            self.lines_required = 8 + (self.world - 1) * 4 + (self.level_in_world - 1) * 2
        
        self.is_boss_level = (self.level_in_world == 4)
        self.big_boss = None
        if self.is_boss_level:
            self.max_boss_hp = 250 + self.world * 100 # Reduced from 400+w*200 for fairness
            self.boss_hp = self.max_boss_hp
            self.big_boss = BigBoss(self)
            self.big_boss.hp = self.boss_hp
            self.big_boss.max_hp = self.max_boss_hp
            self.setup_boss_arena()
            self.boss_garbage_timer = 15.0  # More time before first garbage
            self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, "BOSS BATTLE!", C_RED, size='big'))
        
            # self.sound_manager.play('music') # Removed legacy call
        
        # Apply theme colors
        self.apply_level_theme()
        
        # CHANGE MUSIC each level!
        if hasattr(self, 'sound_manager'):
            self.sound_manager.next_track()
        
        # Announcement
        self.show_level_intro = True
        self.level_intro_timer = 4.0
        
        # 3.0 Feature: Level Layouts (Pre-placed blocks)
        self.apply_layout()

    def apply_layout(self):
        """Parse ASCII map and place blocks in grid"""
        layout = get_layout(self.world, self.level_in_world)
        if not layout: return

        # Mapping chars to sprite keys
        # Use theme-specific sprites where possible
        theme_block_map = {
            'OVERWORLD': {'#': 'ground', 'B': 'brick_brown', 'X': 'block_stone'},
            'UNDERGROUND': {'#': 'brick_blue', 'B': 'brick_blue', 'X': 'block_stone'},
            'CASTLE': {'#': 'brick_castle', 'B': 'brick_castle', 'X': 'block_stone'},
            'WATER': {'#': 'block_coral', 'B': 'block_coral', 'X': 'block_stone'},
            'MUSHROOM': {'#': 'block_red', 'B': 'block_red', 'X': 'block_stone'}
        }
        
        # Default mapping
        sprite_map = theme_block_map.get(self.level_theme, theme_block_map['OVERWORLD'])
        
        # Parse map (bottom-up logic or direct indexing)
        for r, row_str in enumerate(layout):
            if r >= GRID_HEIGHT: break
            for c, char in enumerate(row_str):
                if c >= GRID_WIDTH: break
                
                if char == '.': continue
                
                # Determine Block Type & Color Fallbacks
                block_type = 'brick' 
                sprite_key = 'brick' # 'brick' exists in assets
                color = (150, 75, 0) # Default Brown
                
                if char == '#': # Ground / Floor
                    block_type = 'ground'
                    if self.level_theme == 'OVERWORLD':
                        sprite_key = 'brick' 
                        color = (150, 75, 0) # Fallback Brown
                    elif self.level_theme == 'UNDERGROUND':
                         sprite_key = 'brick' 
                         color = (0, 0, 150) # Blue
                    elif self.level_theme == 'CASTLE':
                         sprite_key = 'empty'
                         color = (100, 100, 100) # Grey
                    elif self.level_theme == 'WATER':
                         color = (0, 150, 150) # Teal
                    
                elif char == 'B': # Breakable Brick
                    sprite_key = 'brick'
                    block_type = 'brick'
                    if self.level_theme == 'UNDERGROUND': color = (50, 50, 255)
                    elif self.level_theme == 'ALPS': color = (200, 200, 255)
                    
                elif char == 'X': # Hard Block
                    sprite_key = 'empty' # Use 'empty' (Beaten Block) often looks like stone/metal
                    block_type = 'solid'
                    color = (120, 120, 120) # Grey
                    
                elif char == '?':
                    sprite_key = 'question_1'
                    block_type = 'question'
                    color = (255, 215, 0) # Gold

                # Fetch Sprite
                # Try to load sprite
                s_data = {'sprite': None, 'category': 'blocks'}
                
                # Special TINTING logic
                base_sprite = self.sprite_manager.get_sprite('blocks', sprite_key, scale_factor=2.0)
                
                if base_sprite and self.level_theme == 'UNDERGROUND' and sprite_key == 'brick':
                    # Manually tint blue for Underground to match original game style
                    s_data['sprite'] = base_sprite.copy()
                    s_data['sprite'].fill((100, 100, 255), special_flags=pygame.BLEND_MULT)
                elif base_sprite:
                     s_data['sprite'] = base_sprite
                
                # If lookup failed completely, use fallback colors
                
                # Place Block
                self.grid.grid[r][c] = Block(color, sprite_data=s_data)
                self.grid.grid[r][c].type = block_type
    
    def apply_level_theme(self):
        """Apply visual theme based on current level"""
        # Calculate overall level if not already updated
        self.level = (self.world - 1) * 4 + self.level_in_world
        
        # Select theme based on level index
        theme_idx = (self.level - 1) % len(LEVEL_THEMES)
        theme = LEVEL_THEMES[theme_idx]
        
        self.level_theme = theme['name']
        self.theme_bg = theme['bg']
        # self.theme_grid = theme.get('grid', (30, 30, 30)) # Not used currently?
        self.theme_accent = theme['accent']
        self.active_world = self.level_theme 
        
        print(f"[THEME] Applied level {self.level} theme: {self.level_theme}")
        
        # Spawn World "Treats" (Decorations)
        self.clouds = [] 
        # Add decorative elements based on theme
        for _ in range(25):
            self.clouds.append(BackgroundElement(self.level_theme, self.sprite_manager))
            
        # 2.0 Feature: Generate Ground / Blocks for Theme
        self.generate_level_decorations()

    def generate_level_decorations(self):
        """Populate the bottom decorative row based on theme"""
        self.grid.ground_row = []
        
        # Determine block type based on theme
        # Use existing 'brick' or 'empty' sprites + tinting if needed
        block_sprite = None
        sf = 2.0 # 2.0 * 16px (source) = 32px (BLOCK_SIZE)
        
        if self.level_theme == 'OVERWORLD':
            block_sprite = self.sprite_manager.get_sprite('blocks', 'brick', scale_factor=sf) 
        elif self.level_theme == 'UNDERGROUND':
            s = self.sprite_manager.get_sprite('blocks', 'brick', scale_factor=sf)
            if s: 
                block_sprite = s.copy()
                block_sprite.fill((100, 100, 255), special_flags=pygame.BLEND_MULT)
        elif self.level_theme == 'CASTLE':
            block_sprite = self.sprite_manager.get_sprite('blocks', 'empty', scale_factor=sf) 
        elif self.level_theme == 'WATER':
             # Fallback to empty (solid block)
             block_sprite = self.sprite_manager.get_sprite('blocks', 'empty', scale_factor=sf)
        elif self.level_theme == 'MUSHROOM':
             block_sprite = self.sprite_manager.get_sprite('blocks', 'brick', scale_factor=sf)
             
        # Fallback
        if not block_sprite:
             block_sprite = self.sprite_manager.get_sprite('blocks', 'brick', scale_factor=sf)
             
        # DEBUG
        print(f"[DEBUG] BLOCK_SIZE: {BLOCK_SIZE}")
        if block_sprite:
            print(f"[DEBUG] block_sprite size: {block_sprite.get_size()}")
        
        # Generate Row
        for x in range(GRID_WIDTH):
            self.grid.ground_row.append(block_sprite)


    def setup_boss_arena(self):
        """Setup the partially filled line above the boss"""
        # Clear middle section but keep some blocks at the top if any
        # Actually reset_level already cleared the grid.
        
        # Shield line (partially filled line) above the boss
        shield_row = random.randint(14, 16)
        gap_start = random.randint(1, GRID_WIDTH - 3)
        gaps = [gap_start, gap_start + 1] # 2-wide gap
        
        # Draw some bricks with gaps
        for x in range(GRID_WIDTH):
            if x not in gaps:
                # Use a specific color for shield blocks
                self.grid.grid[shield_row][x] = Block((150, 150, 150), 'brick')
            
        self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2 + 40, "SHOOT THROUGH THE GAPS!", C_GOLD))

    def damage_boss(self, amount, reason="HIT"):
        """Centralized damage handler for the boss"""
        if not self.big_boss: return
        
        self.big_boss.hp -= amount
        self.boss_hp = self.big_boss.hp # Keep in sync for UI
        self.big_boss.hit_timer = 0.3
        self.sound_manager.play('impact_heavy')  # Heavy impact sound for boss
        self.screen_shake_timer = 0.4
        
        # Color based on damage
        color = C_RED if amount < 50 else C_NEON_PINK
        self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2 - 60, f"BOSS {reason}! -{amount}", color, size='med'))
        
        # Particles at boss position
        bx = PLAYFIELD_X + (self.big_boss.x + 1.5) * BLOCK_SIZE
        by = PLAYFIELD_Y + (self.big_boss.y - 1.5) * BLOCK_SIZE
        self.spawn_particles(bx, by, color, count=int(amount/2))
        
        if self.big_boss.hp <= 0:
            self.sound_manager.play('world_clear') 
            self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, "BOSS DEFEATED!", C_GOLD, size='big'))
            self.trigger_level_win()

    def spawn_particles(self, x, y, color, count=10):
        for _ in range(count):
             vx = random.uniform(-200, 200)
             vy = random.uniform(-300, 100)
             self.effects.append({'x': x, 'y': y, 'vx': vx, 'vy': vy, 'life': 1.0, 'color': color, 'type': 'particle'})

    def spawn_random_item(self):
        items = ['SUPER_MUSHROOM', '1UP_MUSHROOM', 'STAR', 'PWING']
        choice = random.choice(items)
        if choice == 'SUPER_MUSHROOM':
            self.trigger_antigravity(10.0)
            self.score += 1000
            self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, "SUPER MUSHROOM!", C_GREEN))
        elif choice == '1UP_MUSHROOM':
            self.lives += 1
            self.sound_manager.play('level_up')
            self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, "1UP!", C_GREEN))
        elif choice == 'STAR':
            self.trigger_star_power(10.0)
        elif choice == 'PWING':
            self.p_wing_active = True
            self.p_wing_timer = 15.0
            self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, "P-WING!", C_GOLD))

    def handle_line_clear(self, cleared, events=[], line_indices=[]):
        self.lines_this_level += cleared
        self.lines_cleared_total += cleared
        self.lines_since_mushroom += cleared
        self.line_flash_timer = 0.3
        self.flash_lines = line_indices
        
        # BOSS DAMAGE - Line Clears are super effective!
        if self.big_boss:
            dmg_map = {1: 20, 2: 45, 3: 80, 4: 150}
            dmg = dmg_map.get(cleared, 15 * cleared)
            self.damage_boss(dmg, "LINE CLEAR")
        
        # Scoring 2.0 (Classic Multipliers)
        self.level = (self.world - 1) * 4 + self.level_in_world
        base_pts = [0, 100, 300, 500, 800][min(cleared, 4)] * self.level
        multiplier = 1.0
        
        # Back-to-Back Tetris (1.5x)
        if cleared == 4:
            streak = self.b2b_chain + 1
            multiplier *= (1.0 + 0.5 * self.b2b_chain)
            
            # Messaging
            if streak == 1:
                 self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2 - 40, "TETRIS!", C_NEON_PINK))
            elif streak == 2:
                 self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2 - 40, "DOUBLE TETRIS! x2", C_NEON_PINK))
            elif streak == 3:
                 self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2 - 40, "TETRIS MASTER! x3", C_NEON_PINK))
            else:
                 self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2 - 40, f"GOAT! x{streak}", (255, 215, 0)))
                 
            self.b2b_chain += 1
        else:
            self.b2b_chain = 0
            
        final_pts = int(base_pts * multiplier)
        self.score += final_pts
        self.sound_manager.play('clear')
        
        if cleared >= 4:
             self.popups.append(PopupText(WINDOW_WIDTH//2 - 60, WINDOW_HEIGHT//2 - 30, "TETRIS!", C_NEON_PINK))
             # Chance for Star on Tetris
             if random.random() < 0.1: self.trigger_star_power(10.0)

        # Mushroom Spawn (Every 3 lines)
        if self.lines_since_mushroom >= 3:
            self.lines_since_mushroom -= 3
            m = MagicMushroom(self)
            m.x = random.randint(0, GRID_WIDTH - 1)
            m.y = -1
            m.state = 'active'
            self.turtles.append(m)
            self.popups.append(PopupText(PLAYFIELD_X + m.x*BLOCK_SIZE, 150, "MAGIC MUSHROOM!", (100, 255, 100)))

        if self.is_boss_level:
            # EXTRA DAMAGE FOR GARBAGE
            if 'BRICK_CLEAR' in events: 
                self.damage_boss(15, "BRICK SMASH")
        else:
            # Check for level win
            if self.lines_this_level >= self.lines_required:
                self.trigger_level_win()
        
        # Spawn particles if cleared
        if cleared > 0:
            # Spawn particles at line clear locations
            for row_idx in line_indices:
                self.spawn_particles(PLAYFIELD_X + (GRID_WIDTH//2)*BLOCK_SIZE, 
                                   PLAYFIELD_Y + row_idx*BLOCK_SIZE, 
                                   (255, 215, 0), count=20)

    def trigger_level_win(self):
        self.sound_manager.play('world_clear')
        
        # Advance Level Progress
        self.level_in_world += 1
        if self.level_in_world > 4:
            self.level_in_world = 1
            self.world += 1
            
        self.apply_level_theme() # Update theme for new level
    
        # Go to Results Screen
        self.game_state = 'WORLD_CLEAR'
        self.transition_timer = 0
        
    def spawn_magic_star(self, x, y):
        s = MagicStar(self)
        s.x = x
        s.y = y
        self.turtles.append(s)

    def trigger_mega_mode(self, duration=20.0):
        self.mega_mode = True
        self.mega_mode_timer = duration
        self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, "MEGA MODE!", (255, 0, 0), size=60))
        if self.sound_manager: self.sound_manager.play('star_theme')
    

    def trigger_boss_garbage(self):
        # Bowser attacks! Push garbage line from bottom
        rows = 1  # EASIER: Only 1 row per attack
        for _ in range(rows):
            new_row = [Block((128, 128, 128), 'brick') for _ in range(GRID_WIDTH)]
            # Leave 2 gaps so it's easier to clear
            gap1 = random.randint(0, GRID_WIDTH - 1)
            gap2 = (gap1 + random.randint(2, 4)) % GRID_WIDTH  # Second gap
            new_row[gap1] = None
            new_row[gap2] = None
            self.grid.grid.pop(0)
            self.grid.grid.append(new_row)
        self.popups.append(PopupText(WINDOW_WIDTH//2, PLAYFIELD_Y, "BOWSER ATTACK!", C_ORANGE))
        self.sound_manager.play('damage')
        
    def calculate_speed(self):
        # Formula: (World * 4) + Level
        difficulty_index = (self.world - 1) * 4 + self.level_in_world
        # Base speed 0.8s, gets faster. Cap at 0.05s.
        return max(0.05, 1.0 - (difficulty_index - 1) * 0.05)
    
    def handle_block_out(self):
        """Handle when blocks reach the top - use a life or game over"""
        if self.lives > 0:
            # Lose a life but continue at same level
            self.lives -= 1
            self.sound_manager.play('damage')
            
            # Show dramatic "RETRY" sequence
            self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//3, f"LIVES: {self.lives}", (255, 50, 50)))
            self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, "TRY AGAIN!", (255, 215, 0)))
            
            # Clear the grid but keep progress
            self.grid.grid = [[None for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
            
            # Clear enemies too
            self.turtles.clear()
            
            # Get fresh pieces
            self.current_piece = self.spawner.get_next_piece()
            self.next_piece = self.spawner.get_next_piece()
            
            # Reset timers
            self.fall_timer = 0
            self.lock_timer = 0
            self.lock_move_count = 0
            self.turtle_spawn_timer = 0
            
            # Reset hearts to max
            self.hearts = self.max_hearts
            
            # Keep level progress - don't reset lines_this_level
            # Player keeps score and level, just cleared grid
            
            # Small delay/visual feedback
            self.screen_shake_timer = 0.5
            self.damage_flash_timer = 0.3
            
            return False  # Not game over
        else:
            # No lives left - actual game over
            self.game_state = 'GAMEOVER'
            self.sound_manager.play('gameover')
            return True  # Game over

    def trigger_antigravity(self, duration):
        self.antigravity_active = True
        self.antigravity_timer = duration
        self.popups.append(PopupText(WINDOW_WIDTH//2 - 60, WINDOW_HEIGHT//2, "GRAVITY SHIFT!", C_NEON_PINK))
        self.sound_manager.play('rotate') 

    def trigger_star_power(self, duration):
        self.star_active = True
        self.star_timer = duration
        self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, "STAR POWER!", C_GOLD))
        self.sound_manager.play('level_up')
    
    # --- MARIO HELPER SYSTEM ---
    # Mario helps in different ways each time!
    MARIO_HELP_MODES = ['SMASH', 'STOMP', 'CLEAR', 'STAR']
    
    def trigger_mario_helper(self, mode=None):
        """Mario helps in different ways each time!"""
        if self.mario_helper_active:
            return  # Already running
        
        # Pick mode - cycle through or use specified
        if mode is None:
            if not hasattr(self, 'mario_help_index'):
                self.mario_help_index = 0
            mode = self.MARIO_HELP_MODES[self.mario_help_index % len(self.MARIO_HELP_MODES)]
            self.mario_help_index += 1
            
        self.mario_helper_active = True
        self.mario_helper_mode = mode
        self.mario_helper_x = -60  # Start off-screen left
        self.mario_helper_timer = 0
        self.lines_since_helper = 0
        
        # Mode-specific announcements
        if mode == 'SMASH':
            self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//3, "IT'S-A-ME!", (255, 50, 50)))
            self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//3 + 40, "SMASH TIME!", (255, 215, 0)))
        elif mode == 'STOMP':
            self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//3, "MARIO STOMP!", (255, 50, 50)))
            self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//3 + 40, "INCOMING!", (255, 215, 0)))
        elif mode == 'CLEAR':
            self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//3, "MARIO MAGIC!", (255, 50, 50)))
            self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//3 + 40, "LINE CLEAR!", (0, 255, 255)))
        elif mode == 'STAR':
            self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//3, "MARIO GIFT!", (255, 50, 50)))
            self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//3 + 40, "STAR POWER!", (255, 255, 0)))
            
        self.sound_manager.play('level_up')
        
    def update_mario_helper(self, dt):
        """Update Mario's position and execute help based on mode"""
        if not self.mario_helper_active:
            return
            
        self.mario_helper_timer += dt
        mode = getattr(self, 'mario_helper_mode', 'SMASH')
        
        if mode == 'SMASH':
            # Mode 1: Run across bottom smashing blocks
            run_speed = 400
            self.mario_helper_x += run_speed * dt
            mario_grid_x = int((self.mario_helper_x - PLAYFIELD_X) / BLOCK_SIZE)
            
            if 0 <= mario_grid_x < GRID_WIDTH:
                for row in range(GRID_HEIGHT - 3, GRID_HEIGHT):
                    if self.grid.grid[row][mario_grid_x] is not None:
                        self.grid.grid[row][mario_grid_x] = None
                        px = PLAYFIELD_X + mario_grid_x * BLOCK_SIZE + BLOCK_SIZE // 2
                        py = PLAYFIELD_Y + row * BLOCK_SIZE + BLOCK_SIZE // 2
                        for _ in range(3):
                            self.effects.append({
                                'x': px, 'y': py,
                                'vx': random.uniform(-100, 100),
                                'vy': random.uniform(-200, -50),
                                'life': 1.0,
                                'color': (255, random.randint(100, 200), 0)
                            })
            
            if self.mario_helper_x > PLAYFIELD_X + GRID_WIDTH * BLOCK_SIZE + 60:
                self._finish_mario_helper("THANKS MARIO!")
                
        elif mode == 'STOMP':
            # Mode 2: Mario jumps and stomps all turtles/enemies
            run_speed = 500
            self.mario_helper_x += run_speed * dt
            
            # Stomp turtles as Mario passes
            for t in self.turtles[:]:
                turtle_screen_x = PLAYFIELD_X + t.x * BLOCK_SIZE
                if abs(turtle_screen_x - self.mario_helper_x) < 40:
                    # Stomp effect
                    self.sound_manager.play('stomp')
                    px = PLAYFIELD_X + t.x * BLOCK_SIZE
                    py = PLAYFIELD_Y + t.y * BLOCK_SIZE
                    self.popups.append(PopupText(px, py, "STOMP!", (255, 255, 0)))
                    self.score += 200
                    if t in self.turtles:
                        self.turtles.remove(t)
            
            if self.mario_helper_x > PLAYFIELD_X + GRID_WIDTH * BLOCK_SIZE + 60:
                self._finish_mario_helper("ALL CLEAR!")
                
        elif mode == 'CLEAR':
            # Mode 3: Mario jumps to center and clears 2 random lines
            if self.mario_helper_timer < 0.5:
                # Jump to center
                self.mario_helper_x = WINDOW_WIDTH // 2 - 30
            elif self.mario_helper_timer < 1.0:
                # Clear lines at 0.5 seconds
                if not hasattr(self, '_mario_cleared_lines'):
                    self._mario_cleared_lines = True
                    lines_to_clear = 2
                    cleared = 0
                    # Find rows with most blocks
                    for _ in range(lines_to_clear):
                        best_row = -1
                        best_count = 0
                        for row in range(GRID_HEIGHT):
                            count = sum(1 for c in self.grid.grid[row] if c is not None)
                            if count > best_count:
                                best_count = count
                                best_row = row
                        if best_row >= 0 and best_count > 0:
                            # Clear this row with effects
                            for col in range(GRID_WIDTH):
                                if self.grid.grid[best_row][col]:
                                    px = PLAYFIELD_X + col * BLOCK_SIZE
                                    py = PLAYFIELD_Y + best_row * BLOCK_SIZE
                                    self.effects.append({
                                        'x': px, 'y': py, 'vx': random.uniform(-50, 50),
                                        'vy': random.uniform(-100, -50), 'life': 0.8,
                                        'color': (100, 200, 255)
                                    })
                                self.grid.grid[best_row][col] = None
                            cleared += 1
                    self.score += cleared * 100
            elif self.mario_helper_timer > 1.5:
                self._mario_cleared_lines = False
                self._finish_mario_helper("LINES GONE!")
                
        elif mode == 'STAR':
            # Mode 4: Mario gives you star power (invincibility)
            if self.mario_helper_timer < 0.3:
                self.mario_helper_x = PLAYFIELD_X + GRID_WIDTH * BLOCK_SIZE // 2
            elif self.mario_helper_timer < 0.6:
                if not hasattr(self, '_mario_gave_star'):
                    self._mario_gave_star = True
                    self.trigger_star_power(10.0)  # 10 seconds of star power
            elif self.mario_helper_timer > 1.2:
                self._mario_gave_star = False
                self._finish_mario_helper("USE IT WELL!")
    
    def _finish_mario_helper(self, message):
        """Finish the Mario helper sequence"""
        self.mario_helper_active = False
        self.mario_helper_x = -100
        self.mario_helper_cooldown = 45.0 + random.random() * 30
        self.score += 500
        self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, message, C_GREEN))
            
    def draw_mario_helper(self, surface):
        """Draw Mario during helper sequence"""
        if not self.mario_helper_active:
            return
        
        mode = getattr(self, 'mario_helper_mode', 'SMASH')
        
        # Get Mario animation frame
        if mode == 'SMASH' or mode == 'STOMP':
            anim_frame = int(self.mario_helper_timer * 10) % 3
            frame_names = ['walk_1', 'walk_2', 'walk_3']
        else:
            frame_names = ['stand']
            anim_frame = 0
            
        mario_img = self.sprite_manager.get_sprite('mario', frame_names[anim_frame], scale_factor=3.0)
        if not mario_img:
            mario_img = self.sprite_manager.get_sprite('mario', 'stand', scale_factor=3.0)
        
        if mario_img:
            if mode == 'SMASH':
                y = PLAYFIELD_Y + (GRID_HEIGHT - 2) * BLOCK_SIZE
            elif mode == 'STOMP':
                # Bouncy jump effect
                jump_offset = abs(math.sin(self.mario_helper_timer * 8)) * 50
                y = PLAYFIELD_Y + (GRID_HEIGHT - 3) * BLOCK_SIZE - jump_offset
            elif mode == 'CLEAR':
                y = PLAYFIELD_Y + GRID_HEIGHT // 2 * BLOCK_SIZE
            elif mode == 'STAR':
                y = PLAYFIELD_Y + GRID_HEIGHT // 2 * BLOCK_SIZE
            else:
                y = PLAYFIELD_Y + (GRID_HEIGHT - 2) * BLOCK_SIZE
                
            surface.blit(mario_img, (int(self.mario_helper_x), int(y)))
            
            # Dust trail for running modes
            if mode in ['SMASH', 'STOMP'] and random.random() < 0.3:
                dust_x = self.mario_helper_x - 20
                dust_y = y + mario_img.get_height() - 10
                self.effects.append({
                    'x': dust_x, 'y': dust_y,
                    'vx': random.uniform(-50, -20),
                    'vy': random.uniform(-30, 0),
                    'life': 0.5,
                    'color': (200, 200, 200)
                })
            
            # Star sparkles for STAR mode
            if mode == 'STAR' and random.random() < 0.5:
                self.effects.append({
                    'x': self.mario_helper_x + random.randint(0, 40),
                    'y': y + random.randint(0, 40),
                    'vx': random.uniform(-30, 30),
                    'vy': random.uniform(-50, -20),
                    'life': 0.6,
                    'color': (255, 255, random.randint(0, 100))
                })
                
    def check_mario_helper_trigger(self):
        """Check if Mario should come help"""
        if self.mario_helper_active:
            return False
        if self.mario_helper_cooldown > 0:
            return False
        
        # Check danger level
        danger_rows = sum(1 for row in range(5) if any(self.grid.grid[row]))
        
        if danger_rows >= 3 and random.random() < 0.30:
            return True
        elif self.lines_since_helper >= 10 and random.random() < 0.15:
            return True
        elif random.random() < 0.02:
            return True
            
        return False
        
    def load_highscore(self):
        try:
            if os.path.exists(self.highscore_file):
                with open(self.highscore_file, 'r') as f:
                    data = json.load(f)
                    self.highscore = data.get('highscore', 0)
        except Exception as e:
            print(f"Error loading highscore: {e}")
            self.highscore = 0

    def save_highscore(self):
        try:
            with open(self.highscore_file, 'w') as f:
                json.dump({'highscore': self.highscore}, f)
        except Exception as e:
            print(f"Error saving highscore: {e}")
            
    def check_highscore(self):
        if self.score > self.highscore:
            self.highscore = self.score
            return True
        return False
        
    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)
        
        sw, sh = self.screen.get_size()
        scale_w = sw / WINDOW_WIDTH
        scale_h = sh / WINDOW_HEIGHT
        self.scale = min(scale_w, scale_h)
        self.offset_x = (sw - (WINDOW_WIDTH * self.scale)) // 2
        self.offset_y = (sh - (WINDOW_HEIGHT * self.scale)) // 2

    def trigger_slot_machine(self, spins=1, reason='COMBO'):
        # SLOTS DISABLED - Award instant bonus instead!
        # Bonus = stomps × (lines cleared / 5) or minimum 10 coins per stomp
        bonus_multiplier = max(1, self.lines_this_level // 5)
        bonus_coins = self.frame_stomps * 10 * bonus_multiplier
        
        if bonus_coins > 0:
            self.coins += bonus_coins
            self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2 - 50, f"+{bonus_coins} COINS!", (255, 215, 0)))
            self.sound_manager.play('coin')
            print(f"[BONUS] Awarded {bonus_coins} coins (stomps: {self.frame_stomps}, multiplier: {bonus_multiplier})")
        
        # Don't change game state - stay in PLAYING
        return

    def handle_slot_finish(self, coins):
        # Convert coins to score (10x multiplier)
        total_score = coins * 10
        
        # Set pending winnings for countdown animation
        self.pending_winnings = total_score
        
        # Bonus Lives for huge wins
        lives_gain = coins // 5000
        if lives_gain > 0:
            self.lives += lives_gain
        
        msg = "TRANSFERRING WINNINGS..."
        if lives_gain > 0: msg += f" +{lives_gain} LIVES!"
        
        self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, msg, C_GREEN))
        self.game_state = 'PLAYING'
        # Music will resume after Countdown finishes
        # self.sound_manager.play_music_gameplay()

    def update(self, dt):
        # Update Mega Mode
        if getattr(self, 'mega_mode', False):
            self.mega_mode_timer -= dt
            if self.mega_mode_timer <= 0:
                self.mega_mode = False
                self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, "MEGA MODE END", C_WHITE))
        
             
        try:
            # AI Hook
            if hasattr(self, 'ai_bot'):
                 self.ai_bot.active = getattr(self, 'auto_play', False)
                 self.ai_bot.update(dt)
            if self.game_state == 'INTRO':
                if hasattr(self, 'intro_scene'):
                    self.intro_scene.update(dt)
                return

            if self.game_state == 'BONUS':
                 if self.bonus_level:
                     self.bonus_level.update(dt)
                 return
                 
            if self.game_state == 'DARK_WORLD':
                if self.dark_world:
                    self.dark_world.update(dt, pygame.key.get_pressed())
                return
            
            # Countdown before returning to game
            if self.game_state == 'COUNTDOWN':
                self.countdown_timer -= dt
                new_val = int(self.countdown_timer) + 1
                if new_val != self.countdown_value:
                    self.countdown_value = new_val
                    if new_val > 0:
                        self.sound_manager.play('move')  # Beep for each number
                
                if self.countdown_timer <= 0:
                    self.game_state = 'PLAYING'
                    self.sound_manager.play('clear')  # GO! sound
                    self.sound_manager.play_music_gameplay()  # Resume gameplay music!
                    self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, "GO!", C_GREEN))
                return

            if self.game_state == 'GAMEOVER':
                 self.check_highscore()
                 self.save_highscore()
                 if pygame.key.get_pressed()[pygame.K_RETURN]:
                     self.reset_game()
                 return

            if self.game_state == 'WORLD_CLEAR':
             # RESULTS SCREEN ANIMATION
             self.transition_timer += dt
             if self.transition_timer >= 5.0: # 5 Seconds Results
                 self.transition_timer = 0
                 
                 # END-OF-LEVEL BONUS: Lines × Stomps = Bonus Coins!
                 lines = getattr(self, 'lines_this_level', 0)
                 stomps = getattr(self, 'turtles_stomped', 0)
                 bonus = lines * stomps
                 
                 print(f"[BONUS] Level Complete! Lines: {lines} × Stomps: {stomps} = {bonus} coins")
                 
                 if bonus > 0:
                     self.coins += bonus
                     self.score += bonus * 10  # Also add to score
                     # Show bonus breakdown - BIG TEXT
                     self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2 - 120, f"LINES: {lines}", (100, 255, 100), size='med'))
                     self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2 - 60, f"STOMPS: {stomps}", (255, 100, 100), size='med'))
                     self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, f"─────────", C_WHITE, size='med'))
                     self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2 + 80, f"BONUS: {bonus} COINS!", (255, 215, 0), size='big'))
                     self.sound_manager.play('coin')
                 
                 # Reset counters for next level
                 self.turtles_stomped = 0
                 self.lines_this_level = 0
                 
                 # Advance to next level
                 self.game_state = 'PLAYING'
                 self.reset_level()
             return

            self.total_time += dt
            
            # --- CAMERA ZOOM LOGIC ---
            # Find highest block
            highest_y = GRID_HEIGHT
            for y in range(GRID_HEIGHT):
                 if any(self.grid.grid[y]):
                     highest_y = y
                     break
            
            # Map highest_y to Zoom
            # If y=20 (Empty), Zoom = 1.35
            # If y=5 (High stack), Zoom = 1.0
            # Range [5, 18]
            zoom_factor = max(0.0, min(1.0, (highest_y - 5) / 13.0))
            target_zoom = 1.0 + (0.15 * zoom_factor) # Max Zoom 1.15 (Less dramatic)
            
            # Smooth Lerp
            self.camera_zoom += (target_zoom - self.camera_zoom) * 1.0 * dt # Slower zoom
            
            # Update Clouds & Popups
            for c in self.clouds: c.update(dt)
            for p in self.popups[:]:
                p.update(dt)
                if p.life <= 0: self.popups.remove(p)
            
            # Score Counting Animation
            if self.displayed_score < self.score:
                diff = self.score - self.displayed_score
                step = max(1, int(diff * 0.1))
                self.displayed_score += step
            elif self.displayed_score > self.score:
                self.displayed_score = self.score
            
            # Polled Input for Soft Drop
            keys = pygame.key.get_pressed()
            self.key_down_held = keys[pygame.K_DOWN]


            # Gesture controls handled via events (MOUSEBUTTONDOWN/UP), not polling

            # DAS Logic
            if self.das_direction != 0:
                self.das_timer += dt
                if self.das_timer > DAS_DELAY:
                    if self.das_timer > DAS_DELAY + DAS_REPEAT:
                        self.das_timer -= DAS_REPEAT
                        self.current_piece.x += self.das_direction
                        if self.grid.check_collision(self.current_piece):
                            self.current_piece.x -= self.das_direction

            # Lakitu Logic - ONLY spawn in non-boss levels
            if self.is_boss_level:
                # No Lakitu during boss fights! Clear it if it exists
                if self.lakitu:
                    self.lakitu = None
            elif self.lakitu and hasattr(self.lakitu, 'update'):
                try:
                    self.lakitu.update(dt)
                except Exception as e:
                    print(f"Lakitu update error: {e}")
                    self.lakitu = None
            elif self.level >= 3 and not self.is_boss_level:
                self.lakitu_timer += dt
                if self.lakitu_timer > 20: 
                    try:
                        self.lakitu = Lakitu(self)
                        self.lakitu_timer = 0
                        self.popups.append(PopupText(WINDOW_WIDTH//2, 50, "LAKITU!", C_RED))
                    except Exception as e:
                        print(f"Lakitu spawn error: {e}")
                        self.lakitu = None 

            # REMOVED: Antigravity Timer Logic
            pass
                
            # Update Screen Shake
            if self.screen_shake_timer > 0:
                self.screen_shake_timer -= dt
                mag = 5 # Magnitude
                self.shake_offset = (random.randint(-mag, mag), random.randint(-mag, mag))
            else:
                self.shake_offset = (0, 0)
                
            # P-Wing Logic
            if self.p_wing_active:
                self.p_wing_timer -= dt
                if self.p_wing_timer <= 0:
                    self.p_wing_active = False
                    self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, "P-WING EXPIRED", C_WHITE))

            # Boss Garbage - More forgiving timing
            if getattr(self, 'is_boss_level', False) and self.game_state == 'PLAYING':
                self.boss_garbage_timer -= dt
                if self.boss_garbage_timer <= 0:
                    self.trigger_boss_garbage()
                    self.boss_garbage_timer = 15.0 - min(3.0, self.world * 0.3)  # Gentler scaling

            # Antigravity Logic
            if self.antigravity_active:
                self.antigravity_timer -= dt
                if self.antigravity_timer <= 0:
                    self.antigravity_active = False
                    self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, "GRAVITY RESTORED", C_GREEN))

            # Star Logic
            if self.star_active:
                self.star_timer -= dt
                if self.star_timer <= 0:
                     self.star_active = False
                     self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, "STAR END", C_RED))

            # Update Big Boss
            if self.big_boss:
                self.big_boss.update(dt)

            # --- PIECE GRAVITY & LOCK DELAY ---
            if self.game_state == 'PLAYING':
                g_dir = 1
                target_speed = self.calculate_speed()
                if self.key_down_held: target_speed /= 20.0
                
                self.fall_timer += dt
                if self.fall_timer > target_speed:
                    self.fall_timer = 0
                    self.current_piece.y += g_dir
                    if self.grid.check_collision(self.current_piece):
                        self.current_piece.y -= g_dir
                    else:
                        # NEW: Check for Big Boss Hit
                        if self.big_boss:
                            hit = False
                            px_g, py_g = int(self.current_piece.x), int(self.current_piece.y)
                            for bx, by in self.current_piece.blocks:
                                grid_x, grid_y = px_g + bx, py_g + by
                                if grid_x >= self.big_boss.x and grid_x < self.big_boss.x + self.big_boss.width:
                                    if grid_y >= self.big_boss.y - 1.5 and grid_y <= self.big_boss.y + 0.5:
                                        hit = True; break
                            if hit:
                                damage = 20 if self.key_down_held else 10
                                self.damage_boss(damage, "HIT")
                                
                                # Reset piece if it hits the boss
                                self.current_piece = self.next_piece
                                self.next_piece = self.spawner.get_next_piece()
                                return

                        # NEW: Check for stomping during regular fall
                        piece_x_grid = int(self.current_piece.x)
                        piece_y_grid = int(self.current_piece.y)
                        for bx, by in self.current_piece.blocks:
                            px, py = piece_x_grid + bx, piece_y_grid + by
                            for t in self.turtles[:]:
                                # Skip Lakitu and already dying enemies
                                if hasattr(t, 'enemy_type') and t.enemy_type == 'lakitu':
                                    continue
                                if t.state in ['dying', 'dead', 'falling_out', 'thrown']:
                                    continue
                                    
                                # GENEROUS collision - within 1 cell
                                if abs(t.x - px) < 1.0 and abs(t.y - py) < 1.0:
                                    if hasattr(t, 'handle_stomp'):
                                        print(f"[STOMP-FALL] Piece at ({px},{py}) stomped turtle at ({t.x:.1f},{t.y:.1f}) state={t.state}")
                                        t.handle_stomp(self)
                                        if t.enemy_type in ['magic_mushroom', 'magic_star', 'item']:
                                            if t in self.turtles: self.turtles.remove(t)
                                        else:
                                            self.turtles_stomped += 1
                
                self.current_piece.y += g_dir
                on_floor = self.grid.check_collision(self.current_piece)
                self.current_piece.y -= g_dir
                
                if on_floor:
                    self.lock_timer += dt
                    if self.lock_timer >= self.max_lock_delay:
                        self.sound_manager.play('lock')
                        self.grid.lock_piece(self.current_piece)
                        self.lock_timer = 0
                        self.lock_move_count = 0
                        cleared, events, line_indices = self.grid.clear_lines()
                        if cleared > 0: self.handle_line_clear(cleared, events, line_indices)
                        self.current_piece = self.next_piece
                        self.next_piece = self.spawner.get_next_piece()
                        if self.grid.check_collision(self.current_piece):
                            self.handle_block_out()  # Use lives system
                else: self.lock_timer = 0

            # Spawning
            self.turtle_spawn_timer += dt
            spawn_rate = max(4.0, 8.0 - (self.level * 0.3))
            if self.turtle_spawn_timer > spawn_rate: 
                self.turtle_spawn_timer = 0; r = random.random()
                if self.level == 1: 
                    t = Turtle(is_golden=True, tetris=self) if r < 0.05 else Turtle(tetris=self)
                elif self.level == 2: 
                    if r < 0.20: t = Blooper(tetris=self)
                    elif r < 0.40: t = RedTurtle(tetris=self)
                    else: t = Turtle(tetris=self)
                elif self.level == 3:
                    if r < 0.15: t = HammerBro(tetris=self)
                    elif r < 0.30: t = Blooper(tetris=self)
                    else: t = Turtle(tetris=self)
                else: 
                    if r < 0.10: t = HammerBro(tetris=self)
                    elif r < 0.20: t = Blooper(tetris=self)
                    elif r < 0.30: t = Piranha(tetris=self)
                    elif r < 0.45: t = Spiny(tetris=self)
                    elif r < 0.60: t = RedTurtle(tetris=self)
                    else: t = Turtle(tetris=self)
                self.turtles.append(t)

            for t in self.turtles[:]:
                try:
                    # Skip Lakitu - it's updated separately above
                    if hasattr(t, 'enemy_type') and t.enemy_type == 'lakitu':
                        continue
                    
                    # Update animation for ALL states    
                    t.update_animation()
                    
                    # Update movement and get result
                    result = t.update_movement(dt, self.grid)
                    
                    # Check for stomping ONLY if enemy is still alive/active
                    if t.state not in ['dying', 'falling_out', 'dead']:
                        if self.current_piece:
                            piece_grid_x, piece_grid_y = int(self.current_piece.x), int(self.current_piece.y)
                            stomped = False
                            for bx, by in self.current_piece.blocks:
                                gx, gy = piece_grid_x + bx, piece_grid_y + by
                                # Relaxed collision for interaction
                                if abs(t.x - gx) < 1.0 and abs(t.y - gy) < 1.5:
                                     t.handle_stomp(self)
                                     if t.enemy_type in ['magic_mushroom', 'magic_star']:
                                         if t in self.turtles: self.turtles.remove(t)
                                     else: 
                                         self.turtles_stomped += 1
                                         self.frame_stomps += 1
                                     stomped = True
                                     break
                            if stomped:
                                continue
                    
                    # Handle special results
                    if result == 'SQUISHED':
                        self.sound_manager.play('stomp')
                        self.frame_stomps += 1
                        if t in self.turtles: self.turtles.remove(t)
                        continue
                        
                    # Remove if update returned True (death animation complete or fell off screen)
                    if result == True:
                        if t.state == 'falling_out' and t.enemy_type not in ['magic_mushroom', 'magic_star', 'item']:
                            # Damage player if enemy escapes off bottom
                            if not self.star_active:
                                self.hearts -= 1; self.damage_flash_timer = 0.2; self.screen_shake_timer = 0.3
                                self.sound_manager.play('damage')
                                if self.hearts <= 0:
                                    self.lives -= 1; self.hearts = self.max_hearts
                                    if self.lives <= 0: self.game_state = 'GAMEOVER'
                        if t in self.turtles: self.turtles.remove(t)
                except Exception as e:
                    print(f"[TURTLE ERROR] {e} - removing turtle")
                    if t in self.turtles: self.turtles.remove(t)
            
            # Check for stomp combos
            if self.frame_stomps == 2:
                # 2x stomp combo
                self.sound_manager.play('stomp_combo')
                self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, "DOUBLE STOMP!", (255, 200, 0)))
                self.score += 200
            elif self.frame_stomps >= 3:
                bonus = self.frame_stomps * 500
                self.score += bonus
                self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2 - 50, f"{self.frame_stomps}x STOMP COMBO!", (255, 215, 0)))
                self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, f"+{bonus} POINTS!", C_NEON_PINK))
                self.sound_manager.play('level_up')
            self.frame_stomps = 0  # Reset for next frame

            if self.game_state == 'PLAYING':
                self.match_timer -= dt
                if self.match_timer <= 0:
                    self.lives -= 1; self.hearts = self.max_hearts
                    self.sound_manager.play('damage')
                    if self.lives <= 0: self.game_state = 'GAMEOVER'
                    else: self.match_timer = 400.0

            for heart in self.falling_hearts[:]:
                heart['y'] += heart['vy']; heart['vy'] += 0.5
                if heart['y'] > WINDOW_HEIGHT: self.falling_hearts.remove(heart)
            if self.damage_flash_timer > 0: self.damage_flash_timer -= dt
            for e in self.effects[:]:
                 if isinstance(e, dict):
                      # Standard particle
                      e['x'] += e['vx'] * dt; e['y'] += e['vy'] * dt; e['vy'] += 800 * dt
                      e['life'] -= dt * 1.5
                      if e['life'] <= 0: self.effects.remove(e)
                 elif hasattr(e, 'update'):
                      # Hammer or other object
                      e.update(dt)
                      # Collision with CURRENT PIECE
                      if hasattr(e, 'x') and self.current_piece:
                          for bx, by in self.current_piece.blocks:
                              if abs(e.x - (self.current_piece.x + bx)) < 0.8 and abs(e.y - (self.current_piece.y + by)) < 0.8:
                                  self.sound_manager.play('damage')
                                  self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, "BLOCK SMASHED!", C_RED))
                                  if e in self.effects: self.effects.remove(e)
                                  break
                      if hasattr(e, 'y') and e.y > GRID_HEIGHT + 2:
                          if e in self.effects: self.effects.remove(e)
            
            # Mario Helper System Update
            if self.game_state == 'PLAYING':
                self.mario_helper_cooldown -= dt
                self.update_mario_helper(dt)
                
                # Check if Mario should appear
                if not self.mario_helper_active and self.check_mario_helper_trigger():
                    self.trigger_mario_helper()

            # Update Sound Manager
            if hasattr(self, 'sound_manager'):
                self.sound_manager.update(dt)

        except Exception as e:
            self.log_event(f"CRASH IN UPDATE: {e}")
            import traceback
            traceback.print_exc()

    def draw(self):
        try:
            # Always Draw to Virtual Surface first
            target = self.game_surface
            
            if self.game_state == 'INTRO':
                self.draw_intro()
            elif self.game_state == 'BONUS':
                if self.bonus_level: self.bonus_level.draw(target)
            elif self.game_state == 'COUNTDOWN':
                self._draw_actual_game(target)
                # Dark overlay
                overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 150))
                target.blit(overlay, (0, 0))
                # Big countdown number
                countdown_val = getattr(self, 'countdown_value', 3)
                if countdown_val > 0:
                    try:
                        big_font = pygame.font.SysFont('arial black', 120, bold=True)
                    except:
                        big_font = self.font_big
                    cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2
                    main_txt = big_font.render(str(countdown_val), True, (255, 255, 0))
                    target.blit(main_txt, main_txt.get_rect(center=(cx, cy)))
            else:
                self._draw_actual_game(target)

            # Mobile Controls Visual Feedback (touch ripples, zone highlights)
            if hasattr(self, 'gesture_controls') and self.game_state == 'PLAYING':
                game_time = pygame.time.get_ticks() / 1000.0
                self.gesture_controls.draw(target, game_time)
            
            # Draw Mario Helper running across screen
            if self.game_state == 'PLAYING':
                self.draw_mario_helper(target)

            self.draw_persistent_ui(target)
            
            # FINAL SCALING BLIT TO PHYSICAL SCREEN
            self.screen.fill((0, 0, 0)) # Clean margins
            scaled_surf = pygame.transform.scale(self.game_surface, 
                                               (int(WINDOW_WIDTH * self.scale), 
                                                int(WINDOW_HEIGHT * self.scale)))
            self.screen.blit(scaled_surf, (self.offset_x, self.offset_y))
            
            pygame.display.flip()
        except Exception as e:
            self.log_event(f"DRAW ERROR: {e}")

    def draw_intro(self):
        try:
            target = self.game_surface
            self.intro_scene.draw(target, muted=self.sound_manager.muted)
            cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2
            title_shadow = self.font_big.render("MARIO TETRIS", True, (0, 0, 0))
            target.blit(title_shadow, title_shadow.get_rect(center=(cx + 4, cy - 146)))
            title = self.font_big.render("MARIO TETRIS", True, C_NEON_PINK)
            target.blit(title, title.get_rect(center=(cx, cy - 150)))
            esc = self.font_small.render("PRESS ESC TO QUIT", True, C_WHITE)
            target.blit(esc, esc.get_rect(center=(cx, cy + 140)))
            
            # Larger Hitbox for Mobile
            tetris_btn_rect = pygame.Rect(0, 0, 400, 100); tetris_btn_rect.center = (cx, cy + 20)
            self.btn_tetris_rect = tetris_btn_rect
            pygame.draw.rect(target, (255, 20, 147), tetris_btn_rect, border_radius=15)
            pygame.draw.rect(target, C_WHITE, tetris_btn_rect, 2, border_radius=15)
            t_surf = self.font_small.render("PLAY MARIO TETRIS", True, C_WHITE)
            target.blit(t_surf, t_surf.get_rect(center=tetris_btn_rect.center))
            
            # BIG dynamic "TAP ANYWHERE" text
            # Add breathing/pulsing effect
            pulse = math.sin(pygame.time.get_ticks() * 0.005) * 0.5 + 0.5
            pulse_color = (int(255 * pulse), int(255 * pulse), 0)
            tap_text = self.font_med.render("PRESS ANYWHERE TO START?", True, pulse_color)
            target.blit(tap_text, tap_text.get_rect(center=(cx, cy + 100)))
            
            # DIRECT MOUSE POLLING (bypass events for mobile)
            mouse_buttons = pygame.mouse.get_pressed()
            real_mouse_pos = pygame.mouse.get_pos()
            mouse_pos = self.get_game_coords(real_mouse_pos)
            if mouse_buttons[0]:  # Left click/touch
                if not hasattr(self, '_intro_click_handled'):
                    self._intro_click_handled = True
                    if mouse_pos[1] > 60:  # Below UI
                        print(f"DIRECT MOUSE POLL START at {mouse_pos}")
                        self.reset_game()
                        self.game_state = 'PLAYING'
            else:
                self._intro_click_handled = False
                
        except Exception as e:
            self.log_event(f"INTRO DRAW ERROR: {e}")

    def draw_persistent_ui(self, target):
        ui_w, ui_h = 480, 50
        ui_x, ui_y = (WINDOW_WIDTH - ui_w) // 2, 5
        
        if not self.ui_bg or self.ui_bg.get_width() != ui_w:
            self.ui_bg = pygame.Surface((ui_w, ui_h), pygame.SRCALPHA)
            pygame.draw.rect(self.ui_bg, (0, 0, 0, 160), (0, 0, ui_w, ui_h), border_radius=12)
        
        target.blit(self.ui_bg, (ui_x, ui_y))
        
        # Mute
        self.mute_btn_rect = pygame.Rect(ui_x + 10, ui_y + 5, 40, 40)
        pygame.draw.rect(target, (70, 70, 90), self.mute_btn_rect, border_radius=8)
        m_cx, m_cy = self.mute_btn_rect.center
        pygame.draw.rect(target, C_WHITE, (m_cx-7, m_cy-4, 7, 8))
        pygame.draw.polygon(target, C_WHITE, [(m_cx, m_cy-8), (m_cx+8, m_cy-12), (m_cx+8, m_cy+12), (m_cx, m_cy+8)])
        if self.sound_manager.muted:
            pygame.draw.line(target, (255, 0, 0), (m_cx-12, m_cy-12), (m_cx+12, m_cy+12), 4)

        # Volume
        self.vol_rect = pygame.Rect(ui_x + 60, ui_y + 20, 150, 10)
        pygame.draw.rect(target, (40, 40, 50), self.vol_rect, border_radius=5)
        
        # Corrected volume property access
        v_val = getattr(self.sound_manager, 'master_volume', 0.5)
        v_fill = int(v_val * 150)
        pygame.draw.rect(target, (0, 180, 255), (ui_x + 60, ui_y + 20, v_fill, 10), border_radius=5)
        pygame.draw.circle(target, C_WHITE, (ui_x + 60 + v_fill, ui_y + 25), 8)

        # Song
        self.song_btn_rect = pygame.Rect(ui_x + 220, ui_y + 5, 190, 40)
        pygame.draw.rect(target, (0, 120, 215), self.song_btn_rect, border_radius=10)
        tr = self.sound_manager.neon_playlist[self.sound_manager.neon_track_index]
        s_txt = self.font_small.render(f"MUSIC: {tr[:14]}", True, C_WHITE)
        target.blit(s_txt, s_txt.get_rect(center=self.song_btn_rect.center))

        # Settings (Gear)
        self.settings_btn_rect = pygame.Rect(ui_x + 420, ui_y + 5, 40, 40)
        pygame.draw.rect(target, (60, 60, 80), self.settings_btn_rect, border_radius=8)
        gx, gy = self.settings_btn_rect.center
        for angle in range(0, 360, 45):
            dx = int(14 * math.cos(math.radians(angle)))
            dy = int(14 * math.sin(math.radians(angle)))
            pygame.draw.circle(target, (200, 200, 200), (gx + dx, gy + dy), 4)
        
        # DEBUG: Draw touch feedback (red circles that fade)
        if hasattr(self, 'touch_debug_pos'):
            current_time = pygame.time.get_ticks()
            self.touch_debug_pos = [(pos, t) for pos, t in self.touch_debug_pos if current_time - t < 1000]
            for pos, timestamp in self.touch_debug_pos:
                age = current_time - timestamp
                alpha = max(0, 255 - int(age * 0.255))
                radius = 30 + int(age * 0.02)
                surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(surf, (255, 0, 0, alpha), (radius, radius), radius, 3)
                self.screen.blit(surf, (pos[0] - radius, pos[1] - radius))

    def _draw_actual_game(self, target):
        try:
            # We draw everything to target (self.game_surface)
            if self.game_state == 'WORLD_CLEAR':
                # Draw the game board behind the pipe
                pass 
            else:
                # Basic states with immediate return
                if self.game_state == 'GAMEOVER':
                    self.draw_game_over()
                    return

            # Draw To Virtual Surface
            # Dynamic Level Background - uses per-level theme
            if hasattr(self, 'theme_bg'):
                self.game_surface.fill(self.theme_bg)
            else:
                theme = WORLD_THEMES.get(self.world, WORLD_THEMES[1])
                self.game_surface.fill(theme['bg'])
            
            # Draw Clouds (with safety check)
            for c in self.clouds:
                if hasattr(c, 'draw'):
                    c.draw(self.game_surface)
            
            self.grid.draw(self.game_surface, self.total_time, 
                         bg_color=getattr(self, 'theme_bg', None),
                         accent_color=getattr(self, 'theme_accent', None))
            
            # Line Flash Highlight (Subtler)
            if getattr(self, 'line_flash_timer', 0) > 0:
                self.line_flash_timer -= 0.016 # Assumed 60fps dt
                alpha = int(120 * (self.line_flash_timer / 0.3)) # Max 120 alpha instead of 255
                for ly in getattr(self, 'flash_lines', []):
                    flash_rect = pygame.Rect(PLAYFIELD_X, PLAYFIELD_Y + ly * BLOCK_SIZE, PLAYFIELD_WIDTH, BLOCK_SIZE)
                    s = pygame.Surface((PLAYFIELD_WIDTH, BLOCK_SIZE))
                    s.set_alpha(alpha)
                    s.fill((255, 255, 255))
                    self.game_surface.blit(s, flash_rect)
            
            # Star Power Effect
            if self.star_active:
                 s = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
                 s.set_alpha(50)
                 cols = [(255, 0, 0), (255, 165, 0), (255, 255, 0), (0, 255, 0), (0, 0, 255), (75, 0, 130)]
                 tick = pygame.time.get_ticks() // 100
                 s.fill(cols[tick % len(cols)])
                 self.game_surface.blit(s, (0, 0))

            if self.damage_flash_timer > 0:
                 # Subtle VIGNETTE instead of full screen flash
                 v_thickness = 40
                 s = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
                 # Top
                 pygame.draw.rect(s, (255, 0, 0, 100), (0, 0, WINDOW_WIDTH, v_thickness))
                 # Bottom
                 pygame.draw.rect(s, (255, 0, 0, 100), (0, WINDOW_HEIGHT - v_thickness, WINDOW_WIDTH, v_thickness))
                 # Left/Right
                 pygame.draw.rect(s, (255, 0, 0, 100), (0, 0, v_thickness, WINDOW_HEIGHT))
                 pygame.draw.rect(s, (255, 0, 0, 100), (WINDOW_WIDTH - v_thickness, 0, v_thickness, WINDOW_HEIGHT))
                 self.game_surface.blit(s, (0, 0))
            
            for p in self.popups:
                p.draw(self.game_surface, {'small': self.font_small, 'med': self.font_med, 'big': self.font_big})
                
            if getattr(self, 'show_level_intro', False):
             self.level_intro_timer -= 0.016
             if self.level_intro_timer <= 0: self.show_level_intro = False
             
             cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 100
             
             # Theme accent color
             accent = getattr(self, 'theme_accent', C_NEON_PINK)
             theme_name = getattr(self, 'level_theme', 'NEON')
             
             # DRAW PREMIUM BANNER BOX
             banner_w, banner_h = 640, 120
             banner_rect = pygame.Rect(cx-banner_w//2, cy-80, banner_w, banner_h)
             s_banner = pygame.Surface((banner_w, banner_h), pygame.SRCALPHA)
             pygame.draw.rect(s_banner, (0, 0, 0, 180), (0, 0, banner_w, banner_h), border_radius=20)
             pygame.draw.rect(s_banner, accent, (0, 0, banner_w, banner_h), 3, border_radius=20)
             self.game_surface.blit(s_banner, banner_rect)

             txt1 = self.font_big.render(f"WORLD {self.world}-{self.level_in_world}", True, C_WHITE)
             txt_theme = self.font_med.render(f"~ {theme_name} ~", True, accent)
             
             self.game_surface.blit(txt1, txt1.get_rect(center=(cx, cy-30)))
             self.game_surface.blit(txt_theme, txt_theme.get_rect(center=(cx, cy+25)))

             for e in self.effects:
                 if isinstance(e, dict) and e.get('type') == 'particle':
                      alpha = int(255 * e['life'])
                      s = pygame.Surface((4,4))
                      s.fill(e['color'])
                      s.set_alpha(alpha)
                      self.game_surface.blit(s, (e['x'], e['y']))
                 elif hasattr(e, 'draw'):
                      e.draw(self.game_surface)

            # Draw Ghost Piece
            ghost_y = self.current_piece.y
            g_dir = 1 # Standard gravity only now
            while not self.grid.check_collision(self.current_piece) and abs(self.current_piece.y) < GRID_HEIGHT * 2:
                 self.current_piece.y += g_dir
            self.current_piece.y -= g_dir
            
            # Use a transparent surface for the ghost blocks for better alpha blending
            ghost_block_surf = pygame.Surface((BLOCK_SIZE, BLOCK_SIZE), pygame.SRCALPHA)
            ghost_block_surf.fill(C_GHOST)
            pygame.draw.rect(ghost_block_surf, (255, 255, 255, 100), (0, 0, BLOCK_SIZE, BLOCK_SIZE), 1)

            for bx, by in self.current_piece.blocks:
                px = PLAYFIELD_X + (self.current_piece.x + bx) * BLOCK_SIZE
                py = PLAYFIELD_Y + (self.current_piece.y + by) * BLOCK_SIZE
                self.game_surface.blit(ghost_block_surf, (px, py))
            self.current_piece.y = ghost_y 

            # Draw Active Piece
            t_data = TETROMINO_DATA.get(self.current_piece.name, {})
            active_img = None
            if 'sprite' in t_data:
                cat = t_data['category']
                name = t_data['sprite']
                
                # Check for animated type
                if cat in ['koopa_green', 'koopa_red', 'spiny']:
                    frames = self.sprite_manager.get_animation_frames(cat, prefix='walk', scale_factor=2.0)
                    if frames:
                        idx = int(self.total_time * 6) % len(frames)
                        active_img = frames[idx]
                else:
                    active_img = self.sprite_manager.get_sprite(cat, name, scale_factor=2.0)

            for bx, by in self.current_piece.blocks:
                px = PLAYFIELD_X + (self.current_piece.x + bx) * BLOCK_SIZE
                py = PLAYFIELD_Y + (self.current_piece.y + by) * BLOCK_SIZE
                
                if active_img:
                    self.game_surface.blit(active_img, (px, py))
                else:
                    draw_3d_block(self.game_surface, self.current_piece.color, px, py, BLOCK_SIZE)

            # Draw Turtles & Magic Mushrooms
            for t in self.turtles:
                # Skip Lakitu - it has its own draw method called separately
                if hasattr(t, 'enemy_type') and t.enemy_type == 'lakitu':
                    continue
                if t.state == 'dead': continue
                
                target_frames = None
                if t.state == 'flying':
                    target_frames = t.fly_frames_right if t.direction == 1 else t.fly_frames_left
                elif t.state == 'dying':
                    # Use walk frames for dying (shell frames often empty)
                    target_frames = t.walk_frames_right if t.direction == 1 else t.walk_frames_left
                else:
                    target_frames = t.walk_frames_right if t.direction == 1 else t.walk_frames_left
                
                if target_frames and len(target_frames) > 0:
                     img = target_frames[t.current_frame % len(target_frames)]
                     
                     # Calculate position
                     px = PLAYFIELD_X + t.x * BLOCK_SIZE
                     py = PLAYFIELD_Y + (t.y + 1) * BLOCK_SIZE - img.get_height()
                     
                     # Apply shake when dying
                     if t.state == 'dying':
                         shake_x = getattr(t, 'shake_offset_x', 0) * BLOCK_SIZE
                         shake_y = getattr(t, 'shake_offset_y', 0) * BLOCK_SIZE
                         px += shake_x
                         py += shake_y
                         # Tint red/white flash
                         flash_surf = img.copy()
                         flash_surf.fill((255, 100, 100), special_flags=pygame.BLEND_RGB_ADD)
                         img = flash_surf
                     
                     self.game_surface.blit(img, (px, py))
                else:
                    px = PLAYFIELD_X + t.x * BLOCK_SIZE
                    py = PLAYFIELD_Y + t.y * BLOCK_SIZE
                    pygame.draw.rect(self.game_surface, (0, 255, 0), (px, py, BLOCK_SIZE, BLOCK_SIZE))
                
                if t.state == 'landed':
                    bar_w, bar_h = BLOCK_SIZE, 4
                    pct = 1.0 - (t.landed_timer / t.max_lifetime)
                    fill_w = int(bar_w * max(0, pct))
                    pygame.draw.rect(self.game_surface, (50, 0, 0), (px, py - 8, bar_w, bar_h))
                    col = C_GREEN if pct > 0.5 else C_RED
                    pygame.draw.rect(self.game_surface, col, (px, py - 8, fill_w, bar_h))

            if self.lakitu and hasattr(self.lakitu, 'draw'):
                try:
                    self.lakitu.draw(self.game_surface)
                except Exception as e:
                    print(f"Lakitu draw error: {e}")
                    self.lakitu = None

            # Draw Big Boss
            if self.big_boss:
                self.big_boss.draw(self.game_surface)

            # HUD (Responsive) - ONLY DRAW DURING PLAYING OR WORLD CLEAR
            if self.game_state in ['PLAYING', 'WORLD_CLEAR']:
                is_vertical = WINDOW_HEIGHT > WINDOW_WIDTH * 1.2
                
                # PREPARE ASSETS
                mario_head = None
                if hasattr(self, 'sprite_manager'):
                     mario_head = self.sprite_manager.get_sprite('mario', 'stand', scale_factor=2.0)
                
                if is_vertical:
                    # [VERTICAL HUD]
                    pygame.draw.rect(self.game_surface, (10, 10, 20), (0, 0, WINDOW_WIDTH, 100))
                    pygame.draw.line(self.game_surface, (100, 100, 150), (0, 100), (WINDOW_WIDTH, 100), 2)
        
                    spacing = WINDOW_WIDTH // 4
                    # 1. COINS (Was Mario/Score)
                    self.game_surface.blit(self.font_small.render("COINS", True, (255,215,0)), (30, 25))
                    self.game_surface.blit(self.font_small.render(f"{int(self.score):06d}", True, C_WHITE), (30, 50))
                    
                    # 2. LIVES (Mario x N)
                    if mario_head:
                        self.game_surface.blit(mario_head, (spacing + 10, 35))
                        self.game_surface.blit(self.font_small.render(f"x {self.lives}", True, C_WHITE), (spacing + 45, 50))
                    
                    # 3. WORLD
                    self.game_surface.blit(self.font_small.render("WORLD", True, (200,200,200)), (2 * spacing + 10, 25))
                    self.game_surface.blit(self.font_small.render(f"{self.world}-{self.level_in_world}", True, C_WHITE), (2 * spacing + 10, 50))
                    self.game_surface.blit(self.font_small.render(f"Ln: {self.lines_this_level}/{self.lines_required}", True, C_NEON_PINK), (2 * spacing + 10, 78))
                    
                    # 4. NEXT PIECE (Top Right)
                    np_x = 3 * spacing + 20
                    np_y = 30
                    # Bg Box
                    pygame.draw.rect(self.game_surface, (0, 0, 0), (np_x - 10, np_y - 10, 90, 70), border_radius=8)
                    pygame.draw.rect(self.game_surface, (100, 100, 100), (np_x - 10, np_y - 10, 90, 70), 2, border_radius=8)
                    self.game_surface.blit(self.font_small.render("NEXT", True, (150, 150, 150)), (np_x + 10, np_y - 25))
                    
                    # Draw Next Piece
                    p = self.next_piece
                    scale_sz = 20 # Bigger
                    for bx, by in p.blocks:
                        d_x = np_x + (bx + 1) * scale_sz
                        d_y = np_y + (by + 1) * scale_sz
                        sprite_name = COLOR_TO_SPRITE.get(p.color)
                        img = None
                        if sprite_name: img = self.sprite_manager.get_sprite('tetris_blocks', sprite_name, scale_factor=scale_sz/32.0)
                        if img: self.game_surface.blit(img, (d_x, d_y))
                        else: draw_3d_block(self.game_surface, p.color, d_x, d_y, scale_sz)

                else:
                    # [HORIZONTAL HUD (Right Side)]
                    hud_x = PLAYFIELD_X + PLAYFIELD_WIDTH + 50
                    hud_y = 60
                    
                    # Panel Background
                    panel_rect = pygame.Rect(hud_x - 20, 40, 220, 600)
                    panel_surf = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
                    panel_surf.fill((0, 0, 0, 150)) 
                    self.game_surface.blit(panel_surf, panel_rect)
                    
                    # 1. COINS (Combined Score)
                    self.game_surface.blit(self.font_small.render("COINS", True, (255, 215, 0)), (hud_x, hud_y))
                    self.game_surface.blit(self.font_small.render(f"{int(self.displayed_score):06d}", True, C_WHITE), (hud_x, hud_y + 25))
                    
                    # 1a. STOMPS (For Bonus Spins)
                    self.game_surface.blit(self.font_small.render(f"STOMPS: {getattr(self, 'turtles_stomped', 0)}", True, C_GREEN), (hud_x, hud_y + 50))

                    hud_y += 80
                    
                    # 1b. WORLD
                    self.game_surface.blit(self.font_small.render("WORLD", True, (200,200,200)), (hud_x, hud_y))
                    self.game_surface.blit(self.font_small.render(f"{self.world}-{self.level_in_world}", True, C_WHITE), (hud_x, hud_y + 25))
                    self.game_surface.blit(self.font_small.render(f"Lines: {self.lines_this_level}/{self.lines_required}", True, C_NEON_PINK), (hud_x, hud_y + 50))
                    
                    hud_y += 80
                    
                    # 2. MATCH TIMER
                    self.game_surface.blit(self.font_small.render("TIME", True, (200,200,200)), (hud_x, hud_y))
                    self.game_surface.blit(self.font_small.render(f"{max(0, int(self.match_timer)):03d}", True, C_WHITE), (hud_x, hud_y + 25))
                    
                    hud_y += 80
                    
                    # 3. LIVES (Mario x N) display
                    if mario_head:
                         self.game_surface.blit(mario_head, (hud_x, hud_y))
                         self.game_surface.blit(self.font_small.render(f"x {self.lives}", True, C_WHITE), (hud_x + 40, hud_y + 15))
                    else:
                         self.game_surface.blit(self.font_small.render(f"LIVES: {self.lives}", True, C_WHITE), (hud_x, hud_y))

                    hud_y += 80
                    
                    # 4. NEXT PIECE (Bigger & Clearer)
                    self.game_surface.blit(self.font_small.render("NEXT", True, (200, 200, 200)), (hud_x, hud_y))
                    
                    # Draw Box
                    box_rect = (hud_x - 10, hud_y + 30, 120, 100)
                    pygame.draw.rect(self.game_surface, (20, 20, 30), box_rect, border_radius=8)
                    pygame.draw.rect(self.game_surface, (100, 100, 120), box_rect, 2, border_radius=8)
                    
                    p = self.next_piece
                    scale_sz = 24 # Nice and big
                    start_nx = hud_x + 10
                    start_ny = hud_y + 40
                    
                    for bx, by in p.blocks:
                        d_x = start_nx + (bx + 1) * scale_sz
                        d_y = start_ny + (by + 1) * scale_sz
                        sprite_name = COLOR_TO_SPRITE.get(p.color)
                        img = None
                        if sprite_name: img = self.sprite_manager.get_sprite('tetris_blocks', sprite_name, scale_factor=scale_sz/32.0)
                        if img: self.game_surface.blit(img, (d_x, d_y))
                        else: draw_3d_block(self.game_surface, p.color, d_x, d_y, scale_sz)
                    
                    # Controls Helper
                    hud_y += 180
                     
                    # --- INPUT VISUALIZER (Moved down) ---
                    keys_pressed = pygame.key.get_pressed()
                    viz_x = hud_x
                    viz_y = hud_y
                    
                    def draw_key(label, k_code, kx, ky, kw=30):
                        is_pressed = keys_pressed[k_code]
                        col = (200, 200, 255) if is_pressed else (50, 50, 80)
                        pygame.draw.rect(self.game_surface, col, (kx, ky, kw, 30), border_radius=4)
                        pygame.draw.rect(self.game_surface, C_WHITE, (kx, ky, kw, 30), 1, border_radius=4)
                        lbl = self.font_small.render(label, True, C_WHITE if not is_pressed else (0,0,0))
                        self.game_surface.blit(lbl, lbl.get_rect(center=(kx + kw//2, ky + 15)))

                    # Arrow Keys layout
                    draw_key("UP", pygame.K_UP, viz_x + 35, viz_y)
                    draw_key("LT", pygame.K_LEFT, viz_x, viz_y + 35)
                    draw_key("DN", pygame.K_DOWN, viz_x + 35, viz_y + 35)
                    draw_key("RT", pygame.K_RIGHT, viz_x + 70, viz_y + 35)
                    
                    # Z, X, Space
                    draw_key("Z", pygame.K_z, viz_x + 120, viz_y + 10)
                    draw_key("X", pygame.K_x, viz_x + 155, viz_y + 10)
                    
                    # Spacebar (Wide)
                    draw_key("SPACE (SHIFT)", pygame.K_SPACE, viz_x, viz_y + 80, kw=150)
                    
                    # === MUSIC DISPLAY (Added Below Controls) ===
                    hud_y += 200
                    music_box_y = hud_y
                    
                    # Music Box Background
                    music_rect = pygame.Rect(hud_x - 10, music_box_y, 180, 85)
                    pygame.draw.rect(self.game_surface, (10, 10, 30), music_rect, border_radius=8)
                    pygame.draw.rect(self.game_surface, (100, 200, 255), music_rect, 2, border_radius=8)
                    
                    # Music Icon/Label
                    self.game_surface.blit(self.font_small.render("♫ NOW PLAYING", True, (150, 200, 255)), (hud_x, music_box_y + 8))
                    
                    # Track Name
                    track_name = self.sound_manager.get_track_display_name()
                    self.game_surface.blit(self.font_small.render(track_name, True, C_WHITE), (hud_x, music_box_y + 30))
                    
                    # Track Position
                    track_num, track_total = self.sound_manager.get_track_position()
                    position_text = f"Track {track_num}/{track_total}"
                    self.game_surface.blit(self.font_small.render(position_text, True, (200, 200, 200)), (hud_x, music_box_y + 52))
                    
                    # Next Track hint
                    self.game_surface.blit(self.font_small.render("Press N for next", True, (120, 120, 140)), (hud_x, music_box_y + 70))
                    
                # HEARTS HUD
                heart_x = PLAYFIELD_X + 10
                heart_y = PLAYFIELD_Y - 40
                for i in range(self.max_hearts):
                    # Pulsate if low health or if it is the current heart being lost
                    pulsate = 0
                    if self.hearts <= 1 or (i == self.hearts - 1):
                         pulsate = math.sin(pygame.time.get_ticks() * 0.015) * 4
                    
                    if i < self.hearts:
                        draw_heart(self.game_surface, heart_x + i*35, heart_y + pulsate, 28, active=True)
                    else:
                        draw_heart(self.game_surface, heart_x + i*35, heart_y, 28, active=False)

                # PROGRESS BAR
                bar_w, bar_h, bar_x, bar_y = PLAYFIELD_WIDTH, 6, PLAYFIELD_X, PLAYFIELD_Y - 5
                pygame.draw.rect(self.game_surface, (30, 30, 40), (bar_x, bar_y, bar_w, bar_h), border_radius=3)

    
                # Progress Bar - Slim flat line that doesn't interfere with gameplay
                bar_w, bar_h, bar_x, bar_y = PLAYFIELD_WIDTH, 4, PLAYFIELD_X, 96
                pygame.draw.rect(self.game_surface, (40, 40, 60), (bar_x, bar_y, bar_w, bar_h))
                if self.is_boss_level:
                    fill_pct = max(0, self.boss_hp / self.max_boss_hp)
                    pygame.draw.rect(self.game_surface, (255, 0, 0), (bar_x, bar_y, int(bar_w * fill_pct), bar_h))
                    # Boss Label
                    lbl = self.font_small.render("BOSS HP", True, C_WHITE)
                    self.game_surface.blit(lbl, (bar_x, bar_y - 18))
                else:
                    fill_pct = min(1.0, self.lines_this_level / self.lines_required)
                    pygame.draw.rect(self.game_surface, C_GREEN, (bar_x, bar_y, int(bar_w * fill_pct), bar_h))
    
                if self.antigravity_active:
                     txt = f"ANTIGRAVITY: {int(self.antigravity_timer)+1}"
                     surf = self.font_small.render(txt, True, C_NEON_PINK)
                     self.game_surface.blit(surf, (WINDOW_WIDTH//2-surf.get_width()//2, 140))
    
                for heart in self.falling_hearts: draw_heart(self.game_surface, heart['x'], heart['y'], 24)
                
                # Draw Popups (Centered or localized)
                for p in self.popups:
                    p.draw(self.game_surface, {'small': self.font_small, 'med': self.font_med, 'big': self.font_big})
                
                # HUD END

            # Screen size remains constant with gesture controls
            # (No need for dynamic height adjustment)

            # Responsive Layout Logic
            is_vertical = WINDOW_HEIGHT > WINDOW_WIDTH * 1.2
            
            # Apply Camera Zoom / Effect ONTO target (if vertically oriented)
            if is_vertical and self.camera_zoom > 1.01:
                # Copy current target state to crop it from
                raw_draw = target.copy()
                
                # Anchor bottom-center
                view_w = int(WINDOW_WIDTH / self.camera_zoom)
                view_h = int(WINDOW_HEIGHT / self.camera_zoom)
                
                # PANNING LOGIC
                target_center_x = WINDOW_WIDTH // 2
                if hasattr(self, 'current_piece') and self.current_piece:
                     px = PLAYFIELD_X + (self.current_piece.x + 2) * BLOCK_SIZE
                     target_center_x = px
                
                target_view_x = target_center_x - (view_w // 2)
                if not hasattr(self, 'camera_x'): self.camera_x = 0
                diff = target_view_x - self.camera_x
                if abs(diff) > 20: self.camera_x += diff * 0.05
                
                view_x = int(self.camera_x)
                view_y = WINDOW_HEIGHT - view_h
                view_x = max(0, min(view_x, WINDOW_WIDTH - view_w))
                view_y = max(0, view_y)
                
                sub = raw_draw.subsurface((view_x, view_y, view_w, view_h))
                scaled = pygame.transform.smoothscale(sub, (WINDOW_WIDTH, WINDOW_HEIGHT))
                target.blit(scaled, self.shake_offset)
            else:
                # Horizontal Mode: Just apply shake offset if any
                if self.shake_offset != (0,0):
                    raw_draw = target.copy()
                    target.fill((0,0,0))
                    target.blit(raw_draw, self.shake_offset)

            # Special Overlays
            if self.game_state == 'WORLD_CLEAR':
                 self.draw_world_clear()
                

            # Draw Scanline Overlay (Retro Vibe)
            if self.scanline_overlay:
                 target.blit(self.scanline_overlay, (0,0))
                 
            # Draw gesture tutorial if enabled
            if getattr(self, 'show_gesture_tutorial', False):
                self.gesture_controls.draw_tutorial(target, self.font_small)
            
            # Draw Bot Debug
            if hasattr(self, 'ai_bot'): self.ai_bot.draw_debug(target)

        except Exception as e:
            self.log_event(f"CRASH IN DRAW: {e}")
            import traceback
            traceback.print_exc()

    def log_event(self, message):
        print(f"[{pygame.time.get_ticks()}] {message}")

    def draw_world_clear(self):
        try:
            target = self.game_surface
            # Stats Screen - Use Overlay
            overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
            overlay.set_alpha(180) # Lighter alpha so game is visible
            overlay.fill((0, 0, 0))
            target.blit(overlay, (0, 0))
            
            # Center info
            cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2
            
            # Draw Panel
            panel_rect = pygame.Rect(0, 0, 600, 400)
            panel_rect.center = (cx, cy)
            pygame.draw.rect(target, (20, 20, 40), panel_rect, border_radius=20)
            pygame.draw.rect(target, C_NEON_PINK, panel_rect, 4, border_radius=20)
            
            # Text
            l1 = self.font_big.render("LEVEL CLEARED!", True, C_NEON_PINK)
            l2 = self.font_big.render(f"SCORE: {int(self.score)}", True, C_WHITE)
            l3 = self.font_med.render(f"STOMPS: {getattr(self, 'turtles_stomped', 0)}", True, C_GREEN)
            
            # Enemy Unlocks Logic (Flavor)
            unlocks = ["RED KOOPAS", "PARATROOPAS", "SPINYS", "HAMMER BROS", "BOWSER?"]
            e_idx = max(0, (self.world - 1) * 4 + (self.level_in_world - 1))
            new_enemy = unlocks[e_idx % len(unlocks)]
            
            theme_txt = f"{self.world}-{self.level_in_world}: {getattr(self, 'level_theme', 'NEON')}"
            
            l4 = self.font_big.render(f"UNLOCKED: {new_enemy}!", True, (255, 215, 0))
            l5 = self.font_med.render("NEXT: BONUS ROUND...", True, (200, 200, 255))
            l6 = self.font_med.render(theme_txt, True, C_WHITE) # Theme info

            target.blit(l1, l1.get_rect(center=(cx, cy - 140)))
            target.blit(l6, l6.get_rect(center=(cx, cy - 90))) # Theme
            target.blit(l2, l2.get_rect(center=(cx, cy - 40)))
            target.blit(l3, l3.get_rect(center=(cx, cy + 10)))
            target.blit(l4, l4.get_rect(center=(cx, cy + 70)))
            target.blit(l5, l5.get_rect(center=(cx, cy + 130)))
            
        except Exception as e:
            print(f"Error drawing world clear: {e}")
        
        # Animated Character (Mario Running across bottom)
        anim_time = self.transition_timer * 10
        # Frame index 0,1,2 - use walk animation
        m_frame = None
        if hasattr(self, 'sprite_manager'):
            # Try to get walk animation frames
            walk_frames = ['walk_1', 'walk_2', 'walk_3']
            frame_name = walk_frames[int(anim_time) % len(walk_frames)]
            m_frame = self.sprite_manager.get_sprite('mario', frame_name, scale_factor=3.0)
            # Fallback to stand if walk frames don't exist
            if not m_frame:
                m_frame = self.sprite_manager.get_sprite('mario', 'stand', scale_factor=3.0)
        
        mx = (self.transition_timer / 5.0) * (WINDOW_WIDTH + 100) - 50
        my = WINDOW_HEIGHT - 100
        if m_frame:
            self.screen.blit(m_frame, (mx, my))
        else:
            # Fallback: draw Mario-colored placeholder
            pygame.draw.rect(target, (255, 0, 0), (mx, my, 50, 50))  # Red (should not happen)

    def draw_game_over(self):
        target = self.game_surface
        target.fill((50, 0, 0))
        font_big = pygame.font.SysFont('Arial', 60, bold=True)
        font_small = pygame.font.SysFont('Arial', 30)
        
        title = font_big.render("GAME OVER", True, C_WHITE)
        score = font_small.render(f"FINAL SCORE: {self.score}", True, (255, 215, 0))
        retry = font_small.render("PRESS ENTER TO RETRY", True, C_WHITE)
        
        cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2
        target.blit(title, title.get_rect(center=(cx, cy - 50)))
        target.blit(score, score.get_rect(center=(cx, cy + 20)))
        target.blit(retry, retry.get_rect(center=(cx, cy + 80)))

    # --- Input Actions ---
    def _process_mobile_action(self, action):
        """Process actions returned from MobileControls"""
        if action == 'MOVE_LEFT':
            self.action_move(-1)
        elif action == 'MOVE_RIGHT':
            self.action_move(1)
        elif action == 'ROTATE':
            self.action_rotate(1)
        elif action == 'HARD_DROP':
            self.sound_manager.play('drop')
            self.action_hard_drop()
        elif action == 'SOFT_DROP':
            self.action_soft_drop()
    
    def action_soft_drop(self):
        """Move piece down one row (soft drop)"""
        self.current_piece.y += 1
        if self.grid.check_collision(self.current_piece):
            self.current_piece.y -= 1
        else:
            self.score += 1  # Award 1 point per soft drop cell
            
    def action_move(self, dx):
        self.current_piece.x += dx
        if self.grid.check_collision(self.current_piece): 
            self.current_piece.x -= dx
        else: 
            self.sound_manager.play('move')
            # Reset lock delay on successful move
            if self.lock_move_count < self.max_lock_moves:
                self.lock_timer = 0
                self.lock_move_count += 1
                
        self.das_direction = dx
        self.das_timer = 0

    def action_rotate(self, direction=1):
        # SRS-lite Wall Kick logic
        # 1. Try normal rotation
        orig_rotation = self.current_piece.rotation_index
        self.current_piece.rotate(direction)
        if not self.grid.check_collision(self.current_piece):
             self.sound_manager.play('rotate')
             if self.lock_move_count < self.max_lock_moves:
                 self.lock_timer = 0
                 self.lock_move_count += 1
             return
             
        # 2. Try Wall Kicks (Right 1, Left 1, Up 1, Right 2, Left 2)
        kicks = [(1, 0), (-1, 0), (0, -1), (2, 0), (-2, 0)]
        for dx, dy in kicks:
            self.current_piece.x += dx
            self.current_piece.y += dy
            if not self.grid.check_collision(self.current_piece):
                self.sound_manager.play('rotate')
                if self.lock_move_count < self.max_lock_moves:
                    self.lock_timer = 0
                    self.lock_move_count += 1
                return
            # Backtrack
            self.current_piece.x -= dx
            self.current_piece.y -= dy
            
        # 3. Fail
        self.current_piece.rotate(-direction)

    def action_hard_drop(self):
        g_dir = 1
        turtles_killed = 0
        # Drop until collision
        while not self.grid.check_collision(self.current_piece) and self.current_piece.y < GRID_HEIGHT:
             self.current_piece.y += g_dir
             
             # BOSS HIT CHECK - During Hard Drop
             if self.big_boss:
                 hit = False
                 for bx, by in self.current_piece.blocks:
                     gx, gy = int(self.current_piece.x + bx), int(self.current_piece.y + by)
                     if gx >= self.big_boss.x and gx < self.big_boss.x + self.big_boss.width:
                         if gy >= self.big_boss.y - 1.5 and gy <= self.big_boss.y + 0.5:
                             hit = True; break
                 if hit:
                     self.damage_boss(50, "SMASH")
                     # Consume piece on hit
                     self.current_piece = self.next_piece
                     self.next_piece = self.spawner.get_next_piece()
                     return

             # STOMP LOGIC: Check if we hit any turtles on the way down
             for bx, by in self.current_piece.blocks:
                 piece_x = self.current_piece.x + bx
                 piece_y = self.current_piece.y + by
                 for t in self.turtles[:]:
                     if hasattr(t, 'enemy_type') and t.enemy_type == 'lakitu': continue
                     # Generous collision for Hard Drop
                     if abs(t.x - piece_x) < 1.0 and abs(t.y - piece_y) < 1.0:
                          if t.state not in ['dying', 'dead', 'falling_out']:
                               t.handle_stomp(self)
                               if t.enemy_type in ['magic_mushroom', 'magic_star', 'item']:
                                   if t in self.turtles: self.turtles.remove(t)
                               else: 
                                   turtles_killed += 1
                                   
                                   self.kills_this_level += 1
                                   if not hasattr(self, 'turtles_stomped'): self.turtles_stomped = 0
                                   self.turtles_stomped += 1
        
        self.current_piece.y -= g_dir
        
        # Check for Slot Machine Trigger (3+ kills)
        if turtles_killed > 0:
            print(f"DEBUG: Turtles killed this drop: {turtles_killed}")
        
        if turtles_killed >= 3:
             # User requested Slots only between levels.
             self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, "COMBO SMASH!", C_RED))
             # self.trigger_slot_machine(spins=1, reason='COMBO')
                
        # Immediate Lock for modern feel
        self.sound_manager.play('lock')
        self.grid.lock_piece(self.current_piece)
        
        # Line Clearing
        cleared, events, line_indices = self.grid.clear_lines()
        if cleared > 0: self.handle_line_clear(cleared, events, line_indices)
        
        # Next Piece
        self.current_piece = self.next_piece
        self.next_piece = self.spawner.get_next_piece()
        if self.grid.check_collision(self.current_piece):
            self.handle_block_out()  # Use lives system
        
        self.lock_timer = 0
        self.lock_move_count = 0
        self.fall_timer = 0
        # Screen Shake on Hard Drop
        self.screen_shake_timer = 0.15 

    # World Shift Mechanic REMOVED as per user preference.

    async def run(self):
        self.running = True
        
        # DEFERRED MUSIC START - Wait for FIRST interaction
        # Browser policies block audio until the user clicks.
        # We handle this in the Event loop now.
        pass

        
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            
            # Input (Updated from previous remappings)
            for event in pygame.event.get():
                if event.type == pygame.QUIT: self.running = False
                if event.type == pygame.VIDEORESIZE:
                    self.update_scaling()
                    # Re-init gesture controls with new dimensions if they existed
                    if hasattr(self, 'gesture_controls'):
                        self.gesture_controls = GestureControls((WINDOW_WIDTH, WINDOW_HEIGHT))
                
                if event.type == pygame.KEYUP:
                    if event.key == pygame.K_DOWN: self.key_down_held = False
                    if event.key == pygame.K_LEFT and self.das_direction == -1: self.das_direction = 0
                    if event.key == pygame.K_RIGHT and self.das_direction == 1: self.das_direction = 0
                
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.game_state == 'PLAYING': 
                             self.sound_manager.stop_music()
                             self.game_state = 'GAMEOVER'  # Go to game over instead
                        else: 
                             self.running = False
                             pygame.quit()
                             sys.exit()
                    if self.game_state == 'INTRO' or self.game_state == 'GAMEOVER':
                        if event.key == pygame.K_RETURN:
                            self.reset_game()
                            self.game_state = 'PLAYING'
                            
                    # Gameplay Controls
                    if self.game_state == 'PLAYING':
                        # if event.key == pygame.K_UP: self.action_hard_drop() # REMOVED: Conflict with Rotate
                        if event.key == pygame.K_z: self.action_rotate(-1)
                        if event.key == pygame.K_x or event.key == pygame.K_UP: self.action_rotate(1)
                        if event.key == pygame.K_SPACE: 
                                self.sound_manager.play('drop')
                                self.action_hard_drop()
                        if event.key == pygame.K_LEFT: self.action_move(-1)
                        if event.key == pygame.K_RIGHT: self.action_move(1)
                        if event.key == pygame.K_DOWN:
                            self.current_piece.y += 1
                            if self.grid.check_collision(self.current_piece): self.current_piece.y -= 1
                        
                        if event.key == pygame.K_w and self.p_wing_active:
                             self.current_piece.y -= 1
                             if self.grid.check_collision(self.current_piece): self.current_piece.y += 1
                        
                        if event.key == pygame.K_b: # Manual Bonus Trigger (moved from Z)
                             self.game_state = 'BONUS'
                             print("Entering Bonus Level...")
                             self.bonus_level.start()
                             
                        if event.key == pygame.K_0:
                             self.auto_play = not getattr(self, 'auto_play', False)
                             state_txt = "ON" if self.auto_play else "OFF"
                             # Using C_BLUE or similar if NEON_BLUE fails
                             col = (100, 200, 255)
                             self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, f"AUTO-PLAY {state_txt}", col))

                        if event.key == pygame.K_n:
                             self.sound_manager.next_track()
                             self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, "NEXT TRACK", (100, 255, 100)))

                        if event.key == pygame.K_m:
                             self.sound_manager.toggle_mute()
                             state_txt = "MUTED" if self.sound_manager.muted else "UNMUTED"
                             self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, state_txt, (255, 215, 0)))

                        if event.key == pygame.K_s: # AUDIO DIAGNOSTIC
                             mixer_init = pygame.mixer.get_init() is not None
                             music_busy = pygame.mixer.music.get_busy()
                             sfx_count = len(self.sound_manager.sounds)
                             msg = f"MIXER: {mixer_init} | BUSY: {music_busy} | SFX: {sfx_count}"
                             self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2 + 40, msg, (100, 200, 255), size='small'))
                             print(f"--- AUDIO DIAGNOSTIC --- \n{msg}\nTrack: {self.sound_manager._current_track}")
                             self.sound_manager.play('rotate') # Test SFX
                        
                        if event.key == pygame.K_l:  # Level Skip (Debug)
                             self.level += 1
                             self.level_in_world += 1
                             if self.level_in_world > 4:
                                 self.level_in_world = 1
                                 self.world += 1
                             self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, f"LEVEL {self.level}", (255, 215, 0)))
                        
                        if event.key == pygame.K_m:  # Manual Mario Helper (Debug)
                             self.mario_helper_cooldown = 0  # Reset cooldown
                             self.trigger_mario_helper()
                    
                    # Global Keys
                    if event.key == pygame.K_f: self.toggle_fullscreen()
                    if event.key == pygame.K_n:  # Next Track
                        self.sound_manager.next_song()
                        self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, f"♫ {self.sound_manager.get_track_display_name()}", C_NEON_BLUE))
                
                # Mouse Inputs
            if self.game_state == 'SLOT_MACHINE':
                self.slot_machine.handle_input(event)
                
            # Handle FINGERDOWN (true mobile touch) in addition to MOUSEBUTTONDOWN
            game_time = pygame.time.get_ticks() / 1000.0
            
            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN) and self.game_state != 'SLOT_MACHINE':
                # SATISFY BROWSER INTERACTION REQUIREMENT
                if not getattr(self, '_interaction_triggered', False):
                    self._interaction_triggered = True
                    if self.game_state == 'INTRO':
                        self.sound_manager.play_music_intro()
                        print("[Audio] First interaction: Starting Intro Music")
                    else:
                        self.sound_manager.play_music_gameplay()
                        print("[Audio] First interaction: Starting Gameplay Music")

                # Get position and map to game coordinates

                if event.type == pygame.FINGERDOWN:
                    sw, sh = self.screen.get_size()
                    real_pos = (int(event.x * sw), int(event.y * sh))
                    touch_pos = self.get_game_coords(real_pos)
                else:
                    if event.button != 1: continue
                    touch_pos = self.get_game_coords(event.pos)
                
                ui_handled = False
                
                # Shared UI Handlers (check these FIRST)
                if hasattr(self, 'mute_btn_rect') and self.mute_btn_rect.collidepoint(touch_pos):
                    self.sound_manager.toggle_mute()
                    ui_handled = True
                elif hasattr(self, 'song_btn_rect') and self.song_btn_rect.collidepoint(touch_pos):
                    self.sound_manager.next_song()
                    ui_handled = True
                elif hasattr(self, 'settings_btn_rect') and self.settings_btn_rect.collidepoint(touch_pos):
                    if sys.platform != 'emscripten':
                        import subprocess
                        subprocess.Popen([sys.executable, 'asset_editor.py'], cwd=os.path.dirname(os.path.abspath(__file__)))
                    else:
                        print("Asset Editor not available in web version")
                    ui_handled = True
                elif hasattr(self, 'vol_rect') and self.vol_rect.collidepoint(touch_pos):
                    vol = (touch_pos[0] - self.vol_rect.left) / self.vol_rect.width
                    self.sound_manager.set_volume(vol)
                    ui_handled = True
                
                # Settings Button (Intro)
                if self.game_state == 'INTRO' and hasattr(self, 'intro_scene'):
                    action = self.intro_scene.handle_click(touch_pos)
                    if action == 'settings':
                        if sys.platform != 'emscripten':
                            import subprocess
                            subprocess.Popen([sys.executable, 'asset_editor.py'], cwd=os.path.dirname(os.path.abspath(__file__)))
                        else:
                            print("Asset Editor not available in web version")
                        ui_handled = True
                    if action == 'mute':
                        self.sound_manager.toggle_mute()
                        ui_handled = True
                
                # Check Tetris Button (Main Game) - ULTRA AGGRESSIVE FOR MOBILE
                if self.game_state == 'INTRO':
                    # Any tap below the UI bar starts the game (mobile fix)
                    if touch_pos[1] > 60:
                        print(f"Starting Tetris Mode (Touch at {touch_pos})...")
                        self.reset_game()
                        self.game_state = 'PLAYING'
                        ui_handled = True
                
                # Mobile Controls - Pass to new MobileControls system
                if self.game_state == 'PLAYING' and not ui_handled:
                    if hasattr(self, 'gesture_controls'):
                        self.gesture_controls.handle_touch_down(touch_pos, game_time)
            
            # Handle touch/finger move for drag tracking
            if event.type == pygame.FINGERMOTION:
                sw, sh = self.screen.get_size()
                touch_pos = self.get_game_coords((int(event.x * sw), int(event.y * sh)))
                if hasattr(self, 'gesture_controls'):
                    self.gesture_controls.handle_touch_move(touch_pos)
            
            if event.type in (pygame.MOUSEBUTTONUP, pygame.FINGERUP):
                self.key_down_held = False
                
                # Get position
                if event.type == pygame.FINGERUP:
                    sw, sh = self.screen.get_size()
                    touch_pos = self.get_game_coords((int(event.x * sw), int(event.y * sh)))
                else:
                    touch_pos = self.get_game_coords(event.pos)
                
                if self.game_state == 'INTRO' and hasattr(self, 'intro_scene'):
                    self.intro_scene.handle_mouse_up(touch_pos)
                
                # Mobile Controls - Get action from gesture
                if self.game_state == 'PLAYING' and hasattr(self, 'gesture_controls'):
                    action = self.gesture_controls.handle_touch_up(touch_pos, game_time)
                    if action:
                        self._process_mobile_action(action)
                    
            
            try:
                if self.game_state == 'PLAYING':
                    if self.active_world == 'SHADOW': dt *= 1.25
                    if getattr(self, 'shift_cooldown', 0) > 0: self.shift_cooldown -= dt
                    
                    # Mobile Controls DAS (hold-to-repeat) update
                    if hasattr(self, 'gesture_controls'):
                        game_time = pygame.time.get_ticks() / 1000.0
                        das_action = self.gesture_controls.update(dt, game_time)
                        if das_action:
                            self._process_mobile_action(das_action)

                self.update(dt)
                self.draw() # Corrected draw pass (inside run)
            except Exception as e:
                self.log_event(f"RUN LOOP ERROR: {e}")
                import traceback
                traceback.print_exc()

            # Yield control to the browser
            await asyncio.sleep(0)

if __name__ == "__main__":
    try:
        game = Tetris()
        asyncio.run(game.run())
    except Exception as e:
        import traceback
        # In browser, we can't write to crash.txt, so just print
        if sys.platform == 'emscripten':
             print(f"CRASH: {e}")
             traceback.print_exc()
        else:
             with open("crash.txt", "w") as f:
                 f.write(traceback.format_exc())
             print(e)
             input("Press Enter to Exit")
