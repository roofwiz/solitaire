"""
AssetLoader - Configuration-driven asset management for Super Block Bros.
Reads from assets.json and provides clean APIs for loading sprites, animations, and sounds.
"""

import pygame
import json
import os


class AssetLoader:
    """
    Loads and manages game assets from a JSON configuration file.
    Handles sprite sheet slicing, animation sequences, and sound effects.
    """
    
    def __init__(self, config_path='assets.json', base_path='assets'):
        self.config_path = config_path
        self.base_path = base_path
        self.config = {}
        self.sheets = {}  # Cached loaded sprite sheets
        self.sprites = {}  # Cached sliced sprites
        self.sounds = {}  # Cached sound effects
        
        self._load_config()
        self._load_sheets()
    
    def _load_config(self):
        """Load the JSON configuration file."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
                print(f"[AssetLoader] Loaded config from {self.config_path}")
            else:
                print(f"[AssetLoader] ERROR: {self.config_path} not found!")
                self.config = {}
        except Exception as e:
            print(f"[AssetLoader] ERROR loading config: {e}")
            self.config = {}
    
    def _load_sheets(self):
        """Pre-load all sprite sheets defined in the config."""
        images_config = self.config.get('images', {})
        for name, filename in images_config.items():
            path = os.path.join(self.base_path, filename)
            if os.path.exists(path):
                try:
                    self.sheets[name] = pygame.image.load(path).convert_alpha()
                    print(f"[AssetLoader] Loaded sheet: {name} ({filename})")
                except Exception as e:
                    print(f"[AssetLoader] Failed to load {name}: {e}")
            else:
                print(f"[AssetLoader] Sheet not found: {path}")
    
    def get_sprite(self, category, sprite_name, scale=1.0, **kwargs):
        """
        Get a single sprite by name.
        
        Args:
            category: The sprite category (e.g., 'items', 'blocks', 'mario')
            sprite_name: The sprite name within the category (e.g., 'mushroom_super')
            scale: Scale factor to apply (default 1.0)
            **kwargs: Catch legacy arguments like scale_factor
        
        Returns:
            pygame.Surface or None
        """
        if 'scale_factor' in kwargs:
            scale = kwargs['scale_factor']
            
        cache_key = f"{category}:{sprite_name}:{scale}"
        if cache_key in self.sprites:
            return self.sprites[cache_key]
        
        sprite_coords = self.config.get('sprite_coords', {}).get(category, {}).get(sprite_name)
        if not sprite_coords:
            return None
        
        sheet_name = sprite_coords.get('file', 'spritesheet')
        sheet = self.sheets.get(sheet_name)
        if not sheet:
            return None
        
        try:
            x, y = sprite_coords['x'], sprite_coords['y']
            w, h = sprite_coords['w'], sprite_coords['h']
            
            rect = pygame.Rect(x, y, w, h)
            if not sheet.get_rect().contains(rect):
                print(f"[AssetLoader] Sprite out of bounds: {category}/{sprite_name}")
                return None
            
            sprite = sheet.subsurface(rect).copy()
            
            if scale != 1.0:
                new_w = int(w * scale)
                new_h = int(h * scale)
                sprite = pygame.transform.scale(sprite, (new_w, new_h))
            
            self.sprites[cache_key] = sprite
            return sprite
            
        except Exception as e:
            print(f"[AssetLoader] Error extracting {category}/{sprite_name}: {e}")
            return None

    def get_cloud_image(self, size=(32, 24)):
        """Compatibility method for Cloud class"""
        # Try getting cloud from sprite sheet
        cloud = self.get_sprite("cloud", "walk_1", scale=1.0)
        if cloud:
            return pygame.transform.scale(cloud, size)
        
        # Fallback
        c = pygame.Surface(size, pygame.SRCALPHA)
        pygame.draw.ellipse(c, (255,255,255, 200), (0,0,size[0],size[1]))
        return c
    
    def get_animation(self, category, prefix, scale=1.0):
        """
        Get an animation sequence (list of sprites with common prefix).
        
        Args:
            category: The sprite category (e.g., 'items')
            prefix: The prefix for animation frames (e.g., 'star_' for star_1, star_2, etc.)
            scale: Scale factor to apply
        
        Returns:
            List of pygame.Surface
        """
        frames = []
        sprite_data = self.config.get('sprite_coords', {}).get(category, {})
        
        # Find all sprites matching the prefix and sort them
        matching_keys = sorted([k for k in sprite_data.keys() if k.startswith(prefix)])
        
        for key in matching_keys:
            sprite = self.get_sprite(category, key, scale)
            if sprite:
                frames.append(sprite)
        
        return frames
    
    def get_animation_frames(self, category, scale=1.0, prefix=None, **kwargs):
        """Compatibility alias for get_animation"""
        if 'scale_factor' in kwargs:
            scale = kwargs['scale_factor']
            
        if prefix is None:
             # In old SpriteManager, if prefix was None, it meant 'get all'.
             prefix = ""
        return self.get_animation(category, prefix, scale)
    
    def get_block_sprite(self, block_type, frame=0, scale=1.0):
        """
        Get a block sprite by type and frame number.
        
        Args:
            block_type: 'question', 'brick', 'empty'
            frame: Frame number for animated blocks (0-indexed)
            scale: Scale factor
        
        Returns:
            pygame.Surface or None
        """
        if block_type == 'question':
            # Animated: question_1, question_2, question_3
            frame_name = f"question_{(frame % 3) + 1}"
            return self.get_sprite('blocks', frame_name, scale)
        elif block_type == 'empty':
            return self.get_sprite('blocks', 'empty', scale)
        elif block_type == 'brick':
            return self.get_sprite('blocks', 'brick', scale)
        return None
    
    def get_coin_sprite(self, frame=0, scale=1.0):
        """
        Get a spinning coin frame.
        
        Args:
            frame: Animation frame (will be modulated)
            scale: Scale factor
        
        Returns:
            pygame.Surface or None
        """
        # Coin animation: 1, 2, 3, 2, 1, 2, 3... (ping-pong)
        sequence = [1, 2, 3, 2]
        frame_num = sequence[frame % len(sequence)]
        return self.get_sprite('items', f'coin_{frame_num}', scale)
    
    def get_star_sprite(self, frame=0, scale=1.0):
        """
        Get a rainbow star frame.
        
        Args:
            frame: Animation frame (cycles through 4 colors)
            scale: Scale factor
        
        Returns:
            pygame.Surface or None
        """
        frame_num = (frame % 4) + 1
        return self.get_sprite('items', f'star_{frame_num}', scale)
    
    def load_sound(self, sound_name):
        """
        Load a sound effect by name.
        
        Args:
            sound_name: Key from the sounds config
        
        Returns:
            pygame.mixer.Sound or None
        """
        if sound_name in self.sounds:
            return self.sounds[sound_name]
        
        sounds_config = self.config.get('sounds', {})
        filename = sounds_config.get(sound_name)
        if not filename:
            return None
        
        # Try multiple paths for robustness
        paths = [
            os.path.join(self.base_path, 'sounds', filename),
            os.path.join(self.base_path, filename),
            os.path.join('sounds', filename),
            filename
        ]
        
        # In web environment, we might need forward slashes
        if sys.platform == 'emscripten':
            paths = [p.replace('\\', '/') for p in paths]
            
        for path in paths:
            if os.path.exists(path):
                try:
                    sound = pygame.mixer.Sound(path)
                    self.sounds[sound_name] = sound
                    return sound
                except Exception as e:
                    print(f"[AssetLoader] Failed to load sound {sound_name} from {path}: {e}")
        
        print(f"[AssetLoader] Sound NOT found: {sound_name} ({filename})")
        return None
    
    def play_sound(self, sound_name):
        """Play a sound effect by name."""
        sound = self.load_sound(sound_name)
        if sound:
            try:
                sound.play()
            except:
                pass


# --- Level Progress System ---

class LevelProgress:
    """
    Tracks level win conditions for both standard and boss levels.
    """
    
    def __init__(self, world=1, level=1):
        self.world = world
        self.level = level  # 1-3 = standard, 4 = boss
        self.lines_cleared = 0
        self.boss_hp = 0
        self.max_boss_hp = 0
        
        self.reset_level(world, level)
    
    @property
    def is_boss_level(self):
        return self.level == 4
    
    @property
    def lines_required(self):
        """Standard levels require a line quota."""
        # Base: 10 lines, +5 per world, +2 per level
        return 10 + (self.world - 1) * 5 + (self.level - 1) * 2
    
    @property
    def progress_percent(self):
        """Returns progress as 0.0 to 1.0."""
        if self.is_boss_level:
            if self.max_boss_hp == 0:
                return 0.0
            return max(0.0, 1.0 - (self.boss_hp / self.max_boss_hp))
        else:
            if self.lines_required == 0:
                return 1.0
            return min(1.0, self.lines_cleared / self.lines_required)
    
    def reset_level(self, world, level):
        """Reset for a new level."""
        self.world = world
        self.level = level
        self.lines_cleared = 0
        
        if self.is_boss_level:
            # Boss HP scales with world
            self.max_boss_hp = 10 + world * 5
            self.boss_hp = self.max_boss_hp
        else:
            self.boss_hp = 0
            self.max_boss_hp = 0
    
    def add_lines(self, count):
        """
        Add cleared lines and return damage dealt (for boss levels).
        
        Returns:
            tuple: (level_won: bool, damage_dealt: int)
        """
        self.lines_cleared += count
        damage = 0
        
        if self.is_boss_level:
            # Tetris (4 lines) = 5 damage, otherwise 1 damage per line
            if count >= 4:
                damage = 5
            else:
                damage = count
            
            self.boss_hp -= damage
            if self.boss_hp <= 0:
                self.boss_hp = 0
                return (True, damage)  # Boss defeated!
            return (False, damage)
        else:
            # Standard level - check quota
            if self.lines_cleared >= self.lines_required:
                return (True, 0)  # Level complete!
            return (False, 0)
    
    def check_level_win(self):
        """Check if the current level is won."""
        if self.is_boss_level:
            return self.boss_hp <= 0
        else:
            return self.lines_cleared >= self.lines_required


# Global instance for easy access
asset_loader = None

def init_asset_loader(config_path='assets.json'):
    """Initialize the global asset loader."""
    global asset_loader
    asset_loader = AssetLoader(config_path)
    return asset_loader
