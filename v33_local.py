
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

# --- V33 LOGGING ---
DEBUG_FILE = "v33_lobby_log.txt"
def log(msg):
    try:
        ts = time.strftime('%H:%M:%S')
        with open(DEBUG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
            f.flush()
    except: pass
    print(f"[V33] {msg}")

with open(DEBUG_FILE, "w", encoding="utf-8") as f: f.write("--- V33 START ---\n")

# --- NO-DEPENDENCY FIREBASE ---
class FirebaseManagerV33:
    def __init__(self, db_url):
        self.db_url = db_url.rstrip('/')
        self.room_id = "battle_v33"
        self.player_slot = "p1"
        self.opp_slot = "p2"
        self.connected = False
        
        # Game State Sync
        self.room_state = "waiting" # waiting, countdown, playing
        self.countdown_start = 0
        self.p1_ready = False
        self.p2_ready = False
        self.opponent_status = "offline"
        
        # Battle Sync
        self.lines_received_total = 0 
        self.pending_garbage = 0 
        self.last_poll_time = 0
        self.poll_interval = 0.5 

    def _sync_request(self, url, method="GET", data=None):
        try:
            req = urllib.request.Request(url, method=method)
            if data:
                req.add_header('Content-Type', 'application/json')
                body = json.dumps(data).encode('utf-8')
            else: body = None
            with urllib.request.urlopen(req, data=body, timeout=5) as response:
                content = response.read().decode('utf-8')
                return json.loads(content) if content else {}
        except: return None

    async def join(self):
        log("Joining room...")
        url = f"{self.db_url}/battles/{self.room_id}.json"
        data = await asyncio.to_thread(self._sync_request, url)
        curr_time = time.time()
        
        if not data or (data.get('last_update', 0) and curr_time - data['last_update'] > 3600):
            self.player_slot, self.opp_slot = 'p1', 'p2'
            init_data = {
                "state": "waiting", 
                "p1": {"status": "alive", "attack_queue": 0, "ready": False}, 
                "p2": {"status": "offline", "attack_queue": 0, "ready": False}, 
                "countdown_start": 0,
                "last_update": curr_time
            }
            await asyncio.to_thread(self._sync_request, url, "PUT", init_data)
            self.connected = True
            return 'P1'
        else:
            if data.get('p2', {}).get('status', 'offline') == 'offline':
                self.player_slot, self.opp_slot = 'p2', 'p1'
                await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}/p2.json", "PATCH", {"status": "alive", "attack_queue": 0, "ready": False})
                self.connected = True
                return 'P2'
            return "BUSY"

    async def poll(self):
        if not self.connected: return
        t = time.time()
        if t - self.last_poll_time < self.poll_interval: return
        self.last_poll_time = t
        
        data = await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}.json")
        if not data: return
        
        # Sync Global State
        self.room_state = data.get('state', 'waiting')
        self.countdown_start = data.get('countdown_start', 0)
        
        # Sync Players
        p1_data = data.get('p1', {})
        p2_data = data.get('p2', {})
        self.p1_ready = p1_data.get('ready', False)
        self.p2_ready = p2_data.get('ready', False)
        
        opp_data = data.get(self.opp_slot, {})
        self.opponent_status = opp_data.get('status', 'offline')
        
        # Sync Garbage
        remote_q = opp_data.get('attack_queue', 0)
        if remote_q > self.lines_received_total:
            self.pending_garbage += (remote_q - self.lines_received_total)
            self.lines_received_total = remote_q
            
        if self.player_slot == "p1":
             await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}.json", "PATCH", {"last_update": time.time()})

    async def set_ready(self, ready_bool):
        await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}/{self.player_slot}.json", "PATCH", {"ready": ready_bool})

    async def start_countdown(self):
        # Only P1 triggers the countdown start to ensure sync
        if self.player_slot == 'p1':
            start_ts = time.time()
            await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}.json", "PATCH", {"state": "countdown", "countdown_start": start_ts})

    async def send_attack(self, lines):
        data = await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}/{self.player_slot}.json")
        cur = data.get('attack_queue', 0) if data else 0
        await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}/{self.player_slot}.json", "PATCH", {"attack_queue": cur + lines})

# --- GAME ENGINE ---
WW, WH = 1000, 700
GW, GH = 10, 20
BS = 30
T_SHAPES = {'I': [[(0,0),(1,0),(2,0),(3,0)],(0,255,255)], 'O': [[(0,0),(1,0),(0,1),(1,1)],(255,255,0)], 'T': [[(1,0),(0,1),(1,1),(2,1)],(128,0,128)], 'S': [[(1,0),(2,0),(0,1),(1,1)],(0,255,0)], 'Z': [[(0,0),(1,0),(1,1),(2,1)],(255,0,0)], 'J': [[(0,0),(0,1),(1,1),(2,1)],(0,0,255)], 'L': [[(2,0),(0,1),(1,1),(2,1)],(255,165,0)]}

