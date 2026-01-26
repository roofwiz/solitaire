
import pygame
import random
import json
import asyncio
import sys
import os
import time
import traceback
import urllib.request

# --- V32 AUTO-CONNECT LOGGING ---
DEBUG_FILE = "v32_auto_log.txt"
def log(msg):
    try:
        ts = time.strftime('%H:%M:%S')
        with open(DEBUG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
            f.flush()
    except: pass
    print(f"[V32] {msg}")

with open(DEBUG_FILE, "w", encoding="utf-8") as f: f.write("--- Mario Tetris V32 AUTO-CONNECT ---\n")

# --- NO-DEPENDENCY FIREBASE ---
class FirebaseManagerV32:
    def __init__(self, db_url):
        self.db_url = db_url.rstrip('/')
        self.room_id = "battle_v32"
        self.player_slot = "p1"
        self.opp_slot = "p2"
        self.connected = False
        self.lines_received_total = 0 
        self.pending_garbage = 0 
        self.last_poll_time = 0
        self.poll_interval = 0.8
        self.opponent_status = "searching"

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
        log("Attempting to claim role...")
        url = f"{self.db_url}/battles/{self.room_id}.json"
        
        # Retry up to 3 times for initial join
        for attempt in range(3):
            data = await asyncio.to_thread(self._sync_request, url)
            curr_time = time.time()
            
            # Case 1: Room doesn't exist or is stale
            if not data or (data.get('last_update', 0) and curr_time - data['last_update'] > 3600):
                log(f"Attempt {attempt+1}: Initializing as P1...")
                self.player_slot, self.opp_slot = "p1", "p2"
                init_data = {"state": "waiting", "p1": {"status": "alive", "attack_queue": 0}, "p2": {"status": "offline", "attack_queue": 0}, "last_update": curr_time}
                res = await asyncio.to_thread(self._sync_request, url, "PUT", init_data)
                if res:
                    self.connected = True
                    return "P1"
            
            # Case 2: Room exists, check P2
            elif data.get('p2', {}).get('status', 'offline') == 'offline':
                log(f"Attempt {attempt+1}: Joining as P2...")
                self.player_slot, self.opp_slot = "p2", "p1"
                await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}/p2.json", "PATCH", {"status": "alive", "attack_queue": 0})
                await asyncio.to_thread(self._sync_request, url, "PATCH", {"state": "playing"})
                self.connected = True
                return "P2"
            
            await asyncio.sleep(1) # Wait before retry
            
        return "BUSY"

    async def poll(self):
        if not self.connected: return
        t = time.time()
        if t - self.last_poll_time < self.poll_interval: return
        self.last_poll_time = t
        data = await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}.json")
        if not data: return
        opp_data = data.get(self.opp_slot, {})
        self.opponent_status = opp_data.get('status', 'offline')
        remote_q = opp_data.get('attack_queue', 0)
        if remote_q > self.lines_received_total:
            self.pending_garbage += (remote_q - self.lines_received_total)
            self.lines_received_total = remote_q
        if self.player_slot == "p1": # P1 keeps room alive
             await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}.json", "PATCH", {"last_update": time.time()})

    async def send_attack(self, lines):
        if not self.connected: return
        data = await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}/{self.player_slot}.json")
        cur = data.get('attack_queue', 0) if data else 0
        await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}/{self.player_slot}.json", "PATCH", {"attack_queue": cur + lines})

# --- GAME ENGINE ---
WW, WH = 950, 680
GW, GH = 10, 20
BS = 28
T_SHAPES = {'I': [[(0,0),(1,0),(2,0),(3,0)],(0,255,255)], 'O': [[(0,0),(1,0),(0,1),(1,1)],(255,255,0)], 'T': [[(1,0),(0,1),(1,1),(2,1)],(128,0,128)], 'S': [[(1,0),(2,0),(0,1),(1,1)],(0,255,0)], 'Z': [[(0,0),(1,0),(1,1),(2,1)],(255,0,0)], 'J': [[(0,0),(0,1),(1,1),(2,1)],(0,0,255)], 'L': [[(2,0),(0,1),(1,1),(2,1)],(255,165,0)]}

class TetrisV32:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WW, WH))
        pygame.display.set_caption("Mario Tetris V32 - AUTO-CONNECT BATTLE")
        self.clock = pygame.time.Clock()
        self.grid = [[None for _ in range(GW)] for _ in range(GH)]
        self.bag = []
        self.pos = [GW//2-1, 0]
        self.shape = self.spawn()
        self.fb = FirebaseManagerV32("https://mario-tetris-game-default-rtdb.firebaseio.com/")
        self.role = "JOINING..."
        self.font = pygame.font.SysFont("Arial", 22)
        self.fall_dt = 0

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
        # AUTO JOIN
        log("Initial auto-join starting...")
        asyncio.create_task(self.auto_join())
        
        while True:
            dt = self.clock.tick(60)/1000.0
            for e in pygame.event.get():
                if e.type == pygame.QUIT: return
                if e.type == pygame.KEYDOWN and self.fb.connected:
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
                await self.fb.poll()
                if self.fb.pending_garbage > 0:
                    for _ in range(int(self.fb.pending_garbage)):
                        self.grid.pop(0); h = random.randint(0, GW-1); self.grid.append([(100,100,100) if x!=h else None for x in range(GW)])
                    self.fb.pending_garbage = 0

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
                        if self.collide(self.pos, self.shape): self.grid = [[None for _ in range(GW)] for _ in range(GH)]

            self.draw(); await asyncio.sleep(0.01)

    async def auto_join(self):
        self.role = await self.fb.join()
        log(f"Role assigned: {self.role}")

    def draw(self):
        self.screen.fill((15, 15, 20))
        pygame.draw.rect(self.screen, (30,30,50), (50, 50, GW*BS, GH*BS))
        for y, row in enumerate(self.grid):
            for x, col in enumerate(row):
                if col:
                    pygame.draw.rect(self.screen, col, (50+x*BS, 50+y*BS, BS, BS))
                    pygame.draw.rect(self.screen, (255,255,255), (50+x*BS, 50+y*BS, BS, BS), 1)
        if self.fb.connected:
            for bx, by in self.shape[0]:
                pygame.draw.rect(self.screen, self.shape[1], (50+(self.pos[0]+bx)*BS, 50+(self.pos[1]+by)*BS, BS, BS)); pygame.draw.rect(self.screen, (255,255,255), (50+(self.pos[0]+bx)*BS, 50+(self.pos[1]+by)*BS, BS, BS), 1)
        if self.font:
            self.screen.blit(self.font.render(f"ROLE: {self.role}", True, (255,255,255)), (350, 50))
            self.screen.blit(self.font.render(f"OPPONENT: {self.fb.opponent_status}", True, (0,255,0) if self.fb.opponent_status=='alive' else (255,0,0)), (350, 80))
            self.screen.blit(self.font.render("Arrow Keys to Play", True, (200,200,200)), (350, 150))
        pygame.display.flip()

if __name__ == "__main__":
    try: app = TetrisV32(); asyncio.run(app.run())
    except Exception as e:
        with open("v32_CRASH.txt", "w") as f: f.write(traceback.format_exc())
        input("CRASH! Press Enter to Exit...")
