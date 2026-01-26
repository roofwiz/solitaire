
import pygame
import random
import json
import asyncio
import sys
import os
import time
import urllib.request
import subprocess
import math
import traceback

# --- V52 - "STABILITY BATTLE PRO" ---
# Features: 
# - Fixes the "won't start" issue (added better role feedback and error handling)
# - Physics-based Falling Enemies
# - Direct HUD (Integrated scores/stomps)
# - Visual Shell Attack feedback

PID = os.getpid()
LOG_FILE = f"v52_log_{PID}.txt"

def log(msg):
    try:
        ts = time.strftime('%H:%M:%S')
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
            f.flush()
    except: pass
    print(f"[V52] {msg}")

log("Application Early Init...")

class FirebaseManagerV52:
    def __init__(self, db_url):
        self.db_url = db_url.rstrip('/')
        self.room_id = "battle_v51" # Reusing room for simplicity
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
        self.opp_score = 0
        self.opp_stomps = 0

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
        log(f"Picking role: {role}...")
        if role == "p1":
            d = {
                "state":"waiting", 
                "p1":{"ready":False, "attack_queue":0, "grid_comp":"0"*200, "last_update":time.time(), "score":0, "stomps":0}, 
                "p2":{"ready":False, "attack_queue":0, "grid_comp":"0"*200, "status":"offline", "score":0, "stomps":0},
                "countdown_start":0
            }
            await asyncio.to_thread(self._req, url, "PUT", d)
        else:
            await asyncio.to_thread(self._req, f"{self.db_url}/battles/{self.room_id}/p2.json", "PATCH", {"status":"alive", "ready":False, "grid_comp":"0"*200})
        self.connected = True
        log(f"Connected as {role}")

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
            self.opp_score = opp_data.get('score', 0)
            self.opp_stomps = opp_data.get('stomps', 0)
            
            remote_q = opp_data.get('attack_queue', 0)
            if remote_q > self.total_received:
                self.pending_garbage += (remote_q - self.total_received)
                self.total_received = remote_q

    async def sync_data(self, grid_str, score, stomps):
        if not self.connected: return
        await asyncio.to_thread(self._req, f"{self.db_url}/battles/{self.room_id}/{self.role}.json", "PATCH", {"grid_comp": grid_str, "score": score, "stomps": stomps, "last_update": time.time()})

    async def set_ready(self, b):
        await asyncio.to_thread(self._req, f"{self.db_url}/battles/{self.room_id}/{self.role}.json", "PATCH", {"ready": b})

    async def send_attack(self, lines):
        if not self.connected: return
        data = await asyncio.to_thread(self._req, f"{self.db_url}/battles/{self.room_id}/{self.role}.json")
        cur = data.get('attack_queue', 0) if data else 0
        await asyncio.to_thread(self._req, f"{self.db_url}/battles/{self.room_id}/{self.role}.json", "PATCH", {"attack_queue": cur + lines})

