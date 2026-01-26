
import pygame
import random
import json
import asyncio
import sys
import os
import time
import traceback
import urllib.request
import argparse

# --- V37 ARGUMENT & LOGGING ---
parser = argparse.ArgumentParser()
parser.add_argument('--role', type=str, choices=['p1', 'p2'], help='Force a specific role')
args, unknown = parser.parse_known_args()

PID = os.getpid()
DEBUG_FILE = "multiplayer_debug.log"
def log(msg):
    try:
        ts = time.strftime('%H:%M:%S')
        full_msg = f"[{ts}][PID:{PID}] {msg}"
        with open(DEBUG_FILE, "a", encoding="utf-8") as f:
            f.write(full_msg + "\n")
            f.flush()
        print(full_msg)
    except: pass

with open(DEBUG_FILE, "a", encoding="utf-8") as f: f.write(f"\n--- SESSION START [PID:{PID}][FORCED:{args.role}] ---\n")

class FirebaseManagerV37:
    def __init__(self, db_url, forced_role=None):
        self.db_url = db_url.rstrip('/')
        self.room_id = "battle_v37"
        self.player_role = forced_role # 'p1' or 'p2'
        self.opp_role = "p2" if self.player_role == "p1" else "p1"
        self.connected = False
        self.room_state = "waiting"
        self.countdown_start = 0
        self.p1_ready = False
        self.p2_ready = False
        self.p1_status = "offline"
        self.p2_status = "offline"
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
        except Exception as e:
            return None

    async def join(self):
        log(f"Attempting to join as {self.player_role.upper()}...")
        url = f"{self.db_url}/battles/{self.room_id}.json"
        
        while not self.connected:
            data = await asyncio.to_thread(self._sync_request, url)
            curr_time = time.time()
            
            if self.player_role == 'p1':
                # P1 initializes or re-claims
                if not data or curr_time - data.get('last_update', 0) > 300:
                    log("Room empty/stale. Creating room as P1.")
                    init_data = {
                        "state": "waiting", 
                        "p1": {"status": "alive", "attack_queue": 0, "ready": False}, 
                        "p2": {"status": "offline", "attack_queue": 0, "ready": False}, 
                        "countdown_start": 0,
                        "last_update": curr_time
                    }
                    res = await asyncio.to_thread(self._sync_request, url, "PUT", init_data)
                    if res: self.connected = True
                else:
                    log("Shared room exists. Occupying P1 slot.")
                    await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}/p1.json", "PATCH", {"status": "alive", "ready": False})
                    self.connected = True
            else:
                # P2 waits for room to exist
                if data:
                    log("Room found. Joining as P2.")
                    await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}/p2.json", "PATCH", {"status": "alive", "ready": False})
                    self.connected = True
                else:
                    log("P2 waiting for P1 to create room...")
                    await asyncio.sleep(1)
        
        log(f"Join successful as {self.player_role.upper()}")
        return self.player_role.upper()

    async def poll(self):
        if not self.connected: return
        t = time.time()
        if t - self.last_poll_time < self.poll_interval: return
        self.last_poll_time = t
        
        data = await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}.json")
        if not data: return
        
        self.room_state = data.get('state', 'waiting')
        self.countdown_start = data.get('countdown_start', 0)
        
        p1 = data.get('p1', {})
        p2 = data.get('p2', {})
        self.p1_status = p1.get('status', 'offline')
        self.p2_status = p2.get('status', 'offline')
        self.p1_ready = p1.get('ready', False)
        self.p2_ready = p2.get('ready', False)
        
        opp_data = p2 if self.player_role == 'p1' else p1
        remote_q = opp_data.get('attack_queue', 0)
        if remote_q > self.lines_received_total:
            self.pending_garbage += (remote_q - self.lines_received_total)
            self.lines_received_total = remote_q
            
        if self.player_role == "p1":
             await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}.json", "PATCH", {"last_update": time.time()})

    async def set_ready(self, ready):
        await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}/{self.player_role}.json", "PATCH", {"ready": ready})

    async def start_countdown(self):
        if self.player_role == 'p1':
            await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}.json", "PATCH", {"state": "countdown", "countdown_start": time.time()})

    async def trigger_start(self):
        if self.player_role == 'p1':
             await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}.json", "PATCH", {"state": "playing"})

    async def send_attack(self, lines):
        data = await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}/{self.player_role}.json")
        cur = data.get('attack_queue', 0) if data else 0
        await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}/{self.player_role}.json", "PATCH", {"attack_queue": cur + lines})

# --- GAME ENGINE ---
WW, WH = 950, 650
GW, GH = 10, 20
BS = 28
T_SHAPES = {'I': [[(0,0),(1,0),(2,0),(3,0)],(0,255,255)], 'O': [[(0,0),(1,0),(0,1),(1,1)],(255,255,0)], 'T': [[(1,0),(0,1),(1,1),(2,1)],(128,0,128)], 'S': [[(1,0),(2,0),(0,1),(1,1)],(0,255,0)], 'Z': [[(0,0),(1,0),(1,1),(2,1)],(255,0,0)], 'J': [[(0,0),(0,1),(1,1),(2,1)],(0,0,255)], 'L': [[(2,0),(0,1),(1,1),(2,1)],(255,165,0)]}

