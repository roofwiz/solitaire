
import pygame
import sys
import os

# bare minimum to see if window opens
print("V44 Starting...")
pygame.init()
try: pygame.mixer.quit()
except: pass
print("Pygame inited.")
screen = pygame.display.set_mode((400, 300))
pygame.display.set_caption("V44 Minimal Test")
print("Window created.")

font = pygame.font.SysFont("Arial", 20)

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
    screen.fill((50, 50, 80))
    txt = font.render("V44 Minimal - Window Loaded!", True, (255, 255, 255))
    screen.blit(txt, (50, 100))
    pygame.display.flip()
    pygame.time.Clock().tick(60)

pygame.quit()
print("V44 Exit.")
