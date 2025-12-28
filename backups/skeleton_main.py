import asyncio
import pygame

async def main():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    print("!!! SKELETON KERNEL ONLINE !!!")
    
    while True:
        screen.fill((255, 0, 0)) # SOLID RED
        pygame.draw.rect(screen, (255, 255, 255), (100, 100, 440, 280)) # WHITE BOX
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return

        pygame.display.flip()
        await asyncio.sleep(0)

asyncio.run(main())
