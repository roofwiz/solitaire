import pygame
import sys
import os

pygame.init()

def scan_file(filename):
    img_path = os.path.join('assets', filename)
    if not os.path.exists(img_path):
        print(f"Error: {img_path} not found")
        return []
    
    img = pygame.image.load(img_path)
    width, height = img.get_size()
    visited = set()
    rects = []

    print(f"Scanning image {filename} ({width}x{height})...")

    for y in range(height):
        for x in range(width):
            if (x, y) in visited: continue
            
            color = img.get_at((x, y))
            if color.a == 0: 
                visited.add((x, y))
                continue
                
            min_x, max_x = x, x
            min_y, max_y = y, y
            stack = [(x, y)]
            visited.add((x, y))
            
            while stack:
                cx, cy = stack.pop()
                min_x = min(min_x, cx)
                max_x = max(max_x, cx)
                min_y = min(min_y, cy)
                max_y = max(max_y, cy)
                
                for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < width and 0 <= ny < height:
                        if (nx, ny) not in visited:
                            n_color = img.get_at((nx, ny))
                            if n_color.a > 0:
                                 visited.add((nx, ny))
                                 stack.append((nx, ny))

            w = max_x - min_x + 1
            h = max_y - min_y + 1
            if w >= 4 and h >= 4: # Lower threshold for small items/text
                rects.append({'x': min_x, 'y': min_y, 'w': w, 'h': h})
    
    return rects

results = {}
for f in ['items-coins.png', 'blocks.png']:
    results[f] = scan_file(f)

with open('new_sprites_found.txt', 'w') as f:
    for filename, rects in results.items():
        f.write(f"--- {filename} ---\n")
        for r in rects:
            f.write(f"Sprite: x={r['x']}, y={r['y']}, w={r['w']}, h={r['h']}\n")

pygame.quit()
