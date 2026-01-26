
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

# --- V76 - "MARIO BATTLE PRO STRIKE (GHOST + CORR)" ---
# Features:
# - GHOST PIECE: Shows a 50% transparent preview of where your piece will land.
# - STOMP CORRELATION: Spinning shells fly from your stack to the opponent on stomp.
# - ATTACK NOTIFICATIONS: Large "STOMP SENT!" and "STOMP RECV!" messages.
# - LIVE SYNC: Falling pieces are visible on opponent's preview.
# - STRETCHY PHYSICS: Advanced snapping ensures turtles never fall through blocks.

PID = os.getpid()
LOG_FILE = f"v76_log_{PID}.txt"

def log(msg):
    try:
        ts = time.strftime('%H:%M:%S')
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
            f.flush()
    except: pass
    print(f"[V76-{PID}] {msg}")

# --- VISUAL EFFECTS ---
class CombatMessage:
    def __init__(self, text, color, x, y, font_type='font'):
        self.text = text
        self.color = color
        self.x = x
        self.y = y
        self.life = 1.4
        self.font_type = font_type
    
    def update(self, dt):
        self.life -= dt
        self.y -= 35 * dt
        return self.life > 0

class ShellProjectile:
    def __init__(self, x, y, target_x, target_y, img):
        self.x = float(x)
        self.y = float(y)
        self.tx = target_x
        self.ty = target_y
        self.img = img
        self.life = 1.0
        self.angle = 0
        
    def update(self, dt):
        # Fly towards the opponent's grid area
        self.life -= dt * 1.5
        self.x += (self.tx - self.x) * 0.12
        self.y += (self.ty - self.y) * 0.12
        self.angle += 30 # Rapid spin
        return self.life > 0