class TetrisV37:
    def __init__(self, role):
        pygame.init()
        self.screen = pygame.display.set_mode((WW, WH))
        pygame.display.set_caption(f"Mario Tetris V37 - ROLE: {role.upper()}")
        self.clock = pygame.time.Clock()
        self.reset_game()
        self.fb = FirebaseManagerV37("https://mario-tetris-game-default-rtdb.firebaseio.com/", role)
        self.role_str = role.upper()
        self.font = pygame.font.SysFont("Arial", 24)
        self.huge_font = pygame.font.SysFont("Arial", 120)
        self.is_ready = False

    def reset_game(self):
        self.grid = [[None for _ in range(GW)] for _ in range(GH)]
        self.bag = []
        self.pos = [GW//2-1, 0]
        self.shape = self.spawn()
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
        join_task = asyncio.create_task(self.fb.join())
        while True:
            dt = self.clock.tick(60)/1000.0
            t_now = time.time()
            for e in pygame.event.get():
                if e.type == pygame.QUIT: return
                if e.type == pygame.KEYDOWN:
                    if self.fb.room_state == "waiting":
                        if e.key == pygame.K_RETURN and self.fb.connected:
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

            await self.fb.poll()
            
            if self.fb.room_state == "waiting":
                if self.fb.p1_ready and self.fb.p2_ready and self.fb.player_role == "p1":
                    await self.fb.start_countdown()
            elif self.fb.room_state == "countdown":
                diff = t_now - self.fb.countdown_start
                if diff > 3.0:
                    if self.fb.player_role == "p1": await self.fb.trigger_start()
                    if self.fb.room_state != "playing": self.reset_game()
            elif self.fb.room_state == "playing":
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
                        if self.collide(self.pos, self.shape): self.reset_game()
            self.draw(); await asyncio.sleep(0.01)

    def draw(self):
        self.screen.fill((10, 10, 20))
        # Playfield
        pygame.draw.rect(self.screen, (30,30,50), (50, 50, GW*BS, GH*BS))
        if self.fb.room_state in ["playing", "countdown"]:
            for y, r in enumerate(self.grid):
                for x, c in enumerate(r):
                    if c: 
                        pygame.draw.rect(self.screen, c, (50+x*BS, 50+y*BS, BS, BS))
                        pygame.draw.rect(self.screen, (255,255,255), (50+x*BS, 50+y*BS, BS, BS), 1)
            if self.fb.room_state == "playing":
                for bx, by in self.shape[0]:
                    pygame.draw.rect(self.screen, self.shape[1], (50+(self.pos[0]+bx)*BS, 50+(self.pos[1]+by)*BS, BS, BS)); pygame.draw.rect(self.screen, (255,255,255), (50+(self.pos[0]+bx)*BS, 50+(self.pos[1]+by)*BS, BS, BS), 1)
        
        # Sidebar UI
        x_off = GW*BS + 100
        self.screen.blit(self.font.render(f"YOU ARE: {self.role_str}", True, (255,255,255)), (x_off, 50))
        
        # Room status
        s1 = "READY" if self.fb.p1_ready else "WAITING"
        c1 = (0,255,0) if self.fb.p1_ready else (255,100,100)
        s2 = "READY" if self.fb.p2_ready else "WAITING"
        c2 = (0,255,0) if self.fb.p2_ready else (255,100,100)
        
        self.screen.blit(self.font.render("P1 STATUS:", True, (200,200,200)), (x_off, 120))
        self.screen.blit(self.font.render(s1, True, c1), (x_off + 120, 120))
        self.screen.blit(self.font.render("P2 STATUS:", True, (200,200,200)), (x_off, 160))
        self.screen.blit(self.font.render(s2, True, c2), (x_off + 120, 160))
        
        if self.fb.room_state == "waiting":
            if not self.fb.connected:
                msg = "CONNECTING..."
                clr = (255, 255, 0)
            elif not self.is_ready:
                msg = "HIT ENTER TO READY UP!"
                clr = (255, 255, 255)
            else:
                msg = "WAITING FOR OPPONENT"
                clr = (0, 255, 0)
            
            txt = self.font.render(msg, True, clr)
            self.screen.blit(txt, (WW//2 - txt.get_width()//2, WH//2 + 100))
            
        elif self.fb.room_state == "countdown":
            cd = 3 - int(time.time() - self.fb.countdown_start)
            txt_str = str(max(1, cd)) if cd > 0 else "GO!"
            s = self.huge_font.render(txt_str, True, (255, 255, 255))
            self.screen.blit(s, (WW//2-s.get_width()//2, WH//2-s.get_height()//2))

        pygame.display.flip()

if __name__ == "__main__":
    try: app = TetrisV37(args.role); asyncio.run(app.run())
    except: log(traceback.format_exc()); input("CRASH")
