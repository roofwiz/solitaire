    def generate_simple_linear_level(self):
        """Create a simple, clear linear path that's easy to follow"""
        print("Creating simple linear path...")
        
        # Clear existing
        self.platforms = []
        self.coins = []
        self.enemies = []
        
        # Get world dimensions
        w, h = 2000, 800
        if self.bg_image: 
            w, h = self.bg_image.get_size()
        
        import random
        
        # 1. STARTING PLATFORM (wide and safe)
        self.platforms.append(pygame.Rect(0, 600, 400, 40))
        self.coins.append({'x': 200, 'y': 550, 'active': True, 'frame': 0})
        
        # 2. CREATE LINEAR PATH - evenly spaced platforms
        current_x = 400
        current_y = 600
        platform_spacing = 150  # Distance between platforms
        
        while current_x < w - 300:
            # Vary height slightly but keep it reachable
            y_variation = random.randint(-60, 60)
            new_y = current_y + y_variation
            new_y = max(200, min(new_y, 650))  # Keep within reasonable bounds
            
            # Create platform
            platform_width = random.randint(120, 200)
            self.platforms.append(pygame.Rect(current_x, new_y, platform_width, 32))
            
            # Add coin on platform
            self.coins.append({'x': current_x + platform_width//2, 'y': new_y - 40, 'active': True, 'frame': 0})
            
            # Occasionally add an enemy
            if random.random() < 0.2 and len(self.enemies) < 5:
                self.enemies.append(SimpleEnemy(current_x + platform_width//2, new_y - 20, 'goomba', self.asset_loader))
            
            current_x += platform_spacing
            current_y = new_y
        
        # 3. FINAL PLATFORM before flagpole (wide and safe)
        final_platform_x = w - 300
        self.platforms.append(pygame.Rect(final_platform_x, 600, 250, 40))
        
        # 4. FLAGPOLE at the end
        end_x = w - 100
        self.flagpole = Flagpole(end_x, 600 - 160, self.asset_loader)
        self.coins.append({'x': end_x - 50, 'y': 550, 'active': True, 'frame': 0})
        
        # 5. GROUND FLOOR (safety net)
        bottom_y = h - 60
        self.platforms.append(pygame.Rect(0, bottom_y, w, 200))
        
        print(f"Created {len(self.platforms)} platforms and {len(self.coins)} coins")
