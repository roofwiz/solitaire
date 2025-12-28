import pygame
import os

pygame.init()

try:
    sheet = pygame.image.load(os.path.join('assets', 'marioallsprite.png'))
    width, height = sheet.get_size()
    print(f"Loaded sheet: {width}x{height}")

    def get_dominant_color(x, y, w, h):
        r_tot, g_tot, b_tot, count = 0, 0, 0, 0
        for i in range(w):
            for j in range(h):
                c = sheet.get_at((x + i, y + j))
                if c.a > 0: # If not transparent
                    r_tot += c.r
                    g_tot += c.g
                    b_tot += c.b
                    count += 1
        if count == 0: return (0,0,0)
        return (r_tot//count, g_tot//count, b_tot//count)

    # 1. Check Mario's Location (Known Red)
    mario_color = get_dominant_color(170, 40, 16, 32)
    print(f"Mario Color (at 170,40): {mario_color} - {'RED-ish' if mario_color[0] > mario_color[1] else 'GREEN-ish'}")

    # 2. Check Candidate Luigi Location (Row 160)
    luigi_cand_color = get_dominant_color(168, 159, 16, 31)
    print(f"Potential Luigi Color (at 168,159): {luigi_cand_color} - {'RED-ish' if luigi_cand_color[0] > luigi_cand_color[1] else 'GREEN-ish'}")

    # 3. Check Red Koopa Area
    # Let's scan row y=320-330 for Red vs Green turtles
    print("\nScanning for Red Koopas (Row y=320-330)...")
    found_reds = []
    
    # Simple scan of chunks
    for x in range(0, 400, 20):
        # Sample a clearer spot
        c = get_dominant_color(x+4, 325, 8, 8) 
        if c == (0,0,0): continue
        
        is_red = c[0] > c[1] and c[0] > 50
        print(f"  x={x}: {c} {'(RED!)' if is_red else ''}")
        if is_red:
             found_reds.append(x)

except Exception as e:
    print(f"Error: {e}")
