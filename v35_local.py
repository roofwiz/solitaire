
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

# --- V35 PID LOGGING ---
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

with open(DEBUG_FILE, "a", encoding="utf-8") as f: f.write(f"\n--- SESSION START [PID:{PID}] ---\n")

class FirebaseManagerV35:
    def __init__(self, db_url):
        self.db_url = db_url.rstrip('/')
        self.room_id = "battle_v35" # Fresh room
        self.player_slot = "p1"
        self.opp_slot = "p2"
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
        except Exception as e:
            # log(f"REQ ERR: {e}")
            return None

    async def join(self):
        log("Looking for a battle slot...")
        url = f"{self.db_url}/battles/{self.room_id}.json"
        
        # We retry until we find a slot
        while not self.connected:
            data = await asyncio.to_thread(self._sync_request, url)
            curr_time = time.time()
            
            p1_status = data.get('p1', {}).get('status', 'offline') if data else 'offline'
            p2_status = data.get('p2', {}).get('status', 'offline') if data else 'offline'
            last_up = data.get('last_update', 0) if data else 0
            
            # If room is completely fresh or dead for 10 mins (reset stale rooms faster)
            if not data or curr_time - last_up > 600:
                log("Room is empty/stale. Claiming P1.")
                self.player_slot, self.opp_slot = 'p1', 'p2'
                init_data = {
                    "state": "waiting", 
                    "p1": {"status": "alive", "attack_queue": 0, "ready": False}, 
                    "p2": {"status": "offline", "attack_queue": 0, "ready": False}, 
                    "countdown_start": 0,
                    "last_update": curr_time
                }
                res = await asyncio.to_thread(self._sync_request, url, "PUT", init_data)
                if res: self.connected = True
            
            # If P1 is there, try P2
            elif p1_status == 'alive' and p2_status == 'offline':
                log("P1 is waiting. Joining as P2.")
                self.player_slot, self.opp_slot = 'p2', 'p1'
                res = await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}/p2.json", "PATCH", {"status": "alive", "attack_queue": 0, "ready": False})
                if res: self.connected = True
            
            # If P1 is dead/gone, take P1
            elif p1_status == 'offline':
                log("P1 slot is vacant. Joining as P1.")
                self.player_slot, self.opp_slot = 'p1', 'p2'
                res = await asyncio.to_thread(self._sync_request, f"{self.db_url}/battles/{self.room_id}/p1.json", "PATCH", {"status": "alive", "attack_queue": 0, "ready": False})
                if res: self.connected = True

            if not self.connected:
                log("Join failed/Room full. Retrying in 2s...")
                await asyncio.sleep(2)
        
        log(f"Success! I am {self.player_slot.upper()}")
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

class TetrisV35:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WW, WH))
        pygame.display.set_caption(f"Mario Tetris V35 - Battle (PID:{PID})")
        self.clock = pygame.time.Clock()
        self.reset_game()
        self.fb = FirebaseManagerV35("https://mario-tetris-game-default-rtdb.firebaseio.com/")
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
        log("Window open. Starting join task.")
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
            
            # Coordination
            if self.fb.room_state == "waiting":
                if self.fb.p1_ready and self.fb.p2_ready and self.fb.player_slot == "p1":
                    await self.fb.start_countdown()
            
            elif self.fb.room_state == "countdown":
                diff = t_now - self.fb.countdown_start
                if diff > 3.0:
                    if self.fb.player_slot == "p1": await self.fb.trigger_start()
                    # Client-side transition
                    if self.fb.room_state != "playing": # local state update
                        self.reset_game()
            
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
                        if self.collide(self.pos, self.shape): 
                            log("Loss detected! Resetting field.")
                            self.reset_game()

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
            msg = "PRESS ENTER TO READY!" if not self.is_ready else "WAITING FOR OPPONENT..."
            self.screen.blit(self.font.render(msg, True, (255, 255, 0)), (350, 300))
        elif self.fb.room_state == "countdown":
            cd = 3 - int(time.time() - self.fb.countdown_start)
            txt = str(max(1, cd)) if cd > 0 else "GO!"
            s = self.huge_font.render(txt, True, (255, 255, 255))
            self.screen.blit(s, (WW//2-s.get_width()//2, WH//2-s.get_height()//2))

        pygame.display.flip()

if __name__ == "__main__":
    try: app = TetrisV35(); asyncio.run(app.run())
    except: 
        log(traceback.format_exc())
        with open("CRITICAL_CRASH.txt", "w") as f: f.write(traceback.format_exc())
        input("CRASH")
