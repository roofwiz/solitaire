import pygame
import random
import math
try:
    from src.config import WINDOW_WIDTH, WINDOW_HEIGHT
except ImportError:
    WINDOW_WIDTH = 800
    WINDOW_HEIGHT = 600

class SlotMachine:
    def __init__(self, sprite_manager=None, sound_manager=None):
        self.sprite_manager = sprite_manager
        self.sound_manager = sound_manager
        self.active = False
        
        # Dimensions
        self.width = 600
        self.height = 500 # Taller for 3 rows + UI
        self.x = (WINDOW_WIDTH - self.width) // 2
        self.y = (WINDOW_HEIGHT - self.height) // 2
        
        # Game State
        self.state = 'IDLE' 
        self.spins_remaining = 0
        self.total_coins = 500 # Starting coins
        
        # Betting
        self.bet_amount = 3 # 3 Coins per line
        self.lines_bet = 3 # Max Lines (5 Rows/Paylines)
        # Mapping: 1 = Middle, 2 = Top+Bot+Mid (3 lines), 3 = +Diagonals (5 lines)? 
        # User asked for "bet 1,2,3 rows". Let's do:
        # 1: Middle Row (1 Line)
        # 2: Top, Middle, Bottom (3 Lines) - "3 rows"
        # 3: T, M, B + Diagonals (5 Lines) - "Max Bet"
        
        # Symbols & Reels (Removed fillers to improve odds)
        self.symbols = ['jackpot', 'wild', 'mario', 'luigi', 'star', 'mushroom', 'flower', 'coin']
        
        # Normal Weights (More balanced, better odds)
        self.normal_weights = [5, 8, 15, 15, 12, 12, 15, 18]
        
        # BONUS Weights (Free Spins) - Very generous!
        self.bonus_weights = [10, 60, 15, 15, 15, 15, 10, 5] 
        self.weights = self.normal_weights
        
        # Reel Strips (Simulated by just random choice, but we track 'center' index)
        # We need 3 visible rows. 
        self.reel_positions = [0, 0, 0] # Index of the CENTER symbol
        self.reel_state = [0, 0, 0] # 1=Spinning
        self.stop_timers = [0, 0, 0]
        self.reel_bounce_y = [0.0, 0.0, 0.0]
        
        # Win Visuals
        self.winning_lines = [] # List of tuples [(line_idx, amount, [col_indices])]
        # Line Indices: 0=Top, 1=Mid, 2=Bot, 3=DiagTL-BR, 4=DiagBL-TR
        
        # Jackpots
        self.progressive_jackpot = 10000.0
        self.grand_prizes = {
            'MINI': 1000,
            'MAJOR': 5000,
            'GRAND': 25000
        }
        
        # Visuals
        self.particles = [] 
        self.msg = ""
        self.msg_timer = 0
        self.shake_offset = (0,0)
        self.zoom_factor = 1.0
        self.glow_timer = 0.0  # For button glow animation
        
        # Win Celebration State
        self.win_amount = 0
        self.win_flash_timer = 0
        self.win_scale = 1.0
        self.shake_intensity = 0
        
        # Win Announcements (track each spin result)
        self.win_log = []  # List of {spin: #, amount: #, symbols: 'xxx'}
        self.current_spin_number = 0
        self.total_spins_awarded = 0
        
        # Bonus Intro Animation
        self.intro_timer = 0
        self.intro_phase = 0  # 0=none, 1=zooming, 2=text
        
        # Buttons Rects (calculated in draw)
        self.btn_spin = None
        self.btn_bet_up = None
        self.btn_bet_down = None
        self.btn_lines = None # Toggle
        self.btn_back = None # Back to game
        
        # Courier Logic
        self.courier_active = False
        self.courier_type = 'lakitu'
        self.courier_x = -100
        self.courier_y = 100
        self.courier_msg = ""
        self.courier_timer = 0
        
        # Fonts
        self.font_big = pygame.font.SysFont('arial black', 36, bold=True)
        self.font_med = pygame.font.SysFont('arial', 24, bold=True)
        self.font_small = pygame.font.SysFont('arial', 16, bold=True)
        self.font_lcd = pygame.font.SysFont('consolas', 20, bold=True)

        # Load Assets
        self.images = {}
        self.courier_imgs = {}
        self._load_assets()

    def _load_assets(self):
        if self.sprite_manager:
            mapping = {
                'jackpot': ('blocks', 'question_3'),
                'wild': ('blocks', 'question_1'),
                'mario': ('mario', 'stand'),
                'luigi': ('koopa_green', 'walk_1'), # Keep Koopa as Luigi for now (reliable asset)
                'star': ('items', 'star_1'), # Using star items
                'mushroom': ('items', 'mushroom_super'),
                'flower': ('items', 'flower_fire'),
                'coin': ('items', 'coin_1') # Try to load actual coin
            }
            for key, (cat, name) in mapping.items():
                img = self.sprite_manager.get_sprite(cat, name, scale_factor=3.0) 
                if img: 
                    self.images[key] = pygame.transform.scale(img, (50, 50)) # Smaller for 3x3
                    
                    # Add WILD text overlay
                    if key == 'wild':
                        f_wild = pygame.font.SysFont('arial black', 14, bold=True)
                        txt = f_wild.render("WILD", True, (255, 0, 0))
                        shd = f_wild.render("WILD", True, (255, 255, 255))
                        # Centered
                        cx, cy = 25, 25
                        self.images[key].blit(shd, (cx - txt.get_width()//2 + 1, cy - txt.get_height()//2 + 1))
                        self.images[key].blit(txt, (cx - txt.get_width()//2, cy - txt.get_height()//2))

                    print(f"[Slot] Loaded symbol: {key}")
                else:
                    print(f"[Slot] FAILED to load symbol: {key} ({cat}/{name})")
            
            # Courier
            self.courier_imgs['lakitu'] = self.sprite_manager.get_sprite('lakitu', 'default', scale_factor=2.0)
            self.courier_imgs['cloud'] = self.sprite_manager.get_cloud_image((64, 48))
            self.courier_imgs['flying_koopa'] = self.sprite_manager.get_sprite('koopa_green', 'fly_1', scale_factor=2.5)
            self.courier_imgs['shell'] = self.sprite_manager.get_sprite('koopa_green', 'shell_1', scale_factor=3.0)
            self.courier_imgs['spiny'] = self.sprite_manager.get_sprite('spiny', 'walk_1', scale_factor=2.5)

    def trigger(self, spins=0):
        self.active = True
        self.session_winnings = 0  # Track total won this session
        self.show_total_timer = 0  # Timer for showing grand total
        self.win_log = []  # Clear win history
        self.current_spin_number = 0
        
        if spins > 0:
            self.spins_remaining += spins
            self.total_spins_awarded = spins
            # Use BONUS weights for free spins - player-favorable odds!
            self.weights = self.bonus_weights
            # Start with intro animation
            self.state = 'BONUS_INTRO'
            self.intro_timer = 2.5  # 2.5 second intro
            self.intro_phase = 1
            self.msg = ""
            if self.sound_manager: 
                self.sound_manager.play('level_up')  # Exciting sound!
        else:
            self.weights = self.normal_weights
            self.state = 'READY_TO_SPIN'
            self.msg = "PLACE YOUR BETS!"
        
    def handle_input(self, event):
        """Handle pygame events - called by main.py"""
        if not self.active: return
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.handle_click(event.pos)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.active = False
                self.state = 'IDLE'
        
    def handle_click(self, pos):
        if not self.active: return
        
        # Back button - always check (works in any state)
        if self.btn_back and self.btn_back.collidepoint(pos):
            self.active = False
            self.state = 'IDLE'
            return
        
        # Check Buttons
        if self.state == 'READY_TO_SPIN':
            if self.btn_spin and self.btn_spin.collidepoint(pos):
                self.start_spin()
            elif self.btn_bet_up and self.btn_bet_up.collidepoint(pos):
                self.bet_amount = min(100, self.bet_amount + 10)
                if self.sound_manager: self.sound_manager.play('move')
            elif self.btn_bet_down and self.btn_bet_down.collidepoint(pos):
                self.bet_amount = max(10, self.bet_amount - 10)
                if self.sound_manager: self.sound_manager.play('move')
            elif self.btn_lines and self.btn_lines.collidepoint(pos):
                # Cycle 1 -> 2 -> 3
                self.lines_bet = (self.lines_bet % 3) + 1
                if self.sound_manager: self.sound_manager.play('move')
                
    def start_spin(self):
        cost = self._get_total_bet()
        is_free_spin = False
        
        if self.spins_remaining > 0:
            self.spins_remaining -= 1
            is_free_spin = True
            # Keep using bonus weights during free spins
            self.weights = self.bonus_weights
        elif self.total_coins >= cost:
            self.total_coins -= cost
            self.progressive_jackpot += cost * 0.1 # Add to pot
            # Normal weights when paying
            self.weights = self.normal_weights
        else:
            self.msg = "OUT OF COINS!"
            return
        
        self.current_spin_number += 1
        self.state = 'REEL_SPIN'
        self.stop_timers = [0.3, 0.6, 0.9] # Faster spins
        self.reel_state = [1, 1, 1]
        self.winning_lines = []
        self.spin_elapsed = 0
        if self.sound_manager: self.sound_manager.play('slot_spin')
        
        if is_free_spin:
            remaining = self.spins_remaining
            self.msg = f"FREE SPIN #{self.current_spin_number}!"

    def _get_total_bet(self):
        # 1 Row = 1 Line (Mid) coverage
        # 2 Rows = 3 Lines (Top/Mid/Bot) coverage
        # 3 Rows = 5 Lines (T/M/B + Diags) coverage
        line_count = 1
        if self.lines_bet == 2: line_count = 3
        if self.lines_bet == 3: line_count = 5
        return self.bet_amount * line_count

    def pick_random_multiplier(self):
        r = random.random()
        if r < 0.01: return 100
        if r < 0.03: return 50
        if r < 0.06: return 25
        if r < 0.15: return 10
        if r < 0.30: return 5
        if r < 0.50: return 2
        return 1

    def update(self, dt):
        if not self.active: return None
        
        # SKIP LOGIC (Press Space to instantly finish)
        keys = pygame.key.get_pressed()
        if (keys[pygame.K_SPACE] or keys[pygame.K_RETURN]):
             if self.spins_remaining > 0:
                 self._instant_resolve_spins()
             elif self.state == 'MULTIPLIER_ROLL':
                 self.multiplier_timer = 0 # Finish roll
             elif self.state == 'SHOW_TOTAL':
                 self.show_total_timer = 0 # Finish show
        
        # Center Logic
        sw, sh = getattr(self, 'screen_size', (WINDOW_WIDTH, WINDOW_HEIGHT))
        self.x = (sw - self.width) // 2
        self.y = (sh - self.height) // 2
        
        # Glow animation timer
        self.glow_timer += dt
        
        # Win celebration animations
        if self.win_flash_timer > 0:
            self.win_flash_timer -= dt
            self.win_scale = 1.0 + 0.3 * math.sin(self.glow_timer * 8)  # Pulsing scale
        
        # Shake decay
        if self.shake_intensity > 0:
            self.shake_intensity = max(0, self.shake_intensity - dt * 20)
            self.shake_offset = (
                random.randint(-int(self.shake_intensity), int(self.shake_intensity)),
                random.randint(-int(self.shake_intensity), int(self.shake_intensity))
            )
        else:
            self.shake_offset = (0, 0)

        # Physics (Particles)
        for p in self.particles[:]:
             p['x'] += p['vx'] * dt
             p['y'] += p['vy'] * dt
             p['vy'] += 800 * dt
             if p['y'] > WINDOW_HEIGHT: self.particles.remove(p)
        
        # State Machine
        if self.state == 'BONUS_INTRO':
            self.intro_timer -= dt
            if self.intro_timer <= 1.5:
                self.intro_phase = 2  # Show "BONUS!" text
            if self.intro_timer <= 0:
                self.state = 'READY_TO_SPIN'
                self.msg = f"FREE SPINS: {self.spins_remaining}!"
                # Auto-start first spin for bonus
                self.start_spin()
        elif self.state == 'REEL_SPIN':
            self.update_reels(dt)
        elif self.state in ['WIN_SHOW', 'BIG_WIN']:
            self.msg_timer -= dt
            if self.msg_timer <= 0:
                # Check if we should show grand total (spins exhausted)
                if self.spins_remaining <= 0:
                    # Trigger Multiplier Chance!
                    if self.session_winnings > 0:
                        self.state = 'MULTIPLIER_ROLL'
                        self.multiplier_timer = 1.5 # Fast Multiplier
                        self.msg = "MULTIPLIER CHANCE!"
                        self.temp_mult_display = 1
                    else:
                        self.state = 'SHOW_TOTAL'
                        self.show_total_timer = 2.0 # Fast Total
                        self.msg = "BETTER LUCK NEXT TIME!"
                elif self.spins_remaining > 0:
                    # Auto-continue to next free spin
                    self.start_spin()
        
        elif self.state == 'MULTIPLIER_ROLL':
            self.multiplier_timer -= dt
            
            # Animate numbers
            if self.multiplier_timer > 1.0:
                 # Fast cycle logic
                 if int(self.multiplier_timer * 10) % 2 == 0:
                     vals = [2, 5, 10, 25, 50, 100]
                     self.temp_mult_display = random.choice(vals)
                     self.msg = f"MULTIPLIER: x{self.temp_mult_display}?"
            
            if self.multiplier_timer <= 0:
                 # Finalize
                 final_mult = self.pick_random_multiplier()
                 if final_mult > 1:
                     self.session_winnings *= final_mult
                     self.msg = f"x{final_mult} BONUS! TOTAL: {int(self.session_winnings)}"
                     if self.sound_manager: self.sound_manager.play('tetris')
                 else:
                     self.msg = f"TOTAL: {int(self.session_winnings)}"
                 
                 self.state = 'SHOW_TOTAL'
                 self.show_total_timer = 2.5
        
        # SKIP SUMMARY (Brief pause)
        if self.state == 'SKIP_SUMMARY':
            self.skip_timer -= dt
            # Pulse Text?
            self.win_scale = 1.0 + 0.1 * math.sin(self.skip_timer * 10)
            if self.skip_timer <= 0:
                 self.state = 'MULTIPLIER_ROLL'
                 self.multiplier_timer = 1.5
                 self.msg = "MULTIPLIER CHANCE!"
        
        # Show Total state (after all spins done)
        if self.state == 'SHOW_TOTAL':
            self.show_total_timer -= dt
            if self.show_total_timer <= 0:
                # Close slot machine
                self.active = False
                self.state = 'IDLE'
                # Reset weights to normal
                self.weights = self.normal_weights
        
        # Lakitu
        # Lakitu
        # Lakitu
        if self.courier_active: self.update_courier(dt)

    def _instant_resolve_spins(self):
        """Simulate all remaining spins instantly"""
        spawned_win = 0
        while self.spins_remaining > 0:
            self.spins_remaining -= 1
            
            # 1. Randomize Reels
            reel_pos = []
            for i in range(3):
                idx = random.choices(range(len(self.symbols)), weights=self.weights, k=1)[0]
                reel_pos.append(idx)
            
            # 2. Build Grid
            grid = []
            for i in range(3):
                center = int(reel_pos[i]); L=len(self.symbols)
                col = [self.symbols[(center-1)%L], self.symbols[center], self.symbols[(center+1)%L]]
                grid.append(col)
            
            # 3. Check Lines
            lines = [[(0,1), (1,1), (2,1)]]
            if self.lines_bet >= 2: lines.extend([[(0,0), (1,0), (2,0)], [(0,2), (1,2), (2,2)]])
            if self.lines_bet >= 3: lines.extend([[(0,0), (1,1), (2,2)], [(0,2), (1,1), (2,0)]])
            
            total = 0
            for line_coords in lines:
                syms = [grid[x][y] for x,y in line_coords]
                win = self._calc_line_win(syms)
                if win > 0: total += win * self.bet_amount
            
            spawned_win += total
            self.session_winnings += total
            self.total_coins += total
            
        # Animation Result
        if spawned_win > 0:
            self.msg = f"INSTANT WIN: {int(spawned_win)}!"
            if self.sound_manager: self.sound_manager.play('slot_win')
            self.state = 'SKIP_SUMMARY' # New state
            self.skip_timer = 1.0 # Show for 1 second
        elif self.session_winnings > 0:
             self.state = 'MULTIPLIER_ROLL'
             self.multiplier_timer = 1.5
        else:
             self.state = 'SHOW_TOTAL'
             self.show_total_timer = 2.0

    def _instant_resolve_spins(self):
        """Simulate all remaining spins instantly"""
        spawned_win = 0
        while self.spins_remaining > 0:
            self.spins_remaining -= 1
            
            # 1. Randomize Reels
            reel_pos = []
            for i in range(3):
                idx = random.choices(range(len(self.symbols)), weights=self.weights, k=1)[0]
                reel_pos.append(idx)
            
            # 2. Build Grid
            grid = []
            for i in range(3):
                center = int(reel_pos[i]); L=len(self.symbols)
                col = [self.symbols[(center-1)%L], self.symbols[center], self.symbols[(center+1)%L]]
                grid.append(col)
            
            # 3. Check Lines
            lines = [[(0,1), (1,1), (2,1)]]
            if self.lines_bet >= 2: lines.extend([[(0,0), (1,0), (2,0)], [(0,2), (1,2), (2,2)]])
            if self.lines_bet >= 3: lines.extend([[(0,0), (1,1), (2,2)], [(0,2), (1,1), (2,0)]])
            
            total = 0
            for line_coords in lines:
                syms = [grid[x][y] for x,y in line_coords]
                win = self._calc_line_win(syms)
                if win > 0: total += win * self.bet_amount
            
            spawned_win += total
            self.session_winnings += total
            self.total_coins += total
            
        # Animation Result
        if spawned_win > 0:
            self.msg = f"INSTANT WIN: {int(spawned_win)}!"
            if self.sound_manager: self.sound_manager.play('slot_win')
            self.state = 'SKIP_SUMMARY' # New state
            self.skip_timer = 1.0 # Show for 1 second
        elif self.session_winnings > 0:
             self.state = 'MULTIPLIER_ROLL'
             self.multiplier_timer = 1.5
        else:
             self.state = 'SHOW_TOTAL'
             self.show_total_timer = 2.0

    def update_reels(self, dt):
        self.spin_elapsed += dt
        spinning = 0
        
        for i in range(3):
            if self.reel_state[i] == 1:
                spinning += 1
                self.stop_timers[i] -= dt
                # Advance reel position
                self.reel_positions[i] = (self.reel_positions[i] + dt * 20) % len(self.symbols)
                
                if self.stop_timers[i] <= 0:
                    self.reel_state[i] = 2 # Bounce
                    # Snap to integer
                    self.reel_positions[i] = round(self.reel_positions[i]) % len(self.symbols)
                    
                    # Force random outcome weighting here if desired, 
                    # but pure random scroll is fine if we start random
                    # Let's pick a targeted stop to control odds
                    target = random.choices(range(len(self.symbols)), weights=self.weights, k=1)[0]
                    self.reel_positions[i] = target
                    if self.sound_manager: self.sound_manager.play('move')
            elif self.reel_state[i] == 2:
                 # Bounce effect handled visually? Or logic?
                 # Simple logic: done.
                 self.reel_state[i] = 0
        
        if spinning == 0 and all(r == 0 for r in self.reel_state):
             self.check_win()

    def check_win(self):
        # Build the 3x3 Visible Grid
        # Row 0 (Top), Row 1 (Mid/Center), Row 2 (Bot)
        # Reel Index `r` is Center. Top is `r-1`, Bot is `r+1`
        grid = []
        for i in range(3): # Reel 0,1,2
            center = int(self.reel_positions[i])
            col = [
                self.symbols[(center - 1) % len(self.symbols)], # Top
                self.symbols[center],                           # Mid
                self.symbols[(center + 1) % len(self.symbols)]  # Bot
            ]
            grid.append(col)
        
        # Grid access: grid[reel][row]
        # Lines definitions: (reel_idx, row_idx) tuples
        lines = []
        # Line 0: Middle (Always active) -> Row 1
        lines.append([(0,1), (1,1), (2,1)]) 
        
        if self.lines_bet >= 2:
            # Add Top and Bottom
            lines.append([(0,0), (1,0), (2,0)]) # Top
            lines.append([(0,2), (1,2), (2,2)]) # Bot
            
        if self.lines_bet >= 3:
            # Add Diagonals
            lines.append([(0,0), (1,1), (2,2)]) # TL to BR
            lines.append([(0,2), (1,1), (2,0)]) # BL to TR
            
        total_payout = 0
        self.winning_lines = []
        
        for line_idx, param in enumerate(lines):
            syms = [grid[x][y] for x,y in param]
            
            # Check Match
            win = self._calc_line_win(syms)
            if win > 0:
                payout = win * self.bet_amount
                total_payout += payout
                self.winning_lines.append(param) # Store winning coords
                
        if total_payout > 0:
            self.total_coins += total_payout
            self.session_winnings = getattr(self, 'session_winnings', 0) + total_payout  # Accumulate!
            self.win_amount = total_payout
            self.win_flash_timer = 3.0  # Flash for 3 seconds
            self.win_scale = 1.0
            
            # Log this win for announcements
            winning_symbols = []
            if self.winning_lines:
                for line in self.winning_lines:
                    syms = [grid[x][y] for x, y in line]
                    winning_symbols.append('-'.join(syms))
            self.win_log.append({
                'spin': self.current_spin_number,
                'amount': total_payout,
                'symbols': winning_symbols[0] if winning_symbols else 'match'
            })
            
            # Determine win tier and set effects
            if total_payout >= 5000:
                self.state = 'BIG_WIN'
                self.msg = "★ JACKPOT!! ★"
                self.msg_timer = 3.5  # Shorter for faster gameplay
                self.shake_intensity = 15
                self.spawn_coins(50)  # Lots of coins!
                if self.sound_manager: self.sound_manager.play('tetris')  # Epic sound
            elif total_payout >= 1000:
                self.state = 'BIG_WIN'
                self.msg = "★ BIG WIN! ★"
                self.msg_timer = 2.5
                self.shake_intensity = 10
                self.spawn_coins(30)
                if self.sound_manager: self.sound_manager.play('clear')
            elif total_payout >= 100:
                self.state = 'WIN_SHOW'
                self.msg = f"WIN +{total_payout}!"
                self.msg_timer = 1.8
                self.shake_intensity = 5
                self.spawn_coins(15)
                if self.sound_manager: self.sound_manager.play('clear')
            else:
                self.state = 'WIN_SHOW'
                self.msg = f"+{total_payout}"
                self.msg_timer = 1.2
                self.spawn_coins(5)
                if self.sound_manager: self.sound_manager.play('move')
        else:
            self.state = 'WIN_SHOW'
            self.msg = "MISS"
            self.msg_timer = 0.8  # Quick transition on miss
            self.win_amount = 0
            # Log the miss
            self.win_log.append({
                'spin': self.current_spin_number,
                'amount': 0,
                'symbols': 'no match'
            })

    def _calc_line_win(self, syms):
        # Logic: 3 of same, or Wilds substitute
        # syms is list of 3 strings
        s1, s2, s3 = syms
        
        # Identify effective symbol (first non-wild)
        non_wilds = [s for s in syms if s != 'wild']
        if not non_wilds: eff = 'wild' # All wilds
        else: eff = non_wilds[0]
        
        # Check match
        # Must match eff or be wild
        if all(s == eff or s == 'wild' for s in syms):
             # WIN! - UPDATE PAYOUTS (Multiplied)
             base = 0
             if eff == 'jackpot': base = 2000 # Was 500
             elif eff == 'wild': base = 1000  # Was 1000 (Already high, but let's keep it or boost)
             elif eff == 'star': base = 500
             elif eff == 'mario': base = 300
             elif eff == 'luigi': base = 200
             elif eff == 'mushroom': base = 150
             elif eff == 'flower': base = 120
             elif eff == 'coin': base = 100
             else: base = 50
             
             # Bonus for 3 Wilds specifically?
             if eff == 'wild': base = 3000
             
             # Progressive logic?
             if eff == 'jackpot' and self.bet_amount >= 100:
                  return self.progressive_jackpot
             
             return base
        return 0

    def spawn_coins(self, count):
        for _ in range(count):
            self.particles.append({
                'x': self.x + self.width//2,
                'y': self.y + self.height//2,
                'vx': random.randint(-400, 400),
                'vy': random.randint(-600, -200),
                'color': (255, 215, 0),
                'size': random.randint(4, 8)
            })

    def draw(self, surface):
        if not self.active: return
        self.screen_size = surface.get_size()
        sw, sh = self.screen_size
        
        # Overlay with subtle gradient
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        for i in range(sh):
            alpha = int(180 + 40 * (i / sh))  # Darker at bottom
            pygame.draw.line(overlay, (0, 0, 20, min(220, alpha)), (0, i), (sw, i))
        surface.blit(overlay, (0,0))
        
        # Machine Body (with shake offset)
        mx, my = self.x + self.shake_offset[0], self.y + self.shake_offset[1]
        mw, mh = self.width, self.height
        
        # Outer glow effect
        for i in range(5, 0, -1):
            glow_color = (255, 215, 0, 30 // i)
            glow_rect = pygame.Rect(mx - i*3, my - i*3, mw + i*6, mh + i*6)
            glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
            pygame.draw.rect(glow_surf, glow_color, (0, 0, glow_rect.width, glow_rect.height), border_radius=20 + i*2)
            surface.blit(glow_surf, glow_rect.topleft)
        
        # Main Box with gradient
        machine_surf = pygame.Surface((mw, mh), pygame.SRCALPHA)
        for i in range(mh):
            r = int(80 - 30 * (i / mh))
            g = int(20 - 10 * (i / mh))
            b = int(120 - 40 * (i / mh))
            pygame.draw.line(machine_surf, (r, g, b, 255), (0, i), (mw, i))
        pygame.draw.rect(machine_surf, (0, 0, 0, 0), (0, 0, mw, mh), border_radius=20)
        surface.blit(machine_surf, (mx, my))
        
        # Border with animated lights
        pygame.draw.rect(surface, (255, 215, 0), (mx, my, mw, mh), 4, border_radius=20)
        
        # Animated light bulbs around border
        num_lights = 20
        for i in range(num_lights):
            angle = (i / num_lights) * 2 * math.pi + self.glow_timer * 2
            # Top edge
            if i < num_lights // 4:
                lx = mx + 20 + (mw - 40) * (i / (num_lights // 4))
                ly = my + 2
            # Right edge
            elif i < num_lights // 2:
                lx = mx + mw - 2
                ly = my + 20 + (mh - 40) * ((i - num_lights // 4) / (num_lights // 4))
            # Bottom edge
            elif i < 3 * num_lights // 4:
                lx = mx + mw - 20 - (mw - 40) * ((i - num_lights // 2) / (num_lights // 4))
                ly = my + mh - 2
            # Left edge
            else:
                lx = mx + 2
                ly = my + mh - 20 - (mh - 40) * ((i - 3 * num_lights // 4) / (num_lights // 4))
            
            # Alternating brightness
            brightness = int(255 * (0.5 + 0.5 * math.sin(angle)))
            light_color = (brightness, brightness // 2, 0)
            pygame.draw.circle(surface, light_color, (int(lx), int(ly)), 4)
        
        # Marquee with gradient and glow
        marq_rect = pygame.Rect(mx + 20, my + 25, mw - 40, 55)
        # Marquee glow
        for i in range(3, 0, -1):
            glow_surf = pygame.Surface((marq_rect.width + i*4, marq_rect.height + i*4), pygame.SRCALPHA)
            pygame.draw.rect(glow_surf, (255, 100, 0, 50 // i), (0, 0, glow_surf.get_width(), glow_surf.get_height()), border_radius=8)
            surface.blit(glow_surf, (marq_rect.x - i*2, marq_rect.y - i*2))
        
        pygame.draw.rect(surface, (40, 0, 0), marq_rect, border_radius=8)
        pygame.draw.rect(surface, (255, 150, 0), marq_rect, 3, border_radius=8)
        
        # Title with shadow
        title_shadow = self.font_big.render("★ MARIO SLOTS ★", True, (0, 0, 0))
        title = self.font_big.render("★ MARIO SLOTS ★", True, (255, 220, 50))
        surface.blit(title_shadow, title_shadow.get_rect(center=(marq_rect.centerx + 2, marq_rect.centery + 2)))
        surface.blit(title, title.get_rect(center=marq_rect.center))
        
        # Progressive Label with animated color
        prog = self.font_small.render(f"GRAND: {int(self.progressive_jackpot)}", True, (0, 255, 0))
        surface.blit(prog, (marq_rect.centerx - prog.get_width()//2, marq_rect.bottom + 5))
        
        # FREE SPINS display (prominent when active)
        if self.spins_remaining > 0:
            # Glowing background
            spin_rect = pygame.Rect(mx + mw//2 - 80, marq_rect.bottom + 25, 160, 35)
            for i in range(4, 0, -1):
                glow_surf = pygame.Surface((spin_rect.width + i*4, spin_rect.height + i*4), pygame.SRCALPHA)
                pulse = (math.sin(self.glow_timer * 6) + 1) / 2
                alpha = int(100 * pulse) // i
                pygame.draw.rect(glow_surf, (0, 255, 255, alpha), (0, 0, glow_surf.get_width(), glow_surf.get_height()), border_radius=8)
                surface.blit(glow_surf, (spin_rect.x - i*2, spin_rect.y - i*2))
            
            pygame.draw.rect(surface, (0, 50, 80), spin_rect, border_radius=8)
            pygame.draw.rect(surface, (0, 255, 255), spin_rect, 2, border_radius=8)
            
            free_txt = self.font_med.render(f"FREE SPINS: {self.spins_remaining}", True, (255, 255, 0))
            surface.blit(free_txt, free_txt.get_rect(center=spin_rect.center))
        
        # REEL WINDOW with premium styling
        # We need 3x3
        reel_x = mx + 40
        reel_y = my + 110
        reel_w = mw - 80
        reel_h = 220 # Slightly shorter
        
        # Outer reel frame glow
        for i in range(3, 0, -1):
            glow_surf = pygame.Surface((reel_w + i*6, reel_h + i*6), pygame.SRCALPHA)
            pygame.draw.rect(glow_surf, (100, 100, 255, 40 // i), (0, 0, glow_surf.get_width(), glow_surf.get_height()), border_radius=8)
            surface.blit(glow_surf, (reel_x - i*3, reel_y - i*3))
        
        # Gradient background for reel area
        reel_bg = pygame.Surface((reel_w, reel_h), pygame.SRCALPHA)
        for i in range(reel_h):
            brightness = int(20 + 30 * (1 - abs(i - reel_h/2) / (reel_h/2)))
            pygame.draw.line(reel_bg, (brightness, brightness, brightness + 20, 255), (0, i), (reel_w, i))
        surface.blit(reel_bg, (reel_x, reel_y))
        
        # Inner shadow effect
        shadow_surf = pygame.Surface((reel_w, reel_h), pygame.SRCALPHA)
        for i in range(15):
            alpha = 80 - i * 5
            pygame.draw.rect(shadow_surf, (0, 0, 0, max(0, alpha)), (i, i, reel_w - i*2, reel_h - i*2), 1)
        surface.blit(shadow_surf, (reel_x, reel_y))
        
        # Metallic border
        pygame.draw.rect(surface, (180, 180, 200), (reel_x, reel_y, reel_w, reel_h), 4, border_radius=4)
        pygame.draw.rect(surface, (100, 100, 120), (reel_x+2, reel_y+2, reel_w-4, reel_h-4), 2, border_radius=4)

        # DRAW REELS
        col_w = reel_w // 3
        row_h = reel_h // 3
        
        # Draw visible portion based on positions
        for c in range(3): # Columns
            center_idx = self.reel_positions[c]
            # Smooth scrolling? 
            # reel_positions is a float index.
            # We want to draw continuous strip. 
            # Visible: floor(center_idx) - 1, floor(center_idx), floor(center_idx)+1
            # Plus offset.
            
            # Calculate offset in pixels based on fractional part
            fraction = center_idx % 1.0
            # If index increases, items move DOWN.
            # So if we are at 1.5, we see half of 1 and half of 2?
            # Actually standard slots: Index is "Stop Position".
            # Let's say index 5.0 means Symbol 5 is centered.
            # Index 5.5 means Symbol 5 is halfway down, Symbol 4 coming in? 
            # Let's simple implementation: Draw 4 symbols and clip.
            
            base_idx = int(center_idx)
            # Offset = fraction * row_h
            px_offset = int(fraction * row_h)
            
            # Symbols to draw: (base-2), (base-1), (base), (base+1)
            # To handle wrapping
            
            # We draw column strip
            cx = reel_x + c * col_w
            
            for r_off in [-2, -1, 0, 1]:
                s_idx = (base_idx + r_off) % len(self.symbols)
                sym = self.symbols[s_idx]
                
                # Y pos: 
                # r_off = 0 is CENTER row.
                # Center Y = reel_y + row_h*1.5
                # Current Y = (reel_y + row_h*1.5) + (r_off * row_h) + px_offset
                
                # Actually, if index increases, strip moves DOWN.
                # So pixel offset should add to Y.
                
                # Check mapping: 
                # Target: index 5.0 -> Sym 5 at Row 1 (Center)
                # index 5.1 -> Sym 5 moves down 10%... Sym 4 appears at top
                
                # Logic:
                # Slot centers: 
                # Row 0: reel_y + row_h*0.5
                # Row 1: reel_y + row_h*1.5
                # Row 2: reel_y + row_h*2.5
                
                # Draw position for symbol `base_idx + k`:
                # Baseline for base_idx is Row 1.
                # Y = (reel_y + row_h) + (k * row_h) + (fraction * row_h)
                
                # Let's try:
                # r_off = 0 (Sym[base]) -> drawn at Row 1 Center + offset
                # r_off = -1 (Sym[base-1]) -> drawn at Row 0 Center + offset
                
                draw_cy = (reel_y + row_h * 1.5) + (r_off * row_h) + px_offset
                
                # Only draw if within reel window bounds (strict clipping)
                if draw_cy > reel_y and draw_cy < reel_y + reel_h:
                    img = self.images.get(sym)
                    if not img:
                         # Fallback text
                         txt = self.font_small.render(sym[0].upper(), True, (255,255,255))
                         surface.blit(txt, (cx + col_w//2 - 10, int(draw_cy)))
                    else:
                         # Centered
                         img_rect = img.get_rect(center=(cx + col_w//2, int(draw_cy)))
                         surface.blit(img, img_rect)

            # Draw Column Dividers
            pygame.draw.line(surface, (100,100,100), (cx, reel_y), (cx, reel_y+reel_h), 2)
        
        # Redraw reel frame border to cover any overflow
        pygame.draw.rect(surface, (180, 180, 200), (reel_x, reel_y, reel_w, reel_h), 6, border_radius=4)

        # Winning Lines Overlay
        if self.state != 'REEL_SPIN':
            for line in self.winning_lines:
                # line is list of (col, row)
                # Convert to points
                points = []
                for cx, ry in line:
                    px = reel_x + cx * col_w + col_w // 2
                    py = reel_y + ry * row_h + row_h // 2
                    points.append((px, py))
                pygame.draw.lines(surface, (255, 0, 0), False, points, 5)

        # UI PANEL (Bottom)
        ui_y = reel_y + reel_h + 20
        
        # 1. Row Selection (Lines)
        # Button: [ROWS: 1/2/3]
        self.btn_lines = pygame.Rect(mx + 30, ui_y, 140, 50)
        col = (0, 0, 100) if self.lines_bet == 1 else ((0, 0, 150) if self.lines_bet == 2 else (0, 0, 200))
        pygame.draw.rect(surface, col, self.btn_lines, border_radius=10)
        pygame.draw.rect(surface, (100, 100, 255), self.btn_lines, 2, border_radius=10)
        
        l_txt = self.font_small.render(f"ROWS: {self.lines_bet}", True, (255, 255, 255))
        l_sub = self.font_lcd.render(f"{1 if self.lines_bet==1 else (3 if self.lines_bet==2 else 5)} LINES", True, (0, 255, 255))
        surface.blit(l_txt, (self.btn_lines.x + 10, self.btn_lines.y + 5))
        surface.blit(l_sub, (self.btn_lines.x + 10, self.btn_lines.y + 25))

        # 2. Bet Amount
        # Buttons [-] [BET: 10] [+]
        self.btn_bet_down = pygame.Rect(mx + 190, ui_y + 10, 40, 40)
        self.btn_bet_up = pygame.Rect(mx + 310, ui_y + 10, 40, 40)
        
        pygame.draw.rect(surface, (100, 0, 0), self.btn_bet_down, border_radius=5)
        pygame.draw.rect(surface, (0, 100, 0), self.btn_bet_up, border_radius=5)
        
        surface.blit(self.font_med.render("-", True, (255,255,255)), (self.btn_bet_down.x + 12, self.btn_bet_down.y + 5))
        surface.blit(self.font_med.render("+", True, (255,255,255)), (self.btn_bet_up.x + 10, self.btn_bet_up.y + 5))
        
        # Bet Display Center
        bet_center_x = mx + 270
        b_txt = self.font_small.render("BET", True, (200, 200, 200))
        b_val = self.font_lcd.render(f"{self.bet_amount}", True, (255, 255, 0))
        surface.blit(b_txt, (bet_center_x - b_txt.get_width()//2, ui_y + 5))
        surface.blit(b_val, (bet_center_x - b_val.get_width()//2, ui_y + 25))
        
        # 3. Spin Button (Right) with GLOW effect
        self.btn_spin = pygame.Rect(mx + 440, ui_y - 10, 120, 70)
        
        # Base color based on state - only ready when in READY_TO_SPIN
        can_spin = self.state == 'READY_TO_SPIN'
        if self.state == 'REEL_SPIN': 
            scol = (50, 50, 50)  # Dark gray when spinning
        elif self.state in ['WIN_SHOW', 'BIG_WIN', 'SHOW_TOTAL']:
            scol = (80, 80, 0)  # Dim yellow during win display
        elif self.spins_remaining > 0 and can_spin: 
            scol = (0, 255, 200)  # Bright cyan for Free Spins ready
        elif can_spin:
            scol = (0, 200, 0)  # Green when ready
        else: 
            scol = (50, 50, 50)  # Gray otherwise
        
        # Pulsing glow only when truly ready to spin
        if can_spin:
            # Calculate pulse intensity (0.0 to 1.0)
            pulse = (math.sin(self.glow_timer * 4) + 1) / 2  # Oscillates 0-1
            
            # Draw outer glow layers
            for i in range(3, 0, -1):
                glow_alpha = int(100 * pulse)
                glow_rect = self.btn_spin.inflate(i * 8, i * 8)
                glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
                glow_color = (255, 255, 100, glow_alpha // i)
                pygame.draw.rect(glow_surf, glow_color, (0, 0, glow_rect.width, glow_rect.height), border_radius=15 + i*2)
                surface.blit(glow_surf, glow_rect.topleft)
            
            # Brighten base color based on pulse
            bright = int(55 * pulse)
            scol = (min(255, scol[0] + bright), min(255, scol[1] + bright), min(255, scol[2] + bright))
        
        pygame.draw.rect(surface, scol, self.btn_spin, border_radius=15)
        border_col = (255, 255, 100) if can_spin else (100, 100, 100)
        pygame.draw.rect(surface, border_col, self.btn_spin, 3, border_radius=15)
        
        stxt = "SPIN"
        if self.spins_remaining > 0: stxt = f"FREE({self.spins_remaining})"
        
        t_spin = self.font_med.render(stxt, True, (255, 255, 255))
        surface.blit(t_spin, t_spin.get_rect(center=self.btn_spin.center))
        
        # Cost check info
        total_bet = self._get_total_bet()
        c_txt = self.font_small.render(f"Cost: {total_bet}", True, (150, 150, 150))
        surface.blit(c_txt, (self.btn_spin.centerx - c_txt.get_width()//2, self.btn_spin.bottom + 5))
        
        # Draw "PRESS SPACE TO SKIP"
        if self.active and (self.spins_remaining > 0 or self.state in ['MULTIPLIER_ROLL', 'SHOW_TOTAL']):
             skip = self.font_small.render("[SPACE] TO SKIP", True, (255, 255, 255))
             surface.blit(skip, (self.btn_spin.centerx - skip.get_width()//2, self.btn_spin.bottom + 25))
        
        # 4. Digital Status Panel (Bottom of machine)
        # [ CREDITS: 000500 ]  [ WIN: 000000 ]
        panel_rect = pygame.Rect(mx + 20, my + mh - 60, mw - 40, 40)
        pygame.draw.rect(surface, (0, 0, 0), panel_rect)
        
        # Credits
        cr_lbl = self.font_lcd.render(f"CREDITS: {int(self.total_coins):07d}", True, (50, 255, 50))
        surface.blit(cr_lbl, (panel_rect.x + 20, panel_rect.y + 10))
        
        # Msg / Win (enhanced)
        if self.msg:
             # Color based on message type
             if "JACKPOT" in self.msg:
                 # Rainbow cycling for jackpot
                 hue = (self.glow_timer * 100) % 360
                 msg_col = pygame.Color(0)
                 msg_col.hsva = (hue, 100, 100, 100)
             elif "BIG WIN" in self.msg:
                 msg_col = (255, 215, 0)  # Gold
             elif "WIN" in self.msg:
                 msg_col = (100, 255, 100)  # Green
             elif "TRY" in self.msg:
                 msg_col = (150, 150, 150)  # Gray
             else:
                 msg_col = (255, 255, 255)
             
             m_lbl = self.font_lcd.render(self.msg, True, msg_col)
             surface.blit(m_lbl, (panel_rect.right - m_lbl.get_width() - 20, panel_rect.y + 10))
        
        # BIG WIN CELEBRATION OVERLAY
        if self.win_flash_timer > 0 and self.win_amount > 0:
            # Semi-transparent overlay flash
            flash_alpha = int(50 + 50 * math.sin(self.glow_timer * 10))
            flash_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
            flash_surf.fill((255, 215, 0, flash_alpha))
            surface.blit(flash_surf, (0, 0))
            
            # Big centered win text
            win_text = f"+{self.win_amount}"
            
            # Scale the font based on win_scale
            font_size = int(48 * self.win_scale)
            try:
                big_font = pygame.font.SysFont('arial black', font_size, bold=True)
            except:
                big_font = self.font_big
            
            # Render with shadow
            shadow = big_font.render(win_text, True, (0, 0, 0))
            main_text = big_font.render(win_text, True, (255, 255, 0))
            
            # Center position
            cx, cy = sw // 2, sh // 2 - 50
            
            # Shadow
            shadow_rect = shadow.get_rect(center=(cx + 3, cy + 3))
            surface.blit(shadow, shadow_rect)
            
            # Main text
            main_rect = main_text.get_rect(center=(cx, cy))
            surface.blit(main_text, main_rect)
            
            # Sub-text based on tier
            if self.win_amount >= 5000:
                sub = "★ JACKPOT!! ★"
            elif self.win_amount >= 1000:
                sub = "★ BIG WIN! ★"
            else:
                sub = "WINNER!"
            
            sub_text = self.font_med.render(sub, True, (255, 255, 255))
            sub_rect = sub_text.get_rect(center=(cx, cy + 50))
            surface.blit(sub_text, sub_rect)
        
        # BONUS INTRO ANIMATION
        if self.state == 'BONUS_INTRO':
            # Full screen dramatic overlay
            intro_overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
            
            # Radial gradient effect
            pulse = (math.sin(self.glow_timer * 8) + 1) / 2
            center_alpha = int(200 - 50 * pulse)
            intro_overlay.fill((20, 0, 60, center_alpha))
            surface.blit(intro_overlay, (0, 0))
            
            cx, cy = sw // 2, sh // 2
            
            if self.intro_phase >= 1:
                # Zooming stars/particles
                for i in range(20):
                    angle = (i / 20) * 2 * math.pi + self.glow_timer * 3
                    dist = 50 + 150 * ((2.5 - self.intro_timer) / 2.5)  # Expand outward
                    px = cx + int(dist * math.cos(angle))
                    py = cy + int(dist * math.sin(angle))
                    star_size = int(3 + 5 * pulse)
                    pygame.draw.circle(surface, (255, 215, 0), (px, py), star_size)
            
            if self.intro_phase >= 2:
                # Big "BONUS!" text with pulsing
                try:
                    bonus_font = pygame.font.SysFont('arial black', int(80 + 20 * pulse), bold=True)
                except:
                    bonus_font = self.font_big
                
                # Shadow
                shadow = bonus_font.render("★ BONUS! ★", True, (100, 0, 0))
                surface.blit(shadow, shadow.get_rect(center=(cx + 4, cy - 46)))
                
                # Main text with rainbow effect
                hue = (self.glow_timer * 120) % 360
                bonus_col = pygame.Color(0)
                bonus_col.hsva = (hue, 100, 100, 100)
                main_txt = bonus_font.render("★ BONUS! ★", True, bonus_col)
                surface.blit(main_txt, main_txt.get_rect(center=(cx, cy - 50)))
                
                # Spins count
                spins_txt = self.font_big.render(f"{self.spins_remaining} FREE SPINS!", True, (255, 255, 255))
                surface.blit(spins_txt, spins_txt.get_rect(center=(cx, cy + 30)))
        
        # SHOW TOTAL FINAL SUMMARY
        if self.state == 'SHOW_TOTAL':
            # Dramatic overlay
            total_overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
            total_overlay.fill((0, 0, 0, 200))
            surface.blit(total_overlay, (0, 0))
            
            cx, cy = sw // 2, sh // 2
            
            # Title
            title = self.font_big.render("BONUS COMPLETE!", True, (255, 215, 0))
            surface.blit(title, title.get_rect(center=(cx, cy - 120)))
            
            # Win log summary (last 5 spins max)
            log_y = cy - 60
            visible_log = self.win_log[-5:] if len(self.win_log) > 5 else self.win_log
            for entry in visible_log:
                spin_num = entry.get('spin', 0)
                amount = entry.get('amount', 0)
                if amount > 0:
                    log_col = (100, 255, 100)
                    log_txt = f"Spin #{spin_num}: +{amount}"
                else:
                    log_col = (150, 150, 150)
                    log_txt = f"Spin #{spin_num}: miss"
                log_surf = self.font_small.render(log_txt, True, log_col)
                surface.blit(log_surf, log_surf.get_rect(center=(cx, log_y)))
                log_y += 25
            
            # GRAND TOTAL - Big and flashy
            pulse = (math.sin(self.glow_timer * 6) + 1) / 2
            if self.session_winnings > 0:
                try:
                    total_font = pygame.font.SysFont('arial black', int(60 + 10 * pulse), bold=True)
                except:
                    total_font = self.font_big
                
                total_txt = f"+{int(self.session_winnings)}"
                shadow = total_font.render(total_txt, True, (0, 0, 0))
                surface.blit(shadow, shadow.get_rect(center=(cx + 3, log_y + 43)))
                
                # Rainbow color for big wins
                if self.session_winnings >= 1000:
                    hue = (self.glow_timer * 100) % 360
                    txt_col = pygame.Color(0)
                    txt_col.hsva = (hue, 100, 100, 100)
                else:
                    txt_col = (255, 255, 0)
                
                main = total_font.render(total_txt, True, txt_col)
                surface.blit(main, main.get_rect(center=(cx, log_y + 40)))
                
                # Label
                lbl = self.font_med.render("TOTAL WON", True, (200, 200, 200))
                surface.blit(lbl, lbl.get_rect(center=(cx, log_y + 90)))
            else:
                no_win = self.font_med.render("Better luck next time!", True, (150, 150, 150))
                surface.blit(no_win, no_win.get_rect(center=(cx, log_y + 40)))
            
            # Countdown hint
            if self.show_total_timer > 0:
                countdown = self.font_small.render(f"Returning in {int(self.show_total_timer) + 1}...", True, (100, 100, 100))
                surface.blit(countdown, countdown.get_rect(center=(cx, cy + 180)))
        
        # Win Log Panel (side display during active bonus - shows running tally)
        if self.spins_remaining > 0 or self.state in ['WIN_SHOW', 'BIG_WIN', 'REEL_SPIN']:
            if len(self.win_log) > 0 and self.state != 'SHOW_TOTAL':
                # Small panel on left side showing recent wins
                panel_x = mx - 140
                panel_y = my + 100
                panel_w = 130
                panel_h = 150
                
                # Panel background
                log_panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
                pygame.draw.rect(log_panel, (0, 0, 0, 180), (0, 0, panel_w, panel_h), border_radius=8)
                surface.blit(log_panel, (panel_x, panel_y))
                pygame.draw.rect(surface, (100, 100, 150), (panel_x, panel_y, panel_w, panel_h), 2, border_radius=8)
                
                # Title
                log_title = self.font_small.render("SPIN LOG", True, (200, 200, 255))
                surface.blit(log_title, (panel_x + 10, panel_y + 5))
                
                # Recent entries (last 4)
                recent = self.win_log[-4:]
                entry_y = panel_y + 30
                for entry in recent:
                    spin = entry.get('spin', 0)
                    amt = entry.get('amount', 0)
                    if amt > 0:
                        e_col = (100, 255, 100)
                        e_txt = f"#{spin}: +{amt}"
                    else:
                        e_col = (100, 100, 100)
                        e_txt = f"#{spin}: -"
                    e_surf = self.font_small.render(e_txt, True, e_col)
                    surface.blit(e_surf, (panel_x + 8, entry_y))
                    entry_y += 22
                
                # Running total
                pygame.draw.line(surface, (100, 100, 150), (panel_x + 5, entry_y), (panel_x + panel_w - 5, entry_y), 1)
                total_txt = self.font_small.render(f"TOTAL: +{int(self.session_winnings)}", True, (255, 215, 0))
                surface.blit(total_txt, (panel_x + 8, entry_y + 5))
        
        # 5. Back to Game Button (Top Right)
        self.btn_back = pygame.Rect(mx + mw - 100, my + 5, 90, 30)
        pygame.draw.rect(surface, (100, 0, 0), self.btn_back, border_radius=5)
        pygame.draw.rect(surface, (255, 100, 100), self.btn_back, 2, border_radius=5)
        back_txt = self.font_small.render("← BACK", True, (255, 255, 255))
        surface.blit(back_txt, back_txt.get_rect(center=self.btn_back.center))
        
        # Particles (coins) - draw on top
        for p in self.particles:
            pygame.draw.circle(surface, p['color'], (int(p['x']), int(p['y'])), p['size'])

    def update_courier(self, dt):
        pass # Todo implemented lakitu back if needed, but focus on slots for now

