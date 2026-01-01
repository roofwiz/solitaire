import pygame
import math
import os
import random
from src.config import WINDOW_WIDTH, WINDOW_HEIGHT, C_WHITE, C_BLACK, C_NEON_PINK

class IntroActor:
    def __init__(self, name, x, y, frames, scale=3.0, behavior='walk_to_center'):
        self.name = name
        self.x = x
        self.y = y
        self.original_y = y
        self.vx = 0
        self.vy = 0
        self.frames = frames
        self.current_frame = 0
        self.scale = scale
        self.behavior = behavior # 'walk_to_center', 'patrol', 'hover'
        self.state = 'walk' # 'walk', 'idle', 'jump', 'shell'
        self.timer = 0
        self.flip = False
        self.clicked_timer = 0
        self.target_x = x # Default target
        
        # Dimensions (Need these early for centering/anchoring)
        self.width, self.height = 32, 32
        if frames:
            for f in frames:
                if f:
                     self.width = f.get_width()
                     self.height = f.get_height()
                     break
                     
        # Physics
        self.gravity = 800
        # If behavior is not hover, treat the initial Y as the top, but we need to know the ground.
        # We'll set ground_y during update or via a setter if needed, but for now we'll assume Y is TOP.
        self.ground_y = y 
        
        # Dragging
        self.is_dragging = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0

    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)
        
    def update(self, dt, current_ground=None):
        if self.is_dragging:
            return
            
        self.timer += dt
        
        # Determine actual ground (could be the floor or a platform)
        target_ground = current_ground if current_ground is not None else self.ground_y
        
        # Global Gravity (for anyone not hovering)
        if self.behavior != 'hover':
            if self.y < target_ground or self.vy != 0:
                self.vy += self.gravity * dt
                self.y += self.vy * dt
                if self.y >= target_ground:
                    self.y = target_ground
                    self.vy = 0
                    if self.state == 'jump':
                        self.state = 'walk' if self.behavior == 'patrol' else 'idle'
            elif self.y > target_ground and abs(self.y - target_ground) < 10:
                self.y = target_ground # Snap to ground if slightly below

        # State Management
        if self.state == 'shell':
            self.clicked_timer -= dt
            # Spin/Slide effect
            self.x += self.vx * dt * 3.0 # Slide fast
            
            # Bounce off walls
            if self.x < 0: self.vx = abs(self.vx); self.x = 0
            if self.x > WINDOW_WIDTH - self.width: self.vx = -abs(self.vx); self.x = WINDOW_WIDTH - self.width
            
            if self.clicked_timer <= 0:
                self.state = 'walk'
                self.vx = 50 if self.flip else -50 # Reset speed
                
        elif self.behavior == 'walk_to_center':
            # Move towards target (only if on ground)
            if abs(self.y - target_ground) < 5:
                if abs(self.x - self.target_x) > 5:
                    direction = 1 if self.target_x > self.x else -1
                    self.vx = 100 * direction
                    self.x += self.vx * dt
                    if self.state != 'jump': self.state = 'walk'
                    self.flip = (direction < 0)
                else:
                    self.vx = 0
                    if self.state != 'jump': self.state = 'idle'
                    # Occasional look around
                    if random.random() < 0.01: self.flip = not self.flip
                
        elif self.behavior == 'patrol':
            if abs(self.y - target_ground) < 5:
                self.x += self.vx * dt
                if self.x < -100: self.vx = abs(self.vx); self.flip = True
                if self.x > WINDOW_WIDTH + 100: self.vx = -abs(self.vx); self.flip = False
                if self.state != 'jump' and self.state != 'shell': self.state = 'walk'
            
        elif self.behavior == 'hover':
            self.y = self.original_y + math.sin(self.timer * 2) * 20
            self.x += self.vx * dt
            if self.x < 50: self.vx = abs(self.vx); self.flip = True
            if self.x > WINDOW_WIDTH - 50: self.vx = -abs(self.vx); self.flip = False

        # Animation
        if self.frames and len(self.frames) > 0:
            rate = 0.15 if self.state == 'walk' else 0.5
            if self.state == 'shell': rate = 0.05
            
            frame_idx = int(self.timer / rate) % len(self.frames)
            self.current_frame = frame_idx

    def draw(self, surface):
        if not self.frames: 
            # Fallback: Draw colored rect if no frames
            pygame.draw.rect(surface, (255, 0, 0), (self.x, self.y, self.width, self.height))
            return
        
        # Safety check for index
        if self.current_frame >= len(self.frames): self.current_frame = 0
            
        img = self.frames[self.current_frame]
        if not img: return # Skip if frame is specifically None
        
        # Handle Flips
        if self.flip:
            img = pygame.transform.flip(img, True, False)
            
        surface.blit(img, (self.x, self.y))

    def on_click(self):
        if self.name in ['mario', 'luigi']:
            self.state = 'jump'
            self.vy = -400
            return 'jump'
        elif 'koopa' in self.name:
            self.state = 'shell'
            self.clicked_timer = 2.0 # Slide for 2 seconds
            self.vx = 200 * (1 if random.random() > 0.5 else -1)
            return 'kick'
        elif self.name == 'lakitu':
             self.vx *= -1
             return 'chirp'
        elif self.name == 'spiny':
             self.state = 'jump'
             self.vy = -300
             return 'jump'

