"""
Click tracker - saves coordinates to a file
"""
import pygame
import sys
import json

pygame.init()

# Load sprite sheet
spritesheet = pygame.image.load('assets/marioallsprite.png')
sheet_w, sheet_h = spritesheet.get_size()

# Create window
WINDOW_WIDTH = min(1400, sheet_w + 200)
WINDOW_HEIGHT = min(900, sheet_h + 200)
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Click to Save Coordinates to File")

font = pygame.font.Font(None, 20)
offset_x, offset_y = 0, 0
zoom = 1.5
clicks = []

print("=" * 60)
print("CLICK TRACKER - Coordinates saved to 'clicked_coords.txt'")
print("=" * 60)
print("Left click on sprites, then check clicked_coords.txt")
print("=" * 60)

running = True
clock = pygame.time.Clock()
dragging = False
last_pos = None

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_c:
                clicks = []
                print("Cleared all clicks!")
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                mx, my = event.pos
                sheet_x = int((mx - 100 - offset_x) / zoom)
                sheet_y = int((my - 100 - offset_y) / zoom)
                
                click_data = {
                    "click_number": len(clicks) + 1,
                    "x": sheet_x,
                    "y": sheet_y
                }
                clicks.append(click_data)
                
                # Save to file
                with open('clicked_coords.txt', 'w') as f:
                    f.write("CLICKED COORDINATES\n")
                    f.write("=" * 60 + "\n\n")
                    for c in clicks:
                        f.write(f"Click #{c['click_number']}:\n")
                        f.write(f'  "x": {c["x"]},\n')
                        f.write(f'  "y": {c["y"]},\n')
                        f.write(f'  "w": 16,  // Standard sprite width\n')
                        f.write(f'  "h": 16   // Adjust if needed\n')
                        f.write("\n")
                
                print(f"Click #{len(clicks)}: ({sheet_x}, {sheet_y}) - Saved to file!")
                
            elif event.button == 3:  # Right click
                dragging = True
                last_pos = event.pos
            elif event.button == 4:
                zoom = min(zoom * 1.1, 5.0)
            elif event.button == 5:
                zoom = max(zoom / 1.1, 0.3)
        
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
    
    # Draw sprite sheet
    scaled_w = int(sheet_w * zoom)
    scaled_h = int(sheet_h * zoom)
    scaled_sheet = pygame.transform.scale(spritesheet, (scaled_w, scaled_h))
    screen.blit(scaled_sheet, (100 + offset_x, 100 + offset_y))
    
    # Draw clicked points
    for c in clicks:
        sx = 100 + offset_x + int(c['x'] * zoom)
        sy = 100 + offset_y + int(c['y'] * zoom)
        pygame.draw.circle(screen, (255, 0, 0), (sx, sy), 5)
        num_text = font.render(str(c['click_number']), True, (255, 255, 0))
        screen.blit(num_text, (sx + 10, sy - 10))
    
    # Instructions
    inst = font.render(f"Clicks: {len(clicks)} | Zoom: {zoom:.1f}x | C: Clear | ESC: Exit", True, (200, 200, 200))
    screen.blit(inst, (10, WINDOW_HEIGHT - 30))
    
    file_inst = font.render("Coordinates saved to: clicked_coords.txt", True, (100, 255, 100))
    screen.blit(file_inst, (10, WINDOW_HEIGHT - 60))
    
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
print(f"\nTotal clicks: {len(clicks)}")
print("Check 'clicked_coords.txt' for all coordinates!")
