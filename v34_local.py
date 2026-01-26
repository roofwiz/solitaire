
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

# --- V34 LOGGING ---
DEBUG_FILE = "v34_lobby_log.txt"
def log(msg):
    try:
        ts = time.strftime('%H:%M:%S')
        full_msg = f"[{ts}] {msg}"
        with open(DEBUG_FILE, "a", encoding="utf-8") as f:
            f.write(full_msg + "\n")
            f.flush()
            os.fsync(f.fileno())
        print(full_msg)
    except: pass

with open(DEBUG_FILE, "w", encoding="utf-8") as f: f.write("--- Mario Tetris V34 START ---\n")

# --- NO-DEPENDENCY FIREBASE ---
class FirebaseManagerV34:
    def __init__(self, db_url):
        self.db_url = db_url.rstrip('/')
        self.room_id = "battle_v34"
        self.player_slot = "p1"
        self.opp_slot = "p2"
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

    async def join(self):
        log("Async Join Task Started.")
        url = f"{self.db_url}/battles/{self.room_id}.json"
        data = await asyncio.to_thread(self._sync_request, url)
        curr_time = time.time()
        
        if not data or (data.get('last_update', 0) and curr_time - data['last_update'] > 3600):
            log("Claiming P1 Role.")
            self.player_slot, self.opp_slot = 'p1', 'p2'
            init_data = {
                "state": "waiting", 
                "p1": {"status": "alive", "attack_queue": 0, "ready": False}, 
                "p2": {"status": "offline", "attack_queue": 0, "ready": False}, 
                "countdown_start": 0,
                "last_update": curr_time
            }
            await asyncio.to_thread(self._sync_request, url, "PUT", init_data)
        else:
            p2_status = data.get('p2', {}).get('status', 'offline')
            if p2_status == 'offline':
                log("Claiming P2 Role.")
                self.player_slot, self.opp_slot = 'p2', 'p1'
                await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}/p2.json", "PATCH", {"status": "alive", "attack_queue": 0, "ready": False})
            else:
                log("Room Full.")
                return "FULL"
        
        self.connected = True
        return self.player_slot.upper()

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
        
        opp_data = data.get(self.opp_slot, {})
        self.opponent_status = opp_data.get('status', 'offline')
        
        remote_q = opp_data.get('attack_queue', 0)
        if remote_q > self.lines_received_total:
            self.pending_garbage += (remote_q - self.lines_received_total)
            self.lines_received_total = remote_q
            
        if self.player_slot == "p1":
             await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}.json", "PATCH", {"last_update": time.time()})

    async def set_ready(self, ready):
        await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}/{self.player_slot}.json", "PATCH", {"ready": ready})

    async def start_countdown(self):
        if self.player_slot == 'p1':
            await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}.json", "PATCH", {"state": "countdown", "countdown_start": time.time()})

    async def trigger_start(self):
        if self.player_slot == 'p1':
             await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}.json", "PATCH", {"state": "playing"})

    async def send_attack(self, lines):
        data = await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}/{self.player_slot}.json")
        cur = data.get('attack_queue', 0) if data else 0
        await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}/{self.player_slot}.json", "PATCH", {"attack_queue": cur + lines})

# --- GAME ENGINE ---
WW, WH = 950, 650
GW, GH = 10, 20
BS = 28
T_SHAPES = {'I': [[(0,0),(1,0),(2,0),(3,0)],(0,255,255)], 'O': [[(0,0),(1,0),(0,1),(1,1)],(255,255,0)], 'T': [[(1,0),(0,1),(1,1),(2,1)],(128,0,128)], 'S': [[(1,0),(2,0),(0,1),(1,1)],(0,255,0)], 'Z': [[(0,0),(1,0),(1,1),(2,1)],(255,0,0)], 'J': [[(0,0),(0,1),(1,1),(2,1)],(0,0,255)], 'L': [[(2,0),(0,1),(1,1),(2,1)],(255,165,0)]}

class TetrisV34:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WW, WH))
        pygame.display.set_caption("Mario Tetris V34 - LOBBY REFIX")
        self.clock = pygame.time.Clock()
        self.grid = [[None for _ in range(GW)] for _ in range(GH)]
        self.bag = []
        self.pos = [GW//2-1, 0]
        self.shape = self.spawn()
        self.fb = FirebaseManagerV34("https://mario-tetris-game-default-rtdb.firebaseio.com/")
        self.role = "IDLE"
        self.font = pygame.font.SysFont("Arial", 22)
        self.huge_font = pygame.font.SysFont("Arial", 80)
        self.is_ready = False
        self.connecting = False

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
        log("Main Loop Initialized.")
        # Start Join Task immediately but don't AWAIT it here to keep window alive
        asyncio.create_task(self.auto_join())
        
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

            await self.fb.poll()
            
            if self.fb.room_state == "waiting":
                if self.fb.p1_ready and self.fb.p2_ready and self.fb.player_slot == "p1":
                    await self.fb.start_countdown()
            
            elif self.fb.room_state == "countdown":
                diff = t_now - self.fb.countdown_start
                if diff > 3.0:
                    if self.fb.player_slot == "p1": await self.fb.trigger_start()
                    # Client side start
                    self.grid = [[None for _ in range(GW)] for _ in range(GH)]
                    self.pos = [GW//2-1, 0]
                    self.shape = self.spawn()
            
            elif self.fb.room_state == "playing":
                if self.fb.pending_garbage > 0:
                    for _ in range(int(self.fb.pending_garbage)):
                        self.grid.pop(0); h = random.randint(0, GW-1); self.grid.append([(100,100,100) if x!=h else None for x in range(GW)])
                    self.fb.pending_garbage = 0
                
                self.fall_dt = getattr(self, "fall_dt", 0) + dt
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
                        if self.collide(self.pos, self.shape): self.grid = [[None]*GW]*GH

            self.draw(); await asyncio.sleep(0.01)

    async def auto_join(self):
        self.role = await self.fb.join()
        log(f"Role determined: {self.role}")

    def draw(self):
        self.screen.fill((10, 10, 20))
        # Draw Playfield
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

        # Labels
        self.screen.blit(self.font.render(f"ROLE: {self.role}", True, (255,255,255)), (350, 50))
        self.screen.blit(self.font.render(f"OPPONENT: {self.fb.opponent_status}", True, (0,255,0) if self.fb.opponent_status=='alive' else (255,0,0)), (350, 80))
        
        if self.fb.room_state == "waiting":
            p1_c = (0, 255, 0) if self.fb.p1_ready else (255, 50, 50)
            p2_c = (0, 255, 0) if self.fb.p2_ready else (255, 50, 50)
            self.screen.blit(self.font.render(f"P1 READY: {self.fb.p1_ready}", True, p1_c), (350, 200))
            self.screen.blit(self.font.render(f"P2 READY: {self.fb.p2_ready}", True, p2_c), (350, 240))
            msg = "PRESS ENTER TO READY!" if not self.is_ready else "WAITING..."
            self.screen.blit(self.font.render(msg, True, (255, 255, 0)), (350, 300))
        elif self.fb.room_state == "countdown":
            cd = 3 - int(time.time() - self.fb.countdown_start)
            txt = str(cd) if cd > 0 else "GO!"
            s = self.huge_font.render(txt, True, (255, 255, 255))
            self.screen.blit(s, (WW//2-s.get_width()//2, WH//2-s.get_height()//2))

        pygame.display.flip()

if __name__ == "__main__":
    try: app = TetrisV34(); asyncio.run(app.run())
    except: traceback.print_exc(); input("PAUSE")
