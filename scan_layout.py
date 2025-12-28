import pygame

pygame.init()
path = r"C:\Users\eric\React Projects\Mario-Tetris-main\assets\level_reference.png"

try:
    img = pygame.image.load(path)
    w, h = img.get_size()
    print(f"Scanning {w}x{h} image for platforms...")
    
    # Threshold for "Solid"
    # Assuming Ground is Brighter than Sky (Sky ~ (18,14,2))
    def is_solid(c):
        return (c.r + c.g + c.b) > 40

    platforms = []
    
    # Scan horizontal strips (Grid size 20px)
    for y in range(0, h, 20):
        start_x = -1
        for x in range(0, w, 10):
            c = img.get_at((x, y))
            solid = is_solid(c)
            
            if solid and start_x == -1:
                start_x = x
            elif not solid and start_x != -1:
                # Found a run
                width = x - start_x
                if width > 50: # Ignore small noise
                    platforms.append((start_x, y, width))
                start_x = -1
                
        # Close run at end
        if start_x != -1:
            width = w - start_x
            if width > 50:
                 platforms.append((start_x, y, width))

    # Group close Ys?
    # Simple print first
    print(f"Found {len(platforms)} potential platform segments.")
    for p in platforms[:20]: # Print first 20
        print(f"Platform: x={p[0]}, y={p[1]}, w={p[2]}")
        
except Exception as e:
    print(f"Error: {e}")
