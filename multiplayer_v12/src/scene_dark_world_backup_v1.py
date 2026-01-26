import pygame
import os
import math
from src.config import WINDOW_WIDTH, WINDOW_HEIGHT

# Physics Constants
GRAVITY = 1500
MAX_FALL_SPEED = 600
MOVE_SPEED = 200
RUN_SPEED = 350
JUMP_FORCE = -900  # Massively increased for easy jumping
FRICTION = 600
ACCELERATION = 800
SKID_FRICTION = 1200
COYOTE_TIME = 0.1 # 100ms
JUMP_BUFFER_TIME = 0.1 # 100ms

class PlatformerPlayer:
    def __init__(self, x, y, sprite_manager):
        self.x = x
        self.y = y
        self.vx = 0
        self.vy = 0
        self.width = 32
        self.height = 64 # Gigantic Mario for maximum visibility
        self.sprite_manager = sprite_manager
        self.current_sprite = None
        
        # States
        self.on_ground = False
        # States
        self.on_ground = False
        self.facing_right = True
        self.is_jumping = False
        self.state = 'normal' # normal, sliding, finished
        
        # Timers
        self.coyote_timer = 0
        self.jump_buffer_timer = 0
        self.anim_timer = 0
        
    def update(self, dt, inputs, collision_mask, mask_w, mask_h, procedural_platforms=[], sky_color=(0,0,0)):
        # --- STATE: SLIDING (Flagpole) ---
        if self.state == 'sliding':
            self.vx = 0
            self.vy = 200 # Slide down speed
            self.x += 0 # Stay on pole
            self.y += self.vy * dt
            
            # Floor Collision Logic for Sliding
            def is_solid(px, py):
                if px < 0 or px >= mask_w or py < 0 or py >= mask_h: return True
                try:
                    # CHECK PROCEDURAL PLATFORMS FIRST
                    for plat in procedural_platforms:
                        if plat.collidepoint(px, py): return True

                    c = collision_mask.get_at((int(px), int(py)))
                    # TILE MODE OVERRIDE:
                    if procedural_platforms: return False
                     
                    # Legacy Smart Collision (Backup)
                    dist = abs(c.r - sky_color[0]) + abs(c.g - sky_color[1]) + abs(c.b - sky_color[2])
                    if dist < 10: return False # It's Sky (Strict Tolerance)
                    
                    if (c.r + c.g + c.b) > 50: return True
                    
                    if c.r < 5 and c.g < 5 and c.b < 5: return False
                    
                    return True # It's a wall/block
                except: 
                    # If out of bounds Y > Height, it's solid (Floor safety)
                    if py >= mask_h - 20: return True 
                    return False
                
            if is_solid(self.x + self.width/2, self.y + self.height):
                 self.y = int(self.y)
                 # Safety Loop
                 for _ in range(50):
                     if not is_solid(self.x + self.width/2, self.y + self.height): break
                     self.y -= 1
                 self.vy = 0
                 self.state = 'finished' # Done sliding
                 self.vx = 100 # Walk off
            return

        # --- STATE: FINISHED (Walking away) ---
        if self.state == 'finished':
            self.vx = 100
            self.vy += 1500 * dt
            self.x += self.vx * dt
            self.y += self.vy * dt
            # Simple floor collision
            # (Reuse sliding check logic or duplicate limited check)
            # For brevity, assuming flat ground after pole mostly
            return

        # --- INPUTS & BUFFERS ---
        if inputs['jump_pressed']:
            self.jump_buffer_timer = JUMP_BUFFER_TIME
            
        if self.jump_buffer_timer > 0:
            self.jump_buffer_timer -= dt
            
            
        # Removed flicker timer - no longer needed
            
        if self.on_ground:
            self.coyote_timer = COYOTE_TIME
        else:
            self.coyote_timer -= dt
            
        # --- HORIZONTAL MOVEMENT ---
        target_vx = 0
        accel = ACCELERATION
        friction = FRICTION
        
        if inputs['left']:
            target_vx = -MOVE_SPEED
            self.facing_right = False
            # Skid check
            if self.vx > 0: friction = SKID_FRICTION
                
        elif inputs['right']:
            target_vx = MOVE_SPEED
            self.facing_right = True
            if self.vx < 0: friction = SKID_FRICTION
        
        # Run Check
        speed_cap = MOVE_SPEED
        if inputs.get('run_held', False):
             speed_cap = RUN_SPEED
             
        if target_vx > 0: target_vx = speed_cap
        elif target_vx < 0: target_vx = -speed_cap
            
        # Apply Acceleration/Friction
        if target_vx != 0:
            # Accelerate towards target
            if self.vx < target_vx:
                self.vx += accel * dt * 1.5 # SNAPPY
                if self.vx > target_vx: self.vx = target_vx
            elif self.vx > target_vx:
                self.vx -= accel * dt * 1.5
                if self.vx < target_vx: self.vx = target_vx
        else:
            # Friction (Stop)
            if self.vx > 0:
                self.vx -= friction * dt
                if self.vx < 0: self.vx = 0
            elif self.vx < 0:
                self.vx += friction * dt
                if self.vx > 0: self.vx = 0
        
        # Dead zone - snap very small velocities to zero
        if abs(self.vx) < 5:
            self.vx = 0
                
        # --- VERTICAL MOVEMENT & JUMP ---
        # Variable Jump Height (Button Release)
        if not inputs['jump_held'] and self.vy < 0:
            self.vy *= 0.5 # Cut velocity immediately
            
        # Jump Execution (Buffer + Coyote)
        if self.jump_buffer_timer > 0 and self.coyote_timer > 0:
            self.vy = JUMP_FORCE
            self.jump_buffer_timer = 0
            self.coyote_timer = 0
            self.on_ground = False
            print(f"JUMP! on_ground={self.on_ground}, vy={self.vy}")  # Debug
        
        # Simpler jump trigger - just press jump while on ground
        if inputs['jump_pressed'] and self.on_ground:
            self.vy = JUMP_FORCE
            self.on_ground = False
            print(f"DIRECT JUMP! vy={self.vy}")  # Debug
            
        # Gravity
        self.vy += GRAVITY * dt
        if self.vy > MAX_FALL_SPEED: self.vy = MAX_FALL_SPEED
        
        # --- PHYSICS STEP X ---
        self.x += self.vx * dt
        # Wall Collision X
        self.check_collision(collision_mask, mask_w, mask_h, True, procedural_platforms, sky_color)
        
        # --- PHYSICS STEP Y ---
        self.y += self.vy * dt
        # Floor/Ceiling Collision Y
        self.check_collision(collision_mask, mask_w, mask_h, False, procedural_platforms, sky_color)
        
        # Screen bounds (safety)
        self.x = max(0, min(self.x, mask_w - self.width))
        if self.y > 850: # Fell off world - respawn quickly
            print("Fell off world! Respawning...")
            self.respawn()

        # --- ANIMATION UPDATE ---
        # Use a lower threshold so Mario stands still more easily
        if abs(self.vx) > 10:  # Reduced from 20 to 10
            self.anim_timer += dt * (abs(self.vx) / 100.0) * 6.0  # Slowed from 12.0 to 6.0
            idx = int(self.anim_timer) % 3 + 1
            s_name = f"walk_{idx}"
        else:
            # Standing still - use stand sprite
            s_name = "stand"
            self.anim_timer = 0
            
        # Override with jump sprite if in air
        if not self.on_ground:
            s_name = "walk_3"  # Jump pose
            
        # Cache flipped sprite with EXACT height (64px)
        # Use BIG MARIO sprites that user selected (around Y=80 in spritesheet)
        sprite = None
        
        try:
            # Load the main spritesheet
            sheet_path = os.path.join('assets', 'marioallsprite.png')
            if os.path.exists(sheet_path):
                sheet = pygame.image.load(sheet_path).convert_alpha()
                
                # Big Mario sprite coordinates (user selected these)
                big_mario_sprites = {
                    'stand': (8, 82, 32, 32),      # Standing
                    'walk_1': (49, 80, 32, 32),    # Walk frame 1
                    'walk_2': (86, 79, 32, 32),    # Walk frame 2
                    'walk_3': (128, 82, 32, 32),   # Walk frame 3
                    'jump': (166, 81, 32, 32),     # Jump
                    'skid': (208, 81, 32, 32),     # Skid
                    'crouch': (248, 82, 32, 32),   # Crouch
                    'climb': (289, 78, 32, 32),    # Climb
                }
                
                if s_name in big_mario_sprites:
                    x, y, w, h = big_mario_sprites[s_name]
                    sprite = sheet.subsurface((x, y, w, h))
                    # Scale to 64px (2x)
                    sprite = pygame.transform.scale(sprite, (64, 64))
        except Exception as e:
            print(f"Error loading big Mario sprite: {e}")
        
        if sprite:
            if not self.facing_right:
                sprite = pygame.transform.flip(sprite, True, False)
            self.current_sprite = sprite
        else:
            # Debug: Sprite failed to load
            if not hasattr(self, '_sprite_warning_shown'):
                print(f"WARNING: Mario sprite '{s_name}' failed to load! Using fallback rectangle.")
                self._sprite_warning_shown = True
            self.current_sprite = None

    def check_collision(self, mask, w, h, is_x, procedural_platforms, sky_color):
        # PRODUCTION READY AABB COLLISION
        # Resolves directly against rects instead of iterating pixels
        
        player_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        
        # 1. Check against Procedural Rects (Primary)
        hits = []
        for plat in procedural_platforms:
             if player_rect.colliderect(plat):
                 hits.append(plat)
                 
        # 2. Resolve
        if hits:
             # Find the most relevant hit (usually closest or just first)
             # For simple AABB with axis separation, we can resolve against the first valid overlap
             # To be robust, we might loop, but usually one resolution is enough per axis step
             
             hit = hits[0] # Pick first collision
             
             if is_x:
                 if self.vx > 0: # Moving Right, hit Left side of wall
                     self.x = hit.left - self.width
                     self.vx = 0
                 elif self.vx < 0: # Moving Left, hit Right side of wall
                     self.x = hit.right
                     self.vx = 0
             else:
                 if self.vy > 0: # Falling, hit Floor
                     self.y = hit.top - self.height
                     self.vy = 0
                     self.on_ground = True
                 elif self.vy < 0: # Jumping, hit Ceiling
                     self.y = hit.bottom
                     self.vy = 0
        else:
             if not is_x and self.vy > 0:
                 self.on_ground = False
                 
        # 3. Legacy / Fallback Bounds Check (World Edges)
        if self.x < 0: self.x = 0
        if self.x > w - self.width: self.x = w - self.width
        # Note: Y bounds handled in update loop (respawn)
        
    def _legacy_check(self):
        # Kept for reference but unused in new AABB model
        pass

    def respawn(self):
        self.x = 150
        self.y = 550  # Spawn on the safe starting platform
        self.vx = 0
        self.vy = 0
        self.state = 'normal'
        # Removed flicker_timer - no more flashing

    def draw(self, surface):
        # Removed flicker effect - it was distracting
        
        if self.current_sprite:
            # Floor coordinates to avoid jitter
            draw_x = int(round(self.x))
            draw_y = int(round(self.y))
            
            # Draw Mario directly without outline
            # (Removed outline - it was causing double image)
            surface.blit(self.current_sprite, (draw_x, draw_y))
        else:
            # BRIGHT FALLBACK - Make Mario VERY visible even without sprite
            draw_x = int(self.x)
            draw_y = int(self.y)
            
            # Bright magenta rectangle with yellow outline
            pygame.draw.rect(surface, (255, 0, 255), (draw_x, draw_y, self.width, self.height))  # Magenta fill
            pygame.draw.rect(surface, (255, 255, 0), (draw_x-2, draw_y-2, self.width+4, self.height+4), 3)  # Yellow outline
            
            # Draw a simple face so you know which way he's facing
            eye_y = draw_y + 10
            if self.facing_right:
                pygame.draw.circle(surface, (255, 255, 255), (draw_x + 20, eye_y), 3)  # Eye
            else:
                pygame.draw.circle(surface, (255, 255, 255), (draw_x + 12, eye_y), 3)  # Eye



