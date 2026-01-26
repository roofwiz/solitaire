
import pygame
import random
import json
import asyncio
import sys
import os
import time
import traceback
import urllib.request
import urllib.error

# --- V31 LOGGING (The most robust version) ---
DEBUG_FILE = "v31_debug_log.txt"
def log(msg):
    try:
        ts = time.strftime('%H:%M:%S')
        full_msg = f"[{ts}] {msg}"
        with open(DEBUG_FILE, "a", encoding="utf-8") as f:
            f.write(full_msg + "\n")
            f.flush()
            os.fsync(f.fileno())
        # Also print to console
        print(full_msg)
        sys.stdout.flush()
    except: pass

with open(DEBUG_FILE, "w", encoding="utf-8") as f: f.write("--- Mario Tetris V31 START ---\n")

# --- NO-DEPENDENCY FIREBASE ---
class FirebaseManagerV31:
    def __init__(self, db_url):
        self.db_url = db_url.rstrip('/')
        self.room_id = "battle_v31"
        self.player_slot = "p1"
        self.opp_slot = "p2"
        self.connected = False
        self.lines_received_total = 0 
        self.pending_garbage = 0 
        self.last_poll_time = 0
        self.poll_interval = 1.0 # 1 second poll for ultra safety
        self.opponent_status = "unknown"

    def _sync_request(self, url, method="GET", data=None):
        """Blocking request ran in a thread"""
        try:
            req = urllib.request.Request(url, method=method)
            if data:
                req.add_header('Content-Type', 'application/json')
                body = json.dumps(data).encode('utf-8')
            else:
                body = None
            
            with urllib.request.urlopen(req, data=body, timeout=5) as response:
                content = response.read().decode('utf-8')
                return json.loads(content) if content else {}
        except Exception as e:
            log(f"Backend Request Error: {e}")
            return None

    async def join(self):
        log("Contacting Firebase...")
        url = f"{self.db_url}/battles/{self.room_id}.json"
        data = await asyncio.to_thread(self._sync_request, url)
        
        curr_time = time.time()
        # Fresh Room Case
        if not data or (data.get('last_update', 0) and curr_time - data['last_update'] > 3600):
            log("Claiming P1 Role.")
            self.player_slot, self.opp_slot = "p1", "p2"
            init_data = {"state": "waiting", "p1": {"status": "alive", "attack_queue": 0}, "p2": {"status": "offline", "attack_queue": 0}, "last_update": curr_time}
            await asyncio.to_thread(self._sync_request, url, "PUT", init_data)
            self.connected = True
            return "P1"
        
        # Join Case
        p2_status = data.get('p2', {}).get('status', 'offline')
        if p2_status == 'offline':
            log("Claiming P2 Role.")
            self.player_slot, self.opp_slot = "p2", "p1"
            await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}/p2.json", "PATCH", {"status": "alive", "attack_queue": 0})
            await asyncio.to_thread(self._sync_request, url, "PATCH", {"state": "playing"})
            self.connected = True
            return "P2"
            
        log("Room Full.")
        return "FULL"

    async def poll(self):
        if not self.connected: return
        t = time.time()
        if t - self.last_poll_time < self.poll_interval: return
        self.last_poll_time = t
        
        data = await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}.json")
        if not data: return
        
        opp_data = data.get(self.opp_slot, {})
        self.opponent_status = opp_data.get('status', 'offline')
        
        # Check Garbage
        remote_q = opp_data.get('attack_queue', 0)
        if remote_q > self.lines_received_total:
            diff = remote_q - self.lines_received_total
            if 0 < diff < 50: # Sanity limit
                self.pending_garbage += diff
            self.lines_received_total = remote_q

    async def send_attack(self, lines):
        if not self.connected: return
        # Atomic-ish increment: get then set
        data = await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}/{self.player_slot}.json")
        cur = data.get('attack_queue', 0) if data else 0
        await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}/{self.player_slot}.json", "PATCH", {"attack_queue": cur + lines})

# --- GAME ENGINE ---
WW, WH = 900, 650
GW, GH = 10, 20
BS = 28
T_SHAPES = {'I': [[(0,0),(1,0),(2,0),(3,0)],(0,255,255)], 'O': [[(0,0),(1,0),(0,1),(1,1)],(255,255,0)], 'T': [[(1,0),(0,1),(1,1),(2,1)],(128,0,128)], 'S': [[(1,0),(2,0),(0,1),(1,1)],(0,255,0)], 'Z': [[(0,0),(1,0),(1,1),(2,1)],(255,0,0)], 'J': [[(0,0),(0,1),(1,1),(2,1)],(0,0,255)], 'L': [[(2,0),(0,1),(1,1),(2,1)],(255,165,0)]}

