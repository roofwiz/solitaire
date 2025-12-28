import pygame
import sys

pygame.init()

# Set display mode first
screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption("Coin Sprite Viewer - Click to select")

# Load items-coins.png
img = pygame.image.load('assets/items-coins.png').convert_alpha()

# Resize window to fit image if needed
if img.get_width() < 800 and img.get_height() < 600:
    screen = pygame.display.set_mode((img.get_width(), img.get_height()))

scroll_x, scroll_y = 0, 0
running = True
font = pygame.font.SysFont('Arial', 16)

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            real_x = mx - scroll_x
            real_y = my - scroll_y
            print(f"Clicked coin at: x={real_x}, y={real_y}")
            with open("clicked_sprites.txt", "a") as f:
                f.write(f"Coin: x={real_x}, y={real_y}\n")
    
    keys = pygame.key.get_pressed()
    if keys[pygame.K_w]: scroll_y += 5
    if keys[pygame.K_s]: scroll_y -= 5
    if keys[pygame.K_a]: scroll_x += 5
    if keys[pygame.K_d]: scroll_x -= 5
    
    screen.fill((50, 50, 50))
    screen.blit(img, (scroll_x, scroll_y))
    
    mx, my = pygame.mouse.get_pos()
    pygame.draw.rect(screen, (255, 0, 0), (mx, my, 16, 16), 2)
    
    info = font.render(f"Mouse: {mx-scroll_x},{my-scroll_y} | WASD to scroll | Click to select coin", True, (255, 255, 255))
    pygame.draw.rect(screen, (0, 0, 0), (5, 5, 600, 25))
    screen.blit(info, (10, 10))
    
    pygame.display.flip()

pygame.quit()