# --- SOUND MANAGER ---
class SoundManager:
    def __init__(self):
        self.sounds = {}
        self.playlist = ['2. Bring The Noise.mp3', '06. Them and Us.mp3', '05. Ten in 2010.mp3']
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.pre_init(44100, -16, 2, 512)
                pygame.mixer.init()
            pygame.mixer.set_num_channels(32)
            self._load_all()
        except: 
            log("Mixer Init Failed.")

    def _load_all(self):
        sfx = {
            'rotate':'rotate.wav', 'lock':'lock.wav', 'clear':'clear.wav', 
            'stomp':'stomp.wav', 'move':'move.wav',
            'damage':'impactBell_heavy_004.ogg', 'land':'impactGeneric_light_002.ogg',
            'shell':'impactGeneric_power_001.ogg'
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
        if name in self.sounds:
            try:
                self.sounds[name].play()
            except: pass

    def play_bgm(self, idx=None):
        if idx is None:
            idx = random.randint(0, len(self.playlist)-1)
        tk = self.playlist[idx]
        p = os.path.join('sounds', tk)
        if not os.path.exists(p): p = tk
        if os.path.exists(p):
            try:
                pygame.mixer.music.load(p)
                pygame.mixer.music.set_volume(0.25)
                pygame.mixer.music.play(-1, fade_ms=2000)
            except: pass

# --- NETWORK ---
class FirebaseManagerV76:
    def __init__(self, db_url):
        self.db_url = db_url.rstrip('/')
        self.room_id = "battle_v76_pro"
        self.role = None
        self.opp_role = None
        self.connected = False
        self.room_state = "waiting"
        self.countdown_start = 0
        self.p1_ready = False
        self.p2_ready = False
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
                with urllib.request.urlopen(req, data=body, timeout=4) as r:
                    return json.loads(r.read().decode('utf-8'))
            else:
                with urllib.request.urlopen(req, timeout=4) as r:
                    return json.loads(r.read().decode('utf-8'))
        except: return None

    async def join(self, role):
        self.role = role
        self.opp_role = "p2" if role == "p1" else "p1"
        url = f"{self.db_url}/battles/{self.room_id}.json"
        if role == "p1":
            d = {
                "state":"waiting", 
                "p1":{"ready":False, "attack_queue":0, "grid_comp":"0"*200, "score":0, "stomps":0}, 
                "p2":{"ready":False, "attack_queue":0, "grid_comp":"0"*200, "score":0, "stomps":0}, 
                "countdown_start":0
            }
            await asyncio.to_thread(self._req, url, "PUT", d)
        else:
            await asyncio.to_thread(self._req, f"{self.db_url}/battles/{self.room_id}/p2.json", "PATCH", {"status":"alive", "ready":False})
        self.connected = True

    async def poll(self):
        if not self.connected: return
        t = time.time()
        if t - self.poll_time > 0.42:
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
            self.poll_time = t

    async def set_ready(self, b):
        if self.connected:
            url = f"{self.db_url}/battles/{self.room_id}/{self.role}.json"
            await asyncio.to_thread(self._req, url, "PATCH", {"ready":b})

    async def sync(self, grid_str, score, stomps):
        if self.connected:
            url = f"{self.db_url}/battles/{self.room_id}/{self.role}.json"
            await asyncio.to_thread(self._req, url, "PATCH", {"grid_comp":grid_str, "score":score, "stomps":stomps})

    async def attack(self, n):
        if self.connected:
            url = f"{self.db_url}/battles/{self.room_id}/{self.role}.json"
            data = await asyncio.to_thread(self._req, url)
            cur = data.get('attack_queue', 0) if data else 0
            await asyncio.to_thread(self._req, url, "PATCH", {"attack_queue": cur + n})

# --- PHYSICS ---
class Enemy:
    def __init__(self, x, type_id='K'):
        self.x = float(x)
        self.y = -1.0
        self.type_id = type_id
        self.state = 'falling'
        self.vy = 0
        self.dir = random.choice([-1, 1])
        self.lifetime = 15.0
        self.anim_frame = 0
        self.anim_timer = 0
        
    def update(self, dt, grid, sm):
        self.anim_timer += dt
        if self.anim_timer > 0.12:
            self.anim_timer = 0
            self.anim_frame = 1 - self.anim_frame
        
        self.vy += 35 * dt
        self.y += self.vy * dt
        
        # Snap to highest point in column
        ix = int(max(0, min(9, self.x + 0.5)))
        target_y = 19.0
        start_row = int(max(0, self.y))
        for row in range(start_row, 20):
            if grid[row][ix] is not None:
                target_y = float(row - 1.0)
                break
        
        landed = False
        if self.y >= target_y:
            self.y = target_y
            self.vy = 0
            landed = True
            
        if landed:
            if self.state == 'falling':
                self.state = 'walking'
                sm.play('land')
        else:
            self.state = 'falling'

        if landed:
            row_idx = int(self.y + 0.5)
            if 0 <= row_idx < 20 and grid[row_idx][ix] is not None:
                sm.play('damage')
                return True

        if self.state == 'walking':
            self.lifetime -= dt
            next_x = self.x + self.dir * 1.5 * dt
            nx = int(max(0, min(9, next_x + 0.5)))
            
            turn = False
            if next_x < 0 or next_x > 9:
                turn = True
            elif 0 <= nx < 10 and 0 <= int(self.y + 0.5) < 20:
                if grid[int(self.y + 0.5)][nx] is not None:
                    turn = True
            
            if turn: self.dir *= -1
            else: self.x = next_x
            
            return self.lifetime <= 0
        return False

# --- CORE GAME ---
WW, WH = 1000, 720
GW, GH = 10, 20
BS = 32
GRID_Y = 60
ID_TO_COLOR = {
    '1':(0,240,240),'2':(240,240,0),'3':(160,0,240),'4':(0,240,0),
    '5':(240,0,0),'6':(0,0,240),'7':(240,160,0),'G':(140,140,140)
}
COLOR_TO_ID = {v: k for k, v in ID_TO_COLOR.items()}

class TetrisV76:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WW, WH))
        pygame.display.set_caption("MARIO BATTLE PRO V76")
        self.clock = pygame.time.Clock()
        self.fb = FirebaseManagerV76("https://mario-tetris-game-default-rtdb.firebaseio.com/")
        self.sm = SoundManager()
        try:
            f = "assets/PressStart2P-Regular.ttf"
            if os.path.exists(f):
                self.font = pygame.font.Font(f, 13)
                self.huge = pygame.font.Font(f, 32)
                self.giant = pygame.font.Font(f, 50)
            else:
                self.font = pygame.font.SysFont("Arial", 18)
                self.huge = pygame.font.SysFont("Arial", 40)
                self.giant = pygame.font.SysFont("Arial", 60)
        except:
            self.font = self.huge = self.giant = None
            
        self.mode = "menu"
        self.load_assets()
        self.reset()
        self.shake = 0
        self.messages = []
        self.projectiles = []

    def load_assets(self):
        try:
            m = pygame.image.load("assets/marioallsprite.png").convert_alpha()
            b = pygame.image.load("assets/blocks.png").convert_alpha()
            self.imgs = {
                'brick': self.get_sprite(b, 368, 112, 16, 16, BS/16),
                'koopa': [self.get_sprite(m, 206, 242, 20, 27, 2.0), self.get_sprite(m, 247, 242, 20, 27, 2.0)],
                'red_koopa': [self.get_sprite(m, 206, 282, 20, 27, 2.0), self.get_sprite(m, 245, 283, 20, 27, 2.0)],
                'shell': self.get_sprite(m, 360, 212, 16, 16, 2.0), # Stomp projectile
                'mario': self.get_sprite(m, 10, 6, 12, 16, 4.0), 
                'luigi': self.get_sprite(m, 10, 6, 12, 16, 4.0),
                'ground': self.get_sprite(b, 0, 0, 16, 16, BS/16)
            }
            if 'luigi' in self.imgs:
                self.imgs['luigi'].fill((100, 255, 100), special_flags=pygame.BLEND_RGB_MULT)
        except:
            self.imgs = {}

    def get_sprite(self, sheet, x, y, w, h, s):
        ss = pygame.Surface((w, h), pygame.SRCALPHA)
        ss.blit(sheet, (0, 0), (x, y, w, h))
        return pygame.transform.scale(ss, (int(w*s), int(h*s)))

    def reset(self):
        self.grid = [[None for _ in range(GW)] for _ in range(GH)]
        self.bag = []
        self.pos = [GW//2-1, 0]
        self.shape = self.spawn()
        self.fall_dt = 0
        self.enemies = []
        self.score = 0
        self.stomps = 0
        self.is_ready = False
        self.spawn_t = 0
        self.clearing = []
        self.clear_t = 0

    def spawn(self):
        if not self.bag:
            self.bag = ['I','O','T','S','Z','J','L']
            random.shuffle(self.bag)
        s = self.bag.pop()
        d = {
            'I':[(0,0),(1,0),(2,0),(3,0)], 'O':[(0,0),(1,0),(0,1),(1,1)], 
            'T':[(1,0),(0,1),(1,1),(2,1)], 'S':[(1,0),(2,0),(0,1),(1,1)], 
            'Z':[(0,0),(1,0),(1,1),(2,1)], 'J':[(0,0),(0,1),(1,1),(2,1)], 
            'L':[(2,0),(0,1),(1,1),(2,1)]
        }
        return [[list(b) for b in d[s]], s]

    def collide(self, p, s):
        for bx, by in s[0]:
            gx, gy = p[0]+bx, p[1]+by
            if gx < 0 or gx >= GW or gy >= GH:
                return True
            if gy >= 0 and self.grid[gy][gx]:
                return True
        return False

    async def run(self):
        while True:
            dt = self.clock.tick(60)/1000.0
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT: return
                if event.type == pygame.KEYDOWN:
                    if self.mode == "menu":
                        if event.key == pygame.K_1:
                            await self.fb.join("p1")
                            self.mode = "lobby" ; self.sm.play_bgm()
                        if event.key == pygame.K_2:
                            await self.fb.join("p2")
                            self.mode = "lobby" ; self.sm.play_bgm()
                    elif self.mode == "lobby" and event.key == pygame.K_RETURN:
                        self.is_ready = not self.is_ready
                        await self.fb.set_ready(self.is_ready)
                    elif self.mode == "play" and not self.clearing:
                        if event.key == pygame.K_LEFT:
                            self.pos[0] -= 1
                            if self.collide(self.pos, self.shape): self.pos[0] += 1
                            else: self.sm.play('move')
                        if event.key == pygame.K_RIGHT:
                            self.pos[0] += 1
                            if self.collide(self.pos, self.shape): self.pos[0] -= 1
                            else: self.sm.play('move')
                        if event.key == pygame.K_UP:
                            old = [list(b) for b in self.shape[0]]
                            self.shape[0] = [(-by, bx) for bx, by in old]
                            if self.collide(self.pos, self.shape): self.shape[0] = old
                            else: self.sm.play('rotate')
                        if event.key == pygame.K_SPACE:
                            while not self.collide([self.pos[0], self.pos[1]+1], self.shape): self.pos[1] += 1
                            self.sm.play('lock') ; self.fall_dt = 10.0

            if self.mode != "menu":
                await self.fb.poll()
                # Global Match Start Check
                if self.fb.p1_ready and self.fb.p2_ready and self.fb.role == "p1" and self.fb.room_state == "waiting":
                    url = f"{self.fb.db_url}/battles/{self.fb.room_id}.json"
                    await asyncio.to_thread(self.fb._req, url, "PATCH", {"state":"countdown", "countdown_start":time.time()})
                
                if self.fb.room_state == "countdown" and self.mode == "lobby":
                    if time.time() - self.fb.countdown_start >= 3.0:
                        self.mode = "play" ; self.reset()
                
                if self.mode == "play":
                    self.messages = [m for m in self.messages if m.update(dt)]
                    self.projectiles = [p for p in self.projectiles if p.update(dt)]
                    if self.shake > 0: self.shake -= dt*20
                    
                    if self.clearing:
                        self.clear_t -= dt
                        if self.clear_t <= 0:
                            new_grid = [r for idx, r in enumerate(self.grid) if idx not in self.clearing]
                            while len(new_grid) < GH: new_grid.insert(0, [None]*GW)
                            self.grid = new_grid ; self.clearing = [] ; self.pos = [GW//2-1, 0] ; self.shape = self.spawn()
                    else:
                        # LIVE SYNC
                        temp_grid = [row[:] for row in self.grid]
                        ccid = {'I':'1','O':'2','T':'3','S':'4','Z':'5','J':'6','L':'7'}[self.shape[1]]
                        for bx, by in self.shape[0]:
                            gx, gy = self.pos[0]+bx, self.pos[1]+by
                            if 0 <= gx < 10 and 0 <= gy < 20: temp_grid[gy][gx] = ID_TO_COLOR[ccid]
                        sync_str = "".join([COLOR_TO_ID.get(c, "0") if c!=(140,140,140) else "G" for row in temp_grid for c in row])
                        asyncio.create_task(self.fb.sync(sync_str, self.score, self.stomps))
                        
                        if self.fb.pending_garbage > 0:
                            self.sm.play('damage') ; self.shake = 12
                            self.messages.append(CombatMessage("⚠️ STOMP RECV!", (255,50,50), 320, 200, 'huge'))
                            for _ in range(int(self.fb.pending_garbage)):
                                self.grid.pop(0) ; self.grid.append([(140,140,140) if x!=random.randint(0,9) else None for x in range(GW)])
                            self.fb.pending_garbage = 0
                            
                        # Enemies & Stomp Logic
                        self.spawn_t += dt
                        if self.spawn_t > 9.0:
                            self.spawn_t = 0 ; self.enemies.append(Enemy(random.randint(0,9), random.choice(['K','R'])))
                        
                        for en in self.enemies[:]:
                            if en.update(dt, self.grid, self.sm): self.enemies.remove(en)
                            elif en.y > GH + 1: self.enemies.remove(en)
                            elif en.state == 'walking':
                                for bx, by in self.shape[0]:
                                    if int(en.x + 0.5) == self.pos[0]+bx and int(en.y + 0.5) == self.pos[1]+by:
                                        self.enemies.remove(en) ; self.stomps += 1 ; self.score += 500 ; self.sm.play('stomp')
                                        # Correlation Effect
                                        self.messages.append(CombatMessage("STOMP SENT! 🚀", (0,255,255), 320, 250, 'huge'))
                                        if 'shell' in self.imgs:
                                            self.projectiles.append(ShellProjectile(60+en.x*BS, GRID_Y+en.y*BS, 620, 200, self.imgs['shell']))
                                        self.sm.play('shell')
                                        asyncio.create_task(self.fb.attack(1)) ; break
                        
                        speed = 0.8
                        if pygame.key.get_pressed()[pygame.K_DOWN]: speed = 0.05
                        self.fall_dt += dt
                        if self.fall_dt > speed:
                            self.fall_dt = 0 ; self.pos[1] += 1
                            if self.collide(self.pos, self.shape):
                                self.pos[1] -= 1 ; self.sm.play('lock') ; c_id = self.shape[1]
                                col = {'I':(0,240,240),'O':(240,240,0),'T':(160,0,240),'S':(0,240,0),'Z':(240,0,0),'J':(0,0,240),'L':(240,160,0)}[c_id]
                                for bx, by in self.shape[0]:
                                    if 0 <= self.pos[1]+by < GH: self.grid[self.pos[1]+by][self.pos[0]+bx] = col
                                self.clearing = [ri for ri, r in enumerate(self.grid) if all(cell is not None for cell in r)]
                                if self.clearing:
                                    self.sm.play('clear') ; self.score += (len(self.clearing)*1000) ; self.clear_t = 0.6 ; self.shake = 22
                                    self.messages.append(CombatMessage(f"ULTRA STRIKE! +{len(self.clearing)} 🔥", (0,255,255), 200, 300, 'huge'))
                                    asyncio.create_task(self.fb.attack(len(self.clearing)))
                                else:
                                    self.pos = [GW//2-1, 0] ; self.shape = self.spawn()
                                    if self.collide(self.pos, self.shape): self.reset()
            self.draw() ; await asyncio.sleep(0.01)

    def draw(self):
        sx, sy = (random.randint(-int(self.shake), int(self.shake)), random.randint(-int(self.shake), int(self.shake))) if self.shake>0 else (0,0)
        self.screen.fill((92, 148, 252))
        
        if self.mode == "menu":
            self.draw_t("MARIO BATTLE PRO V76", self.giant, (255,255,255), WW//2, 200)
            self.draw_t("GHOST PIECE + STOMP CORRELATION", self.huge, (255,255,0), WW//2, 350)
        else:
            mx, my = 60 + sx, GRID_Y + sy
            pygame.draw.rect(self.screen, (0,0,0,225), (mx-4, my-4, GW*BS+8, GH*BS+8)) ; pygame.draw.rect(self.screen, (255,255,255), (mx-4, my-4, GW*BS+8, GH*BS+8), 2)
            if 'ground' in self.imgs:
                for x in range(GW): self.screen.blit(self.imgs['ground'], (mx+x*BS, my+GH*BS))
            
            # GHOST PIECE
            if not self.clearing and self.mode == "play":
                gx, gy = self.pos[0], self.pos[1]
                while not self.collide([gx, gy + 1], self.shape): gy += 1
                sid = self.shape[1] ; scol = {'I':(0,240,240),'O':(240,240,0),'T':(160,0,240),'S':(0,240,0),'Z':(240,0,0),'J':(0,0,240),'L':(240,160,0)}[sid]
                # Draw ghost with low alpha
                for bx, by in self.shape[0]: 
                    gs = pygame.Surface((BS, BS), pygame.SRCALPHA)
                    gs.fill((*scol, 80)) # 50% transparency
                    self.screen.blit(gs, (mx + (gx + bx)*BS, my + (gy + by)*BS))
                    pygame.draw.rect(self.screen, (*scol, 150), (mx + (gx + bx)*BS, my + (gy + by)*BS, BS, BS), 1)

            for y in range(GH):
                if y in self.clearing and int(time.time()*20)%2==0: pygame.draw.rect(self.screen, (255,255,255), (mx, my+y*BS, GW*BS, BS))
                else:
                    for x in range(GW):
                        c = self.grid[y][x] ; if c: self.draw_3d_b(mx+x*BS, my+y*BS, c, BS)
            
            if not self.clearing and self.mode == "play":
                sid = self.shape[1] ; scol = {'I':(0,240,240),'O':(240,240,0),'T':(160,0,240),'S':(0,240,0),'Z':(240,0,0),'J':(0,0,240),'L':(240,160,0)}[sid]
                for bx, by in self.shape[0]: self.draw_3d_b(mx+(self.pos[0]+bx)*BS, my+(self.pos[1]+by)*BS, scol, BS)
            
            for en in self.enemies:
                ikey = 'koopa' if en.type_id=='K' else 'red_koopa' ; eimg = self.imgs[ikey][en.anim_frame]
                if en.dir == 1: eimg = pygame.transform.flip(eimg, True, False)
                y_bob = abs(math.sin(time.time()*10))*6
                self.screen.blit(eimg, (mx+en.x*BS, my+en.y*BS-eimg.get_height()+BS-y_bob))
            for pr in self.projectiles:
                rot_shell = pygame.transform.rotate(pr.img, pr.angle) ; self.screen.blit(rot_shell, (pr.x - 16, pr.y - 16))
            for m in self.messages:
                uf = self.giant if m.font_type == 'giant' else (self.huge if m.font_type=='huge' else self.font)
                self.draw_t(m.text, uf, m.color, m.x, m.y)
            pimg = self.imgs['mario' if self.fb.role=='p1' else 'luigi'] if 'mario' in self.imgs else None
            if pimg: self.screen.blit(pimg, (mx-52, 5))
            self.draw_t(f"SCORE: {self.score}", self.font, (255,255,255), mx, 25, False)
            
            ox, oy = 620, GRID_Y+80 ; sbs = 28 ; pygame.draw.rect(self.screen, (0,0,0,150), (ox-4, oy-4, GW*sbs+8, GH*sbs+8))
            for i, cid in enumerate(self.fb.opp_grid_raw):
                if cid != '0': oc = ID_TO_COLOR.get(cid, (200,200,200)) ; self.draw_3d_b(ox+(i%10)*sbs, oy+(i//10)*sbs, oc, sbs)
            self.draw_t(f"OPP LIVE VIEW", self.huge, (255,255,255), ox, oy-35, False)
            if self.mode == "lobby":
                status = "HIT [ENTER] TO READY" if not self.is_ready else "WAITING..." ; self.draw_t(status, self.font, (255,255,255), WW//2, WH-60)
            if self.fb.room_state == "countdown":
                sec = 3 - int(time.time() - self.fb.countdown_start)
                if sec >= 0: self.draw_t(str(max(1, sec)), self.giant, (255,255,255), WW//2, WH//2)
        pygame.display.flip()

    def draw_3d_b(self, x, y, col, sz):
        if col == (140,140,140) and 'brick' in self.imgs: self.screen.blit(pygame.transform.scale(self.imgs['brick'], (sz, sz)), (x, y)) ; return
        lt, dk = [min(255, c+80) for c in col], [max(0, c-80) for c in col] ; pygame.draw.rect(self.screen, col, (x, y, sz, sz))
        pygame.draw.polygon(self.screen, lt, [(x,y),(x+sz,y),(x+sz-4,y+4),(x+4,y+4)])
        pygame.draw.polygon(self.screen, lt, [(x,y),(x+4,y+4),(x+4,y+sz-4),(x,y+sz)])
        pygame.draw.polygon(self.screen, dk, [(x+sz,y),(x+sz,y+sz),(x+sz-4,y+sz-4),(x+sz-4,y+4)])
        pygame.draw.polygon(self.screen, dk, [(x,y+sz),(x+sz,y+sz),(x+sz-4,y+sz-4),(x+4,y+sz-4)])

    def draw_t(self, t, f, c, x, y, ct=True):
        if f: s=f.render(t,True,c) ; r=s.get_rect(center=(x,y)) if ct else s.get_rect(topleft=(x,y)) ; self.screen.blit(s, r)

if __name__ == "__main__":
    try: asyncio.run(TetrisV76().run())
    except:
        with open(f"crash_v76_{PID}.txt", "w") as f: f.write(traceback.format_exc())
        input("CRASH")
