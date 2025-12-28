import pygame
import sys
import os

pygame.init()

# Load Image
try:
    img_path = os.path.join('assets', 'marioallsprite.png')
    if not os.path.exists(img_path):
        print(f"Error: {img_path} not found")
        sys.exit()
    img = pygame.image.load(img_path)
    # Don't convert alpha yet, just get pixel access
except Exception as e:
    print(f"Error loading: {e}")
    sys.exit()

width, height = img.get_size()
visited = set()
rects = []

print(f"Scanning image {width}x{height}...")

# BFS/Flood Fill to find blobs
for y in range(height):
    for x in range(width):
        if (x, y) in visited: continue
        
        color = img.get_at((x, y))
        # Assuming transparent is (0,0,0,0) or some key color. 
        # Usually PNG uses alpha channel.
        if color.a == 0: 
            visited.add((x, y))
            continue
            
        # Found a non-transparent pixel, flood fill to find bounds
        min_x, max_x = x, x
        min_y, max_y = y, y
        stack = [(x, y)]
        visited.add((x, y))
        pixel_count = 0
        
        while stack:
            cx, cy = stack.pop()
            pixel_count += 1
            
            min_x = min(min_x, cx)
            max_x = max(max_x, cx)
            min_y = min(min_y, cy)
            max_y = max(max_y, cy)
            
            # Check neighbors
            for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < width and 0 <= ny < height:
                    if (nx, ny) not in visited:
                        n_color = img.get_at((nx, ny))
                        if n_color.a > 0: # Non-transparent
                             visited.add((nx, ny))
                             stack.append((nx, ny))

        # Check if blob is big enough to be a sprite
        w = max_x - min_x + 1
        h = max_y - min_y + 1
        
        if w > 8 and h > 8: # Filter small noise
            rects.append({'x': min_x, 'y': min_y, 'w': w, 'h': h})

print(f"Found {len(rects)} potential sprites.")
with open('found_sprites.txt', 'w') as f:
    for r in rects:
        line = f"Sprite: x={r['x']}, y={r['y']}, w={r['w']}, h={r['h']}\n"
        print(line.strip())
        f.write(line)

pygame.quit()
