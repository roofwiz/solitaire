
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

# --- V39 ROBUST LOGGING ---
DEBUG_FILE = "v39_multiplayer.log"
def log(msg):
    try:
        ts = time.strftime('%H:%M:%S')
        with open(DEBUG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
            f.flush()
        print(f"[V39] {msg}")
    except: pass

with open(DEBUG_FILE, "w", encoding="utf-8") as f: f.write("--- V39 SESSION START ---\n")

class FirebaseManagerV39:
    def __init__(self, db_url):
        self.db_url = db_url.rstrip('/')
        self.room_id = "battle_v39"
        self.role = None # p1 or p2
        self.opp_role = None
        self.connected = False
        self.room_state = "waiting" # waiting, countdown, playing
        self.countdown_start = 0
        self.p1_ready = False
        self.p2_ready = False
        self.opponent_status = "offline"
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

    async def pick_role(self, role):
        self.role = role
        self.opp_role = "p2" if role == "p1" else "p1"
        url = f"{self.db_url}/battles/{self.room_id}.json"
        
        if self.role == 'p1':
            log("Initializing Room as P1...")
            init_data = {
                "state": "waiting", 
                "p1": {"status": "alive", "attack_queue": 0, "ready": False}, 
                "p2": {"status": "offline", "attack_queue": 0, "ready": False}, 
                "countdown_start": 0,
                "last_update": time.time()
            }
            await asyncio.to_thread(self._sync_request, url, "PUT", init_data)
        else:
            log("Joining Room as P2...")
            await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}/p2.json", "PATCH", {"status": "alive", "ready": False})
        
        self.connected = True
        return True

    async def poll(self):
        if not self.connected: return
        t = time.time()
        if t - self.last_poll_time < self.poll_interval: return
        self.last_poll_time = t
        
        data = await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}.json")
        if not data: return
        
        self.room_state = data.get('state', 'waiting')
        self.countdown_start = data.get('countdown_start', 0)
        self.p1_ready = data.get('p1', {}).get('ready', False)
        self.p2_ready = data.get('p2', {}).get('ready', False)
        
        opp_data = data.get(self.opp_role, {})
        self.opponent_status = opp_data.get('status', 'offline')
        
        remote_q = opp_data.get('attack_queue', 0)
        if remote_q > self.lines_received_total:
            self.pending_garbage += (remote_q - self.lines_received_total)
            self.lines_received_total = remote_q
            
        if self.role == "p1":
             await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}.json", "PATCH", {"last_update": time.time()})

    async def set_ready(self, ready_bool):
        await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}/{self.role}.json", "PATCH", {"ready": ready_bool})

    async def start_countdown(self):
        if self.role == 'p1':
            await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}.json", "PATCH", {"state": "countdown", "countdown_start": time.time()})

    async def trigger_start(self):
        if self.role == 'p1':
             await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}.json", "PATCH", {"state": "playing"})

    async def send_attack(self, lines):
        data = await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}/{self.role}.json")
        cur = data.get('attack_queue', 0) if data else 0
        await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}/{self.role}.json", "PATCH", {"attack_queue": cur + lines})

# --- GAME ENGINE ---
WW, WH = 950, 650
GW, GH = 10, 20
BS = 28
T_SHAPES = {'I': [[(0,0),(1,0),(2,0),(3,0)],(0,255,255)], 'O': [[(0,0),(1,0),(0,1),(1,1)],(255,255,0)], 'T': [[(1,0),(0,1),(1,1),(2,1)],(128,0,128)], 'S': [[(1,0),(2,0),(0,1),(1,1)],(0,255,0)], 'Z': [[(0,0),(1,0),(1,1),(2,1)],(255,0,0)], 'J': [[(0,0),(0,1),(1,1),(2,1)],(0,0,255)], 'L': [[(2,0),(0,1),(1,1),(2,1)],(255,165,0)]}

