
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

# --- V60 - "MARIO BATTLE PRO MASTER" ---
# Features:
# - HYPER-POLISHED 3D BLOCKS: Jewel-cut facets with inner bevels for professional arcade look.
# - DYNAMIC CLEAR PARTICLES: Real physics-based particles when lines explode.
# - PERFECTED P1/P2 HUD: NES-style character portraits and aligned typography.
# - SECURE LAYOUT: Lifted playfield with decorative Mario floor.
# - STABLE SOUND & BGM: intro_theme.mp3 + calibrated sfx.

PID = os.getpid()
LOG_FILE = f"v60_log_{PID}.txt"

def log(msg):
    try:
        ts = time.strftime('%H:%M:%S')
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
            f.flush()
    except: pass
    print(f"[V60-{PID}] {msg}")

# --- SOUND MANAGER ---
class SoundManager:
    def __init__(self):
        self.sounds = {}
        self.enabled = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.pre_init(44100, -16, 2, 512)
                pygame.mixer.init()
            pygame.mixer.set_num_channels(32)
            self.enabled = True
            log("Sound Mixer OK.")
            self._load_all()
        except: pass

    def _load_all(self):
        sfx = {
            'rotate':'rotate.wav', 'lock':'lock.wav', 'clear':'clear.wav', 
            'stomp':'stomp.wav', 'move':'move.wav',
            'damage':'impactBell_heavy_004.ogg', 'land':'impactGeneric_light_002.ogg' 
        }
        for name, file in sfx.items():
            paths = [os.path.join('sounds', file), file]
            for p in paths:
                if os.path.exists(p):
                    try:
                        self.sounds[name] = pygame.mixer.Sound(p)
                        self.sounds[name].set_volume(0.4 if name != 'move' else 0.2)
                        break
                    except: pass

    def play(self, name):
        if self.enabled and name in self.sounds:
            try: self.sounds[name].play()
            except: pass

    def play_bgm(self):
        if not self.enabled: return
        path = os.path.join('sounds', 'intro_theme.mp3')
        if not os.path.exists(path): path = 'intro_theme.mp3'
        if os.path.exists(path):
            try:
                pygame.mixer.music.load(path)
                pygame.mixer.music.set_volume(0.25)
                pygame.mixer.music.play(-1, fade_ms=2000)
            except: pass

# --- NETWORK ---
class FirebaseManagerV60:
    def __init__(self, db_url):
        self.db_url = db_url.rstrip('/')
        self.room_id = "battle_v60_pro"
        self.role = None ; self.opp_role = None ; self.connected = False
        self.room_state = "waiting" ; self.countdown_start = 0
        self.opp_grid_raw = "0" * 200 ; self.pending_garbage = 0
        self.total_received = 0 ; self.poll_time = 0
        self.opp_score = 0 ; self.opp_stomps = 0

    def _req(self, url, method="GET", data=None):
        try:
            req = urllib.request.Request(url, method=method)
            if data:
                req.add_header('Content-Type', 'application/json')
                body = json.dumps(data).encode('utf-8')
                with urllib.request.urlopen(req, data=body, timeout=4) as r:
                    return json.loads(r.read().decode('utf-8'))
            else:
                with urllib.request.urlopen(req, timeout=4) as r:
                    return json.loads(r.read().decode('utf-8'))
        except: return None

    async def join(self, role):
        self.role = role ; self.opp_role = "p2" if role == "p1" else "p1"
        url = f"{self.db_url}/battles/{self.room_id}.json"
        if role == "p1":
            d = {"state":"waiting", "p1":{"ready":False, "attack_queue":0, "grid_comp":"0"*200, "score":0, "stomps":0}, 
                 "p2":{"ready":False, "attack_queue":0, "grid_comp":"0"*200, "status":"offline", "score":0, "stomps":0}}
            await asyncio.to_thread(self._req, url, "PUT", d)
        else:
            await asyncio.to_thread(self._req, f"{self.db_url}/battles/{self.room_id}/p2.json", "PATCH", {"status":"alive", "ready":False})
        self.connected = True

    async def poll(self):
        if not self.connected: return
        t = time.time()
        if t - self.poll_time < 0.5: return 
        self.poll_time = t
        data = await asyncio.to_thread(self._req, f"{self.db_url}/battles/{self.room_id}.json")
        if data:
            self.room_state = data.get('state', 'waiting')
            self.countdown_start = data.get('countdown_start', 0)
            opp = data.get(self.opp_role, {})
            self.opp_grid_raw = opp.get('grid_comp', "0"*200)
            self.opp_score = opp.get('score', 0)
            self.opp_stomps = opp.get('stomps', 0)
            remote_q = opp.get('attack_queue', 0)
            if remote_q > self.total_received:
                self.pending_garbage += (remote_q - self.total_received)
                self.total_received = remote_q

    async def set_ready(self, b):
        if self.connected: await asyncio.to_thread(self._req, f"{self.db_url}/battles/{self.room_id}/{self.role}.json", "PATCH", {"ready":b})

    async def sync(self, grid, score, stomps):
        if self.connected: await asyncio.to_thread(self._req, f"{self.db_url}/battles/{self.room_id}/{self.role}.json", "PATCH", {"grid_comp":grid, "score":score, "stomps":stomps})

    async def attack(self, n):
        if self.connected:
            data = await asyncio.to_thread(self._req, f"{self.db_url}/battles/{self.room_id}/{self.role}.json")
            cur = data.get('attack_queue', 0) if data else 0
            await asyncio.to_thread(self._req, f"{self.db_url}/battles/{self.room_id}/{self.role}.json", "PATCH", {"attack_queue": cur + n})

