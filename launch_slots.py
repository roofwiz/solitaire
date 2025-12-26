import pygame
import sys
import os

# Create a minimal game loop to run the Slot Machine
try:
    from src.slot_machine import SlotMachine
    from asset_loader import init_asset_loader, AssetLoader
except ImportError as e:
    print(f"Import Error: {e}")
    sys.path.append(os.getcwd())
    from src.slot_machine import SlotMachine
    from asset_loader import init_asset_loader, AssetLoader

# Mock SpriteManager for SlotMachine (it expects get_sprite)
class MockSpriteManager:
    def __init__(self, loader):
        self.loader = loader

    def get_sprite(self, cat, name, scale=1.0, scale_factor=None, **kwargs):
        # Support both scale and scale_factor parameters
        actual_scale = scale_factor if scale_factor is not None else scale
        return self.loader.get_sprite(cat, name, scale=actual_scale)

    def get_cloud_image(self, size):
        return self.loader.get_cloud_image(size)

# Constants
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
FPS = 60

def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Mario Tetris - Slot Machine Test")
    clock = pygame.time.Clock()

    # Load Assets
    print("Loading Assets...")
    asset_loader = init_asset_loader('assets.json')
    sprite_manager = MockSpriteManager(asset_loader)
    
    # Init Slots
    print("Initializing Slot Machine...")
    slots = SlotMachine(sprite_manager=sprite_manager)
    
    # Trigger it immediately with bonus spins - this shows the intro animation!
    slots.trigger(spins=5)  # Give 5 free spins with bonus intro
    
    # For quick testing without intro, uncomment these lines:
    # slots.trigger()  # No spins = betting mode
    # slots.spins_remaining = 5
    # slots.state = 'READY_TO_SPIN'
    
    # Mock Button Logic from SlotMachine needs to be injected or we just handle clicks
    # SlotMachine doesn't handle inputs internaly?
    # update_reels etc are internal.
    # Where is input handling? 
    # It seems logic is inside `update` but we need to click "SPIN".
    
    # SlotMachine code check:
    # draw_reels_scaled draws the button.
    # But where is the click?
    # Main game usually handles clicks. 
    # Let's add click handling here.
    
    # We need to manually define the rect for hit testing since it's dynamic
    slots.spin_btn_rect = pygame.Rect(0,0,120,50) # Placeholder
    slots.btn_hover = False

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    slots.handle_click(event.pos)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    # Restart with bonus spins
                    slots.trigger(spins=5)

        # Update
        res = slots.update(dt)

        # Draw
        screen.fill((50, 0, 50)) # Purple BG
        slots.draw(screen)
        
        # Info
        font = pygame.font.SysFont('arial', 20)
        t = font.render(f"SLOT MACHINE TEST - State: {slots.state}", True, (255, 255, 255))
        screen.blit(t, (10, 10))
        
        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
