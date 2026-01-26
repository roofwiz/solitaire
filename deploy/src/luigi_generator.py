import pygame

def generate_luigi_sprites(asset_loader):
    """
    Consumes Red Mario sprites from the AssetLoader and creates Green Luigi versions.
    Injects them back into the AssetLoader's cache.
    """
    print("[LuigiGenerator] Pre-calculating Green Luigi sprites...")
    
    # Map of Mario Actions -> Luigi Actions
    # We will grab 'mario' sprites, recolor them, and save as 'luigi' sprites
    # if 'luigi' sprites point to Red locations in assets.json.
    
    recipies = [
        ('mario', 'stand', 'luigi', 'stand'),
        ('mario', 'walk', 'luigi', 'walk'),
        ('mario', 'walk_1', 'luigi', 'walk_1'),
        ('mario', 'walk_2', 'luigi', 'walk_2'),
        ('mario', 'walk_3', 'luigi', 'walk_3'),
    ]
    
    # Colors to swap
    # Mario Red Palette -> Luigi Green Palette
    swaps = [
        ((181, 49, 32), (16, 148, 0)),    # Main Red -> Green
        ((107, 109, 0), (16, 148, 0)),    # Brownish -> Green
        ((230, 156, 33), (16, 148, 0)),   # Orange -> Green Highlight
        ((103, 58, 63), (16, 148, 0)),    # Dark Red -> Green
        ((227, 9, 0), (0, 200, 0)),       # Pure Red -> Bright Green
    ]
    
    count = 0
    for src_cat, src_name, dst_cat, dst_name in recipies:
        # Load source (Mario)
        scale = 2.0 # Standard game scale
        src_sprite = asset_loader.get_sprite(src_cat, src_name, scale)
        
        if src_sprite:
            # Create copy
            new_sprite = src_sprite.copy()
            
            # Pixel access
            w, h = new_sprite.get_size()
            for x in range(w):
                for y in range(h):
                    c = new_sprite.get_at((x, y))
                    if c.a > 0:
                        for old, new in swaps:
                            dist = abs(c.r - old[0]) + abs(c.g - old[1]) + abs(c.b - old[2])
                            if dist < 60: # Threshold
                                new_sprite.set_at((x, y), pygame.Color(new[0], new[1], new[2], c.a))
                                break
            
            # Inject into cache
            cache_key = f"{dst_cat}:{dst_name}:{scale}"
            asset_loader.sprites[cache_key] = new_sprite
            count += 1
            
    print(f"[LuigiGenerator] Generated {count} Luigi sprites.")