# --- EFFECTS ---
class Particle:
    def __init__(self, x, y, color):
        self.x, self.y = x, y
        self.vx = random.uniform(-5, 5)
        self.vy = random.uniform(-10, -2)
        self.color = color
        self.life = 1.0

    def update(self, dt):
        self.life -= dt * 1.5
        self.vy += 25 * dt
        self.x += self.vx
        self.y += self.vy
        return self.life > 0

# --- CORE GAME ---
WW, WH = 1000, 720
GW, GH = 10, 20
BS = 32
GRID_Y = 60

ID_TO_COLOR = {'1':(0,240,240),'2':(240,240,0),'3':(160,0,240),'4':(0,240,0),'5':(240,0,0),'6':(0,0,240),'7':(240,160,0),'G':(140,140,140)}
COLOR_TO_ID = {v: k for k, v in ID_TO_COLOR.items()}

class Enemy:
    def __init__(self, x, type_id='K'):
        self.x, self.y = float(x), -1.0
        self.type_id = type_id ; self.state = 'falling' ; self.vy = 0 ; self.dir = random.choice([-1, 1])
        self.lifetime = 12.0 ; self.anim_frame = 0 ; self.anim_timer = 0

    def update(self, dt, grid, sm):
        self.anim_timer += dt
        if self.anim_timer > 0.15: self.anim_timer = 0; self.anim_frame = 1-self.anim_frame
        self.vy += 25 * dt ; self.y += self.vy * dt
        ix, iy = int(self.x), int(self.y)
        on_solid = False
        if self.y >= 19.0: self.y = 19.0 ; self.vy = 0 ; on_solid = True
        elif iy+1 < 20 and 0 <= ix < 10 and grid[iy+1][ix] is not None:
            self.y = float(iy) ; self.vy = 0 ; on_solid = True
        if on_solid:
            if self.state == 'falling': self.state = 'walking' ; sm.play('land')
        else: self.state = 'falling'
        if self.state == 'walking':
            self.lifetime -= dt
            nx = int(self.x + self.dir * 0.5)
            if nx < 0 or nx >= 10 or (int(self.y) < 20 and grid[int(self.y)][nx] is not None): self.dir *= -1
            elif self.type_id == 'R':
                if int(self.y)+1 < 20 and grid[int(self.y)+1][nx] is None: self.dir *= -1
            self.x += self.dir * 1.2 * dt
            return self.lifetime <= 0
        return False

