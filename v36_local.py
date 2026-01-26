
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

# --- V36 ARGUMENT & LOGGING ---
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

class FirebaseManagerV36:
    def __init__(self, db_url, forced_role=None):
        self.db_url = db_url.rstrip('/')
        self.room_id = "battle_v36"
        self.player_slot = forced_role if forced_role else "p1"
        self.opp_slot = "p2" if self.player_slot == "p1" else "p1"
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

    async def join(self):
        log(f"Joining as {self.player_slot.upper()}...")
        url = f"{self.db_url}/battles/{self.room_id}.json"
        
        # If we are P1, we initialize the room if it's dead
        if self.player_slot == "p1":
            data = await asyncio.to_thread(self._sync_request, url)
            curr_time = time.time()
            if not data or curr_time - data.get('last_update', 0) > 600:
                init_data = {
                    "state": "waiting", 
                    "p1": {"status": "alive", "attack_queue": 0, "ready": False}, 
                    "p2": {"status": "offline", "attack_queue": 0, "ready": False}, 
                    "countdown_start": 0,
                    "last_update": curr_time
                }
                await asyncio.to_thread(self._sync_request, url, "PUT", init_data)
            else:
                await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}/p1.json", "PATCH", {"status": "alive", "ready": False})
        else:
            # We are P2, just mark ourselves alive
            await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}/p2.json", "PATCH", {"status": "alive", "ready": False})
            
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

class TetrisV36:
    def __init__(self, forced_role):
        pygame.init()
        self.screen = pygame.display.set_mode((WW, WH))
        role_label = forced_role.upper() if forced_role else "AUTO"
        pygame.display.set_caption(f"Mario Tetris V36 - ROLE: {role_label}")
        self.clock = pygame.time.Clock()
        self.reset_game()
        self.fb = FirebaseManagerV36("https://mario-tetris-game-default-rtdb.firebaseio.com/", forced_role)
        self.role = "CONNECTING..."
        self.font = pygame.font.SysFont("Arial", 22)
        self.huge_font = pygame.font.SysFont("Arial", 100)
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

    async def auto_join(self):
        self.role = await self.fb.join()

    def draw(self):
        self.screen.fill((15, 15, 25))
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
            txt = str(max(1, cd)) if cd > 0 else "GO!"
            s = self.huge_font.render(txt, True, (255, 255, 255))
            self.screen.blit(s, (WW//2-s.get_width()//2, WH//2-s.get_height()//2))
        pygame.display.flip()

if __name__ == "__main__":
    try: app = TetrisV36(args.role); asyncio.run(app.run())
    except: log(traceback.format_exc()); input("CRASH")
