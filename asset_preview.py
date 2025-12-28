"""
Asset Preview Page for Super Block Bros
Shows all characters, blocks, items, and backgrounds used in the game
"""

import pygame
import sys
import os
from settings import game_settings

# Initialize
pygame.init()

SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 700
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Super Block Bros - Asset Preview")

# Colors
BG_COLOR = (30, 30, 50)
SECTION_COLOR = (50, 50, 80)
TEXT_COLOR = (255, 255, 255)
LABEL_COLOR = (255, 215, 0)

# Font
font_title = pygame.font.SysFont('Arial', 28, bold=True)
font_section = pygame.font.SysFont('Arial', 20, bold=True)
font_label = pygame.font.SysFont('Arial', 14)

# Load sprite sheets
sprite_sheets = {}
images_config = game_settings.config.get('images', {})
for name, filename in images_config.items():
    path = os.path.join('assets', filename)
    if os.path.exists(path):
        try:
            sprite_sheets[name] = pygame.image.load(path).convert_alpha()
            print(f"Loaded: {name} ({filename})")
        except Exception as e:
            print(f"Failed to load {name}: {e}")

sprite_data = game_settings.config.get('sprite_coords', {})

def get_sprite(sheet_name, category, frame_name, scale=2.0):
    """Extract a sprite from a sheet"""
    try:
        coords = sprite_data[category][frame_name]
        actual_sheet = coords.get('file', sheet_name)
        sheet = sprite_sheets.get(actual_sheet)
        if not sheet:
            return None
        
        rect = pygame.Rect(coords['x'], coords['y'], coords['w'], coords['h'])
        if not sheet.get_rect().contains(rect):
            return None
        
        sprite = sheet.subsurface(rect).copy()
        new_w = int(coords['w'] * scale)
        new_h = int(coords['h'] * scale)
        return pygame.transform.scale(sprite, (new_w, new_h))
    except:
        return None

def draw_section(surface, title, x, y, width, height):
    """Draw a section box with title"""
    pygame.draw.rect(surface, SECTION_COLOR, (x, y, width, height), border_radius=10)
    pygame.draw.rect(surface, LABEL_COLOR, (x, y, width, height), 2, border_radius=10)
    title_surf = font_section.render(title, True, LABEL_COLOR)
    surface.blit(title_surf, (x + 10, y + 5))
    return y + 30  # Return starting y for content

