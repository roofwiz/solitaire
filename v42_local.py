
import pygame
import random
import json
import asyncio
import sys
import os
import time
import traceback
import urllib.request

# --- V42 ULTIMATE STABILITY ---
PID = os.getpid()
LOG_FILE = f"debug_v42_{PID}.log"

def log(msg):
    try:
        ts = time.strftime('%H:%M:%S')
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
            f.flush()
    except: pass
    print(f"[V42][PID:{PID}] {msg}")

log("Application started.")

class FirebaseManagerV42:
    def __init__(self, db_url):
        self.db_url = db_url.rstrip('/')
        self.room_id = "battle_v42"
        self.role = None 
        self.opp_role = None
        self.connected = False
        self.room_state = "waiting"
        self.countdown_start = 0
        self.p1_ready = False
        self.p2_ready = False
        self.poll_time = 0

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
        log(f"Claiming {role}...")
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
        return True

    async def poll(self):
        if not self.connected: return
        t = time.time()
        if t - self.poll_time < 0.6: return
        self.poll_time = t
        
        data = await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}.json")
        if not data: return
        
        self.room_state = data.get('state', 'waiting')
        self.countdown_start = data.get('countdown_start', 0)
        self.p1_ready = data.get('p1', {}).get('ready', False)
        self.p2_ready = data.get('p2', {}).get('ready', False)
        
        opp_data = data.get(self.opp_role, {})
        remote_q = opp_data.get('attack_queue', 0)
        self.pending_garbage = 0
        if not hasattr(self, 'lines_total'): self.lines_total = remote_q
        if remote_q > self.lines_total:
            self.pending_garbage = remote_q - self.lines_total
            self.lines_total = remote_q
            
        if self.role == "p1":
             await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}.json", "PATCH", {"last_update": time.time()})

    async def set_ready(self, b):
        await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}/{self.role}.json", "PATCH", {"ready": b})

    async def send_attack(self, lines):
        data = await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}/{self.role}.json")
        cur = data.get('attack_queue', 0) if data else 0
        await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}/{self.role}.json", "PATCH", {"attack_queue": cur + lines})

# --- PIECES ---
WW, WH = 950, 650
GW, GH = 10, 20
BS = 28
T_SHAPES = {'I': [[(0,0),(1,0),(2,0),(3,0)],(0,255,255)], 'O': [[(0,0),(1,0),(0,1),(1,1)],(255,255,0)], 'T': [[(1,0),(0,1),(1,1),(2,1)],(128,0,128)], 'S': [[(1,0),(2,0),(0,1),(1,1)],(0,255,0)], 'Z': [[(0,0),(1,0),(1,1),(2,1)],(255,0,0)], 'J': [[(0,0),(0,1),(1,1),(2,1)],(0,0,255)], 'L': [[(2,0),(0,1),(1,1),(2,1)],(255,165,0)]}

