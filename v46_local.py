
import pygame
import random
import json
import asyncio
import sys
import os
import time
import traceback
import urllib.request

# --- V46 - THE "RECOVERY" BUILD ---
# Based exactly on V43 which worked for the user.
PID = os.getpid()
LOG_FILE = f"v46_log_{PID}.txt"

def log(msg):
    try:
        ts = time.strftime('%H:%M:%S')
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
            f.flush()
    except: pass
    print(f"[V46] {msg}")

log("Application starting...")

class FirebaseManagerV46:
    def __init__(self, db_url):
        self.db_url = db_url.rstrip('/')
        self.room_id = "battle_v46"
        self.role = None 
        self.opp_role = None
        self.connected = False
        self.p1_ready = False
        self.p2_ready = False
        self.room_state = "waiting"
        self.countdown_start = 0
        self.pending_garbage = 0
        self.total_received = 0

    def _req(self, url, method="GET", data=None):
        try:
            req = urllib.request.Request(url, method=method)
            if data:
                req.add_header('Content-Type', 'application/json')
                body = json.dumps(data).encode('utf-8')
            else: body = None
            with urllib.request.urlopen(req, data=body, timeout=4) as r:
                return json.loads(r.read().decode('utf-8'))
        except: return None

    async def pick(self, role):
        self.role = role
        self.opp_role = "p2" if role == "p1" else "p1"
        url = f"{self.db_url}/battles/{self.room_id}.json"
        if role == "p1":
            d = {"state":"waiting", "p1":{"ready":False, "attack_queue":0}, "p2":{"ready":False, "attack_queue":0}, "last_update":time.time(), "countdown_start":0}
            await asyncio.to_thread(self._req, url, "PUT", d)
        else:
            await asyncio.to_thread(self._req, f"{self.db_url}/battles/{self.room_id}/p2.json", "PATCH", {"ready":False})
        self.connected = True

    async def poll(self):
        if not self.connected: return
        data = await asyncio.to_thread(self._req, f"{self.db_url}/battles/{self.room_id}.json")
        if data:
            self.room_state = data.get('state', 'waiting')
            self.countdown_start = data.get('countdown_start', 0)
            self.p1_ready = data.get('p1', {}).get('ready', False)
            self.p2_ready = data.get('p2', {}).get('ready', False)
            
            opp_data = data.get(self.opp_role, {})
            remote_q = opp_data.get('attack_queue', 0)
            if remote_q > self.total_received:
                self.pending_garbage += (remote_q - self.total_received)
                self.total_received = remote_q
        
        if self.role == "p1":
             await asyncio.to_thread(self._req, f"{self.db_url}/battles/{self.room_id}.json", "PATCH", {"last_update": time.time()})

WW, WH = 900, 600
GW, GH = 10, 20
BS = 26
T_SHAPES = {'I': [[(0,0),(1,0),(2,0),(3,0)],(0,255,255)], 'O': [[(0,0),(1,0),(0,1),(1,1)],(255,255,0)], 'T': [[(1,0),(0,1),(1,1),(2,1)],(128,0,128)], 'S': [[(1,0),(2,0),(0,1),(1,1)],(0,255,0)], 'Z': [[(0,0),(1,0),(1,1),(2,1)],(255,0,0)], 'J': [[(0,0),(0,1),(1,1),(2,1)],(0,0,255)], 'L': [[(2,0),(0,1),(1,1),(2,1)],(255,165,0)]}

