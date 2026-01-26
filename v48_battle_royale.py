
import pygame
import random
import json
import asyncio
import sys
import os
import time
import traceback
import urllib.request
import subprocess

# --- V48 - "THE BATTLE ROYALE" ---
# Features: Side-by-Side Dual Grids, Koopa Stomping, Mario Themed
PID = os.getpid()
LOG_FILE = f"v48_log_{PID}.txt"

def log(msg):
    try:
        ts = time.strftime('%H:%M:%S')
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
            f.flush()
    except: pass
    print(f"[V48] {msg}")

class FirebaseManagerV48:
    def __init__(self, db_url):
        self.db_url = db_url.rstrip('/')
        self.room_id = "battle_v48"
        self.role = None # p1 or p2
        self.opp_role = None
        self.connected = False
        self.room_state = "waiting"
        self.countdown_start = 0
        self.p1_ready = False
        self.p2_ready = False
        self.opponent_status = "offline"
        self.opp_grid_raw = "0" * 200
        self.pending_garbage = 0
        self.total_received = 0
        self.poll_time = 0

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
            d = {
                "state":"waiting", 
                "p1":{"ready":False, "attack_queue":0, "grid_comp":"0"*200, "last_update":time.time()}, 
                "p2":{"ready":False, "attack_queue":0, "grid_comp":"0"*200, "status":"offline"},
                "countdown_start":0
            }
            await asyncio.to_thread(self._req, url, "PUT", d)
        else:
            await asyncio.to_thread(self._req, f"{self.db_url}/battles/{self.room_id}/p2.json", "PATCH", {"status":"alive", "ready":False, "grid_comp":"0"*200})
        self.connected = True

    async def poll(self):
        if not self.connected: return
        t = time.time()
        if t - self.poll_time < 0.5: return # Polling limit
        self.poll_time = t
        
        data = await asyncio.to_thread(self._req, f"{self.db_url}/battles/{self.room_id}.json")
        if data:
            self.room_state = data.get('state', 'waiting')
            self.countdown_start = data.get('countdown_start', 0)
            self.p1_ready = data.get('p1', {}).get('ready', False)
            self.p2_ready = data.get('p2', {}).get('ready', False)
            
            opp_data = data.get(self.opp_role, {})
            self.opponent_status = opp_data.get('status', 'offline')
            self.opp_grid_raw = opp_data.get('grid_comp', "0" * 200)
            
            remote_q = opp_data.get('attack_queue', 0)
            if remote_q > self.total_received:
                self.pending_garbage += (remote_q - self.total_received)
                self.total_received = remote_q

    async def sync_my_grid(self, grid_str):
        if not self.connected: return
        await asyncio.to_thread(self._req, f"{self.db_url}/battles/{self.room_id}/{self.role}.json", "PATCH", {"grid_comp": grid_str})

    async def set_ready(self, b):
        await asyncio.to_thread(self._req, f"{self.db_url}/battles/{self.room_id}/{self.role}.json", "PATCH", {"ready": b})

    async def send_attack(self, lines):
        data = await asyncio.to_thread(self._req, f"{self.db_url}/battles/{self.room_id}/{self.role}.json")
        cur = data.get('attack_queue', 0) if data else 0
        await asyncio.to_thread(self._req, f"{self.db_url}/battles/{self.room_id}/{self.role}.json", "PATCH", {"attack_queue": cur + lines})

# --- CONSTANTS ---
WW, WH = 950, 700
GW, GH = 10, 20
BS = 28
# Piece ID Mapping for Compression
# 0: Empty, 1-7: Tetris Shapes, 8: Garbage/Brick, 9: Koopa
ID_TO_COLOR = {
    '1': (0,255,255), '2': (255,255,0), '3': (128,0,128), 
    '4': (0,255,0), '5': (255,0,0), '6': (0,0,255), '7': (255,165,0),
    'G': (120, 120, 120), 'K': (0, 255, 0) # Green Koopa
}
COLOR_TO_ID = {v: k for k, v in ID_TO_COLOR.items()}

T_SHAPES = {
    'I': [[(0,0),(1,0),(2,0),(3,0)], '1'], 
    'O': [[(0,0),(1,0),(0,1),(1,1)], '2'], 
    'T': [[(1,0),(0,1),(1,1),(2,1)], '3'], 
    'S': [[(1,0),(2,0),(0,1),(1,1)], '4'], 
    'Z': [[(0,0),(1,0),(1,1),(2,1)], '5'], 
    'J': [[(0,0),(0,1),(1,1),(2,1)], '6'], 
    'L': [[(2,0),(0,1),(1,1),(2,1)], '7']
}