class TetrisV39:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WW, WH))
        pygame.display.set_caption("Mario Tetris V39 - BATTLE SELECTION")
        self.clock = pygame.time.Clock()
        self.reset_game()
        self.fb = FirebaseManagerV39("https://mario-tetris-game-default-rtdb.firebaseio.com/")
        
        try:
            self.font = pygame.font.SysFont("Arial", 28)
            self.huge_font = pygame.font.SysFont("Arial", 120)
        except:
            self.font = None
            self.huge_font = None

        self.screen_mode = "menu" # menu, lobby, countdown, playing
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
        while True:
            dt = self.clock.tick(60)/1000.0
            t_now = time.time()
            
            for e in pygame.event.get():
                if e.type == pygame.QUIT: return
                if e.type == pygame.KEYDOWN:
                    if self.screen_mode == "menu":
                        if e.key == pygame.K_1:
                            await self.fb.pick_role("p1")
                            self.screen_mode = "lobby"
                        if e.key == pygame.K_2:
                            await self.fb.pick_role("p2")
                            self.screen_mode = "lobby"
                    
                    elif self.screen_mode == "lobby":
                        if e.key == pygame.K_RETURN:
                            self.is_ready = not self.is_ready
                            await self.fb.set_ready(self.is_ready)
                    
                    elif self.screen_mode == "playing":
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

            if self.screen_mode != "menu":
                await self.fb.poll()
                # Update screen mode from Firebase state
                if self.fb.room_state == "countdown" and self.screen_mode == "lobby":
                    self.screen_mode = "countdown"
                if self.fb.room_state == "playing" and self.screen_mode == "countdown":
                    self.screen_mode = "playing"
                    self.reset_game()
                if self.fb.room_state == "waiting" and self.screen_mode == "playing":
                    self.screen_mode = "lobby"

            # Coordination
            if self.screen_mode == "lobby":
                if self.fb.p1_ready and self.fb.p2_ready and self.fb.role == "p1":
                    await self.fb.start_countdown()
            
            elif self.screen_mode == "countdown":
                diff = t_now - self.fb.countdown_start
                if diff > 3.0:
                    if self.fb.role == "p1": await self.fb.trigger_start()
                    self.screen_mode = "playing"
                    self.reset_game()
            
            elif self.screen_mode == "playing":
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
                        if self.collide(self.pos, self.shape): 
                            log("Loss detected! Resetting field.")
                            self.reset_game()

            self.draw(); await asyncio.sleep(0.01)

    def draw(self):
        self.screen.fill((10, 10, 20))
        
        if self.screen_mode == "menu":
            if self.font:
                t1 = self.font.render("SELECT YOUR ROLE:", True, (255, 255, 255))
                t2 = self.font.render("Press [1] for PLAYER 1 (Host)", True, (255, 255, 0))
                t3 = self.font.render("Press [2] for PLAYER 2 (Guest)", True, (0, 255, 255))
                self.screen.blit(t1, (WW//2 - t1.get_width()//2, WH//2 - 100))
                self.screen.blit(t2, (WW//2 - t2.get_width()//2, WH//2))
                self.screen.blit(t3, (WW//2 - t3.get_width()//2, WH//2 + 50))
        
        else:
            # Playfield
            pygame.draw.rect(self.screen, (30,30,50), (50, 50, GW*BS, GH*BS))
            
            if self.screen_mode in ["playing", "countdown"]:
                for y, r in enumerate(self.grid):
                    for x, c in enumerate(r):
                        if c: 
                            pygame.draw.rect(self.screen, c, (50+x*BS, 50+y*BS, BS, BS))
                            pygame.draw.rect(self.screen, (255,255,255), (50+x*BS, 50+y*BS, BS, BS), 1)
                if self.screen_mode == "playing":
                    for bx, by in self.shape[0]:
                        pygame.draw.rect(self.screen, self.shape[1], (50+(self.pos[0]+bx)*BS, 50+(self.pos[1]+by)*BS, BS, BS)); pygame.draw.rect(self.screen, (255,255,255), (50+(self.pos[0]+bx)*BS, 50+(self.pos[1]+by)*BS, BS, BS), 1)
            
            # Sidebar
            if self.font:
                x_off = GW*BS + 100
                self.screen.blit(self.font.render(f"ROLE: {self.fb.role.upper()}", True, (255,255,255)), (x_off, 50))
                self.screen.blit(self.font.render(f"OPPONENT: {self.fb.opponent_status}", True, (0,255,0) if self.fb.opponent_status=='alive' else (255,50,50)), (x_off, 100))
                
                if self.screen_mode == "lobby":
                    p1_c = (0, 255, 0) if self.fb.p1_ready else (255, 50, 50)
                    p2_c = (0, 255, 0) if self.fb.p2_ready else (255, 50, 50)
                    self.screen.blit(self.font.render(f"P1: {'READY' if self.fb.p1_ready else 'WAITING'}", True, p1_c), (x_off, 200))
                    self.screen.blit(self.font.render(f"P2: {'READY' if self.fb.p2_ready else 'WAITING'}", True, p2_c), (x_off, 240))
                    msg = "PRESS ENTER TO READY!" if not self.is_ready else "WAITING..."
                    self.screen.blit(self.font.render(msg, True, (255, 255, 0)), (WW//2 - 100, WH - 100))
                
                elif self.screen_mode == "countdown" and self.huge_font:
                    cd = 3 - int(time.time() - self.fb.countdown_start)
                    txt_str = str(max(1, cd)) if cd > 0 else "GO!"
                    s = self.huge_font.render(txt_str, True, (255, 255, 255))
                    self.screen.blit(s, (WW//2-s.get_width()//2, WH//2-s.get_height()//2))

        pygame.display.flip()

if __name__ == "__main__":
    try: app = TetrisV39(); asyncio.run(app.run())
    except: 
        err = traceback.format_exc()
        with open("v39_error.log", "w") as f: f.write(err)
        print(err); input("CRASH! Press Enter...")