class Flagpole:
    def __init__(self, x, y, asset_loader=None):
        self.x = x
        self.y = y # Bottom position
        self.height = 300 # Tall pole
        self.rect = pygame.Rect(x, y - 300, 10, 300)
        self.active = True
        self.asset_loader = asset_loader
        
    def draw(self, surface, offset=(0,0)):
        ox, oy = offset
        # Pole
        pygame.draw.rect(surface, (200, 200, 200), (int(self.x+4 + ox), int(self.y - 300 + oy), 4, 300))
        # Top Ball
        pygame.draw.circle(surface, (255, 215, 0), (int(self.x+6 + ox), int(self.y - 300 + oy)), 8)
        # Base
        pygame.draw.rect(surface, (100, 100, 100), (int(self.x + ox), int(self.y-20 + oy), 16, 20))


class SimpleEnemy:
    def __init__(self, x, y, type_name, sprite_manager):
        self.x = x
        self.y = y
        self.type_name = type_name # 'goomba', 'koopa'
        self.vx = -100 # Walk left default
        self.vy = 0
        self.width = 16
        self.height = 16
        self.sprite_manager = sprite_manager
        self.active = True
        # Simplified - turtles just walk, no shells
        
    def info(self): return f"{self.type_name}"
        
    def update(self, dt, mask, mask_w, mask_h, sky_color=(0,0,0), platforms=[]):
        # Apply Gravity
        self.vy += 1500 * dt # Gravity constant
        if self.vy > 600: self.vy = 600
        
        # Simple walking - no shell mechanics
        # X Move
        self.x += self.vx * dt
        
        enemy_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        
        # 1. Platform Collision (Robust)
        hit_platform = False
        if platforms:
            hits = [p for p in platforms if enemy_rect.colliderect(p)]
            if hits:
                 hit = hits[0] # Pick first
                 overlap_y = min(enemy_rect.bottom, hit.bottom) - max(enemy_rect.top, hit.top)
                 overlap_x = min(enemy_rect.right, hit.right) - max(enemy_rect.left, hit.left)
                 
                 if overlap_x > overlap_y: # Vertical collision (Floor/Ceiling)
                     if self.vy > 0 and enemy_rect.centery < hit.centery: # Falling onto floor
                         self.y = hit.top - self.height
                         self.vy = 0
                         hit_platform = True
                 else: # Horizontal collision (Wall)
                     if overlap_y > 5: # Only if significant vertical overlap
                         self.vx *= -1 # Turn around
                         # Push out
                         if self.vx > 0: self.x = hit.right
                         else: self.x = hit.left - self.width
        
        # 2. World Bounds / Fallback Mask (Legacy)
        if not hit_platform:
             # Basic bounds
             if self.x < 0 or self.x > mask_w - self.width:
                 self.vx *= -1
                 self.x = max(0, min(self.x, mask_w - self.width))
             
             # Floor fallback
             if self.y > mask_h - 20: 
                 self.y = mask_h - 20 - self.height
                 self.vy = 0
        
        # Y Move (if not grounded)
        if not hit_platform:
             self.y += self.vy * dt

    def draw(self, surface):
        if not self.active: return
        
        # Sprite Selection
        s_name = 'walk_1'
        if self.state == 'shell' or self.state == 'kicked':
             s_name = 'shell_1'
        
        # FIX: Map Goomba to Red Koopa if Goomba missing
        cat = 'goomba' 
        if self.type_name == 'goomba': cat = 'koopa_red'
        elif self.type_name == 'koopa': cat = 'koopa_green'
        
        from src.config import BLOCK_SIZE
        sprite = self.sprite_manager.get_sprite(cat, s_name, 48.0 / BLOCK_SIZE)  # Increased from 18px to 48px
        
        if sprite:
             surface.blit(sprite, (int(self.x), int(self.y)))
        else:
             # Fallback
             col = (255, 0, 0) if self.type_name == 'goomba' else (0, 255, 0)
             pygame.draw.rect(surface, col, (self.x, self.y, self.width, self.height))


