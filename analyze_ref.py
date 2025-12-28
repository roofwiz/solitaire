import pygame
from collections import Counter

pygame.init()
path = r"C:\Users\eric\React Projects\Mario-Tetris-main\assets\level_reference.png"

try:
    img = pygame.image.load(path)
    w, h = img.get_size()
    
    colors = []
    # Scan a grid
    for y in range(0, h, 10):
        for x in range(0, w, 10):
            c = img.get_at((x, y))
            # Filter out the dark background (Sky)
            if (c.r + c.g + c.b) > 40: 
                # Quantize slightly to group similar colors
                qr = (c.r // 10) * 10
                qg = (c.g // 10) * 10
                qb = (c.b // 10) * 10
                colors.append((qr, qg, qb))
            
    common = Counter(colors).most_common(20)
    print("Most Common Non-Dark Colors (Quantized):")
    for col, count in common:
        print(f"Color {col}: {count} pixels")
        
except Exception as e:
    print(f"Error: {e}")
