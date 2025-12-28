
import sys
import os

# Ensure game root is in path for web/pygbag
game_root = os.path.dirname(os.path.abspath(__file__))
if game_root not in sys.path:
    sys.path.append(game_root)

import pygame
import random
import json
import asyncio
import math
from settings import game_settings
from asset_loader import init_asset_loader, AssetLoader
from asset_editor import AssetEditor
from src.config import *
from src.ai_player import TetrisBot
from src.luigi_generator import generate_luigi_sprites
from src.bonus_level import BonusLevel
from src.scene_dark_world import Scene_DarkWorld
from src.slot_machine import SlotMachine

# --- Game Configuration ---


# --- DAS Configuration ---
DAS_DELAY = 0.3  # Initial delay before auto-repeat
DAS_REPEAT = 0.12 # Speed of auto-repeat

# --- Colors & Style ---
C_BLACK = (10, 10, 10)
C_DARK_BLUE = (20, 20, 40)
C_GRID_BG = (30, 30, 50)
C_NEON_PINK = (255, 20, 147)
C_WHITE = (240, 240, 240)
C_RED = (255, 50, 50)
C_GREEN = (50, 255, 50)
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
def draw_block(screen, x, y, color):
    """Draws a single Tetris block on the grid."""
    px = PLAYFIELD_X + x * BLOCK_SIZE
    py = PLAYFIELD_Y + y * BLOCK_SIZE
    pygame.draw.rect(screen, color, (px, py, BLOCK_SIZE, BLOCK_SIZE))
    # Bevel effect
    pygame.draw.rect(screen, (255, 255, 255), (px, py, BLOCK_SIZE, BLOCK_SIZE), 1)

