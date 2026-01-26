
import pygame
import random
import json
import asyncio
import math
import sys
import os
import time

# Ensure game root is in path
game_root = os.path.dirname(os.path.abspath(__file__))
if game_root not in sys.path:
    sys.path.append(game_root)

# Early Mixer Hint
try:
    if not pygame.mixer.get_init():
        pygame.mixer.pre_init(44100, -16, 2, 1024)
except: pass

# --- Simplified Configuration ---
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
GRID_WIDTH = 10
GRID_HEIGHT = 20
BLOCK_SIZE = 30
PLAYFIELD_X = 50
PLAYFIELD_Y = 50

C_BLACK = (10, 10, 10)
C_GRID_BG = (30, 30, 50)
C_NEON_BLUE = (100, 200, 255)
C_WHITE = (240, 240, 240)
C_RED = (255, 50, 50)
C_GREEN = (50, 255, 50)

# Multiplayer
FIREBASE_DB_URL = "https://mario-tetris-game-default-rtdb.firebaseio.com/"

from src.firebase_manager import FirebaseManager

class PopupText:
    def __init__(self, x, y, text, color=(255, 255, 255), size='small'):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.life = 2.0
    def update(self, dt):
        self.life -= dt
    def draw(self, surface, font):
        if self.life > 0:
            txt = font.render(self.text, True, self.color)
            surface.blit(txt, (self.x - txt.get_width()//2, self.y))

class Polyomino:
    SHAPES = {
        'I': [(-1, 0), (0, 0), (1, 0), (2, 0)],
        'O': [(0, 0), (1, 0), (0, 1), (1, 1)],
        'T': [(-1, 0), (0, 0), (1, 0), (0, 1)],
        'S': [(-1, 0), (0, 0), (0, 1), (1, 1)],
        'Z': [(-1, 1), (0, 1), (0, 0), (1, 0)],
        'J': [(-1, 0), (0, 0), (1, 0), (1, -1)],
        'L': [(-1, 0), (0, 0), (1, 0), (-1, -1)]
    }
    COLORS = {
        'I': (0, 255, 255), 'O': (255, 255, 0), 'T': (128, 0, 128),
        'S': (0, 255, 0), 'Z': (255, 0, 0), 'J': (0, 0, 255), 'L': (255, 165, 0)
    }
    def __init__(self, shape_key):
        self.x = GRID_WIDTH // 2 - 1
        self.y = 0  
        self.shape_key = shape_key
        self.blocks = list(self.SHAPES[shape_key])
        self.color = self.COLORS[shape_key]
    def rotate(self, direction=1):
        if self.shape_key == 'O': return
        new_blocks = []
        for block in self.blocks:
            bx, by = block
            if direction == 1: new_x, new_y = -by, bx
            else: new_x, new_y = by, -bx
            new_blocks.append((new_x, new_y))
        self.blocks = new_blocks

class Spawner:
    def __init__(self):
        self.bag = []
        self.fill_bag()
    def fill_bag(self):
        self.bag = ['I', 'O', 'T', 'S', 'Z', 'J', 'L']
        random.shuffle(self.bag)
    def get_next_piece(self):
        if not self.bag: self.fill_bag()
        return Polyomino(self.bag.pop(0))

class Grid:
    def __init__(self):
        self.grid = [[None for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
    def check_collision(self, piece):
        for bx, by in piece.blocks:
            gx, gy = int(piece.x + bx), int(piece.y + by)
            if gx < 0 or gx >= GRID_WIDTH or gy >= GRID_HEIGHT: return True
            if gy >= 0 and self.grid[gy][gx]: return True
        return False
    def lock_piece(self, piece):
        for bx, by in piece.blocks:
            gx, gy = int(piece.x + bx), int(piece.y + by)
            if 0 <= gx < GRID_WIDTH and 0 <= gy < GRID_HEIGHT:
                self.grid[gy][gx] = piece.color
    def clear_lines(self):
        new_grid = [row for row in self.grid if any(c is None for c in row)]
        cleared = GRID_HEIGHT - len(new_grid)
        for _ in range(cleared):
            new_grid.insert(0, [None for _ in range(GRID_WIDTH)])
        self.grid = new_grid
        return cleared
    def draw(self, screen):
        for y, row in enumerate(self.grid):
            for x, color in enumerate(row):
                px = PLAYFIELD_X + x * BLOCK_SIZE
                py = PLAYFIELD_Y + y * BLOCK_SIZE
                pygame.draw.rect(screen, (20,20,30), (px, py, BLOCK_SIZE, BLOCK_SIZE), 1)
                if color:
                    pygame.draw.rect(screen, color, (px, py, BLOCK_SIZE, BLOCK_SIZE))
                    pygame.draw.rect(screen, (255,255,255), (px, py, BLOCK_SIZE, BLOCK_SIZE), 1)

class Tetris:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Mario Tetris V22 - Local Battle")
        self.clock = pygame.time.Clock()
        self.grid = Grid()
        self.spawner = Spawner()
        self.current_piece = self.spawner.get_next_piece()
        self.game_state = 'BATTLE'
        self.multiplayer_role = None
        self.opponent_grid = [[None for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.firebase_manager = FirebaseManager(FIREBASE_DB_URL)
        self.fall_time = 0
        self.fall_speed = 0.5
        self.popups = []
        self.font = pygame.font.SysFont("Arial", 24)
        self.large_font = pygame.font.SysFont("Arial", 48)
        
    async def run(self):
        # Auto-Join Room
        print("[Local] Attempting to join battle_v22...")
        role = await self.firebase_manager.join_room("battle_v22")
        self.multiplayer_role = role
        if role:
            print(f"[Local] Joined as {role}")
            self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, f"CONNECTED AS {role.upper()}", C_GREEN))
        else:
            self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, "CONNECTION FAILED", C_RED))

        while True:
            dt = self.clock.tick(60) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT: return
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_LEFT: self.move(-1)
                    if event.key == pygame.K_RIGHT: self.move(1)
                    if event.key == pygame.K_UP: self.rotate()
                    if event.key == pygame.K_DOWN: self.fall_speed = 0.05
                    if event.key == pygame.K_r: # Force Reset/Rejoin
                         self.multiplayer_role = await self.firebase_manager.join_room("battle_v22")
                if event.type == pygame.KEYUP:
                    if event.key == pygame.K_DOWN: self.fall_speed = 0.5

            if self.game_state == 'BATTLE':
                await self.firebase_manager.poll()
                
                # Check for garbage
                if self.firebase_manager.pending_garbage > 0:
                    self.add_garbage(self.firebase_manager.pending_garbage)
                    self.firebase_manager.pending_garbage = 0

                self.fall_time += dt
                if self.fall_time >= self.fall_speed:
                    self.fall_time = 0
                    self.current_piece.y += 1
                    if self.grid.check_collision(self.current_piece):
                        self.current_piece.y -= 1
                        self.grid.lock_piece(self.current_piece)
                        cleared = self.grid.clear_lines()
                        if cleared > 0:
                            await self.firebase_manager.send_attack(cleared)
                        self.current_piece = self.spawner.get_next_piece()
                        if self.grid.check_collision(self.current_piece):
                            self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, "GAME OVER", C_RED))
                            self.grid = Grid() # Reset on loss

            for p in self.popups[:]:
                p.update(dt)
                if p.life <= 0: self.popups.remove(p)

            self.draw()
            await asyncio.sleep(0)

    def move(self, dx):
        self.current_piece.x += dx
        if self.grid.check_collision(self.current_piece): self.current_piece.x -= dx

    def rotate(self):
        self.current_piece.rotate()
        if self.grid.check_collision(self.current_piece): self.current_piece.rotate(-1)

    def add_garbage(self, count):
        for _ in range(count):
            self.grid.grid.pop(0)
            row = [random.choice(list(Polyomino.COLORS.values())) for _ in range(GRID_WIDTH)]
            row[random.randint(0, GRID_WIDTH-1)] = None # Hole
            self.grid.grid.append(row)

    def draw(self):
        self.screen.fill(C_BLACK)
        
        # Draw Playfield BG
        pygame.draw.rect(self.screen, C_GRID_BG, (PLAYFIELD_X, PLAYFIELD_Y, GRID_WIDTH*BLOCK_SIZE, GRID_HEIGHT*BLOCK_SIZE))
        
        # Draw our grid
        self.grid.draw(self.screen)
        
        # Draw current piece
        for bx, by in self.current_piece.blocks:
            px = PLAYFIELD_X + (self.current_piece.x + bx) * BLOCK_SIZE
            py = PLAYFIELD_Y + (self.current_piece.y + by) * BLOCK_SIZE
            pygame.draw.rect(self.screen, self.current_piece.color, (px, py, BLOCK_SIZE, BLOCK_SIZE))
            pygame.draw.rect(self.screen, C_WHITE, (px, py, BLOCK_SIZE, BLOCK_SIZE), 1)
        
        # Draw Status
        role_txt = f"Role: {self.multiplayer_role}" if self.multiplayer_role else "Connecting..."
        self.screen.blit(self.font.render(role_txt, True, C_WHITE), (10, 10))
        self.screen.blit(self.font.render("Arrow keys to move/rotate", True, C_WHITE), (10, 40))
        self.screen.blit(self.font.render("'R' to reconnect", True, C_WHITE), (10, 70))
        
        # Draw opponent status
        opp_status = f"Opponent: {self.firebase_manager.opponent_status}"
        color = C_GREEN if self.firebase_manager.opponent_status == 'alive' else C_RED
        self.screen.blit(self.font.render(opp_status, True, color), (WINDOW_WIDTH - 250, 10))
        
        # Draw Popups
        for p in self.popups:
            p.draw(self.screen, self.large_font)
        
        pygame.display.flip()

if __name__ == "__main__":
    try:
        game = Tetris()
        asyncio.run(game.run())
    except Exception as e:
        import traceback
        print("\n" + "="*50)
        print("CRITICAL ERROR DURING INITIALIZATION")
        print("="*50)
        traceback.print_exc()
        print("="*50)
        input("Press Enter to Exit...")
