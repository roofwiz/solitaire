
import pygame
import sys
print("Checking pygame...")
try:
    pygame.init()
    print("Pygame init success.")
    screen = pygame.display.set_mode((200, 200))
    print("Display set success.")
    pygame.display.set_caption("Test")
    print("Caption set success.")
    pygame.quit()
    print("Pygame quit success.")
    sys.exit(0)
except Exception as e:
    print(f"FAILED: {e}")
    sys.exit(1)