# --- GAME CONSTANTS ---
WW, WH = 960, 680
GW, GH = 10, 20
BS = 30
ID_TO_COLOR = {
    '1': (0,255,255), '2': (255,255,0), '3': (128,0,128), 
    '4': (0,255,0), '5': (255,0,0), '6': (0,0,255), '7': (255,165,0),
    'G': (140, 140, 140), 'K': (0, 255, 0), 'S': (255, 50, 50)
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

class Enemy:
    def __init__(self, x, y, type_id):
        self.x, self.y = x, float(y)
        self.type_id = type_id 
        self.frame = 0 ; self.anim_t = 0
        self.dir = random.choice([-1, 1])
        self.vy = 0 ; self.move_t = 0

    def update(self, dt, grid):
        self.anim_t += dt
        if self.anim_t > 0.2: self.anim_t = 0; self.frame = 1 - self.frame
        below = int(self.y + 1)
        ix = int(self.x)
        if below >= GH or (0 <= ix < GW and grid[below][ix] is not None):
            self.y = float(int(self.y)); self.vy = 0
            self.move_t += dt
            if self.move_t > 0.5:
                self.move_t = 0
                nx = self.x + self.dir
                if 0 <= nx < GW and grid[int(self.y)][nx] is None: self.x = nx
                else: self.dir *= -1
        else:
            self.vy += 30 * dt ; self.y += self.vy * dt

class ShellAnim:
    def __init__(self, start, end):
        self.x, self.y = start ; self.tx, self.ty = end ; self.t = 0.0
    def update(self, dt):
        self.t += dt * 1.5 ; return self.t < 1.0
    def get_pos(self):
        px = self.x + (self.tx - self.x) * self.t
        py = self.y + (self.ty - self.y) * self.t - 80 * math.sin(math.pi * self.t)
        return (int(px), int(py))

class TetrisV52:
    def __init__(self):
        pygame.init()
        try: pygame.mixer.quit()
        except: pass
        self.screen = pygame.display.set_mode((WW, WH))
        pygame.display.set_caption(f"MARIO BATTLE STABLE - PID:{PID}")
        self.clock = pygame.time.Clock()
        self.fb = FirebaseManagerV52("https://mario-tetris-game-default-rtdb.firebaseio.com/")
        
        try:
            f = "assets/PressStart2P-Regular.ttf"
            self.font = pygame.font.Font(f, 12) if os.path.exists(f) else pygame.font.SysFont("Arial", 16)
            self.huge_font = pygame.font.Font(f, 40) if os.path.exists(f) else pygame.font.SysFont("Arial", 50)
        except: self.font = self.huge_font = None

        self.mode = "menu"
        self.load_assets()
        self.reset_game()
        log("Init Complete.")

    def load_assets(self):
        log("Loading Sprites...")
        try:
            m = pygame.image.load("assets/marioallsprite.png").convert_alpha()
            b = pygame.image.load("assets/blocks.png").convert_alpha()
            self.imgs = {
                'brick': self.get_sprite(b, 368, 112, 16, 16, BS/16),
                'question': self.get_sprite(b, 80, 112, 16, 16, BS/16),
                'koopa': [self.get_sprite(m, 206, 242, 20, 27, BS/24), self.get_sprite(m, 247, 242, 20, 27, BS/24)],
                'spiny': [self.get_sprite(m, 87, 366, 19, 17, BS/20), self.get_sprite(m, 127, 366, 19, 17, BS/20)],
                'shell': self.get_sprite(m, 288, 248, 16, 14, BS/16),
                'mario': self.get_sprite(m, 10, 6, 12, 16, 4.0),
                'luigi': self.get_sprite(m, 10, 6, 12, 16, 4.0)
            }
            if self.imgs['luigi']: self.imgs['luigi'].fill((100, 255, 100), special_flags=pygame.BLEND_RGB_MULT)
            log("Sprites Loaded Successful.")
        except Exception as e: 
            log(f"Sprite Error: {e}")
            self.imgs = {}

    def get_sprite(self, sheet, x, y, w, h, s):
        try:
            surf = pygame.Surface((w, h), pygame.SRCALPHA)
            surf.blit(sheet, (0, 0), (x, y, w, h))
            return pygame.transform.scale(surf, (int(w*s), int(h*s)))
        except: return None

    def reset_game(self):
        self.grid = [[None for _ in range(GW)] for _ in range(GH)]
        self.bag = []
        self.pos = [GW//2-1, 0]
        self.shape = self.spawn()
        self.fall_dt = 0; self.spawn_timer = 2.0
        self.enemies = []; self.shells = []; self.particles = []
        self.score = 0; self.lines = 0; self.stomps = 0; self.is_ready = False

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
                res += COLOR_TO_ID.get(self.grid[y][x], "0")
        return res

    async def run(self):
        log("Game Loop Starting.")
        while True:
            dt = self.clock.tick(60)/1000.0
            for e in pygame.event.get():
                if e.type == pygame.QUIT: return
                if e.type == pygame.KEYDOWN:
                    if self.mode == "menu":
                        if e.key == pygame.K_1: await self.fb.pick("p1"); self.mode = "lobby"
                        if e.key == pygame.K_2: await self.fb.pick("p2"); self.mode = "lobby"
                        if e.key == pygame.K_SPACE: subprocess.Popen([sys.executable, os.path.abspath(__file__)])
                    elif self.mode == "lobby" and e.key == pygame.K_RETURN:
                        self.is_ready = not self.is_ready ; await self.fb.set_ready(self.is_ready)
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
                            self.pos[1]+=1
                            if self.collide(self.pos, self.shape): self.pos[1]-=1

            if self.mode != "menu":
                await self.fb.poll()
                if self.fb.p1_ready and self.fb.p2_ready and self.fb.role == "p1" and self.fb.room_state == "waiting":
                    await asyncio.to_thread(self.fb._req, f"{self.fb.db_url}/battles/{self.fb.room_id}.json", "PATCH", {"state":"countdown", "countdown_start":time.time()})
                if self.fb.room_state == "countdown":
                    if self.mode == "lobby": self.mode = "play"; self.reset_game()
                
                if self.mode == "play":
                    asyncio.create_task(self.fb.sync_data(self.compress_grid(), self.score, self.stomps))
                    if self.fb.pending_garbage > 0:
                        for _ in range(int(self.fb.pending_garbage)):
                            self.grid.pop(0); self.grid.append([ID_TO_COLOR['G'] if x!=random.randint(0,9) else None for x in range(GW)])
                        self.fb.pending_garbage = 0
                    
                    self.spawn_timer += dt
                    if self.spawn_timer > 7.0:
                        self.spawn_timer = 0; self.enemies.append(Enemy(random.randint(0, 9), -1, random.choice(['K','S'])))
                    
                    for en in self.enemies[:]:
                        en.update(dt, self.grid)
                        if en.y > GH + 1: self.enemies.remove(en)
                        else:
                            for bx, by in self.shape[0]:
                                if int(en.x) == self.pos[0]+bx and int(en.y) == self.pos[1]+by:
                                    self.enemies.remove(en); self.stomps += 1; self.score += 500
                                    self.shells.append(ShellAnim((60+en.x*BS, 80+en.y*BS), (600, 80)))
                                    asyncio.create_task(self.fb.send_attack(1))
                                    break

                    self.fall_dt += dt
                    if self.fall_dt > 0.8:
                        self.fall_dt = 0; self.pos[1] += 1
                        if self.collide(self.pos, self.shape):
                            self.pos[1] -= 1
                            for bx, by in self.shape[0]:
                                if 0 <= self.pos[1]+by < GH: self.grid[self.pos[1]+by][self.pos[0]+bx] = ID_TO_COLOR[self.shape[1]]
                            new_g = [r for r in self.grid if any(c is None for c in r)]
                            c = GH - len(new_g)
                            if c > 0:
                                self.lines += c; self.score += (c*1000)
                                while len(new_g) < GH: new_g.insert(0, [None]*GW)
                                self.grid = new_g
                                asyncio.create_task(self.fb.send_attack(c))
                            self.pos = [GW//2-1, 0]; self.shape = self.spawn()
                            if self.collide(self.pos, self.shape): self.reset_game()

            self.shells = [s for s in self.shells if s.update(dt)]
            self.draw() ; await asyncio.sleep(0.01)

    def draw(self):
        self.screen.fill((92, 148, 252))
        if self.mode == "menu":
            self.draw_t("MARIO BATTLE PRO V52", self.huge_font, (255,255,255), WW//2, 200)
            self.draw_t("PRESS [1] FOR MARIO, [2] FOR LUIGI", self.font, (255,255,0), WW//2, 350)
            self.draw_t("PRESS [SPACE] FOR SECOND WINDOW", self.font, (200,255,255), WW//2, 400)
        else:
            mx, my = 60, 80
            self.draw_g(mx, my, self.grid, self.pos if self.mode=="play" else None, self.shape if self.mode=="play" else None, BS)
            # HUD L
            self.draw_t(f"SCORE: {self.score}", self.font, (255,255,255), mx, 50, False)
            self.draw_t(f"STOMP: {self.stomps}", self.font, (100,255,100), mx + 160, 50, False)
            if 'mario' in self.imgs:
                p = self.imgs['mario' if self.fb.role=='p1' else 'luigi']
                if p: self.screen.blit(p, (mx-50, 40))
            
            # Opponent Grid
            ox, oy = 580, 80 ; sbs = 25
            opp_grid = [[(ID_TO_COLOR[c] if c!='0' else None) for c in self.fb.opp_grid_raw[i*10:(i+1)*10]] for i in range(20)]
            self.draw_g(ox, oy, opp_grid, None, None, sbs)
            self.draw_t(f"OPP SCORE: {self.fb.opp_score}", self.font, (255,255,255), ox, 50, False)
            self.draw_t(f"OPP STOMP: {self.fb.opp_stomps}", self.font, (255,100,100), ox + 180, 50, False)

            for s in self.shells:
                if 'shell' in self.imgs: self.screen.blit(self.imgs['shell'], s.get_pos())
            
            if self.mode == "lobby":
                msg = "HIT [ENTER] TO READY UP!" if not self.is_ready else "WAITING FOR BRO..."
                self.draw_t(msg, self.font, (255,255,255), WW//2, WH-60)

            if self.fb.room_state == "countdown":
                cd = 3 - int(time.time() - self.fb.countdown_start)
                self.draw_t(str(max(1, cd)), self.huge_font, (255,255,255), WW//2, WH//2)

        pygame.display.flip()

    def draw_g(self, ox, oy, grid, pos, shape, size):
        pygame.draw.rect(self.screen, (0,0,0,160), (ox, oy, GW*size, GH*size))
        for y, row in enumerate(grid):
            for x, c in enumerate(row):
                if c: self.draw_b(ox + x*size, oy + y*size, c, size, False)
        if pos and shape:
            for bx, by in shape[0]: self.draw_b(ox+(pos[0]+bx)*size, oy+(pos[1]+by)*size, ID_TO_COLOR[shape[1]], size, True)
        if grid is self.grid:
            for en in self.enemies:
                k = 'koopa' if en.type_id=='K' else 'spiny'
                if k in self.imgs:
                    img = self.imgs[k][en.frame]
                    if img:
                        if en.dir == -1: img = pygame.transform.flip(img, True, False)
                        self.screen.blit(pygame.transform.scale(img, (size, size)), (ox+en.x*size, oy+en.y*size))

    def draw_b(self, x, y, color, size, is_p):
        cid = COLOR_TO_ID.get(color)
        if cid == 'G' and 'brick' in self.imgs: self.screen.blit(pygame.transform.scale(self.imgs['brick'], (size, size)), (x, y))
        elif not is_p and 'question' in self.imgs:
            t = pygame.transform.scale(self.imgs['question'], (size, size))
            t.fill(color, special_flags=pygame.BLEND_RGB_MULT) ; self.screen.blit(t, (x, y))
        else:
            pygame.draw.rect(self.screen, color, (x, y, size, size))
            pygame.draw.rect(self.screen, (255,255,255), (x, y, size, size), 1)

    def draw_t(self, text, font, color, x, y, center=True):
        if not font: return
        s = font.render(text, True, color)
        r = s.get_rect(center=(x, y)) if center else s.get_rect(topleft=(x, y))
        self.screen.blit(s, r)

if __name__ == "__main__":
    try: asyncio.run(TetrisV52().run())
    except Exception: 
        with open(f"crash_v52_{PID}.txt", "w") as f: f.write(traceback.format_exc())
        log(traceback.format_exc())
        input("CRASH - Press Enter to Close")
