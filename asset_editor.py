"""
Super Block Bros - Asset Editor
A comprehensive tool to view, edit, and manage game sprite coordinates.

Features:
- Animated sprite previews
- Editable coordinates
- Click on sprite sheet to adjust positions
- Save changes to assets.json
"""

import pygame
import sys
import os
import json
from settings import game_settings

# Initialize
pygame.init()

SCREEN_WIDTH = 1400
SCREEN_HEIGHT = 900
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Super Block Bros - Asset Editor")

# Colors
BG_COLOR = (25, 25, 35)
PANEL_COLOR = (40, 40, 55)
SELECTED_COLOR = (80, 80, 120)
TEXT_COLOR = (255, 255, 255)
LABEL_COLOR = (255, 215, 0)
ACCENT_COLOR = (255, 100, 200)
BUTTON_COLOR = (60, 120, 200)
BUTTON_HOVER = (80, 150, 255)
ERROR_COLOR = (255, 80, 80)
SUCCESS_COLOR = (80, 255, 80)

# Fonts
font_title = pygame.font.SysFont('Arial', 24, bold=True)
font_section = pygame.font.SysFont('Arial', 16, bold=True)
font_label = pygame.font.SysFont('Arial', 12)
font_small = pygame.font.SysFont('Arial', 10)

# Asset descriptions
ASSET_DESCRIPTIONS = {
    'mario': {'stand': 'Mario standing pose', 'walk': 'Mario walking animation'},
    'luigi': {'stand': 'Luigi standing pose', 'walk': 'Luigi walking animation'},
    'koopa_green': {
        'walk_1': 'Green Koopa walking frame 1',
        'walk_2': 'Green Koopa walking frame 2',
        'fly_1': 'Green Koopa flying frame 1',
        'fly_2': 'Green Koopa flying frame 2',
        'shell_1': 'Shell spin frame 1',
        'shell_2': 'Shell spin frame 2',
    },
    'koopa_red': {
        'walk_1': 'Red Koopa walking frame 1',
        'walk_2': 'Red Koopa walking frame 2',
        'fly_1': 'Red Koopa flying frame 1',
        'fly_2': 'Red Koopa flying frame 2',
    },
    'spiny': {'walk_1': 'Spiny walking frame 1', 'walk_2': 'Spiny walking frame 2'},
    'items': {
        'mushroom_super': 'Super Mushroom - Power up',
        'mushroom_1up': '1UP Mushroom - Extra life',
        'mushroom_poison': 'Poison Mushroom - Damage',
        'flower_fire': 'Fire Flower - Fire power',
        'star_1': 'Star frame 1 (orange)',
        'star_2': 'Star frame 2 (green)',
        'star_3': 'Star frame 3 (red)',
        'star_4': 'Star frame 4 (blue)',
        'coin_1': 'Coin frame 1',
        'coin_2': 'Coin frame 2',
        'coin_3': 'Coin frame 3',
    },
    'blocks': {
        'question_1': 'Question block frame 1',
        'question_2': 'Question block frame 2',
        'question_3': 'Question block frame 3',
        'empty': 'Empty/hit block',
        'brick': 'Brick block',
    },
}

def make_luigi(surf):
    """Applies Luigi palette swap (Red->Green)"""
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
                    arr[x, y] = (g, r, b, a) # Swap R and G
    return s


