
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

# --- V56 - "MARIO BATTLE OFFICIAL" ---
# Features:
# - PRO-GRADE ENEMY PHYSICS: Land on blocks/floor, Red Koopas turn at edges.
# - DUAL SCORE HUD: Integrated NES-style HUD for both players.
# - SHELL ATTACK SYSTEM: Stomping sends flying shells to punish opponent.
# - P-BAR TIMERS: Enemies expire if not stomped, punishing the player.
# - HIGH STABILITY NETWORKING: Reliable room states and syncing.
# - CLASSIC SOUNDS: Stomp, Clear, Lock, Rotate effects.

PID = os.getpid()
LOG_FILE = f"v56_log_{PID}.txt"

def log(msg):
    try:
        ts = time.strftime('%H:%M:%S')
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
            f.flush()
    except: pass
    print(f"[V56-{PID}] {msg}")

# --- SOUND MANAGER (High Stability) ---
class SoundManager:
    def __init__(self):
        self.sounds = {}
        self.enabled = False
        try:
            pygame.mixer.pre_init(44100, -16, 2, 512)
            pygame.mixer.init()
            pygame.mixer.set_num_channels(24)
            self.enabled = True
            log("Sound Mixer Init OK.")
            self._load_all()
        except Exception as e:
            log(f"Sound Init Fail: {e}")

    def _load_all(self):
        # Maps event names to possible filenames
        sfx_map = {
            'rotate': 'rotate.wav', 
            'lock': 'lock.wav', 
            'clear': 'clear.wav', 
            'stomp': 'stomp.wav', 
            'damage': 'damage.wav', # Fallback to stomp if missing
            'move': 'move.wav'
        }
        for name, file in sfx_map.items():
            path = os.path.join('assets', 'sounds', file)
            if not os.path.exists(path): path = file
            if os.path.exists(path):
                try:
                    self.sounds[name] = pygame.mixer.Sound(path)
                    self.sounds[name].set_volume(0.4)
                except: pass
        
        # Fallback for damage
        if 'damage' not in self.sounds and 'stomp' in self.sounds:
            self.sounds['damage'] = self.sounds['stomp']

    def play(self, name):
        if not self.enabled or name not in self.sounds: return
        try: self.sounds[name].play()
        except: pass

# --- FIREBASE MANAGER ---
class FirebaseManagerV56:
    def __init__(self, db_url):
        self.db_url = db_url.rstrip('/')
        self.room_id = "battle_v56_official"
        self.role = None ; self.opp_role = None ; self.connected = False
        self.room_state = "waiting" ; self.countdown_start = 0
        self.p1_ready = False ; self.p2_ready = False
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
        if t - self.poll_time < 0.45: return 
        self.poll_time = t
        data = await asyncio.to_thread(self._req, f"{self.db_url}/battles/{self.room_id}.json")
        if data:
            self.room_state = data.get('state', 'waiting')
            self.countdown_start = data.get('countdown_start', 0)
            self.p1_ready = data.get('p1', {}).get('ready', False)
            self.p2_ready = data.get('p2', {}).get('ready', False)
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

# --- GAME OBJECTS ---
class TurtleV56:
    def __init__(self, x, type_id='K'):
        self.x, self.y = float(x), -1.0
        self.type_id = type_id # 'K'=Green, 'R'=Red
        self.state = 'falling'
        self.vy = 0
        self.dir = random.choice([-1, 1])
        self.lifetime = 12.0
        self.speed = 1.0
        self.anim_frame = 0 ; self.anim_timer = 0

    def update(self, dt, grid):
        self.anim_timer += dt
        if self.anim_timer > 0.15: self.anim_timer = 0; self.anim_frame = 1 - self.anim_frame
        
        # Physics
        self.vy += 25 * dt
        self.y += self.vy * dt
        
        ix, iy = int(self.x), int(self.y)
        below = iy + 1
        
        # Floor & Block Collision
        if self.y >= 19.0: # Ground
            self.y = 19.0 ; self.vy = 0
            if self.state == 'falling': self.state = 'walking'
        elif below < 20 and 0 <= ix < 10 and grid[below][ix] is not None:
            self.y = float(below - 1) ; self.vy = 0
            if self.state == 'falling': self.state = 'walking'
        else:
            self.state = 'falling'

        if self.state == 'walking':
            self.lifetime -= dt
            # Move
            nx = int(self.x + self.dir * 0.5)
            if nx < 0 or nx >= 10 or (int(self.y) < 20 and grid[int(self.y)][nx] is not None):
                self.dir *= -1
            elif self.type_id == 'R': # Red turns at edge
                nb = int(self.y + 1)
                if nb < 20 and grid[nb][nx] is None: self.dir *= -1
            
            self.x += self.dir * self.speed * dt
            return self.lifetime <= 0
        return False

