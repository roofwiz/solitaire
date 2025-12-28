import pygame
import os

def create_assets():
    print("Initializing Pygame...")
    pygame.init()
    
    if not os.path.exists("assets"):
        os.makedirs("assets")

    BLOCK_SIZE = 32
    
    print("Generating block_base.png...")
    # 1. BLOCK_BASE
    s = pygame.Surface((BLOCK_SIZE, BLOCK_SIZE), pygame.SRCALPHA)
    s.fill((255, 255, 255, 255)) # White base
    # Inner border (simulated bevel)
    pygame.draw.rect(s, (200, 200, 200), (2, 2, BLOCK_SIZE-4, BLOCK_SIZE-4), 1)
    pygame.image.save(s, "assets/block_base.png")

    print("Generating block_ghost.png...")
    # 2. BLOCK_GHOST
    s = pygame.Surface((BLOCK_SIZE, BLOCK_SIZE), pygame.SRCALPHA)
    pygame.draw.rect(s, (255, 255, 255), (0, 0, BLOCK_SIZE, BLOCK_SIZE), 2)
    pygame.image.save(s, "assets/block_ghost.png")

    print("Generating block_inactive.png...")
    # 3. BLOCK_INACTIVE
    s = pygame.Surface((BLOCK_SIZE, BLOCK_SIZE), pygame.SRCALPHA)
    white_semi = (255, 255, 255, 150)
    # Corners
    # TL
    pygame.draw.line(s, white_semi, (0,0), (8,0), 2)
    pygame.draw.line(s, white_semi, (0,0), (0,8), 2)
    # TR
    pygame.draw.line(s, white_semi, (BLOCK_SIZE-1,0), (BLOCK_SIZE-9,0), 2)
    pygame.draw.line(s, white_semi, (BLOCK_SIZE-1,0), (BLOCK_SIZE-1,8), 2)
    # BL
    pygame.draw.line(s, white_semi, (0,BLOCK_SIZE-1), (8,BLOCK_SIZE-1), 2)
    pygame.draw.line(s, white_semi, (0,BLOCK_SIZE-1), (0,BLOCK_SIZE-9), 2)
    # BR
    pygame.draw.line(s, white_semi, (BLOCK_SIZE-1,BLOCK_SIZE-1), (BLOCK_SIZE-9,BLOCK_SIZE-1), 2)
    pygame.draw.line(s, white_semi, (BLOCK_SIZE-1,BLOCK_SIZE-1), (BLOCK_SIZE-1,BLOCK_SIZE-9), 2)
    # Crosshatch
    pygame.draw.line(s, (255,255,255,50), (0,0), (BLOCK_SIZE,BLOCK_SIZE), 1)
    pygame.image.save(s, "assets/block_inactive.png")

    print("Generating grid_background.png...")
    # 4. GRID_BACKGROUND
    s = pygame.Surface((BLOCK_SIZE, BLOCK_SIZE), pygame.SRCALPHA)
    s.fill((10, 10, 10, 255))
    pygame.draw.rect(s, (40, 40, 40), (0, 0, BLOCK_SIZE, BLOCK_SIZE), 1)
    pygame.image.save(s, "assets/grid_background.png")

    print("Generating particle_pixel.png...")
    # 5. PARTICLE_PIXEL
    s = pygame.Surface((4, 4), pygame.SRCALPHA)
    s.fill((255, 255, 255, 255))
    pygame.image.save(s, "assets/particle_pixel.png")

    print("Generating scanline_overlay.png...")
    # 6. SCANLINE_OVERLAY
    width, height = 1920, 1080
    s = pygame.Surface((width, height), pygame.SRCALPHA)
    for y in range(0, height, 4):
        pygame.draw.line(s, (0, 0, 0, 100), (0, y), (width, y), 1)
    pygame.image.save(s, "assets/scanline_overlay.png")

    print("--- ASSETS COMPLETE ---")
    pygame.quit()

if __name__ == "__main__":
    create_assets()
