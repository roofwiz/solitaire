
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
import math

# --- V49 - "MARIO BATTLE ROYALE PRO" ---
# Features: 
# - Animated Enemies (Koopas, Spinies)
# - Interactive Stomping (Drops a row on opponent)
# - Dual Screen Synchronization
# - Refined NES Style UI

PID = os.getpid()
LOG_FILE = f"v49_log_{PID}.txt"

def log(msg):
    try:
        ts = time.strftime('%H:%M:%S')
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
            f.flush()
    except: pass
    print(f"[STABLE-PRO] {msg}")

class FirebaseManagerV49:
    def __init__(self, db_url):
        self.db_url = db_url.rstrip('/')
        self.room_id = "battle_mario_pro_stable"
        self.role = None 
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
            with urllib.request.urlopen(req, data=body, timeout=3) as r:
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
        if t - self.poll_time < 0.4: return 
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

# --- ENEMY CLASSES ---
class Enemy:
    def __init__(self, x, y, type_id):
        self.x = x
        self.y = y
        self.type_id = type_id # 'K'=Koopa, 'S'=Spiny, 'R'=RedKoopa
        self.frame = 0
        self.timer = 0
        self.dir = 1
        self.state = 'active'
        self.anim_timer = 0

    def update(self, dt, grid):
        self.anim_timer += dt
        if self.anim_timer > 0.2:
            self.anim_timer = 0
            self.frame = 1 - self.frame

        if self.state == 'active':
            # Horizontal patrol if on ground
            self.timer += dt
            if self.timer > 0.5:
                self.timer = 0
                nx = self.x + self.dir
                if 0 <= nx < 10 and grid[int(self.y)][nx] is None:
                    # check if ground below next
                    if int(self.y)+1 >= 20 or grid[int(self.y)+1][nx] is not None:
                        self.x = nx
                    else:
                        self.dir *= -1
                else:
                    self.dir *= -1

