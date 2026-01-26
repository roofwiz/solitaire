import pygame
import math
import os
try:
    from src.config import *
except ImportError:
    # Fallback if running standalone or import path differs
    WINDOW_WIDTH = 1280
    WINDOW_HEIGHT = 720
    C_WHITE = (255, 255, 255)
    C_BLACK = (0, 0, 0)
    C_NEON_PINK = (255, 20, 147)

class RackMenu:
    def __init__(self, game):
        self.game = game
        self.sprite_manager = game.sprite_manager
        
        # Load Full Chassis Background
        self.chassis_bg = self.sprite_manager.images.get('rack')
        if self.chassis_bg:
             # Scale to window
             self.chassis_bg = pygame.transform.smoothscale(self.chassis_bg, (WINDOW_WIDTH, WINDOW_HEIGHT))
        
        # --- Constants & Layout (Pending User Calibration) ---
        self.POS_POWER_SW = (100, 100)
        self.POS_LIGHT = (180, 110)
        self.POS_VOL_KNOB = (1100, 100)
        self.POS_VFD = (WINDOW_WIDTH//2 - 128, 500) # Centered bottom
        self.POS_MEDIA_BTNS = (WINDOW_WIDTH//2 - 100, 600)
        self.POS_EQ_SLIDERS = [(300 + i*60, 300) for i in range(7)]
        
        # --- State ---
        self.power_on = False
        self.volume_level = 1 # 0-3
        self.eq_values = [0.5] * 7 # 0.0 to 1.0
        
        self.vfd_text = "NOW PLAYING: MARIO TETRIS OST... "
        self.vfd_scroll = 0
        self.vfd_timer = 0
        
        self.btn_states = {
            'play': False, 'stop': False, 'back': False, 'fwd': False
        }
        
    def update(self, dt):
        # VFD Scrolling
        if self.power_on:
            self.vfd_timer += dt
            if self.vfd_timer > 0.1: # Scroll speed
                 self.vfd_timer = 0
                 self.vfd_scroll = (self.vfd_scroll + 1) % (len(self.vfd_text) * 20) # Approx pixel width

    def draw(self, screen):
        # 1. Base Layer: Chassis
        if self.chassis_bg:
            screen.blit(self.chassis_bg, (0, 0))
        else:
            screen.fill((50, 50, 50)) # Fallback grey
            
        # 2. CRT Content (Main Menu Buttons inside Screen)
        # Assuming the "Screen Area" is in the middle-top roughly
        # We draw the original Intro Scene content HERE (Title + Game Options)
        # Offset them to fit inside the "CRT"
        
        # Draw Title
        title = self.game.font_big.render("SUPER BLOCK BROS", True, C_NEON_PINK if self.power_on else (50, 20, 50))
        screen.blit(title, (WINDOW_WIDTH//2 - title.get_width()//2, 150))
        
        if self.power_on:
            # Draw Start Buttons Logic (Visual only here, logic in handle_input)
            # Mario Tetris Button
            btn_tetris = pygame.Rect(WINDOW_WIDTH//2 - 150, 250, 300, 50)
            pygame.draw.rect(screen, (0, 150, 255), btn_tetris, border_radius=5)
            txt = self.game.font_small.render("MARIO TETRIS", True, C_WHITE)
            screen.blit(txt, txt.get_rect(center=btn_tetris.center))
            self.rect_btn_tetris = btn_tetris
            
            # Dark Mario Button
            btn_dark = pygame.Rect(WINDOW_WIDTH//2 - 150, 320, 300, 50)
            pygame.draw.rect(screen, (255, 215, 0), btn_dark, border_radius=5)
            txt = self.game.font_small.render("DARK MARIO", True, (0,0,0))
            screen.blit(txt, txt.get_rect(center=btn_dark.center))
            self.rect_btn_dark = btn_dark
        else:
            # Screen Off text
            off_txt = self.game.font_small.render("POWER OFF", True, (20, 20, 20))
            screen.blit(off_txt, (WINDOW_WIDTH//2 - 50, 300))
            self.rect_btn_tetris = None
            self.rect_btn_dark = None

        # 3. Components
        # Power Switch
        sw_sprite = 'switch_on' if self.power_on else 'switch_off'
        self.draw_component(screen, sw_sprite, self.POS_POWER_SW)
        self.rect_power = pygame.Rect(self.POS_POWER_SW[0], self.POS_POWER_SW[1], 64, 64)
        
        # Light
        l_sprite = 'light_on' if self.power_on else 'light_off'
        self.draw_component(screen, l_sprite, self.POS_LIGHT)
        
        # Volume Knob
        k_sprite = f'knob_{self.volume_level}'
        self.draw_component(screen, k_sprite, self.POS_VOL_KNOB)
        self.rect_vol = pygame.Rect(self.POS_VOL_KNOB[0], self.POS_VOL_KNOB[1], 64, 64)
        
        # EQ Sliders
        for i, (expect_x, expect_y) in enumerate(self.POS_EQ_SLIDERS):
             # Draw track line (cosmetic)
             pygame.draw.line(screen, (20, 20, 20), (expect_x + 16, expect_y), (expect_x + 16, expect_y + 100), 4)
             # Draw Cap based on value
             val_y = expect_y + (1.0 - self.eq_values[i]) * 80 # 80 px travel
             self.draw_component(screen, 'slider_cap', (expect_x, int(val_y)))
             # Hitbox for slider i
             # (Simplified logic: we'll check collision in handle_input)

        # 4. Media Player
        # VFD Screen
        self.draw_component(screen, 'vfd_screen', self.POS_VFD)
        
        if self.power_on:
            # Scroll Text
            # Clip rect for text
            clip_rect = pygame.Rect(self.POS_VFD[0] + 10, self.POS_VFD[1] + 16, 230, 32)
            # Ideally use set_clip
            prev_clip = screen.get_clip()
            screen.set_clip(clip_rect)
            
            # Draw repeated text for scroll
            full_txt = self.vfd_text + "   " + self.vfd_text
            txt_surf = self.game.font_small.render(full_txt, True, (0, 255, 255)) # Cyan VFD color
            
            # x offset
            w_char = 12 # approx width per char? Depends on font
            # Pixel scroll
            scr_x = self.POS_VFD[0] + 10 - (self.vfd_scroll % txt_surf.get_width())
            screen.blit(txt_surf, (scr_x, self.POS_VFD[1] + 20))
            screen.blit(txt_surf, (scr_x + txt_surf.get_width(), self.POS_VFD[1] + 20))
            
            screen.set_clip(prev_clip)

        # Media Buttons
        bx, by = self.POS_MEDIA_BTNS
        for b_name in ['play', 'stop', 'back', 'fwd']:
            state = '_lit' if self.btn_states.get(b_name) else ''
            self.draw_component(screen, f'btn_{b_name}{state}', (bx, by))
            
            # Store rect for input?
            # Creating rect map dynamically
            if not hasattr(self, 'rect_media'): self.rect_media = {}
            self.rect_media[b_name] = pygame.Rect(bx, by, 48, 32)
            
            bx += 60 # Spacing

    def draw_component(self, screen, name, pos):
        sprite = self.sprite_manager.get_sprite('rack_components', name)
        if sprite:
            screen.blit(sprite, pos)
        else:
            # Fallback placeholder
            pygame.draw.rect(screen, (255, 0, 255), (*pos, 32, 32)) 

    def handle_input(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            
            # Power
            if hasattr(self, 'rect_power') and self.rect_power.collidepoint(mx, my):
                self.power_on = not self.power_on
                self.game.sound_manager.play('move') # Should be power sound
                return True
                
            # Volume
            if hasattr(self, 'rect_vol') and self.rect_vol.collidepoint(mx, my):
                self.volume_level = (self.volume_level + 1) % 4
                self.game.sound_manager.set_volume(self.volume_level / 3.0) # 0, 0.33, 0.66, 1.0
                self.game.sound_manager.play('rotate')
                return True
                
            # Media Buttons
            if hasattr(self, 'rect_media'):
                for b_name, rect in self.rect_media.items():
                    if rect.collidepoint(mx, my):
                        self.btn_states[b_name] = True
                        self.handle_media(b_name)
                        return True

            # Game Links (Only if Power On)
            if self.power_on:
                 if hasattr(self, 'rect_btn_tetris') and self.rect_btn_tetris and self.rect_btn_tetris.collidepoint(mx, my):
                      self.game.reset_game()
                      self.game.game_state = 'PLAYING'
                      return True
                 if hasattr(self, 'rect_btn_dark') and self.rect_btn_dark and self.rect_btn_dark.collidepoint(mx, my):
                      self.game.game_state = 'DARK_WORLD'
                      return True
            
        elif event.type == pygame.MOUSEBUTTONUP:
            # Reset button states
            for k in self.btn_states: self.btn_states[k] = False
            
        elif event.type == pygame.MOUSEMOTION:
            if event.buttons[0]: # Dragging
                 # Check sliders
                 mx, my = event.pos
                 for i, (ex, ey) in enumerate(self.POS_EQ_SLIDERS):
                      if ex <= mx <= ex + 40 and ey - 20 <= my <= ey + 120:
                           # Update EQ
                           val = 1.0 - ((my - ey) / 80.0)
                           val = max(0.0, min(1.0, val))
                           self.eq_values[i] = val
            
        return False

    def handle_media(self, action):
        sm = self.game.sound_manager
        if action == 'play':
             sm.play_music() 
        elif action == 'stop':
             sm.stop_music()
        elif action == 'fwd':
             sm.current_track = (sm.current_track + 1) % len(sm.playlist)
             sm.load_track(sm.current_track)
             sm.play_music()
        elif action == 'back':
            sm.current_track = (sm.current_track - 1) % len(sm.playlist)
            sm.load_track(sm.current_track)
            sm.play_music()
        
        # Start VFD Update
        if action in ['play', 'fwd', 'back']:
             track_name = sm.playlist[sm.current_track]
             self.vfd_text = f"NOW PLAYING: {track_name.upper()}... "