class AssetEditor:
    def __init__(self):
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Load sprite sheets
        self.sprite_sheets = {}
        self.load_sprite_sheets()
        
        # Load sprite data (editable copy)
        self.sprite_data = json.loads(json.dumps(game_settings.config.get('sprite_coords', {})))
        self.original_data = json.loads(json.dumps(self.sprite_data))
        
        # UI State
        self.selected_category = None
        self.selected_sprite = None
        self.scroll_y = 0
        self.editing_mode = False  # When True, click on sheet to set coords
        self.message = ""
        self.message_timer = 0
        self.message_color = SUCCESS_COLOR
        
        # Animation
        self.anim_timer = 0
        self.anim_frame = 0
        
        # Sheet viewer
        self.sheet_scroll_x = 0
        self.sheet_scroll_y = 0
        self.sheet_zoom = 3  # Zoom level for sprite sheet
        self.current_sheet_name = 'spritesheet'
        
        # Dragging state for panning
        self.dragging = False
        self.drag_start = (0, 0)
        self.drag_scroll_start = (0, 0)
        
        self.mouse_sheet_x = 0
        self.mouse_sheet_y = 0
        self.mouse_in_sheet = False
        
        # CLI Jump
        if len(sys.argv) > 2:
            try:
                cat = sys.argv[1]
                spr = sys.argv[2]
                if cat in self.sprite_data and spr in self.sprite_data[cat]:
                    self.focus_sprite(cat, spr)
            except: pass
            
    def focus_sprite(self, category, sprite):
        self.selected_category = category
        self.selected_sprite = sprite
        coords = self.sprite_data[category][sprite]
        self.current_sheet_name = coords.get('file', 'spritesheet')
        
        # Center View Logic
        # View Area: 700x620 -> Center 350, 310
        view_cx, view_cy = 350, 310
        sprite_cx = coords['x'] + coords['w']//2
        sprite_cy = coords['y'] + coords['h']//2
        
        self.sheet_zoom = 3 # Nice context
        
        self.sheet_scroll_x = max(0, int(sprite_cx * self.sheet_zoom - view_cx))
        self.sheet_scroll_y = max(0, int(sprite_cy * self.sheet_zoom - view_cy))
        
        # Auto-Enter Edit Mode
        if not self.sprite_data[category][sprite].get('verified', False):
            self.editing_mode = True
            self.show_message("Edit Mode Active! Use Arrow Keys to Move Box", LABEL_COLOR)
        
    def load_sprite_sheets(self):
        images_config = game_settings.config.get('images', {})
        for name, filename in images_config.items():
            path = os.path.join('assets', filename)
            if os.path.exists(path):
                try:
                    self.sprite_sheets[name] = pygame.image.load(path).convert_alpha()
                    print(f"Loaded: {name}")
                except Exception as e:
                    print(f"Failed: {name} - {e}")
    
    def get_sprite(self, category, frame_name, scale=2.0):
        """Extract a sprite from sheet"""
        try:
            coords = self.sprite_data[category][frame_name]
            sheet_name = coords.get('file', 'spritesheet')
            sheet = self.sprite_sheets.get(sheet_name)
            if not sheet:
                return None
            
            rect = pygame.Rect(coords['x'], coords['y'], coords['w'], coords['h'])
            if not sheet.get_rect().contains(rect):
                return None
            
            sprite = sheet.subsurface(rect).copy()
            
            # Apply Tint for Luigi
            if category == 'luigi':
                sprite = make_luigi(sprite)
            
            new_w = int(coords['w'] * scale)
            new_h = int(coords['h'] * scale)
            return pygame.transform.scale(sprite, (new_w, new_h))
        except:
            return None
    
    def show_message(self, msg, color=SUCCESS_COLOR):
        self.message = msg
        self.message_timer = 3.0
        self.message_color = color
    
    def save_changes(self):
        """Save changes back to assets.json"""
        try:
            config = game_settings.config.copy()
            config['sprite_coords'] = self.sprite_data
            
            with open('assets.json', 'w') as f:
                json.dump(config, f, indent=4)
            
            self.original_data = json.loads(json.dumps(self.sprite_data))
            self.show_message("Saved to assets.json!", SUCCESS_COLOR)
        except Exception as e:
            self.show_message(f"Save failed: {e}", ERROR_COLOR)
    
    def export_spritesheet(self):
        """Export all sprites to a single consolidated PNG file"""
        try:
            # Calculate layout
            sprites_per_row = 8
            sprite_size = 48  # Output size for each sprite
            padding = 4
            label_height = 16
            
            # Count all sprites
            all_sprites = []
            for category in sorted(self.sprite_data.keys()):
                for sprite_name in sorted(self.sprite_data[category].keys()):
                    sprite = self.get_sprite(category, sprite_name, 2.0)
                    if sprite:
                        all_sprites.append((category, sprite_name, sprite))
            
            if not all_sprites:
                self.show_message("No sprites to export!", ERROR_COLOR)
                return
            
            # Calculate dimensions
            rows = (len(all_sprites) + sprites_per_row - 1) // sprites_per_row
            output_width = sprites_per_row * (sprite_size + padding) + padding
            output_height = rows * (sprite_size + label_height + padding) + padding + 40  # Extra for header
            
            # Create output surface
            output = pygame.Surface((output_width, output_height), pygame.SRCALPHA)
            output.fill((30, 30, 40, 255))
            
            # Draw header
            header_font = pygame.font.SysFont('Arial', 20, bold=True)
            header = header_font.render("Super Block Bros - Sprite Atlas", True, (255, 215, 0))
            output.blit(header, (padding, padding))
            
            # Draw sprites
            small_font = pygame.font.SysFont('Arial', 8)
            for i, (category, sprite_name, sprite) in enumerate(all_sprites):
                col = i % sprites_per_row
                row = i // sprites_per_row
                
                x = padding + col * (sprite_size + padding)
                y = 40 + padding + row * (sprite_size + label_height + padding)
                
                # Background box
                pygame.draw.rect(output, (50, 50, 60), (x, y, sprite_size, sprite_size + label_height))
                pygame.draw.rect(output, (100, 100, 100), (x, y, sprite_size, sprite_size + label_height), 1)
                
                # Scale sprite to fit
                sw, sh = sprite.get_size()
                scale = min((sprite_size - 4) / sw, (sprite_size - 4) / sh)
                new_w, new_h = int(sw * scale), int(sh * scale)
                scaled = pygame.transform.scale(sprite, (new_w, new_h))
                
                # Center in box
                sprite_x = x + (sprite_size - new_w) // 2
                sprite_y = y + (sprite_size - new_h) // 2
                output.blit(scaled, (sprite_x, sprite_y))
                
                # Label
                label = small_font.render(f"{sprite_name[:8]}", True, (200, 200, 200))
                label_x = x + (sprite_size - label.get_width()) // 2
                output.blit(label, (label_x, y + sprite_size + 2))
            
            # Save to file
            output_path = os.path.join('assets', 'sprite_atlas_export.png')
            pygame.image.save(output, output_path)
            
            self.show_message(f"Exported {len(all_sprites)} sprites to {output_path}", SUCCESS_COLOR)
            
        except Exception as e:
            self.show_message(f"Export failed: {e}", ERROR_COLOR)
    
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            if event.type == pygame.VIDEORESIZE:
                global SCREEN_WIDTH, SCREEN_HEIGHT, screen
                SCREEN_WIDTH, SCREEN_HEIGHT = event.w, event.h
                screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.editing_mode:
                        self.editing_mode = False
                        self.show_message("Edit mode cancelled", LABEL_COLOR)
                    else:
                        self.running = False
                
                if event.key == pygame.K_s and pygame.key.get_mods() & pygame.KMOD_CTRL:
                    self.save_changes()
                
                # Adjust coordinates with arrow keys when editing
                if self.editing_mode and self.selected_category and self.selected_sprite:
                    coords = self.sprite_data[self.selected_category][self.selected_sprite]
                    
                    if coords.get('verified', False):
                         self.show_message("Item is LOCKED. Unlock to edit.", ERROR_COLOR)
                    else:
                        shift = pygame.key.get_mods() & pygame.KMOD_SHIFT
                        step = 5 if shift else 1
                        
                        if event.key == pygame.K_LEFT:
                            coords['x'] = max(0, coords['x'] - step)
                        elif event.key == pygame.K_RIGHT:
                            coords['x'] += step
                        elif event.key == pygame.K_UP:
                            coords['y'] = max(0, coords['y'] - step)
                        elif event.key == pygame.K_DOWN:
                            coords['y'] += step
                        # Size Adjustment
                        elif event.key == pygame.K_LEFTBRACKET:
                            coords['w'] = max(1, coords['w'] - step)
                        elif event.key == pygame.K_RIGHTBRACKET:
                            coords['w'] += step
                        elif event.key == pygame.K_MINUS:
                            coords['h'] = max(1, coords['h'] - step)
                        elif event.key == pygame.K_EQUALS:
                            coords['h'] += step
                
                # WASD to scroll sprite sheet
                scroll_step = 50
                if event.key == pygame.K_w:
                    self.sheet_scroll_y = max(0, self.sheet_scroll_y - scroll_step)
                elif event.key == pygame.K_a:
                    self.sheet_scroll_x = max(0, self.sheet_scroll_x - scroll_step)
                elif event.key == pygame.K_d:
                    self.sheet_scroll_x += scroll_step
                elif event.key == pygame.K_z:  # Zoom out
                    self.sheet_zoom = max(1, self.sheet_zoom - 1)
                elif event.key == pygame.K_x:  # Zoom in
                    self.sheet_zoom = min(8, self.sheet_zoom + 1)
                elif event.key == pygame.K_HOME:  # Reset view
                    self.sheet_scroll_x = 0
                    self.sheet_scroll_y = 0
                    self.sheet_zoom = 3
            
            if event.type == pygame.MOUSEWHEEL:
                mx, my = pygame.mouse.get_pos()
                sheet_area = pygame.Rect(690, 70, 700, 620)
                
                if sheet_area.collidepoint(mx, my):
                    # When hovering over sheet, scroll vertically OR zoom with Ctrl
                    if pygame.key.get_mods() & pygame.KMOD_CTRL:
                        self.sheet_zoom = max(1, min(8, self.sheet_zoom + event.y))
                    elif pygame.key.get_mods() & pygame.KMOD_SHIFT:
                        # Shift+scroll = horizontal scroll
                        self.sheet_scroll_x = max(0, self.sheet_scroll_x - event.y * 40)
                    else:
                        # Normal scroll = vertical scroll on sheet
                        self.sheet_scroll_y = max(0, self.sheet_scroll_y - event.y * 40)
                else:
                    # Scroll asset list
                    self.scroll_y += event.y * 30
                    self.scroll_y = min(0, self.scroll_y)
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 2:  # Middle mouse button - start drag
                    sheet_area = pygame.Rect(690, 70, 700, 620)
                    if sheet_area.collidepoint(event.pos):
                        self.dragging = True
                        self.drag_start = event.pos
                        self.drag_scroll_start = (self.sheet_scroll_x, self.sheet_scroll_y)
                else:
                    self.handle_click(event.pos, event.button)
            
            if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 2:  # Middle mouse button released
                    self.dragging = False
            
            if event.type == pygame.MOUSEMOTION:
                # Update mouse position for coordinate display
                mx, my = event.pos
                sheet_area = pygame.Rect(700, 105, 680, 575)
                if sheet_area.collidepoint(mx, my):
                    self.mouse_in_sheet = True
                    rel_x = mx - sheet_area.x + self.sheet_scroll_x
                    rel_y = my - sheet_area.y + self.sheet_scroll_y
                    self.mouse_sheet_x = rel_x // self.sheet_zoom
                    self.mouse_sheet_y = rel_y // self.sheet_zoom
                else:
                    self.mouse_in_sheet = False
                
                # Handle dragging
                if self.dragging:
                    dx = self.drag_start[0] - mx
                    dy = self.drag_start[1] - my
                    self.sheet_scroll_x = max(0, self.drag_scroll_start[0] + dx)
                    self.sheet_scroll_y = max(0, self.drag_scroll_start[1] + dy)
    
    def handle_click(self, pos, button):
        mx, my = pos
        print(f"Click at {pos}, btn={button}")
        
        # Check top buttons
        if hasattr(self, 'save_btn') and self.save_btn.collidepoint(mx, my):
            self.save_changes()
            return
        
        if hasattr(self, 'export_btn') and self.export_btn.collidepoint(mx, my):
            self.export_spritesheet()
            return
        
        # Check sheet area click (right side)
        sheet_area = pygame.Rect(700, 100, 680, 600)
        if sheet_area.collidepoint(mx, my) and self.editing_mode:
            if self.selected_category and self.selected_sprite:
                coords = self.sprite_data[self.selected_category][self.selected_sprite]
                if coords.get('verified', False):
                     self.show_message("Item is LOCKED. Unlock to edit.", ERROR_COLOR)
                     return
                     
                # Calculate sprite sheet coordinates
                rel_x = mx - sheet_area.x + self.sheet_scroll_x
                rel_y = my - sheet_area.y + self.sheet_scroll_y
                
                sheet_x = rel_x // self.sheet_zoom
                sheet_y = rel_y // self.sheet_zoom
                
                heading = coords.get('file', 'spritesheet')
                if heading != self.current_sheet_name:
                     self.show_message("Wrong sheet! This sprite uses " + heading, ERROR_COLOR)
                     return

                coords['x'] = int(sheet_x)
                coords['y'] = int(sheet_y)
                self.show_message(f"Set position to ({sheet_x}, {sheet_y})", SUCCESS_COLOR)
            return
        
        # Check item list clicks (left side)
        if mx < 680:
            # Find clicked item
            y_offset = 80 + self.scroll_y
            for category in sorted(self.sprite_data.keys()):
                # Category header
                cat_rect = pygame.Rect(20, y_offset, 640, 25)
                if cat_rect.collidepoint(mx, my):
                    if self.selected_category == category:
                        self.selected_category = None
                    else:
                        self.selected_category = category
                    self.selected_sprite = None
                    return
                y_offset += 30
                
                # Sprite items (if category is selected)
                if self.selected_category == category:
                    for sprite_name in sorted(self.sprite_data[category].keys()):
                        item_rect = pygame.Rect(40, y_offset, 620, 50)
                        if item_rect.collidepoint(mx, my):
                            self.selected_sprite = sprite_name
                            # Focus View
                            self.focus_sprite(category, sprite_name)
                            return
                        
                        # Check for Edit button
                        edit_btn = pygame.Rect(530, y_offset + 10, 50, 25)
                        if edit_btn.collidepoint(mx, my):
                            self.selected_sprite = sprite_name
                            self.editing_mode = True
                            coords = self.sprite_data[category][sprite_name]
                            if coords.get('verified', False):
                                self.show_message("Item is LOCKED. Unlock to edit.", ERROR_COLOR)
                                self.editing_mode = False
                                return
                            self.current_sheet_name = coords.get('file', 'spritesheet')
                            self.show_message("Click on sprite sheet to set position (Arrow keys to fine-tune)", LABEL_COLOR)
                            return
                        
                        # Check for Lock/Verify button
                        lock_btn = pygame.Rect(590, y_offset + 10, 60, 25)
                        if lock_btn.collidepoint(mx, my):
                            coords = self.sprite_data[category][sprite_name]
                            coords['verified'] = not coords.get('verified', False)
                            status = "LOCKED" if coords['verified'] else "UNLOCKED"
                            self.show_message(f"Sprite {status}. Remember to Save!", SUCCESS_COLOR)
                            return
                        
                        y_offset += 55
    
    def update(self, dt):
        # Animation timer
        self.anim_timer += dt
        if self.anim_timer > 0.2:
            self.anim_timer = 0
            self.anim_frame = (self.anim_frame + 1) % 4
        
        # Message timer
        if self.message_timer > 0:
            self.message_timer -= dt
    
    def draw(self):
        screen.fill(BG_COLOR)
        
        # Title
        title = font_title.render("ASSET EDITOR", True, ACCENT_COLOR)
        screen.blit(title, (20, 15))
        
        # Save button
        self.save_btn = pygame.Rect(200, 12, 100, 30)
        pygame.draw.rect(screen, BUTTON_COLOR, self.save_btn, border_radius=5)
        save_txt = font_section.render("Save (Ctrl+S)", True, TEXT_COLOR)
        screen.blit(save_txt, (210, 17))
        
        # Export button
        self.export_btn = pygame.Rect(310, 12, 110, 30)
        pygame.draw.rect(screen, (100, 60, 150), self.export_btn, border_radius=5)
        export_txt = font_section.render("Export PNG", True, TEXT_COLOR)
        screen.blit(export_txt, (320, 17))
        
        # Mode indicator
        if self.editing_mode:
            mode_txt = font_section.render("EDITING MODE - Click sheet to set position", True, LABEL_COLOR)
            screen.blit(mode_txt, (440, 17))
        
        # Message
        if self.message_timer > 0:
            msg_surf = font_section.render(self.message, True, self.message_color)
            screen.blit(msg_surf, (SCREEN_WIDTH // 2 - msg_surf.get_width() // 2, 50))
        
        # Left panel: Asset list
        self.draw_asset_list()
        
        # Right panel: Sprite sheet viewer
        self.draw_sheet_viewer()
        
        # Bottom: Selected sprite details
        self.draw_sprite_details()
        
        pygame.display.flip()
    
    def draw_asset_list(self):
        # Panel background
        pygame.draw.rect(screen, PANEL_COLOR, (10, 70, 670, 720), border_radius=10)
        
        # Clip rect for scrolling
        clip_rect = pygame.Rect(10, 70, 670, 720)
        screen.set_clip(clip_rect)
        
        y_offset = 80 + self.scroll_y
        
        for category in sorted(self.sprite_data.keys()):
            # Category header
            is_selected = self.selected_category == category
            header_color = SELECTED_COLOR if is_selected else PANEL_COLOR
            pygame.draw.rect(screen, header_color, (20, y_offset, 640, 25), border_radius=5)
            pygame.draw.rect(screen, LABEL_COLOR, (20, y_offset, 640, 25), 1, border_radius=5)
            
            cat_text = font_section.render(f"▼ {category}" if is_selected else f"▶ {category}", True, LABEL_COLOR)
            screen.blit(cat_text, (30, y_offset + 3))
            
            count_text = font_small.render(f"{len(self.sprite_data[category])} sprites", True, TEXT_COLOR)
            screen.blit(count_text, (600, y_offset + 6))
            
            y_offset += 30
            
            # Show sprites if category is selected
            if is_selected:
                for sprite_name in sorted(self.sprite_data[category].keys()):
                    is_sprite_selected = self.selected_sprite == sprite_name
                    item_color = SELECTED_COLOR if is_sprite_selected else (50, 50, 70)
                    pygame.draw.rect(screen, item_color, (40, y_offset, 620, 50), border_radius=5)
                    
                    # Sprite preview
                    sprite = self.get_sprite(category, sprite_name, 2.0)
                    if sprite:
                        screen.blit(sprite, (50, y_offset + 5))
                    else:
                        pygame.draw.rect(screen, ERROR_COLOR, (50, y_offset + 5, 32, 32), 2)
                    
                    # Sprite name
                    name_text = font_label.render(sprite_name, True, TEXT_COLOR)
                    screen.blit(name_text, (100, y_offset + 5))
                    
                    # Coordinates
                    coords = self.sprite_data[category][sprite_name]
                    coord_text = font_small.render(
                        f"x:{coords['x']} y:{coords['y']} w:{coords['w']} h:{coords['h']} file:{coords.get('file', 'spritesheet')}",
                        True, (150, 150, 150)
                    )
                    screen.blit(coord_text, (100, y_offset + 22))
                    
                    # Description
                    desc = ASSET_DESCRIPTIONS.get(category, {}).get(sprite_name, "")
                    if desc:
                        desc_text = font_small.render(desc[:50], True, (100, 150, 100))
                        screen.blit(desc_text, (100, y_offset + 35))
                    
                    # Edit button
                    edit_btn = pygame.Rect(530, y_offset + 10, 50, 25)
                    mx, my = pygame.mouse.get_pos()
                    is_hovering_edit = edit_btn.collidepoint(mx, my)
                    
                    btn_color = BUTTON_HOVER if (self.editing_mode and is_sprite_selected) or is_hovering_edit else BUTTON_COLOR
                    pygame.draw.rect(screen, btn_color, edit_btn, border_radius=3)
                    edit_text = font_small.render("EDIT", True, TEXT_COLOR)
                    screen.blit(edit_text, (540, y_offset + 15))
                    
                    # Verify/Lock button
                    is_verified = coords.get('verified', False)
                    lock_btn = pygame.Rect(590, y_offset + 10, 60, 25)
                    is_hovering_lock = lock_btn.collidepoint(mx, my)
                    
                    base_lock_color = (60, 200, 60) if is_verified else (100, 100, 100)
                    lock_color = (80, 220, 80) if is_hovering_lock else base_lock_color
                    
                    pygame.draw.rect(screen, lock_color, lock_btn, border_radius=3)
                    lock_txt = font_small.render("LOCKED" if is_verified else "LOCK", True, TEXT_COLOR)
                    screen.blit(lock_txt, (595, y_offset + 15))
                    
                    y_offset += 55
        
        screen.set_clip(None)
    
    def draw_sheet_viewer(self):
        # Panel background
        pygame.draw.rect(screen, PANEL_COLOR, (690, 70, 700, 620), border_radius=10)
        
        # Sheet selector tabs
        tab_x = 700
        for sheet_name in self.sprite_sheets.keys():
            is_current = sheet_name == self.current_sheet_name
            tab_color = SELECTED_COLOR if is_current else (50, 50, 70)
            tab_rect = pygame.Rect(tab_x, 75, 80, 25)
            pygame.draw.rect(screen, tab_color, tab_rect, border_radius=5)
            tab_text = font_small.render(sheet_name[:10], True, TEXT_COLOR)
            screen.blit(tab_text, (tab_x + 5, 80))
            tab_x += 85
        
        # Sprite sheet display
        sheet_area = pygame.Rect(700, 105, 680, 575)
        pygame.draw.rect(screen, (20, 20, 30), sheet_area)
        
        sheet = self.sprite_sheets.get(self.current_sheet_name)
        if sheet:
            # Scale sheet
            scaled_w = sheet.get_width() * self.sheet_zoom
            scaled_h = sheet.get_height() * self.sheet_zoom
            scaled_sheet = pygame.transform.scale(sheet, (scaled_w, scaled_h))
            
            # Clip and blit
            screen.set_clip(sheet_area)
            screen.blit(scaled_sheet, (700 - self.sheet_scroll_x, 105 - self.sheet_scroll_y))
            
            # Draw selection rectangle if editing
            if self.selected_category and self.selected_sprite:
                coords = self.sprite_data[self.selected_category][self.selected_sprite]
                if coords.get('file', 'spritesheet') == self.current_sheet_name:
                    sel_x = 700 + (coords['x'] * self.sheet_zoom) - self.sheet_scroll_x
                    sel_y = 105 + (coords['y'] * self.sheet_zoom) - self.sheet_scroll_y
                    sel_w = coords['w'] * self.sheet_zoom
                    sel_h = coords['h'] * self.sheet_zoom
                    pygame.draw.rect(screen, ACCENT_COLOR, (sel_x, sel_y, sel_w, sel_h), 2)
            
            screen.set_clip(None)
        
        # Zoom indicator
        zoom_text = font_small.render(f"Zoom: {self.sheet_zoom}x (Ctrl+Scroll)", True, (150, 150, 150))
        screen.blit(zoom_text, (700, 685))
    
    def draw_sprite_details(self):
        # Bottom panel
        pygame.draw.rect(screen, PANEL_COLOR, (690, 700, 700, 90), border_radius=10)
        
        if self.selected_category and self.selected_sprite:
            coords = self.sprite_data[self.selected_category][self.selected_sprite]
            
            # Animated preview
            preview = self.get_sprite(self.selected_category, self.selected_sprite, 3.0)
            if preview:
                screen.blit(preview, (710, 715))
            
            # Details
            detail_text = font_section.render(f"{self.selected_category} / {self.selected_sprite}", True, LABEL_COLOR)
            screen.blit(detail_text, (800, 710))
            
            coord_text = font_label.render(
                f"Position: ({coords['x']}, {coords['y']})  Size: {coords['w']}x{coords['h']}  Sheet: {coords.get('file', 'spritesheet')}",
                True, TEXT_COLOR
            )
            screen.blit(coord_text, (800, 735))
            
            # Instructions
            if self.editing_mode:
                inst = font_small.render("Arrows: Move | [ ]: Width | - =: Height | Shift: Faster | Click sheet to set | ESC: Cancel", True, LABEL_COLOR)
            else:
                inst = font_small.render("Click EDIT button to modify coordinates", True, (100, 100, 100))
            screen.blit(inst, (800, 760))
        else:
            hint = font_label.render("Select a sprite from the list to view/edit", True, (100, 100, 100))
            screen.blit(hint, (900, 740))
    
    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()
        
        pygame.quit()


if __name__ == "__main__":
    editor = AssetEditor()
    editor.run()
