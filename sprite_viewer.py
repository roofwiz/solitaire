import pygame
import sys
import os

# Initialize Pygame
pygame.init()

# Screen dimensions (adjustable if sheet is huge)
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Sprite Finder Tool")

# Colors
BG_COLOR = (50, 50, 50)
BOX_COLOR = (255, 0, 0) # Red box
TEXT_COLOR = (255, 255, 255)

# Font
font = pygame.font.SysFont('Arial', 18)

# Load Image - MAIN SPRITE SHEET
SCALE = 1  # NO ZOOM - Exact coordinates
try:
    img_path = os.path.join('assets', 'marioallsprite.png')
    if not os.path.exists(img_path):
        print(f"Error: Could not find {img_path}")
        sys.exit()
    original_img = pygame.image.load(img_path).convert_alpha()
    # Scale up for visibility
    scaled_w = original_img.get_width() * SCALE
    scaled_h = original_img.get_height() * SCALE
    original_img = pygame.transform.scale(original_img, (scaled_w, scaled_h))
    print(f"Image loaded: {img_path} (scaled {SCALE}x)")
except Exception as e:
    print(f"Error loading image: {e}")
    sys.exit()

# Variables
scroll_x = 0
scroll_y = 0
box_w = 16
box_h = 24
move_speed = 10

running = True
clock = pygame.time.Clock()

while running:
    # Events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        # Resize Box
        if event.type == pygame.KEYDOWN:
            mods = pygame.key.get_mods()
            amount = 5 if (mods & pygame.KMOD_SHIFT) else 1
            
            if event.key == pygame.K_RIGHT: box_w += amount
            if event.key == pygame.K_LEFT: box_w = max(1, box_w - amount)
            if event.key == pygame.K_DOWN: box_h += amount
            if event.key == pygame.K_UP: box_h = max(1, box_h - amount)
            
        # Print on click
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                # Note: camera_x, camera_y, and SCALE are not defined in the original code.
                # This will cause a NameError if not defined elsewhere.
                # Assuming for the purpose of this edit that they would be defined.
                # For now, using existing scroll_x, scroll_y and a dummy SCALE=1 for compilation.
                # If SCALE is intended to be different, it needs to be defined.
                # If camera_x/y are different from scroll_x/y, they need to be defined.
                camera_x = scroll_x # Placeholder
                camera_y = scroll_y # Placeholder
                SCALE = 1 # Placeholder
                
                scroll_x_scaled = (camera_x // SCALE) * SCALE
                scroll_y_scaled = (camera_y // SCALE) * SCALE
                
                real_x = (event.pos[0] + scroll_x_scaled) // SCALE
                real_y = (event.pos[1] + scroll_y_scaled) // SCALE
                
                msg = f"Clicked: x={real_x}, y={real_y}\n"
                print(msg.strip())
                with open("clicked_sprites.txt", "a") as f:
                    f.write(msg)
                
                # Optional: Draw a marker temporarily (not persistent in loop)ssume non-snapped for manual find)
            
            # Show real sprite sheet coordinates (divide by scale)
            mx, my = pygame.mouse.get_pos()
            real_x_original = (mx - scroll_x) // SCALE
            real_y_original = (my - scroll_y) // SCALE
            print(f"SPRITE FOUND: 'x': {real_x_original}, 'y': {real_y_original}, 'w': 16, 'h': 16")
            print("-" * 30)

    # Input for scrolling
    keys = pygame.key.get_pressed()
    if keys[pygame.K_w]: scroll_y += move_speed
    if keys[pygame.K_s]: scroll_y -= move_speed
    if keys[pygame.K_a]: scroll_x += move_speed
    if keys[pygame.K_d]: scroll_x -= move_speed
    
    # Clamp Scroll
    # scroll_x = min(0, max(scroll_x, SCREEN_WIDTH - original_img.get_width()))
    # scroll_y = min(0, max(scroll_y, SCREEN_HEIGHT - original_img.get_height()))

    # Draw
    screen.fill(BG_COLOR)
    
    # Draw Image at scroll position
    screen.blit(original_img, (scroll_x, scroll_y))
    
    # Draw Mouse Box
    mx, my = pygame.mouse.get_pos()
    pygame.draw.rect(screen, BOX_COLOR, (mx, my, box_w, box_h), 1)
    
    # Draw UI
    info_text = f"Mouse: {mx-scroll_x},{my-scroll_y} | Box: {box_w}x{box_h} | Scroll: WASD | Resize: Arrows (+Shift for fast)"
    text_surf = font.render(info_text, True, TEXT_COLOR)
    pygame.draw.rect(screen, (0,0,0), (0, 0, SCREEN_WIDTH, 30))
    screen.blit(text_surf, (10, 5))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
