
import pygame
import random
import json
import asyncio
import sys
import os
import time
import traceback
import urllib.request

# --- V41 MULTI-WINDOW FIX ---
# We use a unique log file for every single instance to avoid Windows file locks
PID = os.getpid()
DEBUG_FILE = f"debug_pid_{PID}.log"

def log(msg):
    try:
        ts = time.strftime('%H:%M:%S')
        with open(DEBUG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
            f.flush()
    except: pass
    print(f"[PID {PID}] {msg}")

log("Application started.")

class FirebaseManagerV41:
    def __init__(self, db_url):
        self.db_url = db_url.rstrip('/')
        self.room_id = "battle_v41" # Fresh room
        self.role = None 
        self.opp_role = None
        self.connected = False
        self.room_state = "waiting"
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
        log(f"Attempting to claim {role}...")
        self.role = role
        self.opp_role = "p2" if role == "p1" else "p1"
        url = f"{self.db_url}/battles/{self.room_id}.json"
        
        if self.role == 'p1':
            init_data = {
                "state": "waiting", 
                "p1": {"status": "alive", "attack_queue": 0, "ready": False}, 
                "p2": {"status": "offline", "attack_queue": 0, "ready": False}, 
                "countdown_start": 0,
                "last_update": time.time()
            }
            await asyncio.to_thread(self._sync_request, url, "PUT", init_data)
        else:
            await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}/p2.json", "PATCH", {"status": "alive", "ready": False})
        
        self.connected = True
        log(f"Role {role} confirmed.")

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

class TetrisV41:
    def __init__(self):
        log("Init Pygame...")
        # CRITICAL: We skip audio to prevent second-instance initialization failure
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.init()
        # If the sound system is locked by window 1, window 2 might crash. We'll be safe.
        try: pygame.mixer.quit() 
        except: pass
        
        self.screen = pygame.display.set_mode((WW, WH))
        pygame.display.set_caption(f"Mario Tetris V41 (PID: {PID})")
        self.clock = pygame.time.Clock()
        self.reset_game()
        self.fb = FirebaseManagerV41("https://mario-tetris-game-default-rtdb.firebaseio.com/")
        
        try:
            self.font = pygame.font.SysFont("Arial", 28)
            self.huge_font = pygame.font.SysFont("Arial", 120)
        except:
            self.font = None
            self.huge_font = None

        self.screen_mode = "menu" # menu, connecting, lobby, countdown, playing
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
        log("Loop started.")
        while True:
            dt = self.clock.tick(60)/1000.0
            t_now = time.time()
            
            for e in pygame.event.get():
                if e.type == pygame.QUIT: return
                if e.type == pygame.KEYDOWN:
                    if self.screen_mode == "menu":
                        if e.key == pygame.K_1:
                            self.screen_mode = "connecting"
                            asyncio.create_task(self.fb.pick_role("p1"))
                        if e.key == pygame.K_2:
                            self.screen_mode = "connecting"
                            asyncio.create_task(self.fb.pick_role("p2"))
                        # Falling back to the batch file
                        if e.key == pygame.K_n:
                            log("User requested another window launch.")
                            os.startfile(__file__)
                    
                    elif self.screen_mode == "lobby":
                        if e.key == pygame.K_RETURN:
                            self.is_ready = not self.is_ready
                            asyncio.create_task(self.fb.set_ready(self.is_ready))
                    
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
                
                if self.screen_mode == "connecting" and self.fb.connected:
                    self.screen_mode = "lobby"
                
                if self.screen_mode == "lobby":
                    if self.fb.room_state == "countdown":
                        self.screen_mode = "countdown"
                    if self.fb.p1_ready and self.fb.p2_ready and self.fb.role == "p1" and self.fb.room_state == "waiting":
                        asyncio.create_task(self.fb.start_countdown())
                
                elif self.screen_mode == "countdown":
                    diff = t_now - self.fb.countdown_start
                    if diff > 3.0:
                        if self.fb.role == "p1": asyncio.create_task(self.fb.trigger_start())
                        self.screen_mode = "playing"
                        self.reset_game()
                
                elif self.screen_mode == "playing":
                    if self.fb.room_state == "waiting": self.screen_mode = "lobby"
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
        
        if self.screen_mode == "menu":
            if self.font:
                t1 = self.font.render("SELECT YOUR ROLE:", True, (255,255,255))
                t2 = self.font.render("Press [1] for PLAYER 1", True, (255, 255, 0))
                t3 = self.font.render("Press [2] for PLAYER 2", True, (0, 255, 255))
                t4 = self.font.render("Press [N] to launch another window!", True, (150, 150, 150))
                self.screen.blit(t1, (WW//2 - t1.get_width()//2, WH//2 - 120))
                self.screen.blit(t2, (WW//2 - t2.get_width()//2, WH//2 - 20))
                self.screen.blit(t3, (WW//2 - t3.get_width()//2, WH//2 + 30))
                self.screen.blit(t4, (WW//2 - t4.get_width()//2, WH//2 + 100))
        
        elif self.screen_mode == "connecting":
            if self.font:
                t = self.font.render("CONNECTING...", True, (255, 255, 0))
                self.screen.blit(t, (WW//2 - t.get_width()//2, WH//2))
        
        else:
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
            
            if self.font:
                xo = GW*BS + 100
                self.screen.blit(self.font.render(f"ROLE: {self.fb.role.upper()}", True, (255,255,255)), (xo, 50))
                self.screen.blit(self.font.render(f"P1: {'READY' if self.fb.p1_ready else 'WAIT'}", True, (0,255,0) if self.fb.p1_ready else (255,50,50)), (xo, 150))
                self.screen.blit(self.font.render(f"P2: {'READY' if self.fb.p2_ready else 'WAIT'}", True, (0,255,0) if self.fb.p2_ready else (255,50,50)), (xo, 190))
                if self.screen_mode == "lobby":
                    msg = "PRESS ENTER TO READY!" if not self.is_ready else "WAITING..."
                    self.screen.blit(self.font.render(msg, True, (255, 255, 0)), (WW//2-120, WH-50))
                elif self.screen_mode == "countdown" and self.huge_font:
                    cd = 3 - int(time.time() - self.fb.countdown_start)
                    txt = str(max(1, cd)) if cd > 0 else "GO!"
                    s = self.huge_font.render(txt, True, (255, 255, 255))
                    self.screen.blit(s, (WW//2-s.get_width()//2, WH//2-s.get_height()//2))

        pygame.display.flip()

if __name__ == "__main__":
    try: app = TetrisV41(); asyncio.run(app.run())
    except Exception as e:
        with open(f"crash_{PID}.log", "w") as f: f.write(traceback.format_exc())
        input(f"CRASH! Error: {e}")