def main():
    clock = pygame.time.Clock()
    scroll_y = 0
    
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEWHEEL:
                scroll_y += event.y * 30
                scroll_y = min(0, scroll_y)  # Can't scroll up past top
        
        screen.fill(BG_COLOR)
        
        # Title
        title = font_title.render("SUPER BLOCK BROS - ASSET PREVIEW", True, (255, 100, 200))
        screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 10 + scroll_y))
        
        base_y = 50 + scroll_y
        
        # ==================== CHARACTERS ====================
        content_y = draw_section(screen, "CHARACTERS", 20, base_y, 460, 180)
        
        # Mario
        mario = get_sprite('spritesheet', 'mario', 'stand', 3.0)
        if mario:
            screen.blit(mario, (40, content_y + 10))
            lbl = font_label.render("Mario", True, TEXT_COLOR)
            screen.blit(lbl, (40, content_y + 60))
        
        # Luigi (tinted green, uses mario sprite)
        luigi = get_sprite('spritesheet', 'mario', 'stand', 3.0)
        if luigi:
            luigi = luigi.copy()
            luigi.fill((0, 255, 0, 100), special_flags=pygame.BLEND_RGBA_MULT)
            screen.blit(luigi, (120, content_y + 10))
            lbl = font_label.render("Luigi", True, TEXT_COLOR)
            screen.blit(lbl, (120, content_y + 60))
        
        # ==================== ENEMIES ====================
        content_y = draw_section(screen, "ENEMIES", 500, base_y, 480, 180)
        
        enemy_x = 520
        enemies = [
            ('koopa_green', 'walk_1', 'Green Turtle'),
            ('koopa_red', 'walk_1', 'Red Turtle'),
            ('spiny', 'walk_1', 'Spiny'),
        ]
        
        for category, frame, name in enemies:
            sprite = get_sprite('spritesheet', category, frame, 2.0)
            if sprite:
                screen.blit(sprite, (enemy_x, content_y + 10))
                lbl = font_label.render(name, True, TEXT_COLOR)
                screen.blit(lbl, (enemy_x, content_y + 60))
            enemy_x += 80
        
        # Golden Turtle (tinted)
        golden = get_sprite('spritesheet', 'koopa_green', 'walk_1', 2.0)
        if golden:
            golden = golden.copy()
            golden.fill((255, 215, 0, 100), special_flags=pygame.BLEND_RGBA_MULT)
            screen.blit(golden, (enemy_x, content_y + 10))
            lbl = font_label.render("Golden", True, TEXT_COLOR)
            screen.blit(lbl, (enemy_x, content_y + 60))
        
        # ==================== ITEMS ====================
        base_y += 200
        content_y = draw_section(screen, "POWER-UPS & ITEMS", 20, base_y, 460, 180)
        
        item_x = 40
        items = [
            ('items', 'mushroom_super', 'Super Mushroom'),
            ('items', 'mushroom_1up', '1UP Mushroom'),
            ('items', 'mushroom_poison', 'Poison'),
            ('items', 'flower_fire', 'Fire Flower'),
            ('items', 'star_1', 'Star'),
        ]
        
        for category, frame, name in items:
            sprite = get_sprite('items', category, frame, 2.5)
            if sprite:
                screen.blit(sprite, (item_x, content_y + 10))
                lbl = font_label.render(name, True, TEXT_COLOR)
                screen.blit(lbl, (item_x - 10, content_y + 60))
            item_x += 90
        
        # ==================== COINS ====================
        content_y = draw_section(screen, "COINS & EFFECTS", 500, base_y, 480, 180)
        
        coin_x = 520
        for i in range(1, 4):
            coin = get_sprite('items', 'items', f'coin_{i}', 2.5)
            if coin:
                screen.blit(coin, (coin_x, content_y + 10))
                lbl = font_label.render(f"Coin {i}", True, TEXT_COLOR)
                screen.blit(lbl, (coin_x, content_y + 60))
            coin_x += 60
        
        # Sparkles
        sparkle_x = coin_x + 20
        for i in [1, 4, 8]:
            sparkle = get_sprite('items', 'items', f'sparkle_{i}', 2.0)
            if sparkle:
                screen.blit(sparkle, (sparkle_x, content_y + 10))
            sparkle_x += 40
        lbl = font_label.render("Sparkles", True, TEXT_COLOR)
        screen.blit(lbl, (coin_x + 40, content_y + 60))
        
        # ==================== BLOCKS ====================
        base_y += 200
        content_y = draw_section(screen, "BLOCKS", 20, base_y, 460, 140)
        
        block_x = 40
        blocks = [
            ('blocks', 'question_1', '? Block'),
            ('blocks', 'question_2', '? Block 2'),
            ('blocks', 'question_3', '? Block 3'),
            ('blocks', 'empty', 'Empty'),
            ('blocks', 'brick', 'Brick'),
        ]
        
        for category, frame, name in blocks:
            sprite = get_sprite('blocks', category, frame, 2.5)
            if sprite:
                screen.blit(sprite, (block_x, content_y + 10))
                lbl = font_label.render(name, True, TEXT_COLOR)
                screen.blit(lbl, (block_x - 5, content_y + 55))
            block_x += 85
        
        # ==================== SPRITE SHEETS ====================
        content_y = draw_section(screen, "RAW SPRITE SHEETS", 500, base_y, 480, 140)
        
        sheet_x = 520
        for name, sheet in sprite_sheets.items():
            # Draw thumbnail
            thumb_w = min(100, sheet.get_width())
            thumb_h = int((thumb_w / sheet.get_width()) * sheet.get_height())
            thumb = pygame.transform.scale(sheet, (thumb_w, thumb_h))
            screen.blit(thumb, (sheet_x, content_y + 10))
            lbl = font_label.render(name[:12], True, TEXT_COLOR)
            screen.blit(lbl, (sheet_x, content_y + thumb_h + 15))
            sheet_x += 110
        
        # ==================== STATS ====================
        base_y += 160
        stats_text = f"Loaded {len(sprite_sheets)} sprite sheets | {len(sprite_data)} categories defined"
        stats = font_label.render(stats_text, True, (150, 150, 150))
        screen.blit(stats, (20, base_y))
        
        # Instructions
        inst = font_label.render("Scroll with mouse wheel | Press ESC to exit", True, (100, 100, 100))
        screen.blit(inst, (SCREEN_WIDTH - 280, SCREEN_HEIGHT - 25))
        
        pygame.display.flip()
        clock.tick(60)
        
        # Handle ESC
        keys = pygame.key.get_pressed()
        if keys[pygame.K_ESCAPE]:
            pygame.quit()
            sys.exit()

if __name__ == "__main__":
    main()