class TetrisV60:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WW, WH))
        pygame.display.set_caption("MARIO BATTLE PRO MASTER V60")
        self.clock = pygame.time.Clock()
        self.fb = FirebaseManagerV60("https://mario-tetris-game-default-rtdb.firebaseio.com/")
        self.sm = SoundManager()
        try:
            f = "assets/PressStart2P-Regular.ttf"
            self.font = pygame.font.Font(f, 13) if os.path.exists(f) else pygame.font.SysFont("Arial", 18)
            self.huge = pygame.font.Font(f, 40) if os.path.exists(f) else pygame.font.SysFont("Arial", 50)
        except: self.font = self.huge = None
        self.mode = "menu" ; self.load_assets() ; self.reset()

    def load_assets(self):
        try:
            m = pygame.image.load("assets/marioallsprite.png").convert_alpha()
            b = pygame.image.load("assets/blocks.png").convert_alpha()
            self.imgs = {
                'brick': self.get_sprite(b, 368, 112, 16, 16, BS/16),
                'koopa': [self.get_sprite(m, 206, 242, 20, 27, BS/24), self.get_sprite(m, 247, 242, 20, 27, BS/24)],
                'red_koopa': [self.get_sprite(m, 326, 242, 20, 27, BS/24), self.get_sprite(m, 367, 242, 20, 27, BS/24)],
                'mario': self.get_sprite(m, 10, 6, 12, 16, 4.0), 'luigi': self.get_sprite(m, 10, 6, 12, 16, 4.0),
                'ground': self.get_sprite(b, 0, 0, 16, 16, BS/16)
            }
            if 'luigi' in self.imgs: self.imgs['luigi'].fill((100, 255, 100), special_flags=pygame.BLEND_RGB_MULT)
        except: self.imgs = {}

    def get_sprite(self, sheet, x, y, w, h, s):
        ss = pygame.Surface((w, h), pygame.SRCALPHA) ; ss.blit(sheet, (0, 0), (x, y, w, h))
        return pygame.transform.scale(ss, (int(w*s), int(h*s)))

    def reset(self):
        self.grid = [[None for _ in range(GW)] for _ in range(GH)]
        self.bag = [] ; self.pos = [GW//2-1, 0] ; self.shape = self.spawn()
        self.fall_dt = 0 ; self.enemies = [] ; self.score = 0 ; self.stomps = 0 ; self.is_ready = False ; self.spawn_t = 0
        self.clearing = [] ; self.anim_t = 0 ; self.particles = []

    def spawn(self):
        if not self.bag: self.bag = ['I','O','T','S','Z','J','L'] ; random.shuffle(self.bag)
        s = self.bag.pop()
        d = {'I':[(0,0),(1,0),(2,0),(3,0)], 'O':[(0,0),(1,0),(0,1),(1,1)], 'T':[(1,0),(0,1),(1,1),(2,1)], 'S':[(1,0),(2,0),(0,1),(1,1)], 'Z':[(0,0),(1,0),(1,1),(2,1)], 'J':[(0,0),(0,1),(1,1),(2,1)], 'L':[(2,0),(0,1),(1,1),(2,1)]}
        return [[list(b) for b in d[s]], s]

    def collide(self, p, s):
        for bx, by in s[0]:
            gx, gy = p[0]+bx, p[1]+by
            if gx < 0 or gx >= GW or gy >= GH or (gy >= 0 and self.grid[gy][gx]): return True
        return False

    async def run(self):
        while True:
            dt = self.clock.tick(60)/1000.0
            for e in pygame.event.get():
                if e.type == pygame.QUIT: return
                if e.type == pygame.KEYDOWN:
                    if self.mode == "menu":
                        if e.key == pygame.K_1: await self.fb.join("p1") ; self.mode = "lobby" ; self.sm.play_bgm()
                        if e.key == pygame.K_2: await self.fb.join("p2") ; self.mode = "lobby" ; self.sm.play_bgm()
                        if e.key == pygame.K_SPACE: subprocess.Popen([sys.executable, os.path.abspath(__file__)])
                    elif self.mode == "lobby" and e.key == pygame.K_RETURN:
                        self.is_ready = not self.is_ready ; await self.fb.set_ready(self.is_ready)
                    elif self.mode == "play" and not self.clearing:
                        m = False
                        if e.key == pygame.K_LEFT: self.pos[0]-=1; m=True
                        if self.collide(self.pos, self.shape): self.pos[0]+=1; m=False
                        if e.key == pygame.K_RIGHT: self.pos[0]+=1; m=True
                        if self.collide(self.pos, self.shape): self.pos[0]-=1; m=False
                        if m: self.sm.play('move')
                        if e.key == pygame.K_UP:
                            old = [list(b) for b in self.shape[0]]
                            self.shape[0] = [(-by, bx) for bx, by in old]
                            if self.collide(self.pos, self.shape): self.shape[0] = old
                            else: self.sm.play('rotate')
                        if e.key == pygame.K_DOWN: self.pos[1]+=1 ; 
                        if self.collide(self.pos, self.shape): self.pos[1]-=1
                        if e.key == pygame.K_SPACE:
                            while not self.collide([self.pos[0], self.pos[1]+1], self.shape): self.pos[1] += 1
                            self.sm.play('lock') ; self.fall_dt = 10.0

            if self.mode != "menu":
                await self.fb.poll()
                if self.fb.room_state == "countdown" and self.mode == "lobby": self.mode = "play" ; self.reset()
                
                if self.mode == "play":
                    self.particles = [p for p in self.particles if p.update(dt)]
                    if self.clearing:
                        self.anim_t -= dt
                        if self.anim_t <= 0:
                            new_g = [r for i, r in enumerate(self.grid) if i not in self.clearing]
                            while len(new_g) < GH: new_g.insert(0, [None]*GW)
                            self.grid = new_g ; self.clearing = [] ; self.pos = [GW//2-1, 0] ; self.shape = self.spawn()
                    else:
                        sync = "".join([COLOR_TO_ID.get(c, "0") if c!=(140,140,140) else "G" for r in self.grid for c in r])
                        asyncio.create_task(self.fb.sync(sync, self.score, self.stomps))
                        if self.fb.pending_garbage > 0:
                            self.sm.play('damage')
                            for _ in range(int(self.fb.pending_garbage)):
                                self.grid.pop(0) ; self.grid.append([(140,140,140) if x!=random.randint(0,9) else None for x in range(GW)])
                            self.fb.pending_garbage = 0
                        
                        self.spawn_t += dt
                        if self.spawn_t > 9.0:
                            self.spawn_t = 0 ; self.enemies.append(Enemy(random.randint(0,9), random.choice(['K','R'])))
                        
                        for en in self.enemies[:]:
                            if en.update(dt, self.grid, self.sm):
                                self.enemies.remove(en) ; self.sm.play('damage')
                                self.grid.pop(0) ; self.grid.append([(140,140,140) if x!=random.randint(0,9) else None for x in range(GW)])
                            elif en.y > GH + 1: self.enemies.remove(en)
                            elif en.state == 'walking':
                                for bx, by in self.shape[0]:
                                    if int(en.x) == self.pos[0]+bx and int(en.y) == self.pos[1]+by:
                                        self.enemies.remove(en) ; self.stomps += 1 ; self.score += 500 ; self.sm.play('stomp')
                                        asyncio.create_task(self.fb.attack(1)) ; break

                        self.fall_dt += dt
                        if self.fall_dt > 0.8:
                            self.fall_dt = 0; self.pos[1] += 1
                            if self.collide(self.pos, self.shape):
                                self.pos[1] -= 1 ; self.sm.play('lock')
                                c = {'I':(0,240,240),'O':(240,240,0),'T':(160,0,240),'S':(0,240,0),'Z':(240,0,0),'J':(0,0,240),'L':(240,160,0)}[self.shape[1]]
                                for bx, by in self.shape[0]:
                                    if 0 <= self.pos[1]+by < GH: self.grid[self.pos[1]+by][self.pos[0]+bx] = c
                                self.clearing = [i for i, r in enumerate(self.grid) if all(x is not None for x in r)]
                                if self.clearing:
                                    self.sm.play('clear') ; self.score += (len(self.clearing)*1000) ; self.anim_t = 0.5
                                    for row_idx in self.clearing:
                                        for x in range(GW): self.particles.extend([Particle(60+x*BS+16, GRID_Y+row_idx*BS+16, ID_TO_COLOR.get(COLOR_TO_ID.get(self.grid[row_idx][x]), (255,255,255))) for _ in range(2)])
                                    asyncio.create_task(self.fb.attack(len(self.clearing)))
                                else:
                                    self.pos = [GW//2-1, 0] ; self.shape = self.spawn()
                                    if self.collide(self.pos, self.shape): self.reset()

            self.draw() ; await asyncio.sleep(0.01)

    def draw(self):
        self.screen.fill((92, 148, 252))
        if self.mode == "menu":
            self.draw_t("MARIO BATTLE PRO MASTER V60", self.huge, (255,255,255), WW//2, 200)
            self.draw_t("HYPER-POLISHED 3D BLOCKS", self.font, (255,255,0), WW//2, 350)
            self.draw_t("Press [1] or [2] to Battle", self.font, (255,255,255), WW//2, 400)
        else:
            mx, my = 60, GRID_Y
            # Playfield
            pygame.draw.rect(self.screen, (0,0,0,200), (mx-4, my-4, GW*BS+8, GH*BS+8))
            pygame.draw.rect(self.screen, (255,255,255), (mx-4, my-4, GW*BS+8, GH*BS+8), 2)
            if 'ground' in self.imgs:
                for x in range(GW): self.screen.blit(self.imgs['ground'], (mx+x*BS, my+GH*BS))
            
            # Grid
            for y in range(GH):
                if y in self.clearing:
                    pygame.draw.rect(self.screen, (255,255,255), (mx, my+y*BS, GW*BS, BS))
                    continue
                for x in range(GW):
                    c = self.grid[y][x] 
                    if c: self.draw_3d_b(mx+x*BS, my+y*BS, c, BS)
            
            # Active
            if not self.clearing:
                for bx, by in self.shape[0]:
                    c = {'I':(0,240,240),'O':(240,240,0),'T':(160,0,240),'S':(0,240,0),'Z':(240,0,0),'J':(0,0,240),'L':(240,160,0)}[self.shape[1]]
                    self.draw_3d_b(mx+(self.pos[0]+bx)*BS, my+(self.pos[1]+by)*BS, c, BS)
            
            # Particles
            for p in self.particles:
                s = pygame.Surface((4, 4)) ; s.fill(p.color) ; s.set_alpha(int(p.life*255))
                self.screen.blit(s, (p.x, p.y))

            # HUD
            p_img = self.imgs['mario' if self.fb.role=='p1' else 'luigi'] if 'mario' in self.imgs else None
            if p_img: self.screen.blit(p_img, (mx-52, 5))
            self.draw_t(f"SCORE: {self.score}", self.font, (255,255,255), mx, 30, False)
            self.draw_t(f"STOMPS: {self.stomps}", self.font, (100,255,100), mx + 180, 30, False)

            # Opponent
            ox, oy = 620, GRID_Y+80 ; sbs = 28
            pygame.draw.rect(self.screen, (0,0,0,150), (ox-4, oy-4, GW*sbs+8, GH*sbs+8))
            for i, c_id in enumerate(self.fb.opp_grid_raw):
                if c_id != '0':
                    x, y = i%10, i//10 ; c = ID_TO_COLOR.get(c_id, (200,200,200))
                    self.draw_3d_b(ox+x*sbs, oy+y*sbs, c, sbs)
            self.draw_t(f"OPP SCORE: {self.fb.opp_score}", self.font, (255,255,255), ox, oy-30, False)

            # Enemies
            for en in self.enemies:
                img = self.imgs['koopa' if en.type_id=='K' else 'red_koopa'][en.anim_frame]
                if en.dir == -1: img = pygame.transform.flip(img, True, False)
                self.screen.blit(img, (mx+en.x*BS, my+en.y*BS-5))
                if en.state == 'walking':
                    pygame.draw.rect(self.screen, (255,0,0), (mx+en.x*BS, my+en.y*BS-10, BS*(en.lifetime/12.0), 4))

            if self.mode == "lobby":
                msg = "HIT [ENTER] TO READY!" if not self.is_ready else "WAITING FOR BRO..."
                self.draw_t(msg, self.font, (255,255,255), WW//2, WH-60)
            if self.fb.room_state == "countdown":
                cd = 3 - int(time.time() - self.fb.countdown_start)
                self.draw_t(str(max(1, cd)), self.huge, (255,255,255), WW//2, WH//2)

        pygame.display.flip()

    def draw_3d_b(self, x, y, color, size):
        if color == (140,140,140) and 'brick' in self.imgs:
            self.screen.blit(pygame.transform.scale(self.imgs['brick'], (size, size)), (x, y))
            return
        # ARCHER 3D STYLE: 4-FACET JEWEL CUT
        light = [min(255, c + 80) for c in color]
        dark = [max(0, c - 80) for c in color]
        # Main
        pygame.draw.rect(self.screen, color, (x, y, size, size))
        # Bevels
        pygame.draw.polygon(self.screen, light, [(x,y), (x+size,y), (x+size-4,y+4), (x+4,y+4)]) # Top
        pygame.draw.polygon(self.screen, light, [(x,y), (x+4,y+4), (x+4,y+size-4), (x,y+size)]) # Left
        pygame.draw.polygon(self.screen, dark, [(x+size,y), (x+size,y+size), (x+size-4,y+size-4), (x+size-4,y+4)]) # Right
        pygame.draw.polygon(self.screen, dark, [(x,y+size), (x+size,y+size), (x+size-4,y+size-4), (x+4,y+size-4)]) # Bottom

    def draw_t(self, t, f, c, x, y, center=True):
        if f:
            s = f.render(t, True, c) ; r = s.get_rect(center=(x,y)) if center else s.get_rect(topleft=(x,y)) ; self.screen.blit(s, r)

if __name__ == "__main__":
    try: asyncio.run(TetrisV60().run())
    except:
        with open(f"crash_v60_{PID}.txt", "w") as f: f.write(traceback.format_exc())
        input("CRASH")
