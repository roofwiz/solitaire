"""
Auto-labeling sprite viewer - shows sprite sheet with automatic labels
"""
import pygame
import sys

pygame.init()

# Load sprite sheet
spritesheet = pygame.image.load('assets/marioallsprite.png')
sheet_w, sheet_h = spritesheet.get_size()

# Create window
WINDOW_WIDTH = min(1600, sheet_w + 200)
WINDOW_HEIGHT = min(1000, sheet_h + 200)
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Auto-Labeled Sprite Sheet Viewer")

font = pygame.font.Font(None, 16)
title_font = pygame.font.Font(None, 24)

# Define known sprite regions with labels based on typical NES Mario layout
# Format: (x, y, w, h, "Label", color)
sprite_regions = [
    # Left side - Small enemies and items
    (8, 325, 16, 16, "Spiny Walk 1", (255, 100, 100)),
    (48, 325, 16, 16, "Spiny Walk 2", (255, 100, 100)),
    (8, 246, 24, 32, "Lakitu", (100, 200, 255)),
    
    # Green Koopas
    (208, 243, 16, 27, "Green Koopa Walk 1", (100, 255, 100)),
    (248, 244, 16, 27, "Green Koopa Walk 2", (100, 255, 100)),
    (288, 243, 16, 27, "Green Para Walk 1", (100, 255, 200)),
    (328, 243, 16, 27, "Green Para Walk 2", (100, 255, 200)),
    (208, 285, 16, 14, "Green Shell 1", (100, 255, 100)),
    (248, 285, 16, 14, "Green Shell 2", (100, 255, 100)),
    
    # Red Koopas
    (248, 323, 16, 27, "Red Koopa Walk 1", (255, 100, 100)),
    (288, 323, 16, 27, "Red Koopa Walk 2", (255, 100, 100)),
    (287, 325, 16, 24, "Red Para Fly 1", (255, 150, 150)),
    (328, 325, 16, 24, "Red Para Fly 2", (255, 150, 150)),
    (206, 365, 16, 16, "Red Shell 1", (255, 100, 100)),
    (247, 365, 16, 16, "Red Shell 2", (255, 100, 100)),
    
    # Mario sprites
    (170, 40, 16, 32, "Mario Stand", (255, 200, 100)),
    (207, 41, 16, 32, "Mario Walk 1", (255, 200, 100)),
    (247, 43, 16, 32, "Mario Walk 2", (255, 200, 100)),
]

# Camera
offset_x = 0
offset_y = 0
zoom = 1.5
dragging = False
last_pos = None

running = True
clock = pygame.time.Clock()
show_labels = True
show_boxes = True

print("=" * 60)
print("AUTO-LABELED SPRITE SHEET VIEWER")
print("=" * 60)
print("Controls:")
print("  RIGHT CLICK + DRAG: Pan view")
print("  SCROLL: Zoom")
print("  L: Toggle labels")
print("  B: Toggle boxes")
print("  ESC: Exit")
print("=" * 60)

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_l:
                show_labels = not show_labels
            elif event.key == pygame.K_b:
                show_boxes = not show_boxes
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 3:
                dragging = True
                last_pos = event.pos
            elif event.button == 4:  # Scroll up
                zoom = min(zoom * 1.1, 5.0)
            elif event.button == 5:  # Scroll down
                zoom = max(zoom / 1.1, 0.3)
            elif event.button == 1:  # Left click - print clicked region
                mx, my = event.pos
                sheet_x = int((mx - 100 - offset_x) / zoom)
                sheet_y = int((my - 100 - offset_y) / zoom)
                
                # Check if clicked on any labeled region
                for x, y, w, h, label, color in sprite_regions:
                    if x <= sheet_x <= x + w and y <= sheet_y <= y + h:
                        print(f"\n📍 CLICKED: {label}")
                        print(f'    "x": {x}, "y": {y}, "w": {w}, "h": {h}')
                        break
        
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 3:
                dragging = False
        
        elif event.type == pygame.MOUSEMOTION:
            if dragging and last_pos:
                dx = event.pos[0] - last_pos[0]
                dy = event.pos[1] - last_pos[1]
                offset_x += dx
                offset_y += dy
                last_pos = event.pos
    
    # Draw
    screen.fill((30, 30, 40))
    
    # Scale and draw sprite sheet
    scaled_w = int(sheet_w * zoom)
    scaled_h = int(sheet_h * zoom)
    scaled_sheet = pygame.transform.scale(spritesheet, (scaled_w, scaled_h))
    screen.blit(scaled_sheet, (100 + offset_x, 100 + offset_y))
    
    # Draw labeled regions
    for x, y, w, h, label, color in sprite_regions:
        sx = 100 + offset_x + int(x * zoom)
        sy = 100 + offset_y + int(y * zoom)
        sw = int(w * zoom)
        sh = int(h * zoom)
        
        # Draw box
        if show_boxes:
            pygame.draw.rect(screen, color, (sx, sy, sw, sh), 2)
        
        # Draw label
        if show_labels:
            label_surf = font.render(label, True, color)
            label_bg = pygame.Surface((label_surf.get_width() + 4, label_surf.get_height() + 2))
            label_bg.fill((20, 20, 30))
            label_bg.set_alpha(200)
            screen.blit(label_bg, (sx, sy - 18))
            screen.blit(label_surf, (sx + 2, sy - 17))
    
    # Draw title
    title = title_font.render("Auto-Labeled Mario Sprite Sheet", True, (255, 255, 255))
    screen.blit(title, (10, 10))
    
    # Draw instructions
    inst = font.render(f"Zoom: {zoom:.1f}x | L: Labels {'ON' if show_labels else 'OFF'} | B: Boxes {'ON' if show_boxes else 'OFF'}", 
                      True, (200, 200, 200))
    screen.blit(inst, (10, WINDOW_HEIGHT - 30))
    
    # Draw click instruction
    click_inst = font.render("Left Click on sprite to print coordinates", True, (150, 150, 255))
    screen.blit(click_inst, (10, WINDOW_HEIGHT - 50))
    
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
print("\nViewer closed.")