class TetrisV31:
    def __init__(self):
        log("Initializing Graphics...")
        pygame.init()
        self.screen = pygame.display.set_mode((WW, WH))
        pygame.display.set_caption("Mario Tetris V31 - FINAL LOCAL ATTEMPT")
        self.clock = pygame.time.Clock()
        self.reset_grid()
        self.bag = []
        self.pos = [GW//2-1, 0]
        self.shape = self.spawn()
        self.fb = FirebaseManagerV31("https://mario-tetris-game-default-rtdb.firebaseio.com/")
        self.role = "IDLE"
        self.connecting = False
        try:
            self.font = pygame.font.SysFont("Arial", 20)
        except: self.font = None
        log("Initialization Complete.")

    def reset_grid(self):
        self.grid = [[None for _ in range(GW)] for _ in range(GH)]

    def spawn(self):
        if not self.bag: self.bag = list(T_SHAPES.keys()); random.shuffle(self.bag)
        s = self.bag.pop()
        return [list(T_SHAPES[s][0]), T_SHAPES[s][1]]

    def collide(self, p, s):
        for bx, by in s[0]:
            gx, gy = p[0]+bx, p[1]+by
            if gx < 0 or gx >= GW or gy >= GH: return True
            if gy >= 0 and self.grid[gy][gx]: return True
        return False

    async def run(self):
        log("Main Loop Active.")
        while True:
            dt = self.clock.tick(60)/1000.0
            for e in pygame.event.get():
                if e.type == pygame.QUIT: return
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_RETURN and not self.fb.connected and not self.connecting:
                        log("Connection Pressed.")
                        self.connecting, self.role = True, "CONNECT..."
                        asyncio.create_task(self.start_connect())
                    
                    if self.fb.connected:
                        if e.key == pygame.K_LEFT: 
                            self.pos[0]-=1
                            if self.collide(self.pos, self.shape): self.pos[0]+=1
                        if e.key == pygame.K_RIGHT: 
                            self.pos[0]+=1
                            if self.collide(self.pos, self.shape): self.pos[0]-=1
                        if e.key == pygame.K_UP:
                            old = [list(b) for b in self.shape[0]]
                            self.shape[0] = [(-by, bx) for bx, by in old]
                            if self.collide(self.pos, self.shape): self.shape[0] = old

            if self.fb.connected:
                # Polling & Garbage
                try:
                    await self.fb.poll()
                    if self.fb.pending_garbage > 0:
                        log(f"Garbage Received: {self.fb.pending_garbage} lines.")
                        for _ in range(self.fb.pending_garbage):
                            self.grid.pop(0)
                            # Create row with random hole
                            h = random.randint(0, GW-1)
                            row = [(100,100,100) if x != h else None for x in range(GW)]
                            self.grid.append(row)
                        self.fb.pending_garbage = 0
                except Exception as ex: log(f"Network Loop Error: {ex}")

                # Gravity
                self.fall_dt = getattr(self, "fall_dt", 0) + dt
                if self.fall_dt > 0.7:
                    self.fall_dt = 0
                    self.pos[1] += 1
                    if self.collide(self.pos, self.shape):
                        self.pos[1] -= 1
                        # Lock
                        for bx, by in self.shape[0]:
                            gy, gx = self.pos[1]+by, self.pos[0]+bx
                            if 0 <= gy < GH: self.grid[gy][gx] = self.shape[1]
                        
                        # Clear
                        new_g = [r for r in self.grid if any(c is None for c in r)]
                        c = GH - len(new_g)
                        while len(new_g) < GH: new_g.insert(0, [None]*GW)
                        self.grid = new_g
                        
                        if c > 0:
                            log(f"Cleared {c}!")
                            asyncio.create_task(self.fb.send_attack(c))
                        
                        self.pos = [GW//2-1, 0]
                        self.shape = self.spawn()
                        if self.collide(self.pos, self.shape):
                            log("GAME OVER."); self.reset_grid()

            self.draw()
            await asyncio.sleep(0.01)

    async def start_connect(self):
        try:
            r = await self.fb.join()
            log(f"Connection Result: {r}")
            self.role = r
            self.connecting = False
        except Exception as ex:
            log(f"Connect Error: {ex}"); traceback.print_exc()

    def draw(self):
        self.screen.fill((10,10,10))
        # Draw Field
        pygame.draw.rect(self.screen, (30,30,50), (50, 50, GW*BS, GH*BS))
        for y, row in enumerate(self.grid):
            for x, col in enumerate(row):
                if col:
                    pygame.draw.rect(self.screen, col, (50+x*BS, 50+y*BS, BS, BS))
                    pygame.draw.rect(self.screen, (255,255,255), (50+x*BS, 50+y*BS, BS, BS), 1)
        
        # Piece
        if self.fb.connected:
            for bx, by in self.shape[0]:
                pygame.draw.rect(self.screen, self.shape[1], (50+(self.pos[0]+bx)*BS, 50+(self.pos[1]+by)*BS, BS, BS))
                pygame.draw.rect(self.screen, (255,255,255), (50+(self.pos[0]+bx)*BS, 50+(self.pos[1]+by)*BS, BS, BS), 1)
        
        # UI
        if self.font:
            self.screen.blit(self.font.render(f"ROLE: {self.role}", True, (255,255,255)), (GW*BS + 100, 50))
            self.screen.blit(self.font.render(f"OPPONENT: {self.fb.opponent_status}", True, (0,255,0) if self.fb.opponent_status=='alive' else (255,0,0)), (GW*BS + 100, 80))
            if not self.fb.connected:
                self.screen.blit(self.font.render(">> PRESS ENTER <<", True, (255,255,0)), (GW*BS + 100, 150))
        
        pygame.display.flip()

if __name__ == "__main__":
    try:
        app = TetrisV31()
        asyncio.run(app.run())
    except Exception as e:
        log(f"CRASH: {e}")
        with open("v31_CRITICAL_TRACE.txt", "w") as f: f.write(traceback.format_exc())
        print(traceback.format_exc()); input("CRASH! Press Enter to Exit...")
