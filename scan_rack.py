import pygame
import sys
import os

pygame.init()

try:
    img_path = os.path.join('assets', 'rack_spritesheet.png')
    if not os.path.exists(img_path):
        print(f"Error: {img_path} not found")
        sys.exit()
    img = pygame.image.load(img_path)
except Exception as e:
    print(f"Error loading: {e}")
    sys.exit()

width, height = img.get_size()
visited = set()
rects = []

# BFS to find blobs
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
        
        if w > 2 and h > 2: # Filter noise
            rects.append({'x': min_x, 'y': min_y, 'w': w, 'h': h})

# Sort by size (area) roughly to find chassis
rects.sort(key=lambda r: r['w'] * r['h'], reverse=True)

for i, r in enumerate(rects):
    print(f"Sprite {i}: x={r['x']}, y={r['y']}, w={r['w']}, h={r['h']} - Area: {r['w']*r['h']}")

pygame.quit()
