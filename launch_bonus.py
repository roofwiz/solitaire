import pygame
import sys
import os

# Create a minimal game loop to just run the BonusLevel
try:
    from src.bonus_level import BonusLevel
    from asset_loader import init_asset_loader
except ImportError as e:
    print(f"Import Error: {e}")
    # Add root to path
    sys.path.append(os.getcwd())
    from src.bonus_level import BonusLevel
    from asset_loader import init_asset_loader

# Constants from config (matching src.config)
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 900
FPS = 60

def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Mario Tetris - Bonus Level Test")
    clock = pygame.time.Clock()

    # Init Assets
    print("Loading Assets...")
    asset_loader = init_asset_loader('assets.json')
    
    # Init Bonus Level
    print("Initializing Bonus Level...")
    bonus = BonusLevel(asset_loader)
    
    # Start it
    bonus.start()
    
    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    # Reset
                    bonus.start()

        # Update
        bonus.update(dt)
        
        # Draw
        screen.fill((0,0,0))
        bonus.draw(screen)
        
        # Info Text
        font = pygame.font.SysFont('arial', 20)
        t = font.render("BONUS LEVEL TEST - Press R to Reset", True, (255, 255, 255))
        screen.blit(t, (10, 10))
        
        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