class IntroScene:
    def __init__(self, sprite_manager):
        self.sprite_manager = sprite_manager
        self.timer = 0
        self.blink_timer = 0
        
        print("[IntroScene] Initializing...")
        
        # -- Helpers --
        # Tint Luigi Green (Better Palette Swap)
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
                        if r > 150 and g < 100 and b < 100:
                            arr[x, y] = (g, r, b, a)
            return s
            
        # -- Load Actors --
        self.actors = []
        # visual_ground_y is where the feet should touch
        self.visual_ground_y = WINDOW_HEIGHT - 120 
        
        # -- Platforms (Tetris Piece Style) --
        self.platforms = []
        # T-Piece Platform
        tx, ty = WINDOW_WIDTH // 3 - 50, self.visual_ground_y - 120
        bs = 32 # block size in intro
        self.platforms.extend([
            pygame.Rect(tx, ty, bs, bs),       # center
            pygame.Rect(tx-bs, ty, bs, bs),    # left
            pygame.Rect(tx+bs, ty, bs, bs),    # right
            pygame.Rect(tx, ty-bs, bs, bs)     # top
        ])
        # L-Piece Platform
        lx, ly = WINDOW_WIDTH // 3 * 2 - 50, self.visual_ground_y - 200
        self.platforms.extend([
            pygame.Rect(lx, ly, bs, bs),       # bottom corner
            pygame.Rect(lx, ly-bs, bs, bs),    # mid vertical
            pygame.Rect(lx, ly-2*bs, bs, bs),  # top vertical
            pygame.Rect(lx+bs, ly, bs, bs)     # handle
        ])
        
        def spawn_actor(name, x, frames, behavior='patrol', vx=0):
            # Calculate top Y so feet touch visual_ground_y
            temp_actor = IntroActor(name, x, 0, frames, behavior=behavior)
            top_y = self.visual_ground_y - temp_actor.height
            temp_actor.y = top_y
            temp_actor.original_y = top_y
            temp_actor.ground_y = top_y
            temp_actor.vx = vx
            # Fix Orientation: If moving Right (vx > 0), Flip (Face Right)
            if vx > 0: temp_actor.flip = True
            return temp_actor

        # 1. Mario
        m_frames = [sprite_manager.get_sprite('mario', 'walk', 3.0), sprite_manager.get_sprite('mario', 'stand', 3.0)]
        m_frames = [f for f in m_frames if f is not None] 
        mario = spawn_actor('mario', -50, m_frames, behavior='walk_to_center')
        mario.target_x = WINDOW_WIDTH // 2 - 60
        self.actors.append(mario)
        
        # 2. Luigi
        l_frames = [make_luigi(sprite_manager.get_sprite('luigi', 'walk', 3.0)), make_luigi(sprite_manager.get_sprite('luigi', 'stand', 3.0))]
        l_frames = [f for f in l_frames if f is not None] 
        luigi = spawn_actor('luigi', WINDOW_WIDTH + 50, l_frames, behavior='walk_to_center')
        luigi.target_x = WINDOW_WIDTH // 2 + 20
        self.actors.append(luigi)
        
        # 3. Lakitu
        lak_frames = [sprite_manager.get_sprite('lakitu', 'default', 3.0)]
        lakitu = IntroActor('lakitu', 100, 100, [f for f in lak_frames if f], behavior='hover')
        lakitu.vx = 50
        self.actors.append(lakitu)
        
        # 4. Koopa Green
        k_frames = sprite_manager.get_animation_frames('koopa_green', prefix='walk', scale=3.0)
        koopa = spawn_actor('koopa_green', -100, [f for f in k_frames if f], vx=60)
        self.actors.append(koopa)
        
        # 5. Spiny
        s_frames = sprite_manager.get_animation_frames('spiny', prefix='walk', scale=3.0)
        spiny = spawn_actor('spiny', WINDOW_WIDTH + 150, [f for f in s_frames if f], vx=-70)
        self.actors.append(spiny)

        # 6. Koopa Red
        kr_frames = sprite_manager.get_animation_frames('koopa_red', prefix='walk', scale=3.0)
        koopa_red = spawn_actor('koopa_red', -150, [f for f in kr_frames if f], vx=40)
        self.actors.append(koopa_red)
        
        # 7. Flying Koopa
        kf_frames = sprite_manager.get_animation_frames('koopa_green', prefix='fly', scale=3.0)
        if kf_frames: kf_frames = [f for f in kf_frames if f is not None]
        else: kf_frames = []
        if kf_frames:
             fly_koopa = IntroActor('koopa_green_fly', 50, 50, kf_frames, behavior='hover')
             fly_koopa.vx = -40
             fly_koopa.y = 150
             fly_koopa.original_y = 150
             self.actors.append(fly_koopa)

        self.bg_color = (92, 148, 252)

    def update(self, dt):
        self.timer += dt
        self.blink_timer += dt
        
        # dragging update
        mouse_pos = pygame.mouse.get_pos()
        for actor in self.actors:
            if actor.is_dragging:
                actor.x = mouse_pos[0] - actor.drag_offset_x
                actor.y = mouse_pos[1] - actor.drag_offset_y
        
        # Parallax
        self.cloud_scroll = (self.timer * 20) % WINDOW_WIDTH
        self.hill_far_scroll = (self.timer * 10) % WINDOW_WIDTH
        self.hill_near_scroll = (self.timer * 40) % WINDOW_WIDTH
        
        # Update Actors
        for actor in self.actors:
            # Platform Collision
            found_ground = actor.ground_y
            actor_rect = actor.get_rect()
            for p in self.platforms:
                # If actor is falling AND above platform AND within X range
                if actor.vy >= 0 and actor_rect.centerx >= p.left and actor_rect.centerx <= p.right:
                    if actor_rect.bottom <= p.top + 10 and actor_rect.bottom >= p.top - 10:
                        found_ground = p.top - actor.height
                        break
            
            actor.update(dt, current_ground=found_ground)

            
    def draw_cloud(self, surface, x, y):
        cloud_color = (255, 255, 255)
        scale = 1.0
        pygame.draw.circle(surface, cloud_color, (x, y), 30 * scale)
        pygame.draw.circle(surface, cloud_color, (x + 30, y), 35 * scale)
        pygame.draw.circle(surface, cloud_color, (x + 60, y), 30 * scale)

    def draw(self, surface, muted=False):
        # -- Background (Same as before) --
        for y in range(WINDOW_HEIGHT):
            ratio = y / WINDOW_HEIGHT
            r = int(92 + (60 - 92) * ratio)
            g = int(148 + (120 - 148) * ratio)
            b = int(252 + (200 - 252) * ratio)
            pygame.draw.line(surface, (r, g, b), (0, y), (WINDOW_WIDTH, y))
            
        hill_color = (60, 140, 60)
        num_hills = 4
        spacing = WINDOW_WIDTH // (num_hills - 1)
        ground_visual_y = WINDOW_HEIGHT - 200
        
        # Far Hills
        for i in range(num_hills + 1):
            x = (i * spacing) - self.hill_far_scroll
            if x < -spacing: x += (num_hills + 1) * spacing
            pygame.draw.ellipse(surface, hill_color, (x, ground_visual_y + 20, spacing * 1.5, 300))
            
        # Near Hills 
        near_color = (50, 130, 50)
        for i in range(num_hills + 1):
            x = (i * spacing * 0.8) - self.hill_near_scroll
            if x < -spacing: x += (num_hills + 1) * spacing * 0.8
            pygame.draw.ellipse(surface, near_color, (x, ground_visual_y + 40, spacing * 1.2, 250))
            
        # Clouds
        num_clouds = 5
        cloud_spacing = WINDOW_WIDTH // 3
        for i in range(num_clouds):
            x = ((i * cloud_spacing) + 50) - self.cloud_scroll
            y = 60 + (i % 3) * 30
            while x < -100: x += WINDOW_WIDTH + 200
            self.draw_cloud(surface, x, y)
            
        # Ground
        ground_top = ground_visual_y + 80
        pygame.draw.rect(surface, (34, 139, 34), (0, ground_top, WINDOW_WIDTH, 15))
        pygame.draw.rect(surface, (139, 69, 19), (0, ground_top + 15, WINDOW_WIDTH, WINDOW_HEIGHT))
        
        # Grass Blades
        scroll_offset = int(self.hill_near_scroll)
        for x in range(0, WINDOW_WIDTH + 20, 20):
             draw_x = (x - scroll_offset) % WINDOW_WIDTH
             offset = (x // 20) % 3
             pygame.draw.line(surface, (0, 180, 0), (draw_x + offset * 3, ground_top), (draw_x + offset * 3, ground_top - 8), 2)

        # -- Draw Platforms (Tetris Blocks) --
        for i, p in enumerate(self.platforms):
            color = (200, 0, 200) if i < 4 else (255, 165, 0) # T-piece vs L-piece colors
            pygame.draw.rect(surface, color, p)
            pygame.draw.rect(surface, (255, 255, 255), p, 2) # Block border
            # Simple highlight for 3D look
            pygame.draw.line(surface, (255, 255, 255), (p.left, p.top), (p.right, p.top), 2)
            pygame.draw.line(surface, (255, 255, 255), (p.left, p.top), (p.left, p.bottom), 2)
            
        # -- Draw Actors --
        for actor in self.actors:
            actor.draw(surface)
            
        # -- Draw VERSION (Bottom Left) --
        font = pygame.font.SysFont('Arial', 14)
        v_txt = font.render("v1.1.3-ZOOM-FIX", True, (255, 255, 255, 120))
        surface.blit(v_txt, (10, WINDOW_HEIGHT - 20))
            
        # No UI here, handled by Tetris.draw_persistent_ui

    def handle_mouse_down(self, pos):
        """Handle mouse down for dragging or clicking."""
        # 1. UI Buttons
        if hasattr(self, 'settings_btn_rect') and self.settings_btn_rect and self.settings_btn_rect.collidepoint(pos):
            return 'settings'
        if hasattr(self, 'mute_btn_rect') and self.mute_btn_rect and self.mute_btn_rect.collidepoint(pos):
            return 'mute'
            
        # 2. Actors
        for actor in reversed(self.actors):
            if actor.get_rect().collidepoint(pos):
                actor.is_dragging = True
                actor.drag_offset_x = pos[0] - actor.x
                actor.drag_offset_y = pos[1] - actor.y
                return actor.on_click()
                
        return None

    def handle_mouse_up(self, pos):
        """Handle mouse release."""
        for actor in self.actors:
            if actor.is_dragging:
                actor.is_dragging = False
                # Re-sync ground_y if they were dropped
                if hasattr(actor, 'behavior') and actor.behavior != 'hover':
                     actor.y = min(actor.y, actor.ground_y)
                
    def handle_click(self, pos):
        """Legacy alias for backward compatibility."""
        return self.handle_mouse_down(pos)