# --- CONSTANTS ---
WW, WH = 1000, 720
GW, GH = 10, 20
BS = 30
ID_TO_COLOR = {
    '1': (0,255,255), '2': (255,255,0), '3': (128,0,128), 
    '4': (0,255,0), '5': (255,0,0), '6': (0,0,255), '7': (255,165,0),
    'G': (140, 140, 140), 'K': (0, 255, 0), 'S': (255, 50, 50), 'R': (255, 100, 100)
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

class TetrisV49:
    def __init__(self):
        pygame.init()
        try: pygame.mixer.quit()
        except: pass
        self.screen = pygame.display.set_mode((WW, WH))
        pygame.display.set_caption("MARIO BATTLE PRO [STABLE]")
        self.clock = pygame.time.Clock()
        self.fb = FirebaseManagerV49("https://mario-tetris-game-default-rtdb.firebaseio.com/")
        
        # UI
        try:
            f_path = "assets/PressStart2P-Regular.ttf"
            self.font = pygame.font.Font(f_path, 14) if os.path.exists(f_path) else pygame.font.SysFont("Arial", 18)
            self.huge_font = pygame.font.Font(f_path, 40) if os.path.exists(f_path) else pygame.font.SysFont("Arial", 50)
        except:
            self.font = None; self.huge_font = None

        self.mode = "menu"
        self.is_ready = False
        self.enemies = [] # Local Enemy objects
        self.particles = []
        self.popups = []
        
        self.load_assets()
        self.reset_game()

    def load_assets(self):
        self.sheets = {}
        assets_dir = "assets"
        try:
            if os.path.exists(f"{assets_dir}/marioallsprite.png"):
                self.sheets['mario'] = pygame.image.load(f"{assets_dir}/marioallsprite.png").convert_alpha()
            if os.path.exists(f"{assets_dir}/blocks.png"):
                self.sheets['blocks'] = pygame.image.load(f"{assets_dir}/blocks.png").convert_alpha()
        except: log("Sprite Load Fail")

        self.imgs = {}
        if 'blocks' in self.sheets:
            self.imgs['brick'] = self.get_sprite(self.sheets['blocks'], 368, 112, 16, 16, BS/16)
            self.imgs['question'] = self.get_sprite(self.sheets['blocks'], 80, 112, 16, 16, BS/16)
            self.imgs['ground'] = self.get_sprite(self.sheets['blocks'], 0, 0, 16, 16, BS/16)
        
        if 'mario' in self.sheets:
            # Koopa Walk 1, 2
            self.imgs['koopa'] = [
                self.get_sprite(self.sheets['mario'], 206, 242, 20, 27, BS/24),
                self.get_sprite(self.sheets['mario'], 247, 242, 20, 27, BS/24)
            ]
            # Spiny 1, 2
            self.imgs['spiny'] = [
                self.get_sprite(self.sheets['mario'], 87, 366, 19, 17, BS/20),
                self.get_sprite(self.sheets['mario'], 127, 366, 19, 17, BS/20)
            ]
            # Red Koopa (Simplified - just tinted Green)
            red_k = [img.copy() for img in self.imgs['koopa']]
            for img in red_k: img.fill((255, 100, 100), special_flags=pygame.BLEND_RGB_MULT)
            self.imgs['red_koopa'] = red_k

            # Player Portraits
            self.portraits = {
                'p1': self.get_sprite(self.sheets['mario'], 10, 6, 12, 16, 4.0),
                'p2': self.get_sprite(self.sheets['mario'], 10, 6, 12, 16, 4.0)
            }
            self.portraits['p2'].fill((100, 255, 100), special_flags=pygame.BLEND_RGB_MULT)

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
        self.spawn_timer = 0
        self.enemies = []
        self.particles = []
        self.popups = []

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
        for y in range(GH):
            for x in range(GW):
                # Include enemies in the grid sync for the opponent to see
                cell = self.grid[y][x]
                enemy_here = next((e for e in self.enemies if int(e.x)==x and int(e.y)==y), None)
                if enemy_here: res += enemy_here.type_id
                elif cell is None: res += "0"
                else: res += COLOR_TO_ID.get(cell, "G")
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
                        if e.key == pygame.K_DOWN:
                            self.pos[1] += 1
                            if self.collide(self.pos, self.shape): self.pos[1] -= 1

            if self.mode != "menu":
                await self.fb.poll()
                if self.fb.p1_ready and self.fb.p2_ready and self.fb.role == "p1" and self.fb.room_state == "waiting":
                    await asyncio.to_thread(self.fb._req, f"{self.fb.db_url}/battles/{self.fb.room_id}.json", "PATCH", {"state":"countdown", "countdown_start":time.time()})
                if self.fb.room_state == "countdown":
                    if self.mode == "lobby": self.mode = "play"; self.reset_game()
                
                if self.mode == "play":
                    # Sync
                    asyncio.create_task(self.fb.sync_my_grid(self.compress_grid()))
                    
                    # Garbage
                    if self.fb.pending_garbage > 0:
                        count = int(self.fb.pending_garbage)
                        for _ in range(count):
                            self.grid.pop(0)
                            h = random.randint(0, GW-1)
                            self.grid.append([ID_TO_COLOR['G'] if x!=h else None for x in range(GW)])
                        self.fb.pending_garbage = 0
                        log(f"Received {count} rows!")

                    # Enemy Spawning (Local)
                    self.spawn_timer += dt
                    if self.spawn_timer > 6.0:
                        self.spawn_timer = 0
                        types = ['K', 'S', 'R']
                        t = random.choice(types)
                        rx = random.randint(0, GW-1)
                        # Find a spot with ground
                        for ry in range(GH-1, 5, -1):
                            if self.grid[ry][rx] is None:
                                self.enemies.append(Enemy(rx, ry, t))
                                break
                    
                    # Update Enemies & Check Stomp
                    for en in self.enemies[:]:
                        en.update(dt, self.grid)
                        # Check if player piece is falling on them
                        for bx, by in self.shape[0]:
                            px, py = self.pos[0]+bx, self.pos[1]+by
                            if int(en.x) == px and int(en.y) == py:
                                log(f"STOMPED {en.type_id}!")
                                self.spawn_particles(px*BS+65, py*BS+115)
                                self.enemies.remove(en)
                                # SEND ATTACK
                                asyncio.create_task(self.fb.send_attack(1)) 
                                break

                    # Gravity
                    self.fall_dt += dt
                    if self.fall_dt > 0.7:
                        self.fall_dt = 0; self.pos[1] += 1
                        if self.collide(self.pos, self.shape):
                            self.pos[1] -= 1
                            for bx, by in self.shape[0]:
                                if 0 <= self.pos[1]+by < GH: self.grid[self.pos[1]+by][self.pos[0]+bx] = ID_TO_COLOR[self.shape[1]]
                            
                            # Line Clear
                            new_g = [r for r in self.grid if any(c is None for c in r)]
                            c = GH - len(new_g)
                            while len(new_g) < GH: new_g.insert(0, [None]*GW)
                            self.grid = new_g
                            if c > 0: asyncio.create_task(self.fb.send_attack(c))
                            
                            self.pos = [GW//2-1, 0]; self.shape = self.spawn()
                            if self.collide(self.pos, self.shape): self.reset_game()

            # Particles
            for p in self.particles[:]:
                p['x'] += p['vx']; p['y'] += p['vy']; p['vy'] += 0.2; p['life'] -= 1
                if p['life'] <= 0: self.particles.remove(p)

            self.draw()
            await asyncio.sleep(0.01)

    def spawn_particles(self, x, y):
        for _ in range(8):
            self.particles.append({
                'x': x, 'y': y, 
                'vx': random.uniform(-3, 3), 'vy': random.uniform(-4, -1),
                'life': 30, 'c': (255, 255, 255)
            })

    def draw(self):
        # 1-2 Overlay
        self.screen.fill((92, 148, 252))
        
        if self.mode == "menu":
            self.draw_text("MARIO BATTLE PRO (STABLE)", self.huge_font, (255,255,255), WW//2, 150)
            self.draw_text("PRESS [1] OR [2] TO START", self.font, (255,255,100), WW//2, 300)
            self.draw_text("PRESS [SPACE] FOR TWIN WINDOW", self.font, (255,255,255), WW//2, 400)
        else:
            # Layout
            self.draw_grid(50, 100, self.grid, self.pos if self.mode=="play" else None, self.shape if self.mode=="play" else None)
            self.draw_opp_grid(550, 100, self.fb.opp_grid_raw)
            
            # DASHBOARD middle
            mid = 430
            if hasattr(self, 'portraits'):
                p = self.portraits.get(self.fb.role, self.portraits['p1'])
                self.screen.blit(p, (mid, 100))
            
            p1c = (0, 255, 0) if self.fb.p1_ready else (255, 50, 50)
            p2c = (0, 255, 0) if self.fb.p2_ready else (255, 50, 50)
            self.draw_text(f"MARIO: {'READY' if self.fb.p1_ready else 'WAIT'}", self.font, p1c, mid+50, 250)
            self.draw_text(f"LUIGI: {'READY' if self.fb.p2_ready else 'WAIT'}", self.font, p2c, mid+50, 280)
            
            if self.fb.room_state == "countdown":
                cd = 3 - int(time.time() - self.fb.countdown_start)
                self.draw_text(str(max(1, cd)), self.huge_font, (255,255,0), WW//2, WH//2)

            for p in self.particles:
                pygame.draw.circle(self.screen, p['c'], (int(p['x']), int(p['y'])), 3)

        pygame.display.flip()

    def draw_grid(self, ox, oy, grid, pos, shape):
        pygame.draw.rect(self.screen, (0,0,0,160), (ox, oy, GW*BS, GH*BS))
        # Borders
        for i in range(GH):
            if 'ground' in self.imgs:
                self.screen.blit(self.imgs['ground'], (ox - BS, oy + i*BS))
                self.screen.blit(self.imgs['ground'], (ox + GW*BS, oy + i*BS))

        for y in range(GH):
            for x in range(GW):
                c = grid[y][x]
                if c: self.draw_block(ox + x*BS, oy + y*BS, c, BS)
        # Enemies
        for en in self.enemies:
            k = 'koopa' if en.type_id=='K' else 'spiny' if en.type_id=='S' else 'red_koopa'
            if k in self.imgs:
                img = self.imgs[k][en.frame]
                if en.dir == -1: img = pygame.transform.flip(img, True, False)
                self.screen.blit(img, (ox + en.x*BS, oy + en.y*BS - 5))

        if pos and shape:
            for bx, by in shape[0]:
                self.draw_block(ox + (pos[0]+bx)*BS, oy + (pos[1]+by)*BS, ID_TO_COLOR[shape[1]], BS, is_piece=True)

    def draw_opp_grid(self, ox, oy, raw):
        sbs = 24
        pygame.draw.rect(self.screen, (0,0,0,100), (ox, oy, GW*sbs, GH*sbs))
        for i, char in enumerate(raw):
            if char != '0':
                x, y = i % GW, i // GW
                if char in ['K', 'S', 'R']:
                    k = 'koopa' if char=='K' else 'spiny' if char=='S' else 'red_koopa'
                    img = pygame.transform.scale(self.imgs[k][0], (sbs, sbs))
                    self.screen.blit(img, (ox + x*sbs, oy + y*sbs))
                else:
                    c = ID_TO_COLOR.get(char, (100,100,100))
                    pygame.draw.rect(self.screen, c, (ox + x*sbs, oy + y*sbs, sbs, sbs))
                    pygame.draw.rect(self.screen, (255,255,255), (ox + x*sbs, oy + y*sbs, sbs, sbs), 1)

    def draw_block(self, x, y, color, size, is_piece=False):
        cid = COLOR_TO_ID.get(color)
        if cid == 'G' and 'brick' in self.imgs:
            self.screen.blit(pygame.transform.scale(self.imgs['brick'], (size, size)), (x, y))
        elif not is_piece and 'question' in self.imgs:
            t = pygame.transform.scale(self.imgs['question'], (size, size))
            t.fill(color, special_flags=pygame.BLEND_RGB_MULT)
            self.screen.blit(t, (x, y))
        else:
            pygame.draw.rect(self.screen, color, (x, y, size, size))
            pygame.draw.rect(self.screen, (255,255,255), (x, y, size, size), 1)

    def draw_text(self, text, font, color, x, y):
        if not font: return
        s = font.render(text, True, color)
        r = s.get_rect(center=(x, y))
        self.screen.blit(s, r)

if __name__ == "__main__":
    try: asyncio.run(TetrisV49().run())
    except: 
        with open(f"crash_v49_{PID}.txt", "w") as f: f.write(traceback.format_exc())
        input("CRASH")
