
import pygame
import random
import json
import asyncio
import sys
import os
import time
import traceback
import urllib.request

# --- V29 LOGGING (Ultra Robust) ---
DEBUG_FILE = "v29_debug_log.txt"
def log(msg):
    try:
        ts = time.strftime('%H:%M:%S')
        with open(DEBUG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
            f.flush()
            os.fsync(f.fileno())
    except: pass
    print(f"[V29] {msg}")

with open(DEBUG_FILE, "w", encoding="utf-8") as f: f.write("--- V29 START ---\n")

# --- NO-DEPENDENCY FIREBASE (Uses urllib) ---
class FirebaseManager:
    def __init__(self, db_url):
        self.db_url = db_url.rstrip('/')
        self.room_id = None
        self.player_slot = "p1"
        self.opp_slot = "p2"
        self.connected = False
        self.lines_received_total = 0 
        self.pending_garbage = 0 
        self.last_poll_time = 0
        self.poll_interval = 1.2
        self.opponent_status = "unknown"

    def _request(self, url, method="GET", data=None):
        try:
            log(f"Req: {method} {url}")
            req = urllib.request.Request(url, method=method)
            if data:
                req.add_header('Content-Type', 'application/json')
                body = json.dumps(data).encode('utf-8')
            else:
                body = None
            
            with urllib.request.urlopen(req, data=body, timeout=5) as response:
                res_data = response.read().decode('utf-8')
                return json.loads(res_data) if res_data else {}
        except Exception as e:
            log(f"Req Err: {e}")
            return None

    async def join_room(self, room_id):
        self.room_id = room_id
        data = await asyncio.to_thread(self._request, f"{self.db_url}/battles/{self.room_id}.json")
        curr_time = time.time()
        
        if not data or (data.get('last_update', 0) and curr_time - data['last_update'] > 3600):
            self.player_slot, self.opp_slot = 'p1', 'p2'
            await asyncio.to_thread(self._request, f"{self.db_url}/battles/{self.room_id}.json", "PUT", {"state": "waiting", "p1": {"status": "alive", "attack_queue": 0}, "p2": {"status": "offline", "attack_queue": 0}, "last_update": curr_time})
            self.connected = True
            return 'p1'
        else:
            if data.get('p2', {}).get('status', 'offline') == 'offline':
                self.player_slot, self.opp_slot = 'p2', 'p1'
                await asyncio.to_thread(self._request, f"{self.db_url}/battles/{self.room_id}/p2.json", "PATCH", {"status": "alive", "attack_queue": 0})
                await asyncio.to_thread(self._request, f"{self.db_url}/battles/{self.room_id}.json", "PATCH", {"state": "playing"})
                self.connected = True
                return 'p2'
            return None

    async def poll(self):
        if not self.connected: return
        if time.time() - self.last_poll_time < self.poll_interval: return
        self.last_poll_time = time.time()
        data = await asyncio.to_thread(self._request, f"{self.db_url}/battles/{self.room_id}.json")
        if not data: return
        opp_data = data.get(self.opp_slot, {})
        self.opponent_status = opp_data.get('status', 'offline')
        remote_attacks = opp_data.get('attack_queue', 0)
        if remote_attacks > self.lines_received_total:
            self.pending_garbage += (remote_attacks - self.lines_received_total)
            self.lines_received_total = remote_attacks

    async def send_attack(self, lines):
        if not self.connected: return
        # First get current attack_queue to increment safely
        data = await asyncio.to_thread(self._request, f"{self.db_url}/battles/{self.room_id}/{self.player_slot}.json")
        q = data.get('attack_queue', 0) if data else 0
        await asyncio.to_thread(self._request, f"{self.db_url}/battles/{self.room_id}/{self.player_slot}.json", "PATCH", {"attack_queue": q + lines})

# --- GAME ENGINE ---
WINDOW_WIDTH, WINDOW_HEIGHT = 900, 650
GRID_WIDTH, GRID_HEIGHT = 10, 20
BLOCK_SIZE = 28
PLAYFIELD_X, PLAYFIELD_Y = 50, 50
C_BLACK, C_GRID_BG, C_WHITE, C_RED, C_GREEN = (10,10,10), (30,30,50), (240,240,240), (255,50,50), (50,255,50)
T_SHAPES = {'I': [[(0,0),(1,0),(2,0),(3,0)],(0,255,255)], 'O': [[(0,0),(1,0),(0,1),(1,1)],(255,255,0)], 'T': [[(1,0),(0,1),(1,1),(2,1)],(128,0,128)], 'S': [[(1,0),(2,0),(0,1),(1,1)],(0,255,0)], 'Z': [[(0,0),(1,0),(1,1),(2,1)],(255,0,0)], 'J': [[(0,0),(0,1),(1,1),(2,1)],(0,0,255)], 'L': [[(2,0),(0,1),(1,1),(2,1)],(255,165,0)]}

class TetrisV29:
    def __init__(self):
        log("Init Pygame...")
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Mario Tetris V29 - ULTIMATE LOCAL FIX")
        self.clock = pygame.time.Clock()
        self.grid = [[None for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.bag = []
        self.current_pos = [GRID_WIDTH//2-1, 0]
        self.current_shape = self.get_new_piece()
        self.fb = FirebaseManager("https://mario-tetris-game-default-rtdb.firebaseio.com/")
        self.role = "IDLE"
        self.fall_time = 0
        try:
            self.font = pygame.font.SysFont("Arial", 22)
            if not self.font: self.font = pygame.font.SysFont(None, 24)
        except:
            self.font = None
        self.connecting = False

    def get_new_piece(self):
        if not self.bag: self.bag = list(T_SHAPES.keys()); random.shuffle(self.bag)
        s = self.bag.pop()
        return [list(T_SHAPES[s][0]), T_SHAPES[s][1]]

    def check_collision(self, pos, shape):
        for bx, by in shape[0]:
            gx, gy = pos[0]+bx, pos[1]+by
            if gx<0 or gx>=GRID_WIDTH or gy>=GRID_HEIGHT: return True
            if gy>=0 and self.grid[gy][gx]: return True
        return False

    async def run(self):
        log("Loop Start.")
        while True:
            dt = self.clock.tick(60)/1000.0
            for e in pygame.event.get():
                if e.type == pygame.QUIT: return
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_RETURN and not self.fb.connected and not self.connecting:
                        log("Connect requested.")
                        self.connecting, self.role = True, "CONNECTING..."
                        asyncio.create_task(self.connect_network())
                    
                    if self.fb.connected:
                        if e.key == pygame.K_LEFT: 
                            self.current_pos[0]-=1
                            if self.check_collision(self.current_pos, self.current_shape): self.current_pos[0]+=1
                        if e.key == pygame.K_RIGHT: 
                            self.current_pos[0]+=1
                            if self.check_collision(self.current_pos, self.current_shape): self.current_pos[0]-=1
                        if e.key == pygame.K_UP:
                            old = [list(b) for b in self.current_shape[0]]
                            self.current_shape[0] = [(-by, bx) for bx, by in old]
                            if self.check_collision(self.current_pos, self.current_shape): self.current_shape[0] = old

            if self.fb.connected:
                await self.fb.poll()
                if self.fb.pending_garbage > 0:
                    log(f"Applying {self.fb.pending_garbage} garbage lines.")
                    for _ in range(self.fib.pending_garbage):
                        self.grid.pop(0)
                        self.grid.append([random.choice(list(T_SHAPES.values()))[1] if x != random.randint(0,9) else None for x in range(GRID_WIDTH)])
                    self.fb.pending_garbage = 0

                self.fall_time += dt
                if self.fall_time > 0.6:
                    self.fall_time = 0; self.current_pos[1]+=1
                    if self.check_collision(self.current_pos, self.current_shape):
                        self.current_pos[1]-=1
                        for bx, by in self.current_shape[0]:
                            if 0 <= self.current_pos[1]+by < GRID_HEIGHT:
                                self.grid[self.current_pos[1]+by][self.current_pos[0]+bx] = self.current_shape[1]
                        
                        # Clear lines (SAFE REPLACEMENT)
                        new_grid = [r for r in self.grid if any(c is None for c in r)]
                        cleared = GRID_HEIGHT - len(new_grid)
                        while len(new_grid) < GRID_HEIGHT: new_grid.insert(0, [None for _ in range(GRID_WIDTH)])
                        self.grid = new_grid
                        
                        if cleared > 0: 
                            log(f"Cleared {cleared} lines.")
                            asyncio.create_task(self.fb.send_attack(cleared))
                        
                        self.current_pos = [GRID_WIDTH//2-1, 0]; self.current_shape = self.get_new_piece()
                        if self.check_collision(self.current_pos, self.current_shape): 
                            log("GAME OVER."); self.grid = [[None for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]

            self.draw()
            await asyncio.sleep(0.01)

    async def connect_network(self):
        try:
            log("Calling join_room...")
            res = await self.fb.join_room("battle_v29")
            if res: self.role = res.upper(); log(f"Joined as {res}")
            else: self.role = "ROOM FULL"; log("Join failed: Full")
            self.connecting = False
        except Exception as e:
            log(f"Connect Crash: {e}\n{traceback.format_exc()}")
            self.role = "ERROR"

    def draw(self):
        try:
            self.screen.fill(C_BLACK)
            pygame.draw.rect(self.screen, C_GRID_BG, (PLAYFIELD_X, PLAYFIELD_Y, GRID_WIDTH*BLOCK_SIZE, GRID_HEIGHT*BLOCK_SIZE))
            for y, r in enumerate(self.grid):
                for x, c in enumerate(r):
                    if c: 
                        pygame.draw.rect(self.screen, c, (PLAYFIELD_X+x*BLOCK_SIZE, PLAYFIELD_Y+y*BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE))
                        pygame.draw.rect(self.screen, C_WHITE, (PLAYFIELD_X+x*BLOCK_SIZE, PLAYFIELD_Y+y*BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE), 1)
            
            if self.fb.connected:
                for bx, by in self.current_shape[0]:
                    pygame.draw.rect(self.screen, self.current_shape[1], (PLAYFIELD_X+(self.current_pos[0]+bx)*BLOCK_SIZE, PLAYFIELD_Y+(self.current_pos[1]+by)*BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE))
                    pygame.draw.rect(self.screen, C_WHITE, (PLAYFIELD_X+(self.current_pos[0]+bx)*BLOCK_SIZE, PLAYFIELD_Y+(self.current_pos[1]+by)*BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE), 1)
            
            if self.font:
                self.screen.blit(self.font.render(f"ROLE: {self.role}", True, C_WHITE), (WINDOW_WIDTH-200, 50))
                self.screen.blit(self.font.render(f"OPPONENT: {self.fb.opponent_status}", True, C_GREEN if self.fb.opponent_status=='alive' else C_RED), (WINDOW_WIDTH-200, 80))
                if not self.fb.connected:
                    self.screen.blit(self.font.render(">> PRESS ENTER TO START <<", True, (0, 255, 0)), (WINDOW_WIDTH//2-180, WINDOW_HEIGHT//2))
            
            pygame.display.flip()
        except: pass

if __name__ == "__main__":
    try:
        game = TetrisV29()
        asyncio.run(game.run())
    except Exception as e:
        log(f"TOP LEVEL ERR: {e}\n{traceback.format_exc()}")
        with open("v29_CRASH.txt", "w") as f: f.write(traceback.format_exc())
        input("CRASH! Press Enter to Exit...")
