import pygame
import os
from .config import WINDOW_WIDTH, WINDOW_HEIGHT, BLOCK_SIZE

class BonusLevel:
    def __init__(self, asset_loader):
        self.asset_loader = asset_loader
        self.background = None
        self.coins = [] # List of {'x':x, 'y':y, 'frame':0}
        self.active = False
        
        # Load Background
        try:
            bg_path = asset_loader.config['images']['bonus_bg']
            full_path = os.path.join(asset_loader.base_path, bg_path)
            if os.path.exists(full_path):
                self.background = pygame.image.load(full_path).convert()
                self.background = pygame.transform.scale(self.background, (WINDOW_WIDTH, WINDOW_HEIGHT))
                print(f"[BonusLevel] Background loaded: {bg_path}")
            else:
                print(f"[BonusLevel] BG Missing: {full_path}")
        except Exception as e:
            print(f"[BonusLevel] Error loading BG: {e}")
            
        # Scan Reference for Coins
        self.scan_reference_for_coins()

    def start(self):
        print("[BonusLevel] Starting!")
        self.active = True
        # Reset coins if needed, or keep them collected?
        # For now, let's reset them for replayability
        for coin in self.coins:
            coin['collected'] = False
            coin['anim_timer'] = 0
    
    def scan_reference_for_coins(self):
        """
        Scans level_reference.png for coin-colored pixels to spawn coins.
        Assumes coins are aligned to a 16x16 or 30x30 grid.
        """
        print("[BonusLevel] Scanning reference map...")
        try:
            ref_path = self.asset_loader.config['images']['bonus_ref']
            full_path = os.path.join(self.asset_loader.base_path, ref_path)
            
            if not os.path.exists(full_path):
                print(f"[BonusLevel] Reference map missing: {full_path}")
                return
                
            ref_img = pygame.image.load(full_path)
            w, h = ref_img.get_size()
            
            # Lock surface for faster pixel access
            ref_img.lock()
            
            # Scan strict grid to avoid duplicates
            # Assuming coins are somewhat centered in grid cells
            grid_size = 16 # Adjust based on asset scale
            
            for y in range(0, h, grid_size):
                for x in range(0, w, grid_size):
                    # Check center pixel of the cell
                    cx, cy = x + grid_size//2, y + grid_size//2
                    if cx >= w or cy >= h: continue
                    
                    c = ref_img.get_at((cx, cy))
                    
                    # Gold Color Detection (Tolerance)
                    # Standard Mario Coin Gold is roughly (255, 215, 0) or (252, 216, 168)
                    # We check for high Red/Green and low Blue
                    if c.r > 200 and c.g > 180 and c.b < 100:
                        # Found a coin!
                        self.coins.append({
                            'x': x,
                            'y': y,
                            'frame': 0,
                            'anim_timer': 0,
                            'collected': False
                        })
                        
            ref_img.unlock()
            print(f"[BonusLevel] Scan complete. Found {len(self.coins)} coins.")
            
        except Exception as e:
            print(f"[BonusLevel] Scan failed: {e}")

    def update(self, dt):
        # Animate Coins
        for coin in self.coins:
            if coin['collected']: continue
            coin['anim_timer'] += dt
            if coin['anim_timer'] > 0.15: # 150ms frame time
                coin['anim_timer'] = 0
                coin['frame'] = (coin['frame'] + 1) % 3 # 3 frames defined in json

    def draw(self, surface):
        # Draw BG
        if self.background:
            surface.blit(self.background, (0, 0))
        else:
            surface.fill((20, 0, 40)) # Dark Purple fallback
            
        # Draw Coins (Glowing)
        # We ensure they are drawn brightly
        for coin in self.coins:
            if coin['collected']: continue
            
            # Get sprite frame
            frame_idx = coin['frame'] + 1 # coin_1, coin_2...
            sprite = self.asset_loader.get_sprite('items', f'coin_{frame_idx}', scale=2.0)
            
            if sprite:
                # To simulate "Glow", we can draw a small additive aura or just verify brightness.
                # Since user asked for "full brightness", just blitting is usually enough 
                # unless a global dark filter is active. 
                # If there WAS a filter, we'd need to blit these AFTER the filter.
                # Assuming update() handles the filter, we just draw here.
                
                # Manual scale adjust if needed
                surface.blit(sprite, (coin['x'], coin['y']))
