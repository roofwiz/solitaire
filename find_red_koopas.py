import pygame
import os

pygame.init()
sheet = pygame.image.load(os.path.join('assets', 'marioallsprite.png'))

print("Searching for RED WALKING KOOPAS (Height > 20)...")

def is_reddish(c):
    return c.r > c.g + 20 and c.r > c.b + 20

# Scan potential rows for Red Koopas
# We know Koopas are usually y=240 (Green) or y=320 (Red)
y_start = 310
y_end = 360

found_sprites = []

# Simple blob detector 
visited = set()
for y in range(y_start, y_end):
    for x in range(0, 436):
        if (x, y) in visited: continue
        
        c = sheet.get_at((x, y))
        if c.a > 0: # Non-transparent
            # Check color
            if is_reddish(c):
                # Flood fill bounds
                stack = [(x, y)]
                visited.add((x, y))
                min_x, max_x, min_y, max_y = x, x, y, y
                
                while stack:
                    cx, cy = stack.pop()
                    if cx < min_x: min_x = cx
                    if cx > max_x: max_x = cx
                    if cy < min_y: min_y = cy
                    if cy > max_y: max_y = cy
                    
                    # 4-way neighbors
                    for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < 436 and y_start <= ny < y_end:
                            if (nx, ny) not in visited:
                                nc = sheet.get_at((nx, ny))
                                if nc.a > 0:
                                    visited.add((nx, ny))
                                    stack.append((nx, ny))
                
                w = max_x - min_x + 1
                h = max_y - min_y + 1
                
                # We specifically want TALL sprites (Walking) not shells (Short)
                if w > 10 and h > 20:
                    print(f"FOUND RED WALKER: x={min_x}, y={min_y}, w={w}, h={h}")
                    found_sprites.append((min_x, min_y, w, h))

if not found_sprites:
    print("No tall red sprites found. Checking Green walkers for comparison...")
    # (Checking y=243 area for Green walkers just to verify algorithm works)
