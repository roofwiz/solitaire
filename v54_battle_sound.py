
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

# --- V54 - "MARIO BATTLE ULTIMATE WITH SOUND" ---
# Features: 
# - SOUND SUPPORT: Non-blocking, safe mixer handling
# - Enemies MUST land and walk to be stompable
# - Timer / Lifetime for Enemies (Punishes player if expired)
# - Integrated HUD HUD with Score & Stomps
# - Interactive Shell Attacks

PID = os.getpid()
LOG_FILE = f"v54_log_{PID}.txt"

def log(msg):
    try:
        ts = time.strftime('%H:%M:%S')
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
            f.flush()
    except: pass
    print(f"[V54] {msg}")

# --- SOUND MANAGER ---
class SoundManager:
    def __init__(self):
        self.sounds = {}
        self.muted = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.pre_init(44100, -16, 2, 512)
                pygame.mixer.init()
            pygame.mixer.set_num_channels(16)
            self._load_sfx()
            log("Sound System Initialized.")
        except Exception as e:
            log(f"Sound Init Error: {e}")

    def _load_sfx(self):
        sfx_files = {
            'rotate': 'rotate.wav',
            'lock': 'lock.wav',
            'clear': 'clear.wav',
            'stomp': 'stomp.wav',
            'life': 'life.wav',
            'move': 'move.wav',
            'coin': 'life.wav',
            'damage': 'stomp.wav'
        }
        for name, fname in sfx_files.items():
            paths = [
                os.path.join('assets', 'sounds', fname),
                os.path.join('sounds', fname),
                fname
            ]
            for p in paths:
                if os.path.exists(p):
                    try:
                        self.sounds[name] = pygame.mixer.Sound(p)
                        self.sounds[name].set_volume(0.5)
                        break
                    except: pass

    def play(self, name):
        if self.muted or name not in self.sounds: return
        try: self.sounds[name].play()
        except: pass

class FirebaseManagerV54:
    def __init__(self, db_url):
        self.db_url = db_url.rstrip('/')
        self.room_id = "battle_v54"
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
            else: body = None
            with urllib.request.urlopen(req, data=body, timeout=3) as r:
                return json.loads(r.read().decode('utf-8'))
        except: return None

    async def pick(self, role):
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
        if t - self.poll_time < 0.4: return 
        self.poll_time = t
        data = await asyncio.to_thread(self._req, f"{self.db_url}/battles/{self.room_id}.json")
        if data:
            self.room_state, self.countdown_start = data.get('state','waiting'), data.get('countdown_start',0)
            self.p1_ready, self.p2_ready = data.get('p1',{}).get('ready',False), data.get('p2',{}).get('ready',False)
            opp = data.get(self.opp_role, {})
            self.opp_grid_raw, self.opp_score, self.opp_stomps = opp.get('grid_comp',"0"*200), opp.get('score',0), opp.get('stomps',0)
            remote_q = opp.get('attack_queue', 0)
            if remote_q > self.total_received:
                self.pending_garbage += (remote_q - self.total_received) ; self.total_received = remote_q

    async def sync(self, gs, sc, st):
        if self.connected: await asyncio.to_thread(self._req, f"{self.db_url}/battles/{self.room_id}/{self.role}.json", "PATCH", {"grid_comp":gs, "score":sc, "stomps":st})

# --- ENEMY LOGIC ---
class Enemy:
    def __init__(self, x, y, type_id):
        self.x, self.y = x, float(y)
        self.type_id = type_id ; self.frame = 0 ; self.anim_t = 0
        self.dir = random.choice([-1, 1])
        self.vy = 0 ; self.state = 'falling'
        self.lifetime = 12.0 # Slightly more time

    def update(self, dt, grid):
        self.anim_t += dt
        if self.anim_t > 0.15: self.anim_t = 0; self.frame = 1 - self.frame
        below = int(self.y + 1)
        ix = int(self.x)
        if below >= GH or (0 <= ix < GW and grid[below][ix] is not None):
            if self.state == 'falling': self.state = 'walking'
            self.y = float(int(self.y)) ; self.vy = 0
            # Pathfinding
            nx = self.x + self.dir
            if 0 <= nx < GW and grid[int(self.y)][nx] is None:
                if int(self.y)+1 >= GH or grid[int(self.y)+1][nx] is not None: self.x = nx
                else: self.dir *= -1
            else: self.dir *= -1
        else:
            self.state = 'falling'
            self.vy += 25 * dt ; self.y += self.vy * dt
        
        if self.state == 'walking':
            self.lifetime -= dt
            return self.lifetime <= 0
        return False

