import pygame
import sys
import os
pygame.init()
try:
    from src.slot_machine import SlotMachine
    print("Import successful")
    s = SlotMachine()
    print("Init successful")
    s.trigger()
    print("Trigger successful")
    s.update(0.1)
    print("Update successful")
    surface = pygame.Surface((800, 600))
    s.draw(surface)
    print("Draw successful")
except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()