class Scene_DarkWorld:
    def __init__(self, asset_loader):
        self.asset_loader = asset_loader
        self.sprite_manager = asset_loader # Alias support
        self.active = False
        
        # DEFINITIVE INITIALIZATION (Must exist before any possible failure)
        self.coins = []
        self.enemies = []
        self.platforms = [] 
        self.visual_blocks = []
        self.flagpole = None
        self.sky_color = (0, 0, 0)
        self.bg_image = None
        self.collision_mask = None
        self.collision_mask_image = None
        self.intro_timer = 0.5  # Short intro (was 2.5)
        self.intro_duration = 0.5
        self.zoom_level = 1.0
        self.zoom_target = 3.0
        self.camera_x = 0
        self.camera_y = 0
        self.view_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.vignette = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        self.vignette.fill((0,0,0,15))  # Very light vignette (was 40)

        try:
            # Asset Loading
            base = 'assets'
            clean_path = os.path.join(base, 'dark_world_clean.png')
            ref_path = os.path.join(base, 'level_reference.png')
            
            # Load the actual Dark World background
            if os.path.exists(clean_path):
                self.bg_image = pygame.image.load(clean_path).convert()
                print(f"Loaded Dark World background: {clean_path}")
            elif os.path.exists(ref_path):
                self.bg_image = pygame.image.load(ref_path).convert()
                print(f"Loaded reference map as background: {ref_path}")
            else:
                # Fallback: Create gradient if no assets found
                w, h = 2000, 800
                self.bg_image = pygame.Surface((w, h))
                for y in range(h):
                    darkness = int(10 + (y / h) * 20)
                    color = (darkness // 2, darkness // 2, darkness)
                    pygame.draw.line(self.bg_image, color, (0, y), (w, y))
                print("Created fallback gradient background")
            
            # Load collision mask from reference if available
            self.collision_mask_image = self.bg_image  # Fallback
            if os.path.exists(ref_path):
                 try:
                    self.collision_mask_image = pygame.image.load(ref_path).convert()
                    print("Loaded Reference Map for Physics Scanning.")
                 except: 
                    pass

            self.collision_mask = self.collision_mask_image # Logic alias
            
            # SAMPLE SKY COLOR from Visual BG
            if self.bg_image:
                self.sky_color = self.bg_image.get_at((0, 0))[:3]
                print(f"Dynamic Sky Color Detected: {self.sky_color}")
            else:
                self.sky_color = (0, 0, 0)
                
            self.visual_blocks = []
            self.flagpole = None
            
            # Start with Simple Linear Level (Clear Path)
            self.generate_simple_linear_level()
            
            # Map parsing? Only if needed for extra entities
            if os.path.exists(ref_path):
                 pass # self.parse_level(ref_path) # Disable unreliable parsing for now
                 
        except Exception as e:
             print(f"DarkWorld Init Error: {e}")
 
        # Player (Spawn on safe starting platform)
        # Ensure Mario starts on the starting platform we created
        self.player = PlatformerPlayer(150, 550, asset_loader)  # Spawn on the start platform at y=600
        print(f"Player spawned at: ({self.player.x}, {self.player.y})")
        
        # Camera & Zoom
        self.zoom_target = 1.8 # Reduced from 3.0 to see more of the world ahead
        
        # Calculate Start Zoom (Fit World Width)
        world_w = self.bg_image.get_width() if self.bg_image else WINDOW_WIDTH
        self.start_zoom = WINDOW_WIDTH / world_w
        if self.start_zoom > 1.0: self.start_zoom = 1.0 # Don't zoom in if world is small
        
        self.zoom_level = self.start_zoom
        
        # Camera starts centered on world
        world_h = self.bg_image.get_height() if self.bg_image else WINDOW_HEIGHT
        self.camera_x = (world_w - WINDOW_WIDTH/self.zoom_level) / 2
        self.camera_y = (world_h - WINDOW_HEIGHT/self.zoom_level) / 2
        
        self.collision_mask = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT)) # Placeholder until loaded
        self.create_vignette()

    def create_vignette(self):
        # Radial gradient black -> transparent center
        # Center is (WINDOW_WIDTH//2, WINDOW_HEIGHT//2)
        # We draw a big radial gradient
        # Actually simplest is to fill black and cut a hole? 
        # Or draw circles of increasing alpha.
        cx, cy = WINDOW_WIDTH//2, WINDOW_HEIGHT//2
        max_dist = math.sqrt(cx**2 + cy**2)
        
        for r in range(int(max_dist), 100, -2):
            alpha = int(255 * ((r - 100) / (max_dist - 100)))
            alpha = max(0, min(255, alpha))
            # pygame.draw.circle(self.vignette, (0, 0, 0, 1), (cx, cy), r)
            # This is slow to generate, good thing we do it once.
            # Actually this loop is bad for alpha blending in Software.
            # Better approach: Load a 'vignette.png' or just draw a few big rects with holes.
            # Fallback: Just semi-transparent darkness.
        
        self.vignette.fill((0,0,0,40)) # Much lighter (approx 15% opacity)
        # Draw transparent circle in middle (Mode Subtract? or RGBA(0,0,0,0)?)
        # Pygame surfaces don't handle "cutting holes" easily without flags.
        # We'll punt on complex vignette generation for this specific tool call to save tokens/time
        # and just make a dark overlay.

    def parse_level(self, path):
        print(f"Parsing {path}...")
        img = pygame.image.load(path)
        w, h = img.get_size()
        ref_img = pygame.image.load(path)
        w, h = ref_img.get_size()
        # Scale logic? Assuming reference matches BG size
        # We'll just scan simply like before
        ref_img.lock()
        for y in range(0, h, 10):
            for x in range(0, w, 10):
                # Global coordinates for spawned entities
                gx = x * (WINDOW_WIDTH/w)
                gy = y * (WINDOW_HEIGHT/h)

                # Color matching with Tolerance
                c = ref_img.get_at((x, y))
                
                # Check Coin (255, 215, 0)
                d_coin = abs(c.r - 255) + abs(c.g - 215) + abs(c.b - 0)
                if d_coin < 60:
                     self.coins.append({'x': gx, 'y': gy, 'active': True})
                     self.ensure_platform_under(gx, gy)
                     
                # Check Goomba (255, 0, 0)
                d_goomba = abs(c.r - 255) + abs(c.g - 0) + abs(c.b - 0)
                if d_goomba < 60:
                     self.enemies.append(SimpleEnemy(gx, gy, 'goomba', self.asset_loader))
                     self.ensure_platform_under(gx, gy)
                     
                # Check Koopa (0, 255, 0)
                d_koopa = abs(c.r - 0) + abs(c.g - 255) + abs(c.b - 0)
                if d_koopa < 60:
                     self.enemies.append(SimpleEnemy(gx, gy, 'koopa', self.asset_loader))
                     self.ensure_platform_under(gx, gy)

                # Check Flagpole (128, 0, 128)
                d_flag = abs(c.r - 128) + abs(c.g - 0) + abs(c.b - 128)
                if d_flag < 60:
                    self.flagpole = Flagpole(gx, gy)
                    self.ensure_platform_under(gx, gy)

        ref_img.unlock()
        print(f"Parsed {len(self.coins)} coins, {len(self.enemies)} enemies. Flagpole: {self.flagpole is not None}")
        
    def ensure_platform_under(self, x, y):
        # Raycast down to find ground
        ground_found = False
        check_rect = pygame.Rect(x, y, 16, 100)
        
        # Check Scanned Platforms
        for p in self.platforms:
            if p.colliderect(check_rect):
                ground_found = True
                break
        
        # If no ground within 100px, create one
        if not ground_found:
             # Create a small floating block or extend nearby?
             # Let's create a standard block
             print(f"Generating Support Platform at {x}, {y+40}")
             self.platforms.append(pygame.Rect(x - 20, y + 40, 60, 20))
        
        # Fallback Flagpole
        if not self.flagpole:
             self.flagpole = Flagpole(WINDOW_WIDTH - 100, WINDOW_HEIGHT - 60)
             
    def generate_simple_linear_level(self):
        """Create a simple, clear linear path that's easy to follow"""
        print("Creating simple linear path...")
        
        # Clear existing
        self.platforms = []
        self.coins = []
        self.enemies = []
        
        # Get world dimensions
        w, h = 2000, 800
        if self.bg_image: 
            w, h = self.bg_image.get_size()
        
        import random
        
        # Define consistent platform heights (aligned to grid)
        platform_heights = [300, 400, 500, 600]  # Removed 200 - too high
        platform_height = 32  # Consistent platform thickness
        max_jump_height = 120  # Increased to match new jump power
        
        # 1. STARTING PLATFORM (wide and safe, aligned to grid)
        start_y = 600
        self.platforms.append(pygame.Rect(0, start_y, 400, platform_height))
        self.coins.append({'x': 200, 'y': start_y - 50, 'active': True, 'frame': 0})
        
        # 2. CREATE LINEAR PATH - evenly spaced, grid-aligned platforms
        current_x = 450  # Start after the starting platform
        current_y = start_y
        platform_spacing = 180  # Consistent spacing
        
        step_count = 0
        while current_x < w - 400:
            # Choose height from grid (MUST be within jump range)
            possible_heights = [y for y in platform_heights if abs(y - current_y) <= max_jump_height]
            if not possible_heights:
                # If no heights are reachable, stay at current height
                possible_heights = [current_y]
            
            new_y = random.choice(possible_heights)
            
            # If the height difference is still too large, add a stepping platform
            if abs(new_y - current_y) > max_jump_height:
                # Add intermediate platform
                mid_y = (current_y + new_y) // 2
                mid_x = current_x + platform_spacing // 2
                self.platforms.append(pygame.Rect(mid_x, mid_y, 160, platform_height))
                self.coins.append({'x': mid_x + 80, 'y': mid_y - 50, 'active': True, 'frame': 0})
            
            # Create platform with consistent size
            platform_width = 160  # Consistent width
            self.platforms.append(pygame.Rect(current_x, new_y, platform_width, platform_height))
            
            # Add coin centered on platform
            coin_x = current_x + platform_width // 2
            self.coins.append({'x': coin_x, 'y': new_y - 50, 'active': True, 'frame': 0})
            
            # Add enemies more frequently - mix of goombas and turtles
            if step_count % 3 == 0 and len(self.enemies) < 6:
                enemy_x = current_x + platform_width // 2
                # Alternate between goomba and koopa (turtle)
                enemy_type = 'koopa' if step_count % 2 == 0 else 'goomba'
                self.enemies.append(SimpleEnemy(enemy_x, new_y - 30, enemy_type, self.asset_loader))
            
            current_x += platform_spacing
            current_y = new_y
            step_count += 1
        
        # 3. FINAL PLATFORM before flagpole (wide and safe, aligned)
        final_y = 600
        final_platform_x = w - 350
        
        # Add stepping platform if final platform is too high
        if abs(final_y - current_y) > max_jump_height:
            mid_y = (current_y + final_y) // 2
            mid_x = current_x + platform_spacing // 2
            self.platforms.append(pygame.Rect(mid_x, mid_y, 160, platform_height))
            self.coins.append({'x': mid_x + 80, 'y': mid_y - 50, 'active': True, 'frame': 0})
        
        self.platforms.append(pygame.Rect(final_platform_x, final_y, 300, platform_height))
        
        # 4. FLAGPOLE at the end (aligned to platform)
        end_x = w - 100
        flagpole_y = final_y - 180
        self.flagpole = Flagpole(end_x, flagpole_y, self.asset_loader)
        self.coins.append({'x': end_x - 80, 'y': final_y - 50, 'active': True, 'frame': 0})
        
        # Add a turtle near the end as a final challenge
        self.enemies.append(SimpleEnemy(end_x - 200, final_y - 30, 'koopa', self.asset_loader))
        
        # 5. NO GROUND FLOOR - if you fall, you respawn
        # (Removed the bottom safety floor - it was a trap!)
        
        print(f"Created {len(self.platforms)} platforms, {len(self.coins)} coins, {len(self.enemies)} enemies")
        print(f"Platform positions: {[(p.x, p.y, p.width, p.height) for p in self.platforms[:5]]}")  # Show first 5
              
    def generate_procedural_content(self):
        print("Scanning FULL background for layout...")
        # Smart Scan: Turn the BG image visuals into Physical Platforms
        
        scan_sources = []
        if getattr(self, 'collision_mask_image', None):
             scan_sources.append(self.collision_mask_image)
        if self.bg_image and self.bg_image not in scan_sources:
             scan_sources.append(self.bg_image)
             
        detected_rects = []
        
        for i, target_img in enumerate(scan_sources):
             if not target_img: continue
             print(f"Scanning source {i+1}...")
             
             try:
                 target_img.lock()
                 w, h = target_img.get_size()
                 step_y = 10 
                 step_x = 10
                 found_in_pass = []
                 
                 for y in range(0, h, step_y):
                    run_start = -1
                    for x in range(0, w, step_x):
                        c = target_img.get_at((x, y))
                        
                        is_solid_px = False
                        val = c.r + c.g + c.b
                        
                        if target_img != self.bg_image:
                             # Ref Map: Check Alpha > 10 and any Val > 20
                             if c.a > 10 and val > 20: is_solid_px = True
                        else:
                             # Visual BG: Compare to sky
                             dsky = abs(c.r - self.sky_color[0]) + abs(c.g - self.sky_color[1]) + abs(c.b - self.sky_color[2])
                             if dsky > 40 and val > 40 and c.a > 200: is_solid_px = True
                        
                        if is_solid_px:
                            if run_start == -1: run_start = x
                        else:
                            if run_start != -1:
                                rw = x - run_start
                                if rw >= 20: found_in_pass.append(pygame.Rect(run_start, y, rw, 24))
                                run_start = -1
                    
                    if run_start != -1:
                         rw = w - run_start
                         if rw >= 20: found_in_pass.append(pygame.Rect(run_start, y, rw, 24))

                 target_img.unlock()
                 
                 if found_in_pass:
                      detected_rects = found_in_pass
                      print(f"Success: Found {len(detected_rects)} segments in source {i+1}.")
                      break 
                 else:
                      print(f"Source {i+1} yielded 0 segments.")
                      
             except Exception as e:
                 print(f"Scan Error on source {i+1}: {e}")

        # MERGE RECTS (Optimization)
        detected_rects.sort(key=lambda r: (r.y, r.x))
        merged_platforms = []
        if detected_rects:
            current = detected_rects[0]
            for next_rect in detected_rects[1:]:
                # Same Y, Same Height, Close X
                if (next_rect.y == current.y and 
                    next_rect.height == current.height and
                    next_rect.x <= current.right + 25): 
                    current.width = next_rect.right - current.x
                else:
                    merged_platforms.append(current)
                    current = next_rect
            merged_platforms.append(current)
        
        self.platforms = merged_platforms
        
        # Dimensions
        w, h = 2000, 800
        if self.bg_image: w, h = self.bg_image.get_size()
        
        # Entity Spawning (Coins/Enemies)
        import random
        for p in self.platforms:
            if p.width > 200: # Only on large platforms
                 if random.random() < 0.2:
                      self.enemies.append(SimpleEnemy(p.left + p.width//2, p.top - 20, 'goomba', self.asset_loader))
            for px in range(p.x, p.right, 100):
                  if random.random() < 0.15:
                       self.coins.append({'x': px + 10, 'y': p.top - 50, 'active': True})
            
        # 0. GUIDED MAZE LOGIC: Ensure Start Platform (Safety for Entry)
        self.platforms.append(pygame.Rect(0, 600, 500, 40)) 
        
        # 1. WORLD BOTTOM FLOOR (Safety Baseline)
        bottom_y = h - 60
        self.platforms.append(pygame.Rect(0, bottom_y, w, 200))

        # 2. ENSURE ACHIEVABLE PATH (Gap Bridging)
        # We walk through the world in slices and ensure there's a platform within reach
        print("Validating path connectivity...")
        current_x = 0
        last_y = 600
        while current_x < w:
            # Look for a platform in the 200px ahead
            found = False
            for p in self.platforms:
                if p.left >= current_x and p.left <= current_x + 200:
                    # Check vertical reach (approx 120px up/down)
                    if abs(p.top - last_y) < 150:
                        found = True
                        current_x = p.right
                        last_y = p.top
                        break
            
            if not found:
                # Spawn a "Warp Brick" or bridge
                new_y = last_y + random.randint(-80, 80)
                new_y = max(100, min(new_y, bottom_y - 100))
                bridge = pygame.Rect(current_x + 50, new_y, 120, 32)
                self.platforms.append(bridge)
                # Mark it with a coin so user knows it's the path
                self.coins.append({'x': current_x + 100, 'y': new_y - 40, 'active': True})
                # Add extra guide coin
                self.coins.append({'x': current_x + 50, 'y': new_y - 20, 'active': True})
                current_x += 180
                last_y = new_y
            else:
                current_x += 100 # Increment stepped scan
        
        # 3. Ensure Flagpole at End
        end_x = w - 150
        if not self.flagpole:
             self.flagpole = Flagpole(end_x, bottom_y - 160, self.asset_loader)
             # Platform under flagpole
             self.platforms.append(pygame.Rect(end_x - 100, bottom_y, 300, 100))
             # Goal marker
             self.coins.append({'x': end_x, 'y': bottom_y - 200, 'active': True})
        
        # NUCLEAR FALLBACK check (outside try/catch logic now)
        if not self.platforms:
             print("CRITICAL: No platforms found. Adding Safety Floor.")
             self.platforms.append(pygame.Rect(0, 400, 1000, 50))
             self.platforms.append(pygame.Rect(0, 600, 1000, 50)) # Lower floor fallback 
        
    def generate_tile_level(self):
        # Legacy stub
        pass


    def update(self, dt, keys=None):
        # Default keys if none provided
        if keys is None:
             keys = pygame.key.get_pressed()

        inputs = {
            'left': keys[pygame.K_LEFT],
            'right': keys[pygame.K_RIGHT],
            'jump_pressed': keys[pygame.K_SPACE] or keys[pygame.K_z] or keys[pygame.K_UP],
            'jump_held': keys[pygame.K_SPACE] or keys[pygame.K_z] or keys[pygame.K_UP],
            'run_held': keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT] or keys[pygame.K_x],
            # Add other necessary keys if needed by player
            'up': keys[pygame.K_UP],
            'down': keys[pygame.K_DOWN],
            'respawn': keys[pygame.K_r]  # R key to respawn if stuck
        }
        
        # Debug: Respawn if stuck (R key)
        if inputs.get('respawn', False):
            self.player.respawn()
            print("Mario respawned!")
        
        # World Dimensions
        world_w = self.bg_image.get_width() if self.bg_image else WINDOW_WIDTH
        world_h = self.bg_image.get_height() if self.bg_image else WINDOW_HEIGHT
        
        # --- INTRO CINEMATIC LOGIC ---
        
        # --- INTRO CINEMATIC LOGIC ---
        if hasattr(self, 'intro_timer') and self.intro_timer > 0:
            self.intro_timer -= dt
            # Progress 0.0 (Start) -> 1.0 (End)
            progress = 1.0 - (max(0, self.intro_timer) / self.intro_duration)
            # Ease Out Cubic
            t = 1 - pow(1 - progress, 3)
            
            # Interpolate Zoom
            current_target = getattr(self, 'zoom_target', 2.0)
            start_z = getattr(self, 'start_zoom', 1.0)
            self.zoom_level = start_z + (current_target - start_z) * t
            
            # Skip intro if player presses any key
            if inputs['left'] or inputs['right'] or inputs['jump_pressed']:
                self.intro_timer = 0  # Skip to end
            
            # Disable Player Input during intro
            # Preserve keys but set to False
            for k in inputs:
                if k != 'msg': inputs[k] = False

        # --- STANDARD CAMERA & PHYSICS ---
        
        # Resize View Surface if Zoom Changed
        vw = int(WINDOW_WIDTH / self.zoom_level)
        vh = int(WINDOW_HEIGHT / self.zoom_level)
        if self.view_surface.get_width() != vw or self.view_surface.get_height() != vh:
             self.view_surface = pygame.Surface((vw, vh))
        
        # Target: Center on Player
        target_cam_x = self.player.x + self.player.width/2 - vw/2
        target_cam_y = self.player.y + self.player.height/2 - vh/2
        
        # Clamp Camera
        max_x = max(0, world_w - vw)
        max_y = max(0, world_h - vh)
        target_cam_x = max(0, min(target_cam_x, max_x))
        target_cam_y = max(0, min(target_cam_y, max_y)) 
        
        # Smooth Pan
        speed = 5
        if hasattr(self, 'intro_timer') and self.intro_timer > 0: speed = 3 # Cinematic speed
        
        self.camera_x += (target_cam_x - self.camera_x) * speed * dt
        self.camera_y += (target_cam_y - self.camera_y) * speed * dt
        
        # Update Player Physics
        mask_h = world_h # Alias
        platforms = getattr(self, 'platforms', [])
        self.player.update(dt, inputs, self.collision_mask, world_w, world_h, platforms, self.sky_color)
        
        # Flagpole Check
        if self.flagpole and self.player.state == 'normal':
             # Check collision with pole (trigger area)
             # Use World Space
             p_rect = pygame.Rect(self.player.x, self.player.y, self.player.width, self.player.height)
             if p_rect.colliderect(self.flagpole.rect):
                 # TRIGGER SLIDE
                 self.player.state = 'sliding'
                 self.player.x = self.flagpole.x - 4 # Align with pole
                 self.asset_loader.play_sound('world_clear')
        
        # Coin Collection
        if not hasattr(self, 'coin_animations'):
            self.coin_animations = []  # List of {x, y, frame, timer}
        
        player_rect = pygame.Rect(self.player.x, self.player.y, self.player.width, self.player.height)
        for c in self.coins:
            if c['active']:
                coin_rect = pygame.Rect(c['x'], c['y'], 16, 16)
                if player_rect.colliderect(coin_rect):
                    c['active'] = False
                    # Start collection animation at coin position
                    self.coin_animations.append({
                        'x': c['x'],
                        'y': c['y'],
                        'frame': 0,
                        'timer': 0
                    })
                    print(f"Coin collected! Starting animation at ({c['x']}, {c['y']})")  # Debug
                    # Play sound
                    try:
                        self.asset_loader.play_sound('coin')
                    except:
                        pass
        
        # Update coin collection animations
        for anim in self.coin_animations[:]:
            anim['timer'] += dt
            if anim['timer'] >= 0.1:  # 10 fps animation (was 0.05/20fps)
                anim['timer'] = 0
                anim['frame'] += 1
                if anim['frame'] >= 9:  # 9 frames total
                    print(f"Collection animation complete")  # Debug
                    self.coin_animations.remove(anim)
        
        # Enemies
        for e in self.enemies:
            if not e.active: continue
            e.update(dt, self.collision_mask, world_w, mask_h, self.sky_color, self.platforms)
            
            # Collision
            e_rect = pygame.Rect(e.x, e.y, e.width, e.height)
            
            # Platform Collision for Enemies (Simple)
            # We already passed sky_color/mask to e.update, but enemies use simple gravity.
            # We should probably share the platform list with enemies too?
            # For now, let's rely on mask (which might be weak).
            # IMPROVEMENT: Add platforms to enemy update later if they fall through.
            
            if player_rect.colliderect(e_rect):
                 self.handle_player_enemy_collision(e)
        
        # --- FLAGPOLE COLLISION (Victory!) ---
        if self.flagpole and not getattr(self, 'victory_triggered', False):
            # Much larger hitbox for easier collision
            flagpole_rect = pygame.Rect(self.flagpole.x - 40, self.flagpole.y, 80, 180)
            player_rect = pygame.Rect(self.player.x, self.player.y, self.player.width, self.player.height)
            
            if player_rect.colliderect(flagpole_rect):
                print("FLAGPOLE TOUCHED! Victory!")
                self.victory_triggered = True
                self.victory_timer = 0
                self.player.vx = 0  # Stop horizontal movement
                # Position Mario at the flagpole
                self.player.x = self.flagpole.x + 10
                self.asset_loader.play_sound('world_clear')
        
        # --- VICTORY SEQUENCE (Slide down flagpole) ---
        if getattr(self, 'victory_triggered', False):
            self.victory_timer = getattr(self, 'victory_timer', 0) + dt
            
            # Slide Mario down the flagpole
            if self.victory_timer < 2.0:  # 2 second slide
                slide_speed = 100
                self.player.y += slide_speed * dt
                self.player.vy = 0
                # Keep Mario at the flagpole x position
                self.player.x = self.flagpole.x + 10
            
            # After 2 seconds, return victory
            if self.victory_timer >= 2.5:
                return 'WORLD_CLEAR'
        
    def handle_player_enemy_collision(self, e):
        player_rect = pygame.Rect(self.player.x, self.player.y, self.player.width, self.player.height)
        e_rect = pygame.Rect(e.x, e.y, e.width, e.height)

        # STOMP CHECK
        # Player must be falling and above enemy center
        if self.player.vy > 0 and self.player.y + self.player.height < e.y + e.height*0.8:
             # BOUNCE
             self.player.vy = -300
             self.asset_loader.play_sound('stomp')
             
             if e.type_name == 'goomba':
                 e.active = False # Squish
                 # self.enemies.remove(e) # Dangerous in loop?
             elif e.type_name == 'koopa':
                 if e.state == 'walk':
                     e.state = 'shell'
                     e.vx = 0
                     # Shift Y to avoid sticking
                 elif e.state == 'shell' or e.state == 'kicked':
                     e.state = 'kicked'
                     e.vx = 0 # Stomp stops it
                     e.state = 'shell'
        
        # KICK / HURT CHECK
        else: 
             # Side collision
             if e.state == 'shell':
                 # KICK IT
                 e.state = 'kicked'
                 if self.player.x < e.x: e.vx = 400
                 else: e.vx = -400
                 self.asset_loader.play_sound('kick')
                 # Push player slightly to avoid double hit
                 if self.player.x < e.x: self.player.x -= 5
                 else: self.player.x += 5
             elif e.state == 'kicked':
                 # Hurt if running into it? Or safe?
                 # Let's say hurt if it's moving fast against you
                 self.player.respawn() # Ouch
                 self.asset_loader.play_sound('damage')
             else:
                 # Walk into enemy
                 self.player.respawn()
                 self.asset_loader.play_sound('damage')
        


    def draw(self, surface):
        # Render everything to VIEW SURFACE first (Zoomed Crop)
        canvas = self.view_surface
        
        # Clear (though BG covers it)
        canvas.fill((20, 0, 20))
        
        # Apply Camera Offset
        cam_x = int(self.camera_x)
        cam_y = int(self.camera_y)
        
        # 1. Background
        if self.bg_image:
             canvas.blit(self.bg_image, (-cam_x, -cam_y))
        
        # Add visual landmarks in the background for orientation
        # Draw distant pillars/mountains at regular intervals
        world_w = self.bg_image.get_width() if self.bg_image else 2000
        landmark_spacing = 400  # Every 400 pixels
        for landmark_x in range(0, world_w, landmark_spacing):
            # Only draw if visible
            screen_x = landmark_x - cam_x
            if -100 < screen_x < canvas.get_width() + 100:
                # Draw a distant pillar/mountain
                pillar_height = 150
                pillar_width = 60
                pillar_y = canvas.get_height() - 200
                
                # Dark silhouette
                pillar_color = (20, 20, 40, 100)
                pillar_surf = pygame.Surface((pillar_width, pillar_height), pygame.SRCALPHA)
                pillar_surf.fill(pillar_color)
                canvas.blit(pillar_surf, (screen_x - pillar_width//2, pillar_y))
                
                # Top glow (like a distant light)
                glow_surf = pygame.Surface((40, 40), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (100, 100, 150, 60), (20, 20), 20)
                canvas.blit(glow_surf, (screen_x - 20, pillar_y - 20), special_flags=pygame.BLEND_RGBA_ADD)

        # Draw Platforms (ENABLED for visibility)
        if hasattr(self, 'platforms'):
            for plat in self.platforms:
                 # Check Visibility
                 if plat.x - cam_x < canvas.get_width() and plat.right - cam_x > 0:
                     dr = pygame.Rect(plat.x - cam_x, plat.y - cam_y, plat.width, plat.height)
                     
                     # Draw platform with better visual style
                     # 1. Dark fill
                     platform_surf = pygame.Surface((plat.width, plat.height), pygame.SRCALPHA)
                     platform_surf.fill((30, 30, 50, 180))  # Darker blue-gray
                     canvas.blit(platform_surf, (plat.x - cam_x, plat.y - cam_y))
                     
                     # 2. Top highlight (makes it look 3D)
                     highlight_rect = pygame.Rect(plat.x - cam_x, plat.y - cam_y, plat.width, 4)
                     pygame.draw.rect(canvas, (60, 60, 80), highlight_rect)
                     
                     # 3. Bright cyan outline (VERY thick for visibility)
                     pygame.draw.rect(canvas, (0, 255, 255), dr, 5)  # 5px thick outline!

        # 2. Coins (using animated sprites from items-coins.png)
        # Load the 3 coin animation frames the user selected
        coin_sprites = []
        collection_sprites = []  # 9 frames for collection animation
        try:
            coin_path = os.path.join('assets', 'items-coins.png')
            if os.path.exists(coin_path):
                coin_sheet = pygame.image.load(coin_path).convert_alpha()
                # User selected 3 coin frames for idle animation
                coin_coords = [
                    (118, 27, 12, 16),  # Frame 1
                    (130, 30, 12, 16),  # Frame 2
                    (142, 30, 12, 16),  # Frame 3
                ]
                for x, y, w, h in coin_coords:
                    sprite = coin_sheet.subsurface((x, y, w, h))
                    sprite = pygame.transform.scale(sprite, (24, 32))  # Scale up
                    coin_sprites.append(sprite)
                
                # User selected 9 frames for collection animation
                collection_coords = [
                    (6, 72, 16, 16),    # Frame 1
                    (23, 71, 16, 16),   # Frame 2
                    (46, 73, 16, 16),   # Frame 3
                    (66, 73, 16, 16),   # Frame 4
                    (90, 75, 16, 16),   # Frame 5
                    (106, 73, 16, 16),  # Frame 6
                    (129, 71, 16, 16),  # Frame 7
                    (151, 71, 16, 16),  # Frame 8
                    (173, 71, 16, 16),  # Frame 9
                ]
                for x, y, w, h in collection_coords:
                    sprite = coin_sheet.subsurface((x, y, w, h))
                    sprite = pygame.transform.scale(sprite, (32, 32))  # Scale up
                    collection_sprites.append(sprite)
        except Exception as e:
            print(f"Error loading coin sprites: {e}")
        
        # Fallback if coins didn't load
        if not coin_sprites:
            coin_sprite = pygame.Surface((24, 24), pygame.SRCALPHA)
            pygame.draw.circle(coin_sprite, (255, 215, 0), (12, 12), 10)
            coin_sprites = [coin_sprite]
        
        coins_list = getattr(self, 'coins', [])
        for c in coins_list:
            if c['active']:
                pos = (c['x'] - cam_x, c['y'] - cam_y)
                # Cull
                if pos[0] < -20 or pos[0] > canvas.get_width(): continue
                if pos[1] < -20 or pos[1] > canvas.get_height(): continue
                
                # Animate through the 3 coin frames
                import time
                frame_index = int(time.time() * 6) % len(coin_sprites)  # 6 fps animation
                coin_sprite = coin_sprites[frame_index]
                
                if coin_sprite: 
                    canvas.blit(coin_sprite, pos)
        
        # 2b. Coin Collection Animations (9 frames when collected)
        if hasattr(self, 'coin_animations') and collection_sprites:
            for anim in self.coin_animations:
                if anim['frame'] < len(collection_sprites):
                    sprite = collection_sprites[anim['frame']]
                    pos = (anim['x'] - cam_x - 8, anim['y'] - cam_y - 8)  # Center it
                    # Add a bright flash for visibility
                    flash_surf = pygame.Surface((48, 48), pygame.SRCALPHA)
                    pygame.draw.circle(flash_surf, (255, 255, 200, 100), (24, 24), 24)
                    canvas.blit(flash_surf, (pos[0]-8, pos[1]-8), special_flags=pygame.BLEND_RGBA_ADD)
                    canvas.blit(sprite, pos)

        # 3. Enemies
        enemies_list = getattr(self, 'enemies', [])
        for e in enemies_list:
            if not e.active: continue
            
            # Simple Cull
            draw_x = e.x - cam_x
            draw_y = e.y - cam_y
            
            if draw_x + e.width < 0 or draw_x > canvas.get_width(): continue 
            if draw_y + e.height < 0 or draw_y > canvas.get_height(): continue
            
            # Draw with offset trick
            real_x, real_y = e.x, e.y
            e.x = draw_x
            e.y = draw_y
            e.draw(canvas)
            e.x, e.y = real_x, real_y # Restore
            
        # 4. Player
        real_px, real_py = self.player.x, self.player.y
        self.player.x -= cam_x
        self.player.y -= cam_y
        self.player.draw(canvas)
        self.player.x, self.player.y = real_px, real_py
        
        # 5. Flagpole
        if self.flagpole:
             self.flagpole.draw(canvas, offset=(-cam_x, -cam_y))
        
        # 6. Help Text (top-left corner)
        try:
            font = pygame.font.Font(None, 24)
            help_texts = [
                "CONTROLS: Arrow Keys = Move, Space/Z = Jump",
                "Press R to Respawn if Stuck"
            ]
            y_offset = 10
            for text in help_texts:
                text_surf = font.render(text, True, (255, 255, 255))
                # Add black outline for readability
                outline_surf = font.render(text, True, (0, 0, 0))
                for dx, dy in [(-1,-1), (-1,1), (1,-1), (1,1)]:
                    canvas.blit(outline_surf, (10+dx, y_offset+dy))
                canvas.blit(text_surf, (10, y_offset))
                y_offset += 25
            
            # 7. Progress Bar (shows how far through the level)
            world_w = self.bg_image.get_width() if self.bg_image else 2000
            progress = min(1.0, max(0.0, self.player.x / world_w))
            
            # Progress bar background
            bar_width = 200
            bar_height = 20
            bar_x = canvas.get_width() - bar_width - 20
            bar_y = 10
            
            pygame.draw.rect(canvas, (40, 40, 60), (bar_x, bar_y, bar_width, bar_height), border_radius=10)
            pygame.draw.rect(canvas, (0, 255, 255), (bar_x, bar_y, bar_width, bar_height), 2, border_radius=10)
            
            # Progress fill
            fill_width = int((bar_width - 4) * progress)
            if fill_width > 0:
                pygame.draw.rect(canvas, (0, 200, 200), (bar_x + 2, bar_y + 2, fill_width, bar_height - 4), border_radius=8)
            
            # Progress percentage text
            progress_text = font.render(f"{int(progress * 100)}%", True, (255, 255, 255))
            canvas.blit(progress_text, (bar_x + bar_width//2 - 15, bar_y + 2))
            
        except:
            pass  # If font fails, skip help text
             
        # Vignette (Scaled Logic?) - Draw vignette on canvas?
        # If we draw vignette on canvas, it scales up, blurring the gradient.
        # Maybe better to draw vignette on FINAL surface?
        # But 'Dark World' effect should probably respect zoom? 
        # Let's draw on canvas for consistent atmosphere feel.
        if self.vignette:
            # We need a smaller vignette or scale the big one down?
            # Or just blit the big one (-cam_x, -cam_y)? No, vignette is UI overlay usually.
            # If vignette is world-attached, it moves. If UI, it stays.
            # User said "Dark World needs to be mapped out".
            # Let's assume vignette is UI Overlay (Post Process).
            pass # We'll draw it on final surface

        # FINAL SCALE to Screen
        scaled_view = pygame.transform.scale(canvas, (WINDOW_WIDTH, WINDOW_HEIGHT))
        surface.blit(scaled_view, (0, 0))
        
        # Vignette on top of scaled view
        if self.vignette:
            surface.blit(self.vignette, (0,0)) # Disabled for performance for now