class TetrisV42:
    def __init__(self):
        log("Init Start.")
        pygame.init()
        # ABSOLUTE NO SOUND FOR COMPATIBILITY
        try: pygame.mixer.quit()
        except: pass
        
        self.screen = pygame.display.set_mode((WW, WH))
        pygame.display.set_caption(f"MARIO TETRIS V42 [PID {PID}]")
        self.clock = pygame.time.Clock()
        self.fb = FirebaseManagerV42("https://mario-tetris-game-default-rtdb.firebaseio.com/")
        self.reset_game()
        
        try:
            self.font = pygame.font.SysFont("Arial", 28)
            self.huge_font = pygame.font.SysFont("Arial", 120)
        except:
            self.font = None
            self.huge_font = None

        self.mode = "menu" # menu, lobby, countdown, playing
        self.ready_state = False

    def reset_game(self):
        self.grid = [[None for _ in range(GW)] for _ in range(GH)]
        self.bag = []
        self.pos = [GW//2-1, 0]
        self.piece = self.spawn()
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
        log("Run start.")
        while True:
            dt = self.clock.tick(60)/1000.0
            t_now = time.time()
            
            for e in pygame.event.get():
                if e.type == pygame.QUIT: return
                if e.type == pygame.KEYDOWN:
                    if self.mode == "menu":
                        if e.key == pygame.K_1:
                            await self.fb.pick_role("p1")
                            self.mode = "lobby"
                        if e.key == pygame.K_2:
                            await self.fb.pick_role("p2")
                            self.mode = "lobby"
                    elif self.mode == "lobby":
                        if e.key == pygame.K_RETURN:
                            self.ready_state = not self.ready_state
                            await self.fb.set_ready(self.ready_state)
                    elif self.mode == "playing":
                        if e.key == pygame.K_LEFT: 
                            self.pos[0]-=1
                            if self.collide(self.pos, self.piece): self.pos[0]+=1
                        if e.key == pygame.K_RIGHT: 
                            self.pos[0]+=1
                            if self.collide(self.pos, self.piece): self.pos[0]-=1
                        if e.key == pygame.K_UP:
                            old = [list(b) for b in self.piece[0]]
                            self.piece[0] = [(-by, bx) for bx, by in old]
                            if self.collide(self.pos, self.piece): self.piece[0] = old

            if self.mode != "menu":
                await self.fb.poll()
                if self.mode == "lobby" and self.fb.room_state == "countdown": self.mode = "countdown"
                if self.mode == "countdown" and t_now - self.fb.countdown_start > 3.0: 
                    self.mode = "playing"; self.reset_game()
                if self.mode == "playing":
                    # Gravity
                    self.fall_dt += dt
                    if self.fall_dt > 0.6:
                        self.fall_dt = 0; self.pos[1] += 1
                        if self.collide(self.pos, self.piece):
                            self.pos[1] -= 1
                            for bx, by in self.piece[0]:
                                if 0 <= self.pos[1]+by < GH: self.grid[self.pos[1]+by][self.pos[0]+bx] = self.piece[1]
                            new_g = [r for r in self.grid if any(c is None for c in r)]
                            c = GH - len(new_g)
                            while len(new_g) < GH: new_g.insert(0, [None]*GW)
                            self.grid = new_g
                            if c > 0: asyncio.create_task(self.fb.send_attack(c))
                            self.pos = [GW//2-1, 0]; self.piece = self.spawn()
                
                # Check for Countdown Start (P1 only)
                if self.mode == "lobby" and self.fb.p1_ready and self.fb.p2_ready and self.fb.role == "p1" and self.fb.room_state == "waiting":
                    await asyncio.to_thread(self.fb._sync_request, f"{self.fb.db_url}/battles/{self.fb.room_id}.json", "PATCH", {"state": "countdown", "countdown_start": time.time()})

            self.draw(); await asyncio.sleep(0.01)

    def draw(self):
        self.screen.fill((10, 10, 20))
        if self.mode == "menu":
            if self.font:
                self.screen.blit(self.font.render("SELECT ROLE:", True, (255, 255, 255)), (WW//2-100, 200))
                self.screen.blit(self.font.render("[1] Player 1", True, (255, 255, 0)), (WW//2-100, 250))
                self.screen.blit(self.font.render("[2] Player 2", True, (0, 255, 255)), (WW//2-100, 300))
        else:
            pygame.draw.rect(self.screen, (30, 30, 50), (50, 50, GW*BS, GH*BS))
            for y, r in enumerate(self.grid):
                for x, c in enumerate(r):
                    if c: pygame.draw.rect(self.screen, c, (50+x*BS, 50+y*BS, BS, BS))
            if self.mode == "playing":
                for bx, by in self.piece[0]:
                    pygame.draw.rect(self.screen, self.piece[1], (50+(self.pos[0]+bx)*BS, 50+(self.pos[1]+by)*BS, BS, BS))
            if self.font:
                xo = GW*BS + 100
                self.screen.blit(self.font.render(f"I AM: {self.fb.role.upper()}", True, (255,255,255)), (xo, 50))
                p1c = (0,255,0) if self.fb.p1_ready else (255,0,0)
                p2c = (0,255,0) if self.fb.p2_ready else (255,0,0)
                self.screen.blit(self.font.render(f"P1: {'READY' if self.fb.p1_ready else 'WAIT'}", True, p1c), (xo, 150))
                self.screen.blit(self.font.render(f"P2: {'READY' if self.fb.p2_ready else 'WAIT'}", True, p2c), (xo, 190))
            if self.mode == "countdown" and self.huge_font:
                cd = 3 - int(time.time() - self.fb.countdown_start)
                s = self.huge_font.render(str(max(1, cd)) if cd > 0 else "GO!", True, (255,255,255))
                self.screen.blit(s, (WW//2-s.get_width()//2, WH//2-s.get_height()//2))

        pygame.display.flip()

if __name__ == "__main__":
    try: app = TetrisV42(); asyncio.run(app.run())
    except: 
        err = traceback.format_exc()
        with open(f"crash_{PID}.log", "w") as f: f.write(err)
        input("CRASH")
