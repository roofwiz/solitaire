"""
Click-based sprite selector - No dragging required!
Click twice to place corners, then adjust with arrow keys
"""
import pygame
import sys

pygame.init()

# Load sprite sheet
spritesheet = pygame.image.load('assets/marioallsprite.png')
sheet_w, sheet_h = spritesheet.get_size()

# Create window
WINDOW_WIDTH = min(1400, sheet_w + 100)
WINDOW_HEIGHT = min(900, sheet_h + 100)
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Click-Select Tool - No Dragging!")

GRID_SIZE = 16
font = pygame.font.Font(None, 20)

# Camera
offset_x = 0
offset_y = 0
zoom = 1.5

# Selection
corner1 = None  # First corner (x, y)
corner2 = None  # Second corner (x, y)
active_corner = 1  # Which corner is being adjusted (1 or 2)

running = True
clock = pygame.time.Clock()

print("=" * 60)
print("CLICK-SELECT SPRITE TOOL")
print("=" * 60)
print("1. Click to place FIRST corner (top-left)")
print("2. Click again to place SECOND corner (bottom-right)")
print("3. Use ARROW KEYS to adjust active corner")
print("4. Press TAB to switch which corner you're adjusting")
print("5. Press ENTER to save selection")
print("6. Press R to reset")
print("=" * 60)

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                mx, my = event.pos
                sheet_x = int((mx - 50 - offset_x) / zoom)
                sheet_y = int((my - 50 - offset_y) / zoom)
                
                if corner1 is None:
                    corner1 = [sheet_x, sheet_y]
                    active_corner = 2
                    print(f"Corner 1 placed at ({sheet_x}, {sheet_y})")
                    print("Now click the opposite corner...")
                elif corner2 is None:
                    corner2 = [sheet_x, sheet_y]
                    print(f"Corner 2 placed at ({sheet_x}, {sheet_y})")
                    print("Use ARROW KEYS to adjust, TAB to switch corners, ENTER to save")
                    
            elif event.button == 4:  # Scroll up
                zoom = min(zoom * 1.1, 5.0)
            elif event.button == 5:  # Scroll down
                zoom = max(zoom / 1.1, 0.3)
        
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            
            # Navigation
            elif event.key == pygame.K_w:
                offset_y += 50
            elif event.key == pygame.K_s:
                offset_y -= 50
            elif event.key == pygame.K_a:
                offset_x += 50
            elif event.key == pygame.K_d:
                offset_x -= 50
            
            # Reset
            elif event.key == pygame.K_r:
                corner1 = None
                corner2 = None
                active_corner = 1
                print("\n--- RESET ---\nClick to place first corner...")
            
            # Switch active corner
            elif event.key == pygame.K_TAB and corner1 and corner2:
                active_corner = 2 if active_corner == 1 else 1
                print(f"Now adjusting Corner {active_corner}")
            
            # Fine-tune active corner
            elif event.key == pygame.K_LEFT:
                if active_corner == 1 and corner1:
                    corner1[0] -= 1
                elif active_corner == 2 and corner2:
                    corner2[0] -= 1
            elif event.key == pygame.K_RIGHT:
                if active_corner == 1 and corner1:
                    corner1[0] += 1
                elif active_corner == 2 and corner2:
                    corner2[0] += 1
            elif event.key == pygame.K_UP:
                if active_corner == 1 and corner1:
                    corner1[1] -= 1
                elif active_corner == 2 and corner2:
                    corner2[1] -= 1
            elif event.key == pygame.K_DOWN:
                if active_corner == 1 and corner1:
                    corner1[1] += 1
                elif active_corner == 2 and corner2:
                    corner2[1] += 1
            
            # Save selection
            elif event.key == pygame.K_RETURN and corner1 and corner2:
                x = min(corner1[0], corner2[0])
                y = min(corner1[1], corner2[1])
                w = abs(corner2[0] - corner1[0])
                h = abs(corner2[1] - corner1[1])
                
                output = f"\n{'='*60}\nSAVED SELECTION:\n"
                output += f'"sprite_name": {{\n'
                output += f'    "x": {x},\n'
                output += f'    "y": {y},\n'
                output += f'    "w": {w},\n'
                output += f'    "h": {h}\n'
                output += f'}}\n{"="*60}\n'
                
                print(output)
                
                # Also save to file
                with open('sprite_coords.txt', 'a') as f:
                    f.write(output)
                print("Saved to sprite_coords.txt!\n")
                

    # Draw
    screen.fill((30, 30, 40))
    
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
    
    # Draw selection box
    if corner1:
        c1_screen_x = 50 + offset_x + int(corner1[0] * zoom)
        c1_screen_y = 50 + offset_y + int(corner1[1] * zoom)
        
        # Draw corner 1
        color1 = (255, 255, 0) if active_corner == 1 else (150, 150, 0)
        pygame.draw.circle(screen, color1, (c1_screen_x, c1_screen_y), 5)
        
        if corner2:
            c2_screen_x = 50 + offset_x + int(corner2[0] * zoom)
            c2_screen_y = 50 + offset_y + int(corner2[1] * zoom)
            
            # Draw corner 2
            color2 = (255, 255, 0) if active_corner == 2 else (150, 150, 0)
            pygame.draw.circle(screen, color2, (c2_screen_x, c2_screen_y), 5)
            
            # Draw rectangle
            x1 = min(c1_screen_x, c2_screen_x)
            y1 = min(c1_screen_y, c2_screen_y)
            w = abs(c2_screen_x - c1_screen_x)
            h = abs(c2_screen_y - c1_screen_y)
            pygame.draw.rect(screen, (0, 255, 0), (x1, y1, w, h), 2)
            
            # Show dimensions
            dim_text = font.render(f"{abs(corner2[0]-corner1[0])}x{abs(corner2[1]-corner1[1])}", 
                                  True, (0, 255, 0))
            screen.blit(dim_text, (x1, y1 - 25))
    
    # Instructions
    if corner1 is None:
        inst = font.render("Click to place FIRST corner (top-left)", True, (255, 255, 0))
    elif corner2 is None:
        inst = font.render("Click to place SECOND corner (bottom-right)", True, (255, 255, 0))
    else:
        inst = font.render(f"Adjusting Corner {active_corner} | TAB:Switch | ARROWS:Move | ENTER:Save | R:Reset", 
                          True, (0, 255, 0))
    screen.blit(inst, (10, WINDOW_HEIGHT - 30))
    
    nav_text = font.render("WASD: Pan view | Scroll: Zoom", True, (150, 150, 150))
    screen.blit(nav_text, (10, WINDOW_HEIGHT - 60))
    
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
print("\nTool closed.")
