import pygame
import sys

pygame.init()

# Load the main sprite sheet
spritesheet = pygame.image.load('assets/marioallsprite.png')
sheet_w, sheet_h = spritesheet.get_size()

# Create window
WINDOW_WIDTH = min(1400, sheet_w + 100)
WINDOW_HEIGHT = min(900, sheet_h + 100)
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Sprite Sheet Scanner - Click to get coordinates")

# Grid settings
GRID_SIZE = 16  # Most sprites are 16x16 or multiples
font = pygame.font.Font(None, 20)
small_font = pygame.font.Font(None, 14)

# Camera offset for panning
offset_x = 0
offset_y = 0
zoom = 1.0

# Selection rectangle
selection_start = None
selection_end = None

running = True
clock = pygame.time.Clock()
dragging = False
last_mouse_pos = None

print("=" * 60)
print("SPRITE SHEET SCANNER")
print("=" * 60)
print("Controls:")
print("  - LEFT CLICK: Start selection rectangle")
print("  - DRAG: Create selection area")
print("  - RIGHT CLICK + DRAG: Pan the view")
print("  - MOUSE WHEEL: Zoom in/out")
print("  - SPACE: Print current selection to console")
print("=" * 60)

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            
            if event.button == 1:  # Left click - start selection
                # Convert screen coords to sheet coords
                sheet_x = int((mx - 50 - offset_x) / zoom)
                sheet_y = int((my - 50 - offset_y) / zoom)
                selection_start = (sheet_x, sheet_y)
                selection_end = None
                
            elif event.button == 3:  # Right click - start pan
                dragging = True
                last_mouse_pos = event.pos
                
            elif event.button == 4:  # Scroll up - zoom in
                zoom = min(zoom * 1.2, 5.0)
                
            elif event.button == 5:  # Scroll down - zoom out
                zoom = max(zoom / 1.2, 0.5)
        
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1 and selection_start:  # End selection
                mx, my = event.pos
                sheet_x = int((mx - 50 - offset_x) / zoom)
                sheet_y = int((my - 50 - offset_y) / zoom)
                selection_end = (sheet_x, sheet_y)
                
                # Print selection
                x1, y1 = selection_start
                x2, y2 = selection_end
                x = min(x1, x2)
                y = min(y1, y2)
                w = abs(x2 - x1)
                h = abs(y2 - y1)
                
                print(f"\n--- SELECTION ---")
                print(f'"sprite_name": {{')
                print(f'    "x": {x},')
                print(f'    "y": {y},')
                print(f'    "w": {w},')
                print(f'    "h": {h}')
                print(f'}}')
                print(f"Grid position: ({x//GRID_SIZE}, {y//GRID_SIZE})")
                
            elif event.button == 3:
                dragging = False
        
        elif event.type == pygame.MOUSEMOTION:
            if dragging and last_mouse_pos:
                dx = event.pos[0] - last_mouse_pos[0]
                dy = event.pos[1] - last_mouse_pos[1]
                offset_x += dx
                offset_y += dy
                last_mouse_pos = event.pos
            
            elif selection_start and not selection_end:
                # Update selection preview
                mx, my = event.pos
                sheet_x = int((mx - 50 - offset_x) / zoom)
                sheet_y = int((my - 50 - offset_y) / zoom)
                selection_end = (sheet_x, sheet_y)
        
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_SPACE and selection_start and selection_end:
                # Print again
                x1, y1 = selection_start
                x2, y2 = selection_end
                x = min(x1, x2)
                y = min(y1, y2)
                w = abs(x2 - x1)
                h = abs(y2 - y1)
                print(f"\n--- COPIED TO CLIPBOARD (manually copy above) ---")
            # Arrow key panning
            elif event.key == pygame.K_LEFT:
                offset_x += 50
            elif event.key == pygame.K_RIGHT:
                offset_x -= 50
            elif event.key == pygame.K_UP:
                offset_y += 50
            elif event.key == pygame.K_DOWN:
                offset_y -= 50
            # Faster panning with Shift
            elif event.key == pygame.K_a:  # Shift+Left alternative
                offset_x += 100
            elif event.key == pygame.K_d:  # Shift+Right alternative
                offset_x -= 100
            elif event.key == pygame.K_w:  # Shift+Up alternative
                offset_y += 100
            elif event.key == pygame.K_s:  # Shift+Down alternative
                offset_y -= 100
    
    # Draw
    screen.fill((40, 40, 50))
    
    # Draw sprite sheet
    scaled_w = int(sheet_w * zoom)
    scaled_h = int(sheet_h * zoom)
    scaled_sheet = pygame.transform.scale(spritesheet, (scaled_w, scaled_h))
    screen.blit(scaled_sheet, (50 + offset_x, 50 + offset_y))
    
    # Draw grid
    for x in range(0, scaled_w, int(GRID_SIZE * zoom)):
        pygame.draw.line(screen, (60, 60, 70), 
                        (50 + offset_x + x, 50 + offset_y), 
                        (50 + offset_x + x, 50 + offset_y + scaled_h))
    for y in range(0, scaled_h, int(GRID_SIZE * zoom)):
        pygame.draw.line(screen, (60, 60, 70), 
                        (50 + offset_x, 50 + offset_y + y), 
                        (50 + offset_x + scaled_w, 50 + offset_y + y))
    
    # Draw coordinate labels every 5 grid cells
    for i in range(0, sheet_w, GRID_SIZE * 5):
        x_screen = 50 + offset_x + int(i * zoom)
        if 0 < x_screen < WINDOW_WIDTH:
            label = small_font.render(str(i), True, (200, 200, 200))
            screen.blit(label, (x_screen, 30))
            
    for i in range(0, sheet_h, GRID_SIZE * 5):
        y_screen = 50 + offset_y + int(i * zoom)
        if 0 < y_screen < WINDOW_HEIGHT:
            label = small_font.render(str(i), True, (200, 200, 200))
            screen.blit(label, (10, y_screen))
    
    # Draw selection rectangle
    if selection_start and selection_end:
        x1, y1 = selection_start
        x2, y2 = selection_end
        
        sx1 = 50 + offset_x + int(x1 * zoom)
        sy1 = 50 + offset_y + int(y1 * zoom)
        sx2 = 50 + offset_x + int(x2 * zoom)
        sy2 = 50 + offset_y + int(y2 * zoom)
        
        rect = pygame.Rect(min(sx1, sx2), min(sy1, sy2), abs(sx2-sx1), abs(sy2-sy1))
        pygame.draw.rect(screen, (255, 255, 0), rect, 2)
        
        # Show dimensions
        w = abs(x2 - x1)
        h = abs(y2 - y1)
        dim_text = font.render(f"{w}x{h}", True, (255, 255, 0))
        screen.blit(dim_text, (rect.centerx - 20, rect.top - 25))
    
    # Instructions
    text = font.render("Left Click+Drag: Select | Right Click+Drag: Pan | Scroll: Zoom", True, (200, 200, 200))
    screen.blit(text, (10, WINDOW_HEIGHT - 30))
    
    zoom_text = small_font.render(f"Zoom: {zoom:.1f}x", True, (150, 150, 150))
    screen.blit(zoom_text, (WINDOW_WIDTH - 100, WINDOW_HEIGHT - 30))
    
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
print("\nScanner closed.")