class TetrisV46:
    def __init__(self):
        pygame.init()
        try: pygame.mixer.quit()
        except: pass
        self.screen = pygame.display.set_mode((WW, WH))
        pygame.display.set_caption(f"MARIO TETRIS V46 - PID:{PID}")
        self.clock = pygame.time.Clock()
        self.fb = FirebaseManagerV46("https://mario-tetris-game-default-rtdb.firebaseio.com/")
        self.mode = "menu" # menu, lobby, play
        self.font = pygame.font.SysFont("Arial", 24)
        self.huge_font = pygame.font.SysFont("Arial", 100)
        self.reset_game()

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
                    if self.mode == "menu":
                        if e.key == pygame.K_1: await self.fb.pick("p1"); self.mode = "lobby"
                        if e.key == pygame.K_2: await self.fb.pick("p2"); self.mode = "lobby"
                        if e.key == pygame.K_SPACE: 
                            import subprocess
                            abs_path = os.path.abspath(__file__)
                            log(f"Spawning sibling via subprocess: {abs_path}")
                            subprocess.Popen([sys.executable, abs_path])
                    elif self.mode == "lobby" and e.key == pygame.K_RETURN:
                        r = not (self.fb.p1_ready if self.fb.role=="p1" else self.fb.p2_ready)
                        await asyncio.to_thread(self.fb._req, f"{self.fb.db_url}/battles/{self.fb.room_id}/{self.fb.role}.json", "PATCH", {"ready": r})
                    elif self.mode == "play":
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

            if self.mode != "menu":
                await self.fb.poll()
                if self.fb.p1_ready and self.fb.p2_ready and self.fb.role == "p1" and self.fb.room_state == "waiting":
                    await asyncio.to_thread(self.fb._req, f"{self.fb.db_url}/battles/{self.fb.room_id}.json", "PATCH", {"state":"countdown", "countdown_start":time.time()})
                
                if self.fb.room_state == "countdown":
                    if self.mode == "lobby": 
                        self.mode = "play"
                        self.reset_game()
                
                if self.mode == "play":
                    # Garbage Check
                    if self.fb.pending_garbage > 0:
                        for _ in range(int(self.fb.pending_garbage)):
                            self.grid.pop(0); h = random.randint(0, GW-1)
                            self.grid.append([(100,100,100) if x!=h else None for x in range(GW)])
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
                            if c > 0:
                                cur_atk = (await asyncio.to_thread(self.fb._req, f"{self.fb.db_url}/battles/{self.fb.room_id}/{self.fb.role}.json")).get('attack_queue', 0)
                                await asyncio.to_thread(self.fb._req, f"{self.fb.db_url}/battles/{self.fb.room_id}/{self.fb.role}.json", "PATCH", {"attack_queue": cur_atk + c})
                            self.pos = [GW//2-1, 0]; self.shape = self.spawn()
                            if self.collide(self.pos, self.shape): self.reset_game()

            self.draw()
            await asyncio.sleep(0.01)

    def draw(self):
        self.screen.fill((10, 10, 15))
        if self.mode == "menu":
            self.screen.blit(self.font.render("V46 - BATTLE [READY]", True, (255,255,255)), (100, 100))
            self.screen.blit(self.font.render("Press [1] for P1, [2] for P2", True, (255,255,0)), (100, 150))
            self.screen.blit(self.font.render("Press [SPACE] for 2nd Window", True, (0,255,255)), (100, 200))
        else:
            pygame.draw.rect(self.screen, (30,30,50), (50, 50, GW*BS, GH*BS))
            for y, r in enumerate(self.grid):
                for x, c in enumerate(r):
                    if c: pygame.draw.rect(self.screen, c, (50+x*BS, 50+y*BS, BS, BS))
            if self.mode == "play":
                for bx, by in self.shape[0]:
                    pygame.draw.rect(self.screen, self.shape[1], (50+(self.pos[0]+bx)*BS, 50+(self.pos[1]+by)*BS, BS, BS))
            
            xo = GW*BS + 100
            self.screen.blit(self.font.render(f"I AM: {self.fb.role.upper()}", True, (255,255,255)), (xo, 50))
            p1c = (0,255,0) if self.fb.p1_ready else (255,0,0)
            p2c = (0,255,0) if self.fb.p2_ready else (255,0,0)
            self.screen.blit(self.font.render(f"P1: {'READY' if self.fb.p1_ready else 'WAIT'}", True, p1c), (xo, 100))
            self.screen.blit(self.font.render(f"P2: {'READY' if self.fb.p2_ready else 'WAIT'}", True, p2c), (xo, 130))
            
            if self.fb.room_state == "countdown":
                cd = 3 - int(time.time() - self.fb.countdown_start)
                txt = str(max(1, cd)) if cd > 0 else "GO!"
                s = self.huge_font.render(txt, True, (255, 255, 255))
                self.screen.blit(s, (WW//2-s.get_width()//2, WH//2-s.get_height()//2))

        pygame.display.flip()

if __name__ == "__main__":
    try: asyncio.run(TetrisV46().run())
    except: 
        with open(f"crash_v46_{PID}.txt", "w") as f: f.write(traceback.format_exc())
        input("CRASH")