def draw_heart(surface, x, y, size):
    """Draws an 8-bit style heart."""
    # Pixel art approximations
    color = C_RED
    border = C_WHITE
    # Main body
    pygame.draw.rect(surface, color, (x + 4, y + 4, size - 8, size - 8))
    pygame.draw.rect(surface, color, (x + 2, y + 2, 6, 6))
    pygame.draw.rect(surface, color, (x + size - 8, y + 2, 6, 6))
    pygame.draw.rect(surface, color, (x + size//2 - 2, y + size - 6, 4, 4))
    
    # Border (Optional, simple box for now to match 8-bit style)
    pygame.draw.rect(surface, border, (x, y, size, size), 2)

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
        if self.enemy_type == 'magic_mushroom':
            return [self.tetris.sprite_manager.get_sprite('items', 'mushroom_super', scale_factor=1.5)]
        return Tetris.TURTLE_FRAMES

    def update_animation(self):
        now = pygame.time.get_ticks()
        frames = []
        anim_speed = self.animation_speed
        
        if self.state == 'dying': 
            # ALWAYS use green shell for the hit animation as requested
            # Safe access to tetris reference
            game = getattr(self, 'tetris', None)
            frames = []
            
            if game and hasattr(game, 'sprite_manager'):
                try:
                    frames = game.sprite_manager.get_animation_frames('koopa_green', prefix='shell', scale_factor=2.5)
                except:
                    frames = []
            
            # Fallback to local shell_frames if search fails, but try to avoid it
            if not frames: 
                frames = self.shell_frames
            
            # Spin is fast
            anim_speed = 50 
            
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
                # SQUISH!
                self.state = 'dead' # Instantly gone, no shell animation
                
                # Try to access sound manager via a global or by passing game reference?
                # The method signature is update_movement(self, delta_time, game_grid).
                # game_grid doesn't have the sound manager usually.
                # However, this method is called from Tetris.update().
                # We should probably return a specialized status or handle it there.
                # BUT, for quick fix if we assume we can't change signature easily everywhere:
                # We can return 'SQUISH' instead of False?
                # Actually, main.py loop iterates t.update_movement.
                # Let's check calls site.
                return 'SQUISHED'
        if self.state == 'dying':
            self.dying_timer += delta_time
            self.y += 10 * delta_time
            return self.dying_timer > 2.0 # Longer death for shell spin visibility

        if self.state == 'falling_out':
            self.y += 10 * delta_time 
            return self.y > GRID_HEIGHT + 2

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
                 # Try to snap up if we hit floor/block from top, or just separate
                 self.y = int(self.y)
             return False

        if self.state == 'active':
            self.y += self.speed * delta_time
            landed_y = int(self.y + 1)
            landed_x = int(self.x)
            
            # 1. Land on floor (Bottom of grid)
            if landed_y >= GRID_HEIGHT:
                self.y = GRID_HEIGHT - 1
                self.state = 'landed'
                self.move_timer = 0
                self.landed_timer = 0 # RESET timer!
                return False
                
            # 2. Land on blocks (Check CENTER of turtle for reliable landing)
            check_x = int(self.x + 0.5)
            if 0 <= check_x < GRID_WIDTH and 0 <= landed_y < GRID_HEIGHT and game_grid.grid[landed_y][check_x] is not None:
                self.y = landed_y - 1 
                self.state = 'landed'
                self.move_timer = 0
                self.landed_timer = 0 # RESET timer!
                return False 
                self.state = 'landed'
                self.move_timer = 0
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
            
            if scale != 1.0:
                 offset = (scale - 1.0) * BLOCK_SIZE
                 px -= offset / 2
                 py -= offset 
            
            surface.blit(img, (px, py))

    def handle_stomp(self, game):
        game.sound_manager.play('stomp')
        self.state = 'dying'
        
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

class RedTurtle(Turtle): 
    ENEMY_TYPE = 'red'
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.state = 'flying' # Start flying
class Spiny(Turtle):
    ENEMY_TYPE = 'spiny'
    def handle_stomp(self, game):
        # In Tetris mode, crushing a Spiny with a block should just kill it normally
        # No damage to player!
        return super().handle_stomp(game)

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
        self.state = 'dying'
        if self.m_type == 'poison':
            game.lives -= 1
            game.sound_manager.play('lifelost')
            game.popups.append(PopupText(PLAYFIELD_X + self.x*BLOCK_SIZE, PLAYFIELD_Y + self.y*BLOCK_SIZE, "POISON! -1 LIFE", C_RED))
            return 0
        elif self.m_type == 'mega':
            if hasattr(game, 'trigger_mega_mode'): game.trigger_mega_mode(20.0)
            return 1000
        else:
             # Life
             game.lives = min(game.lives + 1, 5)
             game.sound_manager.play('life')
             game.popups.append(PopupText(PLAYFIELD_X + self.x*BLOCK_SIZE, PLAYFIELD_Y + self.y*BLOCK_SIZE, "1UP!", C_GREEN))
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
        
        # Load sprites
        self.cloud_sprite = tetris_ref.sprite_manager.get_cloud_image((32, 24))
        # FIXED: Access 'walk' key since it's now a dict
        self.koopa_sprite = None
        if hasattr(tetris_ref, 'TURTLE_FRAMES') and isinstance(tetris_ref.TURTLE_FRAMES, dict):
             w_frames = tetris_ref.TURTLE_FRAMES.get('walk', [])
             if w_frames: self.koopa_sprite = w_frames[0]
        
        if not self.koopa_sprite:
            # Absolute fallback
            self.koopa_sprite = tetris_ref.sprite_manager.get_sprite('koopa_green', 'walk_1', scale_factor=2.5)
        
    def update(self, dt):
        self.hover_offset += dt * 5
        self.y = 1 + math.sin(self.hover_offset) * 0.5
        
        self.x += self.speed * dt * self.direction
        if self.x > GRID_WIDTH - 2:
            self.direction = -1
        elif self.x < 0:
            self.direction = 1
            
        self.throw_timer += dt
        if self.throw_timer > 5.0:
            self.throw_timer = 0
            if random.random() < 0.5:
                # Throw Spiny
                if self.tetris:
                    try:
                        s = Spiny(tetris=self.tetris)
                        s.x = max(0, min(GRID_WIDTH-1, int(self.x)))
                        s.y = 2.0 # Thrown slightly lower to avoid spawn collision
                        s.state = 'active'
                        self.tetris.turtles.append(s)
                        self.tetris.popups.append(PopupText(PLAYFIELD_X + self.x*BLOCK_SIZE, PLAYFIELD_Y + self.y*BLOCK_SIZE, "SPINY!", C_RED))
                    except Exception as e:
                        print(f"Lakitu Spiny spawn error: {e}")
            else:
                # Flip Gravity
                # Spawn Star instead of Antigravity
                if self.tetris:
                     self.tetris.spawn_magic_star(self.x, self.y)
                     # Play sound
                     if self.tetris.sound_manager: self.tetris.sound_manager.play('powerup_appears')

    def draw(self, surface):
        px = PLAYFIELD_X + self.x * BLOCK_SIZE
        py = PLAYFIELD_Y + self.y * BLOCK_SIZE
        
        # Draw Cloud
        if self.cloud_sprite:
            surface.blit(self.cloud_sprite, (px - 4, py + 8))
        else:
             pygame.draw.rect(surface, (200, 200, 200), (px, py+8, 32, 16))
             
        # Draw Koopa riding
        if self.koopa_sprite:
             # Draw full for now, shifted up
             surface.blit(self.koopa_sprite, (px, py - 6))
        else:
             pygame.draw.rect(surface, (0, 255, 0), (px + 4, py - 6, 16, 16))



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

    def draw(self, screen, total_time, draw_bg=True, alpha=255, level=1):
        # Draw Background 
        if draw_bg:
            bg_rect = (PLAYFIELD_X, PLAYFIELD_Y, PLAYFIELD_WIDTH, PLAYFIELD_HEIGHT)
            
            # Use WORLD_THEMES for dynamic background
            # level is passed or we default to overworld
            world_idx = ((level - 1) // 4) + 1
            world_cfg = WORLD_THEMES.get(world_idx, WORLD_THEMES[1])
            bg_col = world_cfg['bg']
            
            # Darken the background color slightly for the playfield
            dark_bg = [max(0, c - 40) for c in bg_col]
            
            # Premium Background: Vertical Gradient
            r, g, b = dark_bg
            for i in range(PLAYFIELD_HEIGHT):
                # Gradient factor (darker at bottom)
                f = 1.0 - (i / PLAYFIELD_HEIGHT) * 0.3
                col = (int(r * f), int(g * f), int(b * f))
                pygame.draw.line(screen, col, (PLAYFIELD_X, PLAYFIELD_Y + i), (PLAYFIELD_X + PLAYFIELD_WIDTH, PLAYFIELD_Y + i))
            
            # Pattern Overlay: Subtle Grid
            grid_surf = pygame.Surface((PLAYFIELD_WIDTH, PLAYFIELD_HEIGHT), pygame.SRCALPHA)
            for x in range(0, PLAYFIELD_WIDTH, BLOCK_SIZE):
                pygame.draw.line(grid_surf, (0, 0, 0, 20), (x, 0), (x, PLAYFIELD_HEIGHT))
            for y in range(0, PLAYFIELD_HEIGHT, BLOCK_SIZE):
                pygame.draw.line(grid_surf, (0, 0, 0, 20), (0, y), (PLAYFIELD_WIDTH, y))
            screen.blit(grid_surf, (PLAYFIELD_X, PLAYFIELD_Y))
            
            # Border Glow
            glow_color = (100, 100, 255) if level % 2 == 0 else (255, 100, 100)
            
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
    def __init__(self):
        self.sounds = {}
        self.chan_neon = None
        self.chan_shadow = None
        self.music_neon = None
        self.music_shadow = None
        
        # Initialize ALL defaults first to prevent AttributeErrors if mixer fails
        self.current_vol_neon = 0.5
        self.current_vol_shadow = 0.0
        self.target_world = 'NEON'
        self.master_volume = 0.3
        self.manual_stop = False
        # Separate playlists for intro/lobby        # Intro Playlist
        self.intro_playlist = []
        self.intro_track_index = 0
        self.intro_track = None
        self._current_track = ''
        self.muted = False  # Start with music ON 
        
        # Gameplay playlist - All available tracks for variety!
        # Gameplay playlist - Priotize new songs!
        # Removed Funk Loop and Hear It (Slot exclusive)
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
        
        # Slot Bonus Playlist
        self.slot_playlist = [
            'intro_theme.mp3'
        ]
        self.slot_track_index = 0
        
        self.current_mode = 'intro'  # Track which mode we're in
        
        try: # Look for best intro track immediately
            p_jazz = self._get_path('02. undergroundtheme.mp3')
            if os.path.exists(p_jazz):
                self.intro_track = '02. undergroundtheme.mp3'
            
            pygame.mixer.init()
            pygame.mixer.set_num_channels(24) 
            pygame.mixer.set_num_channels(24) 
            # pygame.mixer.set_reserved(0) # No reserved channels needed
            
            # Create channels early
            # self.chan_neon = pygame.mixer.Channel(0)
            # self.chan_shadow = pygame.mixer.Channel(1)
            self.chan_neon = None
            self.chan_shadow = None
            
            sfx_files = {
                'rotate': 'rotate.wav',
                'lock': 'lock.wav',
                'clear': 'clear.wav',
                'stomp': 'success_bell-6776.mp3',  # New sound for stomping enemies!
                'stomp_fallback': 'stomp.wav',  # Old stomp sound as fallback
                'life': 'life.wav',
                'damage': 'damage.wav',
                'gameover': 'gameover.wav',
                'move': 'move.wav',
                'slot_spin': 'coin-drop-in-slot-5-sfx-330557.mp3',
                'slot_win': 'winner-bell-game-show-91932.mp3'
            }
            for name, fname in sfx_files.items():
                path = self._get_path(fname)
                if os.path.exists(path): 
                    self.sounds[name] = pygame.mixer.Sound(path)
                else:
                    # Fallback for stomp
                    if name == 'stomp':
                        p_lock = self._get_path('lock.wav')
                        if os.path.exists(p_lock): self.sounds[name] = pygame.mixer.Sound(p_lock)
                    print(f"SFX not found: {fname}")
            
            # Dual Music System
            # self.chan_neon/shadow created above
            
            # Dual Mode Tracks Removed (Using Playlist System)
            self.music_neon = None
            self.music_shadow = None
            
            # Intro Track already set at top
            pass
            
        except Exception as e:
            print(f"Sound init global error: {e}")

    def _get_path(self, f):
        p1 = os.path.join('assets', 'sounds', f)
        p2 = os.path.join('sounds', f)
        return p1 if os.path.exists(p1) else p2

    def play(self, name):
        if name in self.sounds:
            try: 
                self.sounds[name].play()
            except Exception as e: 
                print(f"Sound play error for {name}: {e}")
        else:
            print(f"[SoundManager] Sound not loaded: {name}")

    def play_music(self):
        self.play_music_intro()

    def play_music_gameplay(self):
        """Play gameplay music (neon playlist)"""
        self.current_mode = 'gameplay'
        self.stop_music()
        if not self.neon_playlist: return
        
        track = self.neon_playlist[self.neon_track_index]
        self.play_track(track)

    def play_music_slots(self):
        """Play slot machine bonus music"""
        self.stop_music() # Ensure silence
        print("[SoundManager] Slot Music Disabled by Request")
        # self.current_mode = 'slots'
        # if not self.slot_playlist: return
        # track = self.slot_playlist[self.slot_track_index]
        # self.slot_track_index = (self.slot_track_index + 1) % len(self.slot_playlist)
        # self.play_track(track)

    def next_track(self):
        """Cycle to next song in appropriate playlist"""
        if self.current_mode == 'intro':
            # Cycle intro playlist
            self.intro_track_index = (self.intro_track_index + 1) % len(self.intro_playlist)
            self.play_music_intro()
        elif self.current_mode == 'gameplay':
            # Cycle gameplay playlist
            self.neon_track_index = (self.neon_track_index + 1) % len(self.neon_playlist)
            self.play_music_gameplay()
        elif self.current_mode == 'slots':
            # Cycle slot playlist
            self.slot_track_index = (self.slot_track_index + 1) % len(self.slot_playlist)
            self.play_music_slots()

    def play_track(self, track_name):
        """Helper to load and play a single track on pygame.mixer.music"""
        p = self._get_path(track_name)
        
        if os.path.exists(p) and self._current_track != track_name:
            try:
                pygame.mixer.music.load(p)
                pygame.mixer.music.play(-1)  # Loop
                
                # Check mute state and force PAUSE if needed
                if self.muted:
                    pygame.mixer.music.set_volume(0)
                    pygame.mixer.music.pause()
                else:
                    pygame.mixer.music.set_volume(self.master_volume)
                
                self._current_track = track_name
                self.manual_stop = False
                print(f"[{self.current_mode.capitalize()} Music] Playing: {track_name}")
            except Exception as e:
                print(f"Error loading music: {e}")

    def play_music_intro(self):
        """Play intro/lobby music (single track looping)"""
        self.current_mode = 'intro'
        self.stop_music()  # Stop any dual-mode music
        
        if not self.intro_playlist:
            return

        # Get current intro track
        track_name = self.intro_playlist[self.intro_track_index]
        p = self._get_path(track_name)
        
        if os.path.exists(p) and self._current_track != track_name:
            try:
                pygame.mixer.music.load(p)
                pygame.mixer.music.play(-1)  # Loop
                
                # Force volume update immediately (Web Fix)
                vol = 0 if self.muted else self.master_volume
                try: pygame.mixer.music.set_volume(vol)
                except: pass
                
                self._current_track = track_name
                self.manual_stop = False
                print(f"[Intro Music] Playing: {track_name}")
            except Exception as e:
                print(f"Error loading intro music: {e}")

    def stop_music(self):
        """Stop ALL music - both mixer.music and channels"""
        try: 
            # TRIPLE STOP to prevent overlap (web audio bug workaround)
            pygame.mixer.music.fadeout(100)  # Fade out over 100ms
            pygame.mixer.music.stop()
            pygame.mixer.music.stop()  # Call twice for web
            pygame.mixer.music.unload()
            pygame.mixer.stop() # NUCLEAR OPTION: Stops all active channels (Sounds)
        except: pass
        
        # Redundant safety
        if self.chan_neon: self.chan_neon.stop()
        if self.chan_shadow: self.chan_shadow.stop()
        self._current_track = ''
        print("[SoundManager] Music stopped (aggressive)")

    def start_dual_mode(self):
        """Start gameplay music (uses standard music system, not channels)"""
        print("[SoundManager] Starting gameplay music...")
        self.current_mode = 'gameplay'
        self.stop_music()  # Ensure everything is stopped
        
        # Use the standard play_track system for consistency
        self.neon_track_index = 0
        track_name = self.neon_playlist[self.neon_track_index]
        self.play_track(track_name)

    def next_song(self):
        """Cycle to next song in appropriate playlist"""
        if self.current_mode == 'intro':
            # Cycle intro playlist
            self.intro_track_index = (self.intro_track_index + 1) % len(self.intro_playlist)
            self.play_music_intro()
        else:
            # Cycle gameplay playlist
            self.neon_track_index = (self.neon_track_index + 1) % len(self.neon_playlist)
            track_name = self.neon_playlist[self.neon_track_index]
            self.stop_music()
            self.play_track(track_name)

    def set_target_world(self, world):
        self.target_world = world
        self.play('rotate') 
        
    def update(self, dt):
        # Dual mode crossfade logic REMOVED
        self.update_volumes()
        
    def update_volumes(self):
        vol = 0 if self.muted else self.master_volume
        
        # Track mute state change to trigger Pause/Unpause
        if not hasattr(self, '_prev_muted'):
            self._prev_muted = False
            
        if self.muted != self._prev_muted:
            self._prev_muted = self.muted
            try:
                if self.muted:
                    print("Muting: Pausing Music")
                    pygame.mixer.music.pause()
                else:
                    print("Unmuting: Resuming Music")
                    pygame.mixer.music.unpause()
                    pygame.mixer.music.set_volume(vol)
            except: pass
        
        # Continuously enforce volume (if unmuted)
        if not self.muted:
            try: pygame.mixer.music.set_volume(vol)
            except: pass
        
        # Update Channels
        # Update Channels
        if self.chan_neon: self.chan_neon.set_volume(0)
        if self.chan_shadow: self.chan_shadow.set_volume(0)
        try:
            # Apply volume to all loaded sounds
            for s in self.sounds.values():
                s.set_volume(vol)
        except: pass

    def toggle_mute(self):
        self.muted = not self.muted
        self.update_volumes()
        return self.muted

    def set_volume(self, v):
        self.master_volume = max(0.0, min(1.0, v))
        self.update_volumes()
    
    def get_track_display_name(self):
        """Returns a clean, short version of the current track name"""
        track = self._current_track
        if not track:
            return "No Music"
        
        # Strip .mp3 extension
        name = track.replace('.mp3', '')
        
        # Clean up specific tracks
        name_map = {
            '01. The James Bond Theme': 'James Bond',
            '02. undergroundtheme': 'Underground',
            '2. Bring The Noise': 'Bring The Noise',
            'energic-funk-upbeat-vintage-and-confident-mood-loop-1-371308': 'Funky Loop',
            'music_dark_jazz': 'Dark Jazz',
            'lifelost': 'Life Lost'
        }
        
        return name_map.get(name, name[:20])  # Fallback to first 20 chars
    
    def get_track_position(self):
        """Returns current track number and total tracks"""
        if self.current_mode == 'intro':
            return (self.intro_track_index + 1, len(self.intro_playlist))
        elif self.current_mode == 'gameplay':
            return (self.neon_track_index + 1, len(self.neon_playlist))
        elif self.current_mode == 'slots':
            return (self.slot_track_index + 1, len(self.slot_playlist))
        return (0, 0)

    @property
    def volume(self):
        return self.master_volume
    
    @volume.setter
    def volume(self, v):
        self.set_volume(v)

# IntroScene moved to src.scene_intro
from src.scene_intro import IntroScene

class GestureControls:
    """Modern gesture-based controls for mobile Tetris"""
    def __init__(self, screen_dimensions):
        self.screen_w, self.screen_h = screen_dimensions
        self.touch_start = None
        self.touch_start_time = 0
        self.swipe_threshold = 50  # Minimum distance for swipe
        self.tap_time_threshold = 0.3  # Maximum time for tap
        self.last_action = None
        self.last_action_time = 0
        self.action_cooldown = 0.15  # Prevent spam
        
    def handle_touch_down(self, pos):
        """Called when touch/click starts"""
        self.touch_start = pos
        self.touch_start_time = pygame.time.get_ticks() / 1000.0
        return None
    
    def handle_touch_up(self, pos):
        """Called when touch/click ends - detects gesture"""
        if not self.touch_start:
            return None
            
        current_time = pygame.time.get_ticks() / 1000.0
        time_elapsed = current_time - self.touch_start_time
        
        # Calculate swipe distance
        dx = pos[0] - self.touch_start[0]
        dy = pos[1] - self.touch_start[1]
        distance = (dx**2 + dy**2) ** 0.5
        
        action = None
        
        # Check cooldown
        if current_time - self.last_action_time < self.action_cooldown:
            self.touch_start = None
            return None
        
        # TAP - Quick touch with minimal movement
        if time_elapsed < self.tap_time_threshold and distance < 30:
            action = 'ROTATE'
        
        # SWIPE - Longer distance movement
        elif distance >= self.swipe_threshold:
            # Determine primary direction
            if abs(dx) > abs(dy):
                # Horizontal swipe
                if dx > 0:
                    action = 'RIGHT'
                else:
                    action = 'LEFT'
            else:
                # Vertical swipe
                if dy > 0:
                    action = 'SOFT_DROP'
                else:
                    action = 'HARD_DROP'
        
        # Reset
        self.touch_start = None
        
        if action:
            self.last_action = action
            self.last_action_time = current_time
            
        return action
    
    def draw(self, surface, font):
        """Draw gesture hints (optional, minimal)"""
        # Show subtle hint overlay only if needed
        # For now, let's keep it clean with no UI
        pass
    
    def draw_tutorial(self, surface, font):
        """Show tutorial overlay for first-time users"""
        # Semi-transparent overlay
        overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))
        
        # Title
        title_font = pygame.font.SysFont('Arial', 32, bold=True)
        title = title_font.render("TOUCH CONTROLS", True, (255, 255, 255))
        surface.blit(title, title.get_rect(center=(self.screen_w//2, 100)))
        
        # Instructions
        instructions = [
            ("SWIPE LEFT/RIGHT", "Move piece"),
            ("SWIPE DOWN", "Soft drop"),
            ("SWIPE UP", "Hard drop"),
            ("TAP", "Rotate piece")
        ]
        
        y = 200
        for gesture, action in instructions:
            gesture_text = font.render(gesture, True, (100, 200, 255))
            action_text = font.render(f"→ {action}", True, (200, 200, 200))
            
            surface.blit(gesture_text, (self.screen_w//2 - 150, y))
            surface.blit(action_text, (self.screen_w//2 + 20, y))
            y += 50
        
        # Hint
        hint = font.render("Touch anywhere to dismiss", True, (150, 150, 150))
        surface.blit(hint, hint.get_rect(center=(self.screen_w//2, self.screen_h - 100)))


class Tetris:
    TURTLE_FRAMES = []
    RED_TURTLE_FRAMES = []
    SPINY_FRAMES = []
    GOLDEN_TURTLE_FRAMES = []
    CLOUD_FRAMES = []
    TURTLE_LIFE_ICON = None
    MUSHROOM_FRAMES = []

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
        self.slot_machine = SlotMachine(sprite_manager=self.sprite_manager, sound_manager=self.sound_manager)
        self.sound_manager.play_music()
        
        self.clouds = [] # Disabled clouds (user reported as fire sprite)
        self.bonus_game = BonusGame(self) # Initialize Bonus Game
        self.intro_scene = IntroScene(self.sprite_manager)
        
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
        
        self.intro_timer = 0
        
        # Scaling & Mobile Response Init
        self.fullscreen = False
        self.is_mobile = False 
        self.is_portrait = False
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
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

        # Ensure single instance (Moved here to only run ONCE)
        try:
            import psutil
            curr = os.getpid()
            for p in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if p.info['pid'] != curr:
                        cmd = p.info.get('cmdline') or []
                        if any('main.py' in str(part) for part in cmd):
                            p.terminate()
                except: continue
        except: pass

        self.reset_game()
        self.game_state = 'PLAYING'  # Start playing immediately!
        # Music started in reset_game via play_music_gameplay
            
        # UI Cache
        self.ui_bg = None

    def reset_game(self):
        # Basic Stats (Init first to prevent draw crashes)
        self.auto_play = False 
        self.ai_bot = TetrisBot(self) # Initialize Bot
        self.active_world = 'NEON'
        self.grid.set_world('NEON')
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
        
        # Start Music Logic
        if hasattr(self, 'sound_manager'):
            self.sound_manager.play_music_gameplay()
            
        # Init Spawner & Pieces
        self.spawner = Spawner()
        self.current_piece = self.spawner.get_next_piece()
        self.next_piece = self.spawner.get_next_piece()
        self.turtles = []
        self.turtles_stomped = 0
        self.turtle_spawn_timer = 5.0
        self.stomp_combo = 0
        self.frame_stomps = 0  # Track stomps in a single action for slot trigger
        self.b2b_chain = 0
        
        self.line_flash_timer = 0
        self.flash_lines = []
        
        # Level Progress
        self.lines_required = 10
        self.boss_hp = 0
        self.max_boss_hp = 0
        self.boss_garbage_timer = 0
        self.is_boss_level = False
        
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

        self.reset_level()

    def reset_level(self):
        # Clear Grid for new level
        self.grid.grid_neon = [[None for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.grid.grid_shadow = [[None for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.grid.grid = self.grid.grid_neon # Reset pointer

        self.lines_this_level = 0
        if self.world == 1 and self.level_in_world == 1:
            self.lines_required = 5  # Easy first level
        else:
            self.lines_required = 8 + (self.world - 1) * 4 + (self.level_in_world - 1) * 2
        
        self.is_boss_level = (self.level_in_world == 4)
        if self.is_boss_level:
            self.max_boss_hp = 10 + self.world * 5
            self.boss_hp = self.max_boss_hp
            self.boss_garbage_timer = 12.0  # Slower start - more time to prepare
            self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, "BOSS LEVEL!", C_RED))
        
            # self.sound_manager.play('music') # Removed legacy call
        
        # LEVEL THEMES - Different visuals per level
        level_idx = (self.world - 1) * 4 + (self.level_in_world - 1)
        theme_names = ['NEON', 'OCEAN', 'FOREST', 'FIRE', 'SHADOW', 'CRYSTAL', 'SUNSET', 'MIDNIGHT']
        self.level_theme = theme_names[level_idx % len(theme_names)]
        
        # Apply theme colors
        self.apply_level_theme()
        
        # CHANGE MUSIC each level!
        if hasattr(self, 'sound_manager'):
            self.sound_manager.next_track()
        
        # Announcement
        self.show_level_intro = True
        self.level_intro_timer = 4.0
    
    def apply_level_theme(self):
        """Apply visual theme based on current level"""
        themes = {
            'NEON': {'bg': (20, 20, 40), 'grid': (30, 30, 50), 'accent': (255, 20, 147)},
            'OCEAN': {'bg': (10, 30, 50), 'grid': (20, 50, 80), 'accent': (0, 200, 255)},
            'FOREST': {'bg': (15, 35, 20), 'grid': (25, 55, 35), 'accent': (100, 255, 100)},
            'FIRE': {'bg': (40, 15, 10), 'grid': (60, 25, 20), 'accent': (255, 100, 50)},
            'SHADOW': {'bg': (15, 15, 25), 'grid': (25, 25, 40), 'accent': (150, 100, 200)},
            'CRYSTAL': {'bg': (25, 35, 45), 'grid': (40, 55, 70), 'accent': (150, 220, 255)},
            'SUNSET': {'bg': (45, 25, 30), 'grid': (70, 40, 50), 'accent': (255, 150, 80)},
            'MIDNIGHT': {'bg': (10, 10, 20), 'grid': (20, 20, 35), 'accent': (100, 100, 180)},
        }
        theme = themes.get(self.level_theme, themes['NEON'])
        self.theme_bg = theme['bg']
        self.theme_grid = theme['grid']
        self.theme_accent = theme['accent']

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

        # Boss Damage
        if self.is_boss_level:
            dmg = 1
            if cleared == 4: dmg = 5
            # EXTRA DAMAGE FOR GARBAGE
            if 'BRICK_CLEAR' in events: 
                dmg += 2
                self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2 - 100, "BRICK SMASH!", C_ORANGE, size='big'))
                self.sound_manager.play('damage')
            self.boss_hp -= dmg
            self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2 - 40, f"HIT! -{dmg} HP", C_RED))
            if self.boss_hp <= 0:
                self.boss_hp = 0
                self.trigger_level_win()
        else:
            # Check for level win
            if self.lines_this_level >= self.lines_required:
                self.trigger_level_win()
        
        # Spawn particles if cleared
        if cleared > 0:
            self.spawn_particles(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, (255, 215, 0), count=cleared*20)

    def trigger_level_win(self):
        self.sound_manager.play('world_clear')
        
        # Advance Level Progress
        self.level_in_world += 1
        if self.level_in_world > 4:
            self.level_in_world = 1
            self.world += 1
    
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
    
    def handle_slot_finish(self, result):
        # Result can be int amount or string "COINS:X"
        coins = 0
        if isinstance(result, int):
            coins = result
        elif str(result).startswith("COINS:"):
            coins = int(result.split(":")[1])
            
        score_gain = coins * 10
        self.score += score_gain
            
        # Bonus Lives for huge wins
        lives_gain = coins // 5000
        if lives_gain > 0:
            self.lives += lives_gain
        
        msg = f"BONUS COMPLETE! WON {coins} COINS!"
        if lives_gain > 0: msg += f" +{lives_gain} LIVES!"
        
        self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, msg, C_GREEN))

        # Check sound manager before usage
        if hasattr(self, 'sound_manager'):
             self.sound_manager.next_song()
        
        if getattr(self, 'slot_trigger_reason', 'LEVEL_WIN') == 'LEVEL_WIN':
            self.reset_level()
        else:
            if hasattr(self, 'sound_manager'):
                self.sound_manager.play_music_game()
            
        self.game_state = 'PLAYING'
    
    # self.reset_level() -> Moved to handle_slot_finish

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
        
        # Transfer Winnings (Countdown effect)
        if getattr(self, 'pending_winnings', 0) > 0:
             # Accelerate transfer if huge
             rate = max(10, int(self.pending_winnings * 5 * dt)) 
             amt = min(self.pending_winnings, rate)
             self.score += amt
             self.pending_winnings -= amt
             
        try:
            if self.game_state == 'INTRO':
                 self.intro_scene.update(dt)
                 if pygame.key.get_pressed()[pygame.K_RETURN] and self.intro_scene.state == 'WAITING':
                      self.reset_game()
                      self.game_state = 'PLAYING'
                 return
                 
            # AI Hook
            if hasattr(self, 'ai_bot'):
                 self.ai_bot.active = getattr(self, 'auto_play', False)
                 self.ai_bot.update(dt)
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

            if self.game_state == 'SLOT_MACHINE':
                res = self.slot_machine.update(dt)
                if res and str(res).startswith("COINS:"):
                     amount = int(res.split(":")[1])
                     self.handle_slot_finish(amount)
                # Check if slot machine was closed
                if not self.slot_machine.active:
                     # Transfer Score
                     session_win = getattr(self.slot_machine, 'session_winnings', 0)
                     self.handle_slot_finish(session_win)

                     # Start countdown
                     self.game_state = 'COUNTDOWN' 
                     self.countdown_timer = 3.0
                     self.countdown_value = 3
                     
                     # Reset level ONLY if confirmed Level Clear
                     if getattr(self, 'slot_trigger_reason', 'COMBO') == 'LEVEL_CLEAR':
                         self.reset_level()
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

            # Lakitu Logic - Added extra safety checks to prevent freeze
            if self.lakitu and hasattr(self.lakitu, 'update'):
                try:
                    self.lakitu.update(dt)
                except Exception as e:
                    print(f"Lakitu update error: {e}")
                    self.lakitu = None
            elif self.level >= 3:
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

            # Boss Garbage
            if getattr(self, 'is_boss_level', False) and self.game_state == 'PLAYING':
                self.boss_garbage_timer -= dt
                if self.boss_garbage_timer <= 0:
                    self.trigger_boss_garbage()
                    self.boss_garbage_timer = 12.0 - min(4.0, self.world * 0.5)  # EASIER: More time

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
                        # NEW: Check for stomping during regular fall
                        piece_x_grid = int(self.current_piece.x)
                        piece_y_grid = int(self.current_piece.y)
                        for bx, by in self.current_piece.blocks:
                            px, py = piece_x_grid + bx, piece_y_grid + by
                            for t in self.turtles[:]:
                                # Skip Lakitu - can't stomp it with pieces
                                if hasattr(t, 'enemy_type') and t.enemy_type == 'lakitu':
                                    continue
                                if int(t.x) == px and int(t.y) == py:
                                    if hasattr(t, 'handle_stomp'):
                                        # Turtles are invincible until they land and timer starts
                                        if t.state == 'landed':
                                            t.handle_stomp(self)
                                            # Play stomp sound!
                                            self.sound_manager.play('stomp')
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
                            self.game_state = 'GAMEOVER'; self.sound_manager.play('gameover')
                else: self.lock_timer = 0

            # Spawning
            self.turtle_spawn_timer += dt
            spawn_rate = max(4.0, 8.0 - (self.level * 0.3))
            if self.turtle_spawn_timer > spawn_rate: 
                self.turtle_spawn_timer = 0; r = random.random()
                if self.level == 1: t = Turtle(is_golden=True, tetris=self) if r < 0.05 else Turtle(tetris=self)
                elif self.level == 2: t = RedTurtle(tetris=self) if r < 0.35 else Turtle(tetris=self)
                else: t = Spiny(tetris=self) if r < 0.25 else (RedTurtle(tetris=self) if r < 0.45 else Turtle(tetris=self))
                self.turtles.append(t)

            for t in self.turtles[:]:
                # Skip Lakitu - it's updated separately above
                if hasattr(t, 'enemy_type') and t.enemy_type == 'lakitu':
                    continue
                    
                t.update_animation()
                result = t.update_movement(dt, self.grid)
                if t.state == 'landed':
                    piece_grid_x, piece_grid_y = int(self.current_piece.x), int(self.current_piece.y)
                    for bx, by in self.current_piece.blocks:
                        if int(t.x + 0.5) == piece_grid_x + bx and int(t.y + 0.5) == piece_grid_y + by:
                             t.handle_stomp(self)
                             if t.enemy_type in ['magic_mushroom', 'magic_star']:
                                 if t in self.turtles: self.turtles.remove(t)
                             else: 
                                 self.turtles_stomped += 1
                                 self.frame_stomps += 1  # Track this frame's stomps
                             break
                if result == 'SQUISHED':
                    self.sound_manager.play('stomp')
                    self.frame_stomps += 1  # Also count squishes
                    if t in self.turtles: self.turtles.remove(t)
                    continue
                if result:
                     if t.state == 'falling_out' and t.enemy_type not in ['magic_mushroom', 'magic_star', 'item']:
                        if not self.star_active:
                            self.hearts -= 1; self.damage_flash_timer = 0.2; self.screen_shake_timer = 0.3
                            self.sound_manager.play('damage')
                            if self.hearts <= 0:
                                self.lives -= 1; self.hearts = self.max_hearts
                                if self.lives <= 0: self.game_state = 'GAMEOVER'
                     if t in self.turtles: self.turtles.remove(t)
            
            # Check for 3+ stomps at once -> Trigger Slot Machine!
            if self.frame_stomps >= 3:
                self.game_state = 'SLOT_MACHINE'
                self.slot_machine.trigger(spins=self.frame_stomps)  # Spins = number stomped
                self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2 - 50, f"{self.frame_stomps}x STOMP COMBO!", (255, 215, 0)))
                self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, "BONUS SPINS!", C_NEON_PINK))
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
                 e['x'] += e['vx'] * dt; e['y'] += e['vy'] * dt; e['vy'] += 800 * dt
                 e['life'] -= dt * 1.5
                 if e['life'] <= 0: self.effects.remove(e)

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
            elif self.game_state == 'SLOT_MACHINE':
                self._draw_actual_game(target)
                if self.slot_machine: self.slot_machine.draw(target)
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
            
            # BIG "TAP ANYWHERE" text for mobile
            tap_text = self.font_med.render("TAP ANYWHERE TO START", True, (255, 255, 0))
            target.blit(tap_text, tap_text.get_rect(center=(cx, cy + 80)))
            
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
            
            self.grid.draw(self.game_surface, self.total_time)
            
            # Line Flash Highlight
            if getattr(self, 'line_flash_timer', 0) > 0:
                self.line_flash_timer -= 0.016 # Assumed 60fps dt
                alpha = int(255 * (self.line_flash_timer / 0.3))
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
                 s = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
                 s.set_alpha(150)
                 s.fill(C_RED)
                 self.game_surface.blit(s, (0, 0))
            elif self.lives == 1 and (pygame.time.get_ticks() % 500 < 250):
                s = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
                s.set_alpha(50)
                s.fill(C_RED)
                self.game_surface.blit(s, (0, 0))
            
            for p in self.popups:
                p.draw(self.game_surface, {'small': self.font_small, 'med': self.font_med, 'big': self.font_big})
                
            if getattr(self, 'show_level_intro', False):
             self.level_intro_timer -= 0.016
             if self.level_intro_timer <= 0: self.show_level_intro = False
             
             cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 100
             
             # Theme accent color (or fallback)
             accent = getattr(self, 'theme_accent', C_NEON_PINK)
             theme_name = getattr(self, 'level_theme', 'NEON')
             
             txt1 = self.font_big.render(f"WORLD {self.world}-{self.level_in_world}", True, C_WHITE)
             txt_theme = self.font_med.render(f"~ {theme_name} ZONE ~", True, accent)
             txt2 = self.font_small.render("STOMP TURTLES = COINS", True, C_GREEN)
             
             s = 2
             # Shadow
             self.game_surface.blit(txt1, txt1.get_rect(center=(cx+s, cy+s)))
             self.game_surface.blit(txt1, txt1.get_rect(center=(cx, cy)))
             # Theme name
             self.game_surface.blit(txt_theme, txt_theme.get_rect(center=(cx, cy + 50)))
             self.game_surface.blit(txt2, txt2.get_rect(center=(cx, cy + 90)))

        # Draw Particles
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
                    target_frames = t.shell_frames_right if t.direction == 1 else t.shell_frames_left
                else:
                    target_frames = t.walk_frames_right if t.direction == 1 else t.walk_frames_left
                
                if target_frames and len(target_frames) > 0:
                     img = target_frames[t.current_frame % len(target_frames)]
                     # FIX: Align feet (bottom of sprite) with the bottom of the grid cell
                     px = PLAYFIELD_X + t.x * BLOCK_SIZE
                     py = PLAYFIELD_Y + (t.y + 1) * BLOCK_SIZE - img.get_height()
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
                    
                # OLD HUD CODE REMOVED

    
                # Progress Bar - Slim flat line that doesn't interfere with gameplay
                bar_w, bar_h, bar_x, bar_y = PLAYFIELD_WIDTH, 4, PLAYFIELD_X, 96
                pygame.draw.rect(self.game_surface, (40, 40, 60), (bar_x, bar_y, bar_w, bar_h))
                if self.is_boss_level:
                    fill_pct = max(0, self.boss_hp / self.max_boss_hp)
                    pygame.draw.rect(self.game_surface, C_RED, (bar_x, bar_y, int(bar_w * fill_pct), bar_h))
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
             # STOMP LOGIC: Check if we hit any turtles on the way down
             for bx, by in self.current_piece.blocks:
                 piece_x = self.current_piece.x + bx
                 piece_y = self.current_piece.y + by
                 for t in self.turtles[:]:
                     if hasattr(t, 'enemy_type') and t.enemy_type == 'lakitu': continue
                     if int(t.x) == piece_x and int(t.y) == piece_y:
                          if t.state == 'landed':
                              self.sound_manager.play('stomp')
                              if t in self.turtles: 
                                  self.turtles.remove(t)
                                  turtles_killed += 1
                                  self.kills_this_level += 1
                                  if not hasattr(self, 'turtles_stomped'): self.turtles_stomped = 0
                                  self.turtles_stomped += 1
                          # Add visual effect and score ONLY when actually stomped                             self.popups.append(PopupText(piece_x * BLOCK_SIZE + PLAYFIELD_X, piece_y * BLOCK_SIZE + PLAYFIELD_Y, "SMASH!", C_RED))
        
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
            self.game_state = 'GAMEOVER'
            self.sound_manager.play('gameover')
        
        self.lock_timer = 0
        self.lock_move_count = 0
        self.fall_timer = 0
        # Screen Shake on Hard Drop
        self.screen_shake_timer = 0.15 

    # World Shift Mechanic REMOVED as per user preference.

    async def run(self):
        self.running = True
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
                
                # Slot Input (First Priority)
                if self.game_state == 'SLOT_MACHINE':
                    self.slot_machine.handle_input(event)
                
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
                            self.sound_manager.start_dual_mode()  # Start gameplay music
                            
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
                             self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, f"AUTO-PLAY {state_txt}", C_NEON_BLUE))
                    
                    # Global Keys
                    if event.key == pygame.K_f: self.toggle_fullscreen()
                    if event.key == pygame.K_n:  # Next Track
                        self.sound_manager.next_song()
                        self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, f"♫ {self.sound_manager.get_track_display_name()}", C_NEON_BLUE))
                
                # Mouse Inputs
            if self.game_state == 'SLOT_MACHINE':
                self.slot_machine.handle_input(event)
                
            # Handle FINGERDOWN (true mobile touch) in addition to MOUSEBUTTONDOWN
            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN) and self.game_state != 'SLOT_MACHINE':
                # Get position and map to game coordinates
                if event.type == pygame.FINGERDOWN:
                    sw, sh = self.screen.get_size()
                    real_pos = (int(event.x * sw), int(event.y * sh))
                    touch_pos = self.get_game_coords(real_pos)
                else:
                    if event.button != 1: continue
                    touch_pos = self.get_game_coords(event.pos)
                
                # Visual feedback for debugging (draw a circle at touch point)
                if not hasattr(self, 'touch_debug_pos'):
                    self.touch_debug_pos = []
                self.touch_debug_pos.append((touch_pos, pygame.time.get_ticks()))
                
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
                
                # Mobile Controls (Zones + Swipes)
                if self.game_state == 'PLAYING' and not ui_handled:
                    self.touch_start = touch_pos
            
            if event.type in (pygame.MOUSEBUTTONUP, pygame.FINGERUP):
                self.key_down_held = False
                
                # Get position
                if event.type == pygame.FINGERUP:
                    touch_pos = (int(event.x * WINDOW_WIDTH), int(event.y * WINDOW_HEIGHT))
                else:
                    touch_pos = event.pos
                
                if self.game_state == 'INTRO' and hasattr(self, 'intro_scene'):
                    self.intro_scene.handle_mouse_up(touch_pos)
                
                # Mobile Logic (Zones) - Direct Implementation
                if self.game_state == 'PLAYING' and hasattr(self, 'touch_start') and self.touch_start:
                    start_pos = self.touch_start
                    end_pos = touch_pos
                    dx = end_pos[0] - start_pos[0]
                    dy = end_pos[1] - start_pos[1]
                    dist = (dx**2 + dy**2)**0.5
                    
                    self.touch_start = None # Reset
                    
                    if dist > 50: # Swipe Detected
                        if abs(dx) > abs(dy): # Horizontal Swipe
                             # Optional: Swipe to dash? For now, stick to taps for precision
                             pass 
                        else: # Vertical Swipe
                            if dy > 50: self.action_hard_drop() # Swipe Down = Hard Drop
                            
                    else: # Tap Detected
                        x = end_pos[0]
                        w = WINDOW_WIDTH
                        if x < w * 0.34: 
                            self.action_move(-1) # Left Zone (34%)
                        elif x > w * 0.66: 
                            self.action_move(1) # Right Zone (34%)
                        else: 
                            self.action_rotate() # Center Zone (Rest)
                    
            
            try:
                if self.game_state == 'PLAYING':
                    if self.active_world == 'SHADOW': dt *= 1.25
                    if getattr(self, 'shift_cooldown', 0) > 0: self.shift_cooldown -= dt

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