# --- CORE GAME ---
WW, WH = 1000, 720
GW, GH = 10, 20
BS = 32 # Back to 32px standard
ID_TO_COLOR = {'1':(0,240,240),'2':(240,240,0),'3':(160,0,240),'4':(0,240,0),'5':(240,0,0),'6':(0,0,240),'7':(240,160,0),'G':(140,140,140)}
COLOR_TO_ID = {v: k for k, v in ID_TO_COLOR.items()}

class TetrisV56:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WW, WH))
        pygame.display.set_caption("MARIO BATTLE OFFICIAL V56")
        self.clock = pygame.time.Clock()
        self.fb = FirebaseManagerV56("https://mario-tetris-game-default-rtdb.firebaseio.com/")
        self.sm = SoundManager()
        
        try:
            f = "assets/PressStart2P-Regular.ttf"
            if not os.path.exists(f): f = "Arial"
            self.font = pygame.font.Font(f, 13) if ".ttf" in f else pygame.font.SysFont(f, 18)
            self.huge = pygame.font.Font(f, 40) if ".ttf" in f else pygame.font.SysFont(f, 50)
        except: self.font = self.huge = None

        self.mode = "menu" ; self.load_assets() ; self.reset()

    def load_assets(self):
        try:
            m = pygame.image.load("assets/marioallsprite.png").convert_alpha()
            b = pygame.image.load("assets/blocks.png").convert_alpha()
            self.imgs = {
                'brick': self.get_sprite(b, 368, 112, 16, 16, BS/16),
                'question': self.get_sprite(b, 80, 112, 16, 16, BS/16),
                'koopa': [self.get_sprite(m, 206, 242, 20, 27, BS/24), self.get_sprite(m, 247, 242, 20, 27, BS/24)],
                'red_koopa': [self.get_sprite(m, 326, 242, 20, 27, BS/24), self.get_sprite(m, 367, 242, 20, 27, BS/24)],
                'mario': self.get_sprite(m, 10, 6, 12, 16, 4.0),
                'luigi': self.get_sprite(m, 10, 6, 12, 16, 4.0),
                'ground': self.get_sprite(b, 0, 0, 16, 16, BS/16)
            }
            if 'luigi' in self.imgs: self.imgs['luigi'].fill((100, 255, 100), special_flags=pygame.BLEND_RGB_MULT)
            if 'red_koopa' not in self.imgs and 'koopa' in self.imgs:
                self.imgs['red_koopa'] = [f.copy() for f in self.imgs['koopa']]
                for f in self.imgs['red_koopa']: f.fill((255,100,100), special_flags=pygame.BLEND_RGB_MULT)
        except Exception as e: log(f"Assets Error: {e}"); self.imgs = {}

    def get_sprite(self, sheet, x, y, w, h, s):
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.blit(sheet, (0, 0), (x, y, w, h))
        return pygame.transform.scale(surf, (int(w*s), int(h*s)))

    def reset(self):
        self.grid = [[None for _ in range(GW)] for _ in range(GH)]
        self.bag = [] ; self.pos = [GW//2-1, 0] ; self.shape = self.spawn()
        self.fall_dt = 0 ; self.enemies = [] ; self.score = 0 ; self.stomps = 0 ; self.is_ready = False ; self.spawn_t = 0

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
                        if e.key == pygame.K_1: await self.fb.join("p1") ; self.mode = "lobby"
                        if e.key == pygame.K_2: await self.fb.join("p2") ; self.mode = "lobby"
                        if e.key == pygame.K_SPACE: subprocess.Popen([sys.executable, os.path.abspath(__file__)])
                    elif self.mode == "lobby" and e.key == pygame.K_RETURN:
                        self.is_ready = not self.is_ready ; await self.fb.set_ready(self.is_ready)
                    elif self.mode == "play":
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
                        if e.key == pygame.K_DOWN:
                            self.pos[1]+=1
                            if self.collide(self.pos, self.shape): self.pos[1]-=1

            if self.mode != "menu":
                await self.fb.poll()
                if self.fb.p1_ready and self.fb.p2_ready and self.fb.role == "p1" and self.fb.room_state == "waiting":
                    await asyncio.to_thread(self.fb._req, f"{self.fb.db_url}/battles/{self.fb.room_id}.json", "PATCH", {"state":"countdown", "countdown_start":time.time()})
                
                if self.fb.room_state == "countdown" and self.mode == "lobby": self.mode = "play" ; self.reset()
                
                if self.mode == "play":
                    # Sync
                    comp = "".join([COLOR_TO_ID.get(c, "0") if c!=(140,140,140) else "G" for r in self.grid for c in r])
                    asyncio.create_task(self.fb.sync(comp, self.score, self.stomps))
                    
                    if self.fb.pending_garbage > 0:
                        self.sm.play('damage')
                        for _ in range(int(self.fb.pending_garbage)):
                            self.grid.pop(0) ; h = random.randint(0,9)
                            self.grid.append([(140,140,140) if x!=h else None for x in range(GW)])
                        self.fb.pending_garbage = 0
                    
                    self.spawn_t += dt
                    if self.spawn_t > 8.0:
                        self.spawn_t = 0
                        t = random.choice(['K', 'R'])
                        self.enemies.append(TurtleV56(random.randint(0,9), t))
                    
                    for en in self.enemies[:]:
                        if en.update(dt, self.grid):
                            self.enemies.remove(en) ; self.sm.play('damage')
                            self.grid.pop(0) ; h = random.randint(0,9)
                            self.grid.append([(140,140,140) if x!=h else None for x in range(GW)])
                        elif en.y > GH + 1: self.enemies.remove(en)
                        elif en.state == 'walking':
                            for bx, by in self.shape[0]:
                                if int(en.x) == self.pos[0]+bx and int(en.y) == self.pos[1]+by:
                                    self.enemies.remove(en) ; self.stomps += 1 ; self.score += 500
                                    self.sm.play('stomp')
                                    asyncio.create_task(self.fb.attack(1)) ; break

                    self.fall_dt += dt
                    if self.fall_dt > 0.8:
                        self.fall_dt = 0; self.pos[1] += 1
                        if self.collide(self.pos, self.shape):
                            self.pos[1] -= 1 ; self.sm.play('lock')
                            c = {'I':(0,240,240),'O':(240,240,0),'T':(160,0,240),'S':(0,240,0),'Z':(240,0,0),'J':(0,0,240),'L':(240,160,0)}[self.shape[1]]
                            for bx, by in self.shape[0]:
                                if 0 <= self.pos[1]+by < GH: self.grid[self.pos[1]+by][self.pos[0]+bx] = c
                            new_g = [r for r in self.grid if any(x is None for x in r)]
                            cleared = GH - len(new_g)
                            if cleared > 0:
                                self.sm.play('clear') ; self.score += (cleared * 1000)
                                while len(new_g) < GH: new_g.insert(0, [None]*GW)
                                self.grid = new_g ; asyncio.create_task(self.fb.attack(cleared))
                            self.pos = [GW//2-1, 0] ; self.shape = self.spawn()
                            if self.collide(self.pos, self.shape): self.reset()

            self.draw() ; await asyncio.sleep(0.01)

    def draw(self):
        self.screen.fill((92, 148, 252))
        if self.mode == "menu":
            self.draw_t("MARIO BATTLE OFFICIAL V56", self.huge, (255,255,255), WW//2, 200)
            self.draw_t("Press [1] for Mario, [2] for Luigi", self.font, (255,255,0), WW//2, 350)
            self.draw_t("Press [ENTER] in both to start", self.font, (255,255,255), WW//2, 400)
        else:
            # Player 1 (Left)
            mx, my = 60, 100
            pygame.draw.rect(self.screen, (0,0,0,160), (mx, my, GW*BS, GH*BS))
            # Grid
            for y in range(GH):
                for x in range(GW):
                    c = self.grid[y][x]
                    if c: self.draw_b(mx+x*BS, my+y*BS, c, BS)
            # Piece
            for bx, by in self.shape[0]:
                c = {'I':(0,240,240),'O':(240,240,0),'T':(160,0,240),'S':(0,240,0),'Z':(240,0,0),'J':(0,0,240),'L':(240,160,0)}[self.shape[1]]
                self.draw_b(mx+(self.pos[0]+bx)*BS, my+(self.pos[1]+by)*BS, c, BS, False)
            # Enemies
            for en in self.enemies:
                k = 'koopa' if en.type_id=='K' else 'red_koopa'
                if k in self.imgs:
                    img = self.imgs[k][en.anim_frame]
                    if en.dir == -1: img = pygame.transform.flip(img, True, False)
                    self.screen.blit(img, (mx+en.x*BS, my+en.y*BS-5))
                if en.state == 'walking':
                    pygame.draw.rect(self.screen, (255,0,0), (mx+en.x*BS, my+en.y*BS-10, BS * (en.lifetime/12.0), 4))
            
            # HUD L
            p = self.imgs['mario' if self.fb.role=='p1' else 'luigi'] if 'mario' in self.imgs else None
            if p: self.screen.blit(p, (mx-50, 40))
            self.draw_t(f"SCORE: {self.score}", self.font, (255,255,255), mx, 70, False)
            self.draw_t(f"STOMPS: {self.stomps}", self.font, (100,255,100), mx + 180, 70, False)

            # Player 2 (Right)
            ox, oy = 600, 100 ; sbs = 28
            pygame.draw.rect(self.screen, (0,0,0,120), (ox, oy, GW*sbs, GH*sbs))
            for i, char in enumerate(self.fb.opp_grid_raw):
                if char != '0':
                    x, y = i%10, i//10 ; c = ID_TO_COLOR.get(char, (200,200,200))
                    pygame.draw.rect(self.screen, c, (ox+x*sbs, oy+y*sbs, sbs, sbs))
                    pygame.draw.rect(self.screen, (255,255,255), (ox+x*sbs, oy+y*sbs, sbs, sbs), 1)
            self.draw_t(f"OPP SCORE: {self.fb.opp_score}", self.font, (255,255,255), ox, 70, False)
            self.draw_t(f"OPP STOMP: {self.fb.opp_stomps}", self.font, (255,100,100), ox + 180, 70, False)

            if self.mode == "lobby":
                msg = "READY UP!" if not self.is_ready else "WAITING..."
                self.draw_t(msg, self.font, (255,255,255), WW//2, WH-60)
            if self.fb.room_state == "countdown":
                cd = 3 - int(time.time() - self.fb.countdown_start)
                self.draw_t(str(max(1, cd)), self.huge, (255,255,255), WW//2, WH//2)

        pygame.display.flip()

    def draw_b(self, x, y, color, size, q=True):
        if color == (140,140,140) and 'brick' in self.imgs: self.screen.blit(self.imgs['brick'], (x,y))
        elif q and 'question' in self.imgs:
            t = self.imgs['question'].copy() ; t.fill(color, special_flags=pygame.BLEND_RGB_MULT) ; self.screen.blit(t, (x,y))
        else:
            pygame.draw.rect(self.screen, color, (x,y,size,size)) ; pygame.draw.rect(self.screen, (255,255,255), (x,y,size,size), 1)

    def draw_t(self, text, font, color, x, y, center=True):
        if not font: return
        s = font.render(text, True, color)
        r = s.get_rect(center=(x, y)) if center else s.get_rect(topleft=(x, y))
        self.screen.blit(s, r)

if __name__ == "__main__":
    try: asyncio.run(TetrisV56().run())
    except:
        with open(f"crash_v56_{PID}.txt", "w") as f: f.write(traceback.format_exc())
        input("CRASH")
