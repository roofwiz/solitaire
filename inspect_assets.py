import pygame
import os

pygame.init()

def inspect_image(filename):
    path = os.path.join('assets', filename)
    if not os.path.exists(path):
        print(f"{filename} not found")
        return
    img = pygame.image.load(path)
    w, h = img.get_size()
    print(f"--- {filename} ({w}x{h}) ---")
    # Check some points to see if it's a grid
    for y in [0, 8, 16, 24, 32]:
        row = ""
        for x in [0, 8, 16, 24, 32, 48, 64, 80]:
            if x < w and y < h:
                c = img.get_at((x, y))
                row += f"({c.r},{c.g},{c.b},{c.a}) "
            else:
                row += "MISS "
        print(f"y={y:2}: {row}")

inspect_image('items-coins.png')
inspect_image('blocks.png')
pygame.quit()