class TetrisV48:
    def __init__(self):
        pygame.init()
        try: pygame.mixer.quit()
        except: pass
        self.screen = pygame.display.set_mode((WW, WH))
        pygame.display.set_caption("MARIO BATTLE ROYALE V48")
        self.clock = pygame.time.Clock()
        self.fb = FirebaseManagerV48("https://mario-tetris-game-default-rtdb.firebaseio.com/")
        self.font = pygame.font.SysFont("Arial", 22)
        self.mode = "menu"
        self.is_ready = False
        self.load_assets()
        self.reset_game()

    def load_assets(self):
        self.sheets = {}
        if os.path.exists("assets/marioallsprite.png"):
            self.sheets['mario'] = pygame.image.load("assets/marioallsprite.png").convert_alpha()
        if os.path.exists("assets/blocks.png"):
            self.sheets['blocks'] = pygame.image.load("assets/blocks.png").convert_alpha()
        
        self.imgs = {}
        if 'blocks' in self.sheets:
            self.imgs['brick'] = self.get_sprite(self.sheets['blocks'], 368, 112, 16, 16, BS/16)
            self.imgs['question'] = self.get_sprite(self.sheets['blocks'], 80, 112, 16, 16, BS/16)
        if 'mario' in self.sheets:
            self.imgs['koopa'] = self.get_sprite(self.sheets['mario'], 206, 242, 20, 27, BS/24)

    def get_sprite(self, sheet, x, y, w, h, s):
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.blit(sheet, (0, 0), (x, y, w, h))
        return pygame.transform.scale(surf, (int(w*s), int(h*s)))

    def reset_game(self):
        self.grid = [[None for _ in range(GW)] for _ in range(GH)]
        self.bag = []
        self.pos = [GW//2-1, 0]
        self.shape = self.spawn()
        self.fall_dt = 0
        self.koopa_timer = 0

    def spawn(self):
        if not self.bag: self.bag = list(T_SHAPES.keys()); random.shuffle(self.bag)
        s = self.bag.pop()
        return [list(T_SHAPES[s][0]), T_SHAPES[s][1]]

    def collide(self, p, s):
        for bx, by in s[0]:
            gx, gy = p[0]+bx, p[1]+by
            if gx < 0 or gx >= GW or gy >= GH or (gy >= 0 and self.grid[gy][gx]): return True
        return False

    def compress_grid(self):
        res = ""
        for r in self.grid:
            for c in r:
                if c is None: res += "0"
                else: res += COLOR_TO_ID.get(c, "G")
        return res

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
                        if e.key == pygame.K_SPACE: subprocess.Popen([sys.executable, os.path.abspath(__file__)])
                    elif self.mode == "lobby" and e.key == pygame.K_RETURN:
                        self.is_ready = not self.is_ready
                        await self.fb.set_ready(self.is_ready)
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
                    if self.mode == "lobby": self.mode = "play"; self.reset_game()
                
                if self.mode == "play":
                    # Sync my grid
                    asyncio.create_task(self.fb.sync_my_grid(self.compress_grid()))
                    
                    # Garbage Check
                    if self.fb.pending_garbage > 0:
                        for _ in range(int(self.fb.pending_garbage)):
                            self.grid.pop(0)
                            h = random.randint(0, GW-1)
                            self.grid.append([ID_TO_COLOR['G'] if x!=h else None for x in range(GW)])
                        self.fb.pending_garbage = 0
                    
                    # Random Koopa Spawn
                    self.koopa_timer += dt
                    if self.koopa_timer > 8.0:
                        self.koopa_timer = 0
                        rx, ry = random.randint(0, GW-1), random.randint(GH-6, GH-1)
                        if self.grid[ry][rx] is None: self.grid[ry][rx] = ID_TO_COLOR['K']

                    # Gravity
                    self.fall_dt += dt
                    if self.fall_dt > 0.6:
                        self.fall_dt = 0; self.pos[1] += 1
                        if self.collide(self.pos, self.shape):
                            self.pos[1] -= 1
                            for bx, by in self.shape[0]:
                                if 0 <= self.pos[1]+by < GH: self.grid[self.pos[1]+by][self.pos[0]+bx] = ID_TO_COLOR[self.shape[1]]
                            
                            # Line Clear & Stomp logic
                            stomp_count = 0
                            new_g = []
                            lines_cleared = 0
                            for r in self.grid:
                                if all(c is not None for c in r):
                                    lines_cleared += 1
                                    if 'K' in [COLOR_TO_ID.get(cell) for cell in r]: stomp_count += 1
                                else:
                                    new_g.append(r)
                            
                            while len(new_g) < GH: new_g.insert(0, [None]*GW)
                            self.grid = new_g
                            
                            attack = lines_cleared + (stomp_count * 2)
                            if attack > 0:
                                log(f"ATTACK: {attack} (Stomps: {stomp_count})")
                                asyncio.create_task(self.fb.send_attack(attack))
                            
                            self.pos = [GW//2-1, 0]; self.shape = self.spawn()
                            if self.collide(self.pos, self.shape): self.reset_game()

            self.draw()
            await asyncio.sleep(0.01)

    def draw(self):
        self.screen.fill((92, 148, 252))
        
        if self.mode == "menu":
            t = self.font.render("MARIO BATTLE ROYALE - Press [1] or [2]", True, (255,255,255))
            self.screen.blit(t, (WW//2-t.get_width()//2, 300))
        else:
            # My Grid (Left)
            self.draw_grid(100, 100, self.grid, self.pos if self.mode=="play" else None, self.shape if self.mode=="play" else None)
            # Opponent Grid (Right - Smaller)
            self.draw_opp_grid(500, 100, self.fb.opp_grid_raw)
            
            xo = 750
            self.screen.blit(self.font.render(f"ROLE: {self.fb.role.upper()}", True, (255,255,255)), (xo, 50))
            self.screen.blit(self.font.render(f"OPP: {self.fb.opponent_status}", True, (255,255,255)), (xo, 80))
            
            if self.fb.room_state == "countdown":
                cd = 3 - int(time.time() - self.fb.countdown_start)
                t = self.font.render(f"STARTING IN {max(1, cd)}...", True, (255,255,100))
                self.screen.blit(t, (WW//2-50, 50))

        pygame.display.flip()

    def draw_grid(self, ox, oy, grid, pos, shape):
        pygame.draw.rect(self.screen, (0,0,0,150), (ox, oy, GW*BS, GH*BS))
        for y, r in enumerate(grid):
            for x, c in enumerate(r):
                if c: self.draw_block(ox + x*BS, oy + y*BS, c, BS)
        # Piece
        if pos and shape:
            for bx, by in shape[0]:
                self.draw_block(ox + (pos[0]+bx)*BS, oy + (pos[1]+by)*BS, ID_TO_COLOR[shape[1]], BS, is_piece=True)

    def draw_opp_grid(self, ox, oy, raw):
        sbs = 18 # Smaller block size
        pygame.draw.rect(self.screen, (0,0,0,100), (ox, oy, GW*sbs, GH*sbs))
        for i, char in enumerate(raw):
            if char != '0':
                x = i % GW
                y = i // GW
                c = ID_TO_COLOR.get(char, (100,100,100))
                self.draw_block(ox + x*sbs, oy + y*sbs, c, sbs)

    def draw_block(self, x, y, color, size, is_piece=False):
        cid = COLOR_TO_ID.get(color)
        scale = size/BS
        if cid == 'G' and 'brick' in self.imgs:
            self.screen.blit(pygame.transform.scale(self.imgs['brick'], (int(size), int(size))), (x, y))
        elif cid == 'K' and 'koopa' in self.imgs:
            self.screen.blit(pygame.transform.scale(self.imgs['koopa'], (int(size), int(size))), (x, y))
        elif not is_piece and 'question' in self.imgs: # Falling pieces are plain, locked are question
            t = pygame.transform.scale(self.imgs['question'], (int(size), int(size)))
            t.fill(color, special_flags=pygame.BLEND_RGB_MULT)
            self.screen.blit(t, (x, y))
        else:
            pygame.draw.rect(self.screen, color, (x, y, size, size))
            pygame.draw.rect(self.screen, (255,255,255), (x, y, size, size), 1)

if __name__ == "__main__":
    try: asyncio.run(TetrisV48().run())
    except: 
        with open(f"crash_v48_{PID}.txt", "w") as f: f.write(traceback.format_exc())
        input("CRASH")