class TetrisV33:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WW, WH))
        pygame.display.set_caption("Mario Tetris V33 - LOBBY & COUNTDOWN")
        self.clock = pygame.time.Clock()
        self.grid = [[None for _ in range(GW)] for _ in range(GH)]
        self.bag = []
        self.pos = [GW//2-1, 0]
        self.shape = self.spawn()
        self.fb = FirebaseManagerV33("https://mario-tetris-game-default-rtdb.firebaseio.com/")
        self.role = "JOINING..."
        self.font = pygame.font.SysFont("Arial", 28)
        self.huge_font = pygame.font.SysFont("Arial", 120)
        self.fall_dt = 0
        self.is_ready = False

    def spawn(self):
        if not self.bag: self.bag = list(T_SHAPES.keys()); random.shuffle(self.bag)
        s = self.bag.pop()
        return [list(T_SHAPES[s][0]), T_SHAPES[s][1]]

    def collide(self, p, s):
        for bx, by in s[0]:
            gx, gy = p[0]+bx, p[1]+by
            if gx < 0 or gx >= GW or gy >= GH or (gy >= 0 and self.grid[gy][gx]): return True
        return False

    async def run(self):
        # Auto-Join
        self.role = await self.fb.join()
        
        while True:
            dt = self.clock.tick(60)/1000.0
            t_now = time.time()
            
            for e in pygame.event.get():
                if e.type == pygame.QUIT: return
                if e.type == pygame.KEYDOWN:
                    if self.fb.room_state == "waiting":
                        if e.key == pygame.K_RETURN:
                            self.is_ready = not self.is_ready
                            await self.fb.set_ready(self.is_ready)
                    
                    if self.fb.room_state == "playing":
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

            # Networking Poll
            await self.fb.poll()
            
            # Logic Branches
            if self.fb.room_state == "waiting":
                # Check if both are ready
                if self.fb.p1_ready and self.fb.p2_ready and self.fb.player_slot == "p1":
                    await self.fb.start_countdown()
            
            elif self.fb.room_state == "countdown":
                diff = t_now - self.fb.countdown_start
                if diff > 3.5: # 3 sec + buffering
                    log("Countdown over! Starting game.")
                    self.fb.room_state = "playing"
                    # Reset game variables
                    self.grid = [[None for _ in range(GW)] for _ in range(GH)]
                    self.pos = [GW//2-1, 0]
                    self.shape = self.spawn()
            
            elif self.fb.room_state == "playing":
                # Garbage
                if self.fb.pending_garbage > 0:
                    for _ in range(int(self.fb.pending_garbage)):
                        self.grid.pop(0); h = random.randint(0, GW-1); self.grid.append([(100,100,100) if x!=h else None for x in range(GW)])
                    self.fb.pending_garbage = 0

                # Gravity
                self.fall_dt += dt
                if self.fall_dt > 0.6:
                    self.fall_dt = 0; self.pos[1] += 1
                    if self.collide(self.pos, self.shape):
                        self.pos[1] -= 1
                        for bx, by in self.shape[0]:
                            if 0 <= self.pos[1]+by < GH: self.grid[self.pos[1]+by][self.pos[0]+bx] = self.shape[1]
                        new_g = [r for r in self.grid if any(c is None for c in r)]
                        c = GH - len(new_g)
                        while len(new_g) < GH: new_g.insert(0, [None]*GW)
                        self.grid = new_g
                        if c > 0: asyncio.create_task(self.fb.send_attack(c))
                        self.pos = [GW//2-1, 0]; self.shape = self.spawn()
                        if self.collide(self.pos, self.shape): pass # GameOver logic here

            self.draw(); await asyncio.sleep(0.01)

    def draw(self):
        self.screen.fill((10, 10, 15))
        
        # Draw Background Grid Area
        pygame.draw.rect(self.screen, (25, 25, 40), (50, 50, GW*BS, GH*BS))
        
        if self.fb.room_state == "playing" or self.fb.room_state == "countdown":
            for y, row in enumerate(self.grid):
                for x, col in enumerate(row):
                    if col:
                        pygame.draw.rect(self.screen, col, (50+x*BS, 50+y*BS, BS, BS))
                        pygame.draw.rect(self.screen, (255,255,255), (50+x*BS, 50+y*BS, BS, BS), 1)
            if self.fb.room_state == "playing":
                for bx, by in self.shape[0]:
                    pygame.draw.rect(self.screen, self.shape[1], (50+(self.pos[0]+bx)*BS, 50+(self.pos[1]+by)*BS, BS, BS)); pygame.draw.rect(self.screen, (255,255,255), (50+(self.pos[0]+bx)*BS, 50+(self.pos[1]+by)*BS, BS, BS), 1)

        # UI Overlay
        # Lobby Status
        self.screen.blit(self.font.render(f"ROOM: {self.fb.room_id}", True, (150,150,150)), (WW-200, 20))
        self.screen.blit(self.font.render(f"ROLE: {self.role}", True, (255,255,255)), (WW-200, 60))
        
        if self.fb.room_state == "waiting":
            p1_c = (0, 255, 0) if self.fb.p1_ready else (255, 50, 50)
            p2_c = (0, 255, 0) if self.fb.p2_ready else (255, 50, 50)
            self.screen.blit(self.font.render(f"P1 READY: {self.fb.p1_ready}", True, p1_c), (WW-250, 200))
            self.screen.blit(self.font.render(f"P2 READY: {self.fb.p2_ready}", True, p2_c), (WW-250, 240))
            
            msg = "PRESS ENTER TO READY!" if not self.is_ready else "WAITING FOR OPPONENT..."
            color = (255, 255, 0) if not self.is_ready else (0, 255, 0)
            txt = self.font.render(msg, True, color)
            self.screen.blit(txt, (WW//2 - txt.get_width()//2, WH//2))
            
        elif self.fb.room_state == "countdown":
            diff = time.time() - self.fb.countdown_start
            cd = 3 - int(diff)
            if cd > 0:
                txt = self.huge_font.render(str(cd), True, (255, 255, 255))
                self.screen.blit(txt, (WW//2 - txt.get_width()//2, WH//2 - txt.get_height()//2))
            else:
                txt = self.huge_font.render("GO!", True, (255, 215, 0))
                self.screen.blit(txt, (WW//2 - txt.get_width()//2, WH//2 - txt.get_height()//2))

        pygame.display.flip()

if __name__ == "__main__":
    try: app = TetrisV33(); asyncio.run(app.run())
    except: traceback.print_exc(); input("PAUSE")