# --- SHELL ANIM ---
class ShellAnim:
    def __init__(self, start, end):
        self.x, self.y = start ; self.tx, self.ty = end ; self.t = 0.0
    def update(self, dt):
        self.t += dt * 1.5 ; return self.t < 1.0
    def get_pos(self):
        px = self.x + (self.tx - self.x) * self.t
        py = self.y + (self.ty - self.y) * self.t - 80 * math.sin(math.pi * self.t)
        return (int(px), int(py))

# --- CORE GAME ---
WW, WH = 1000, 700
GW, GH = 10, 20
BS = 30
ID_TO_COLOR = {'1':(0,255,255),'2':(255,255,0),'3':(128,0,128),'4':(0,255,0),'5':(255,0,0),'6':(0,0,255),'7':(255,165,0),'G':(140,140,140)}
COLOR_TO_ID = {v: k for k, v in ID_TO_COLOR.items()}

class TetrisV54:
    def __init__(self):
        pygame.init()
        # Do not quit mixer here, SoundManager will handle it
        self.screen = pygame.display.set_mode((WW, WH))
        pygame.display.set_caption("MARIO BATTLE ULTIMATE+ V54")
        self.clock = pygame.time.Clock()
        self.fb = FirebaseManagerV54("https://mario-tetris-game-default-rtdb.firebaseio.com/")
        self.sm = SoundManager()
        try:
            f = "assets/PressStart2P-Regular.ttf"
            self.font = pygame.font.Font(f, 12) if os.path.exists(f) else pygame.font.SysFont("Arial", 16)
            self.huge = pygame.font.Font(f, 40) if os.path.exists(f) else pygame.font.SysFont("Arial", 50)
        except: self.font = self.huge = None
        self.mode = "menu" ; self.load_assets() ; self.reset_game()

    def load_assets(self):
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
            self.imgs['luigi'].fill((100, 255, 100), special_flags=pygame.BLEND_RGB_MULT)
        except: self.imgs = {}

    def get_sprite(self, sheet, x, y, w, h, s):
        surf = pygame.Surface((w, h), pygame.SRCALPHA) ; surf.blit(sheet, (0, 0), (x, y, w, h))
        return pygame.transform.scale(surf, (int(w*s), int(h*s)))

    def reset_game(self):
        self.grid = [[None for _ in range(GW)] for _ in range(GH)]
        self.bag = [] ; self.pos = [GW//2-1, 0] ; self.shape = self.spawn()
        self.fall_dt = 0 ; self.enemies = [] ; self.shells = [] ; self.score = 0 ; self.stomps = 0 ; self.is_ready = False ; self.spawn_t = 0

    def spawn(self):
        if not self.bag: self.bag = ['I','O','T','S','Z','J','L'] ; random.shuffle(self.bag)
        s = self.bag.pop() ; return [[list(b) for b in { 'I':[(0,0),(1,0),(2,0),(3,0)], 'O':[(0,0),(1,0),(0,1),(1,1)], 'T':[(1,0),(0,1),(1,1),(2,1)], 'S':[(1,0),(2,0),(0,1),(1,1)], 'Z':[(0,0),(1,0),(1,1),(2,1)], 'J':[(0,0),(0,1),(1,1),(2,1)], 'L':[(2,0),(0,1),(1,1),(2,1)] }[s]], s]

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
                        if e.key == pygame.K_1: await self.fb.pick("p1") ; self.mode = "lobby"
                        if e.key == pygame.K_2: await self.fb.pick("p2") ; self.mode = "lobby"
                        if e.key == pygame.K_SPACE: subprocess.Popen([sys.executable, os.path.abspath(__file__)])
                    elif self.mode == "lobby" and e.key == pygame.K_RETURN:
                        self.is_ready = not self.is_ready ; await self.fb.set_ready(self.is_ready)
                    elif self.mode == "play":
                        m = False
                        if e.key == pygame.K_LEFT: self.pos[0]-=1 ; m = True
                        if self.collide(self.pos, self.shape): self.pos[0]+=1 ; m = False
                        if e.key == pygame.K_RIGHT: self.pos[0]+=1 ; m = True
                        if self.collide(self.pos, self.shape): self.pos[0]-=1 ; m = False
                        if m: self.sm.play('move')
                        if e.key == pygame.K_UP:
                            old = [list(b) for b in self.shape[0]] ; self.shape[0] = [(-by, bx) for bx, by in old]
                            if self.collide(self.pos, self.shape): self.shape[0] = old
                            else: self.sm.play('rotate')
                        if e.key == pygame.K_DOWN: self.pos[1]+=1 ; 
                        if self.collide(self.pos, self.shape): self.pos[1]-=1

            if self.mode != "menu":
                await self.fb.poll()
                if self.fb.p1_ready and self.fb.p2_ready and self.fb.role == "p1" and self.fb.room_state == "waiting":
                    await asyncio.to_thread(self.fb._req, f"{self.fb.db_url}/battles/{self.fb.room_id}.json", "PATCH", {"state":"countdown", "countdown_start":time.time()})
                if self.fb.room_state == "countdown" and self.mode == "lobby": self.mode = "play" ; self.reset_game()
                
                if self.mode == "play":
                    gs = "".join([("0" if c is None else COLOR_TO_ID.get(c, "G")) for r in self.grid for c in r])
                    asyncio.create_task(self.fb.sync(gs, self.score, self.stomps))
                    
                    if self.fb.pending_garbage > 0:
                        self.sm.play('damage')
                        for _ in range(int(self.fb.pending_garbage)):
                            self.grid.pop(0) ; self.grid.append([(140,140,140) if x!=random.randint(0,9) else None for x in range(GW)])
                        self.fb.pending_garbage = 0
                    
                    self.spawn_t += dt
                    if self.spawn_t > 7.0: self.spawn_t = 0 ; self.enemies.append(Enemy(random.randint(0,9), -1, 'K'))
                    
                    for en in self.enemies[:]:
                        punish = en.update(dt, self.grid)
                        if punish:
                            self.sm.play('damage') ; self.enemies.remove(en)
                            self.grid.pop(0) ; self.grid.append([(140,140,140) if x!=random.randint(0,9) else None for x in range(GW)])
                        elif en.y > GH + 1: self.enemies.remove(en)
                        elif en.state == 'walking':
                            for bx, by in self.shape[0]:
                                if int(en.x) == self.pos[0]+bx and int(en.y) == self.pos[1]+by:
                                    self.sm.play('stomp') ; self.enemies.remove(en) ; self.stomps += 1 ; self.score += 500
                                    self.shells.append(ShellAnim((60+en.x*BS, 80+en.y*BS), (600, 80)))
                                    asyncio.create_task(self.fb.send_attack(1)) ; break

                    self.fall_dt += dt
                    if self.fall_dt > 0.8:
                        self.fall_dt = 0 ; self.pos[1] += 1
                        if self.collide(self.pos, self.shape):
                            self.sm.play('lock') ; self.pos[1] -= 1
                            for bx, by in self.shape[0]:
                                if 0 <= self.pos[1]+by < GH: self.grid[self.pos[1]+by][self.pos[0]+bx] = {'I':(0,255,255),'O':(255,255,0),'T':(128,0,128),'S':(0,255,0),'Z':(255,0,0),'J':(0,0,255),'L':(255,165,0)}[self.shape[1]]
                            new_g = [r for r in self.grid if any(c is None for c in r)]
                            c = GH - len(new_g)
                            if c > 0:
                                self.sm.play('clear') ; self.score += (c*1000)
                                while len(new_g) < GH: new_g.insert(0, [None]*GW)
                                self.grid = new_g ; asyncio.create_task(self.fb.send_attack(c))
                            self.pos = [GW//2-1, 0] ; self.shape = self.spawn()
                            if self.collide(self.pos, self.shape): self.reset_game()

            self.shells = [s for s in self.shells if s.update(dt)]
            self.draw() ; await asyncio.sleep(0.01)

    def draw(self):
        self.screen.fill((92, 148, 252))
        if self.mode == "menu":
            self.draw_t("MARIO BATTLE ULTIMATE V54", self.huge, (255,255,255), WW//2, 200)
            self.draw_t("Pick 1 or 2 to Join (Space for Twin)", self.font, (255,255,0), WW//2, 350)
        else:
            mx, my = 60, 80
            pygame.draw.rect(self.screen, (0,0,0,150), (mx, my, GW*BS, GH*BS))
            for y, r in enumerate(self.grid):
                for x, c in enumerate(r):
                    if c: self.draw_b(mx+x*BS, my+y*BS, c, BS)
            for bx, by in self.shape[0]: 
                c = {'I':(0,255,255),'O':(255,255,0),'T':(128,0,128),'S':(0,255,0),'Z':(255,0,0),'J':(0,0,255),'L':(255,165,0)}[self.shape[1]]
                self.draw_b(mx+(self.pos[0]+bx)*BS, my+(self.pos[1]+by)*BS, c, BS, False)
            for en in self.enemies:
                img = self.imgs['koopa' if en.type_id=='K' else 'spiny'][en.frame]
                if en.dir == -1: img = pygame.transform.flip(img, True, False)
                self.screen.blit(img, (mx+en.x*BS, my+en.y*BS-5))
                if en.state == 'walking':
                     pygame.draw.rect(self.screen, (255,0,0), (mx+en.x*BS, my+en.y*BS-10, BS * (en.lifetime/12.0), 3))
            
            # HUD L
            idx = 'mario' if self.fb.role=='p1' else 'luigi'
            if idx in self.imgs: self.screen.blit(self.imgs[idx], (mx-50, 48))
            self.draw_t(f"SCORE:{self.score} STOMPS:{self.stomps}", self.font, (255,255,255), mx, 50, False)
            
            # P2 Grid
            px, py = 600, 80 ; sbs = 25
            pygame.draw.rect(self.screen, (0,0,0,100), (px, py, GW*sbs, GH*sbs))
            for i, char in enumerate(self.fb.opp_grid_raw):
                if char != '0':
                    x, y = i%10, i//10 ; c = ID_TO_COLOR.get(char, (100,100,100))
                    pygame.draw.rect(self.screen, c, (px+x*sbs, py+y*sbs, sbs, sbs))
                    pygame.draw.rect(self.screen, (255,255,255), (px+x*sbs, py+y*sbs, sbs, sbs), 1)
            self.draw_t(f"OPP SCORE:{self.fb.opp_score} STOMPS:{self.fb.opp_stomps}", self.font, (255,255,255), px, 50, False)

            for s in self.shells:
                if 'shell' in self.imgs: self.screen.blit(self.imgs['shell'], s.get_pos())
            
            if self.mode == "lobby":
                msg = "HIT ENTER TO READY" if not self.is_ready else "WAITING FOR BRO..."
                self.draw_t(msg, self.font, (255,255,255), WW//2, WH-50)

        pygame.display.flip()

    def draw_b(self, x, y, color, size, q=True):
        if color == (140,140,140) and 'brick' in self.imgs: self.screen.blit(self.imgs['brick'], (x,y))
        elif q and 'question' in self.imgs:
            t = self.imgs['question'].copy() ; t.fill(color, special_flags=pygame.BLEND_RGB_MULT) ; self.screen.blit(t, (x,y))
        else:
            pygame.draw.rect(self.screen, color, (x,y,size,size)) ; pygame.draw.rect(self.screen, (255,255,255), (x,y,size,size), 1)

    def draw_t(self, t, f, c, x, y, center=True):
        if not f: return
        s = f.render(t, True, c) ; r = s.get_rect(center=(x,y)) if center else s.get_rect(topleft=(x,y)) ; self.screen.blit(s, r)

if __name__ == "__main__":
    try: asyncio.run(TetrisV54().run())
    except: 
        with open(f"crash_v54_{PID}.txt", "w") as f: f.write(traceback.format_exc())
        input("CRASH")
