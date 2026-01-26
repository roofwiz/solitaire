
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

# --- V77 - "MARIO BATTLE COMPETITIVE ELITE" ---
# Features:
# - ACHIEVEMENT ANNOUNCER: Big banners for "STOMP SPREE", "MEGA STRIKE", "FIRST BLOOD".
# - COMPETITIVE HUD: Real-time objectives ("STOMP TO ATTACK!", "CLEAR LINES!").
# - GHOST PIECE & LIVE SYNC: Pro-level positioning and opponent awareness.
# - PHYSICAL CORRELATION: Shell projectiles fly on stomp with clear impact text.
# - WIN/LOSS ANNOUNCEMENTS: Clear declaration of the match result.

PID = os.getpid()

# --- CONSTANTS ---
WW, WH = 1000, 720
GW, GH = 10, 20
BS = 32
GRID_Y = 60
ID_TO_COLOR = {
    '1':(0,240,240),'2':(240,240,0),'3':(160,0,240),'4':(0,240,0),
    '5':(240,0,0),'6':(0,0,240),'7':(240,160,0),'G':(140,140,140)
}
COLOR_TO_ID = {v: k for k, v in ID_TO_COLOR.items()}

# --- VISUAL ENGINES ---
class Achievement:
    def __init__(self, text, color):
        self.text = text
        self.color = color
        self.life = 2.0
        self.alpha = 255
        self.y_off = 0
    def update(self, dt):
        self.life -= dt
        self.y_off -= 20 * dt
        if self.life < 0.5:
            self.alpha = int((self.life / 0.5) * 255)
        return self.life > 0

class ShellProjectile:
    def __init__(self, x, y, tx, ty, img):
        self.x, self.y = float(x), float(y)
        self.tx, self.ty = float(tx), float(ty)
        self.img = img
        self.life = 1.0
        self.angle = 0
    def update(self, dt):
        self.life -= dt * 1.5
        self.x += (self.tx - self.x) * 0.12
        self.y += (self.ty - self.y) * 0.12
        self.angle += 35
        return self.life > 0

class CombatMessage:
    def __init__(self, text, color, x, y, size='font'):
        self.text, self.color, self.x, self.y = text, color, x, y
        self.life = 1.4
        self.size = size
    def update(self, dt):
        self.life -= dt
        self.y -= 40 * dt
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
        except: pass

    def _load_all(self):
        sfx = {'rotate':'rotate.wav', 'lock':'lock.wav', 'clear':'clear.wav', 'stomp':'stomp.wav', 'move':'move.wav', 'damage':'impactBell_heavy_004.ogg', 'land':'impactGeneric_light_002.ogg', 'shell':'impactGeneric_power_001.ogg', 'win':'impactGeneric_heavy_001.ogg'}
        for name, file in sfx.items():
            for p in [os.path.join('sounds', file), file]:
                if os.path.exists(p):
                    try:
                        self.sounds[name] = pygame.mixer.Sound(p)
                        self.sounds[name].set_volume(0.4 if name != 'move' else 0.2)
                        break
                    except: pass

    def play(self, name):
        if name in self.sounds:
            try: self.sounds[name].play()
            except: pass

    def play_bgm(self):
        tk = self.playlist[random.randint(0, len(self.playlist)-1)]
        p = os.path.join('sounds', tk)
        if not os.path.exists(p): p = tk
        if os.path.exists(p):
            try: 
                pygame.mixer.music.load(p) ; pygame.mixer.music.set_volume(0.25) ; pygame.mixer.music.play(-1, fade_ms=2000)
            except: pass

# --- NETWORK ---
class FirebaseManagerV77:
    def __init__(self, db_url):
        self.db_url = db_url.rstrip('/')
        self.room_id = "battle_v77_elite"
        self.role = self.opp_role = None
        self.connected = False
        self.room_state = "waiting"
        self.countdown_start = 0
        self.p1_ready = self.p2_ready = False
        self.opp_grid_raw = "0" * 200
        self.pending_garbage = 0
        self.total_received = 0
        self.poll_time = 0
        self.opp_score = self.opp_stomps = 0
        self.game_over = False
        self.winner = None

    def _req(self, url, method="GET", data=None):
        try:
            req = urllib.request.Request(url, method=method)
            if data:
                req.add_header('Content-Type', 'application/json')
                body = json.dumps(data).encode('utf-8')
                with urllib.request.urlopen(req, data=body, timeout=4) as r: return json.loads(r.read().decode('utf-8'))
            else:
                with urllib.request.urlopen(req, timeout=4) as r: return json.loads(r.read().decode('utf-8'))
        except: return None

    async def join(self, role):
        self.role = role ; self.opp_role = "p2" if role == "p1" else "p1"
        url = f"{self.db_url}/battles/{self.room_id}.json"
        if role == "p1":
            d = {"state":"waiting", "p1":{"ready":False, "attack_queue":0, "grid_comp":"0"*200, "score":0, "stomps":0, "lost":False}, "p2":{"ready":False, "attack_queue":0, "grid_comp":"0"*200, "score":0, "stomps":0, "lost":False}, "countdown_start":0, "winner":""}
            await asyncio.to_thread(self._req, url, "PUT", d)
        else: await asyncio.to_thread(self._req, f"{self.db_url}/battles/{self.room_id}/p2.json", "PATCH", {"ready":False, "lost":False})
        self.connected = True

    async def poll(self):
        if not self.connected: return
        t = time.time()
        if t - self.poll_time > 0.4:
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
                self.winner = data.get('winner')
                if opp.get('lost') and not self.game_over: self.game_over = True
                remote_q = opp.get('attack_queue', 0)
                if remote_q > self.total_received:
                    self.pending_garbage += (remote_q - self.total_received)
                    self.total_received = remote_q
            self.poll_time = t

    async def set_ready(self, b):
        if self.connected: await asyncio.to_thread(self._req, f"{self.db_url}/battles/{self.room_id}/{self.role}.json", "PATCH", {"ready":b})

    async def sync(self, grid_str, score, stomps):
        if self.connected: await asyncio.to_thread(self._req, f"{self.db_url}/battles/{self.room_id}/{self.role}.json", "PATCH", {"grid_comp":grid_str, "score":score, "stomps":stomps})

    async def attack(self, n):
        if self.connected:
            url = f"{self.db_url}/battles/{self.room_id}/{self.role}.json"
            data = await asyncio.to_thread(self._req, url)
            cur = data.get('attack_queue', 0) if data else 0
            await asyncio.to_thread(self._req, url, "PATCH", {"attack_queue": cur + n})

    async def declare_lost(self):
        if self.connected: await asyncio.to_thread(self._req, f"{self.db_url}/battles/{self.room_id}/{self.role}.json", "PATCH", {"lost":True}) ; await asyncio.to_thread(self._req, f"{self.db_url}/battles/{self.room_id}.json", "PATCH", {"winner":self.opp_role, "state":"gameover"})

# --- PHYSICS ---
class Enemy:
    def __init__(self, x, type_id='K'):
        self.x, self.y = float(x), -1.0 ; self.type_id = type_id ; self.state = 'falling' ; self.vy = 0 ; self.dir = random.choice([-1, 1])
        self.lifetime = 15.0 ; self.anim_frame = self.anim_timer = 0
    def update(self, dt, grid, sm):
        self.anim_timer += dt
        if self.anim_timer > 0.12: self.anim_timer = 0 ; self.anim_frame = 1 - self.anim_frame
        self.vy += 35 * dt ; self.y += self.vy * dt ; ix = int(max(0, min(9, self.x + 0.5))) ; target_y = 19.0
        for row in range(int(max(0, self.y)), 20):
            if grid[row][ix] is not None: target_y = float(row - 1.0) ; break
        landed = False
        if self.y >= target_y: self.y = target_y ; self.vy = 0 ; landed = True
        if landed:
            if self.state == 'falling': self.state = 'walking' ; sm.play('land')
            if grid[int(self.y + 0.5)][ix] is not None: sm.play('damage') ; return True
        else: self.state = 'falling'
        if self.state == 'walking':
            self.lifetime -= dt ; next_x = self.x + self.dir * 1.5 * dt ; nx = int(max(0, min(9, next_x + 0.5)))
            turn = False
            if next_x < 0 or next_x > 9: turn = True
            elif 0 <= nx < 10 and grid[int(self.y + 0.5)][nx] is not None: turn = True
            if turn: self.dir *= -1
            else: self.x = next_x
            return self.lifetime <= 0
        return False

# --- CORE GAME ---
class TetrisV77:
    def __init__(self):
        pygame.init() ; self.screen = pygame.display.set_mode((WW, WH)) ; pygame.display.set_caption("MARIO BATTLE ELITE V77")
        self.clock = pygame.time.Clock() ; self.fb = FirebaseManagerV77("https://mario-tetris-game-default-rtdb.firebaseio.com/") ; self.sm = SoundManager()
        try:
            f = "assets/PressStart2P-Regular.ttf"
            if os.path.exists(f): self.font, self.huge, self.giant = pygame.font.Font(f, 13), pygame.font.Font(f, 30), pygame.font.Font(f, 50)
            else: self.font, self.huge, self.giant = pygame.font.SysFont("Arial", 18), pygame.font.SysFont("Arial", 40), pygame.font.SysFont("Arial", 60)
        except: self.font = self.huge = self.giant = None
        self.mode = "menu" ; self.load_assets() ; self.reset() ; self.shake = 0 ; self.messages = [] ; self.projectiles = [] ; self.achievements = []

    def load_assets(self):
        try:
            m = pygame.image.load("assets/marioallsprite.png").convert_alpha() ; b = pygame.image.load("assets/blocks.png").convert_alpha()
            self.imgs = {
                'brick': self.gs(b, 368, 112, 16, 16, BS/16), 'koopa': [self.gs(m, 206, 242, 20, 27, 2.0), self.gs(m, 247, 242, 20, 27, 2.0)],
                'red_koopa': [self.gs(m, 206, 282, 20, 27, 2.0), self.gs(m, 245, 283, 20, 27, 2.0)], 'shell': self.gs(m, 360, 212, 16, 16, 2.0),
                'mario': self.gs(m, 10, 6, 12, 16, 4.0), 'luigi': self.gs(m, 10, 6, 12, 16, 4.0), 'ground': self.gs(b, 0, 0, 16, 16, BS/16)
            }
            if 'luigi' in self.imgs: self.imgs['luigi'].fill((100, 255, 100), special_flags=pygame.BLEND_RGB_MULT)
        except: self.imgs = {}

    def gs(self, sheet, x, y, w, h, s):
        ss = pygame.Surface((w, h), pygame.SRCALPHA) ; ss.blit(sheet, (0, 0), (x, y, w, h)) ; return pygame.transform.scale(ss, (int(w*s), int(h*s)))

    def reset(self):
        self.grid = [[None for _ in range(GW)] for _ in range(GH)] ; self.bag = [] ; self.pos = [GW//2-1, 0] ; self.shape = self.spawn()
        self.fall_dt = self.score = self.stomps = self.spawn_t = self.clear_t = 0 ; self.enemies = [] ; self.is_ready = False ; self.clearing = []

    def spawn(self):
        if not self.bag: self.bag = ['I','O','T','S','Z','J','L'] ; random.shuffle(self.bag)
        s = self.bag.pop() ; d = {'I':[(0,0),(1,0),(2,0),(3,0)], 'O':[(0,0),(1,0),(0,1),(1,1)], 'T':[(1,0),(0,1),(1,1),(2,1)], 'S':[(1,0),(2,0),(0,1),(1,1)], 'Z':[(0,0),(1,0),(1,1),(2,1)], 'J':[(0,0),(0,1),(1,1),(2,1)], 'L':[(2,0),(0,1),(1,1),(2,1)]}
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
                    elif self.mode == "lobby" and e.key == pygame.K_RETURN: self.is_ready = not self.is_ready ; await self.fb.set_ready(self.is_ready)
                    elif self.mode == "play" and not self.clearing and not self.fb.game_over:
                        if e.key == pygame.K_LEFT: 
                            self.pos[0] -= 1 ; 
                            if self.collide(self.pos, self.shape): self.pos[0] += 1
                            else: self.sm.play('move')
                        if e.key == pygame.K_RIGHT: 
                            self.pos[0] += 1 ; 
                            if self.collide(self.pos, self.shape): self.pos[0] -= 1
                            else: self.sm.play('move')
                        if e.key == pygame.K_UP:
                            old = [list(b) for b in self.shape[0]] ; self.shape[0] = [(-by, bx) for bx, by in old]
                            if self.collide(self.pos, self.shape): self.shape[0] = old
                            else: self.sm.play('rotate')
                        if e.key == pygame.K_SPACE:
                            while not self.collide([self.pos[0], self.pos[1]+1], self.shape): self.pos[1] += 1
                            self.sm.play('lock') ; self.fall_dt = 10.0

            if self.mode != "menu":
                await self.fb.poll()
                if self.fb.p1_ready and self.fb.p2_ready and self.fb.role == "p1" and self.fb.room_state == "waiting":
                    await asyncio.to_thread(self.fb._req, f"{self.fb.db_url}/battles/{self.fb.room_id}.json", "PATCH", {"state":"countdown", "countdown_start":time.time()})
                if self.fb.room_state == "countdown" and self.mode == "lobby":
                    if time.time() - self.fb.countdown_start >= 3.0: self.mode = "play" ; self.reset() ; self.achievements.append(Achievement("GO! GO! GO!", (0,255,255)))
                
                if self.mode == "play":
                    self.messages = [m for m in self.messages if m.update(dt)] ; self.projectiles = [p for p in self.projectiles if p.update(dt)] ; self.achievements = [a for a in self.achievements if a.update(dt)]
                    if self.shake > 0: self.shake -= dt*20
                    if not self.fb.game_over:
                        if self.clearing:
                            self.clear_t -= dt
                            if self.clear_t <= 0:
                                new_g = [r for idx, r in enumerate(self.grid) if idx not in self.clearing]
                                while len(new_g) < GH: new_g.insert(0, [None]*GW)
                                self.grid = new_g ; self.clearing = [] ; self.pos = [GW//2-1, 0] ; self.shape = self.spawn()
                                if self.collide(self.pos, self.shape): await self.fb.declare_lost()
                        else:
                            temp_grid = [row[:] for row in self.grid] ; sid = self.shape[1] ; scol = ID_TO_COLOR[{'I':'1','O':'2','T':'3','S':'4','Z':'5','J':'6','L':'7'}[sid]]
                            for bx, by in self.shape[0]:
                                gx, gy = self.pos[0]+bx, self.pos[1]+by
                                if 0 <= gx < 10 and 0 <= gy < 20: temp_grid[gy][gx] = scol
                            sync_str = "".join([COLOR_TO_ID.get(c, "0") if c!=(140,140,140) else "G" for row in temp_grid for c in row])
                            asyncio.create_task(self.fb.sync(sync_str, self.score, self.stomps))
                            if self.fb.pending_garbage > 0:
                                self.sm.play('damage') ; self.shake = 12 ; self.messages.append(CombatMessage("⚠️ RECV STRIKE!", (255,50,50), 320, 200, 'huge'))
                                for _ in range(int(self.fb.pending_garbage)):
                                    self.grid.pop(0) ; self.grid.append([(140,140,140) if x!=random.randint(0,9) else None for x in range(GW)])
                                self.fb.pending_garbage = 0
                            self.spawn_t += dt
                            if self.spawn_t > 9.0: self.spawn_t = 0 ; self.enemies.append(Enemy(random.randint(0,9), random.choice(['K','R'])))
                            for en in self.enemies[:]:
                                if en.update(dt, self.grid, self.sm): self.enemies.remove(en)
                                elif en.y > GH + 1: self.enemies.remove(en)
                                elif en.state == 'walking':
                                    for bx, by in self.shape[0]:
                                        if int(en.x + 0.5) == self.pos[0]+bx and int(en.y + 0.5) == self.pos[1]+by:
                                            self.enemies.remove(en) ; self.stomps += 1 ; self.score += 500 ; self.sm.play('stomp')
                                            self.messages.append(CombatMessage("STOMP SENT! 🚀", (0,255,255), 320, 250, 'huge'))
                                            if self.stomps == 1: self.achievements.append(Achievement("FIRST BLOOD!", (255,50,50)))
                                            elif self.stomps % 5 == 0: self.achievements.append(Achievement(f"{self.stomps} STOMP SPREE!", (255,255,0)))
                                            if 'shell' in self.imgs: self.projectiles.append(ShellProjectile(60+en.x*BS, GRID_Y+en.y*BS, 620, 240, self.imgs['shell']))
                                            self.sm.play('shell') ; asyncio.create_task(self.fb.attack(1)) ; break
                            speed = 0.8
                            if pygame.key.get_pressed()[pygame.K_DOWN]: speed = 0.05
                            self.fall_dt += dt
                            if self.fall_dt > speed:
                                self.fall_dt = 0 ; self.pos[1] += 1
                                if self.collide(self.pos, self.shape):
                                    self.pos[1] -= 1 ; self.sm.play('lock') ; cid = self.shape[1] ; col = ID_TO_COLOR[{'I':'1','O':'2','T':'3','S':'4','Z':'5','J':'6','L':'7'}[cid]]
                                    for bx, by in self.shape[0]:
                                        if 0 <= self.pos[1]+by < GH: self.grid[self.pos[1]+by][self.pos[0]+bx] = col
                                    self.clearing = [ri for ri, r in enumerate(self.grid) if all(cell is not None for cell in r)]
                                    if self.clearing:
                                        self.sm.play('clear') ; self.score += (len(self.clearing)*1000) ; self.clear_t = 0.6 ; self.shake = 22
                                        self.messages.append(CombatMessage(f"STRIKE! +{len(self.clearing)} 🔥", (0,255,255), 200, 300, 'huge'))
                                        if len(self.clearing) == 4: self.achievements.append(Achievement("ULTRA MEGA STRIKE!", (0,255,255)))
                                        asyncio.create_task(self.fb.attack(len(self.clearing)))
                                    else:
                                        self.pos = [GW//2-1, 0] ; self.shape = self.spawn()
                                        if self.collide(self.pos, self.shape): await self.fb.declare_lost()
            self.draw() ; await asyncio.sleep(0.01)

    def draw(self):
        sx, sy = (random.randint(-int(self.shake), int(self.shake)), random.randint(-int(self.shake), int(self.shake))) if self.shake>0 else (0,0)
        self.screen.fill((92, 148, 252))
        if self.mode == "menu":
            self.draw_t("MARIO BATTLE ELITE V77", self.giant, (255,255,255), WW//2, 200)
            self.draw_t("COMPETITIVE MODE: STOMP TO WIN!", self.huge, (255,255,0), WW//2, 350)
        else:
            mx, my = 60 + sx, GRID_Y + sy ; pygame.draw.rect(self.screen, (0,0,0,225), (mx-4, my-4, GW*BS+8, GH*BS+8)) ; pygame.draw.rect(self.screen, (255,255,255), (mx-4, my-4, GW*BS+8, GH*BS+8), 2)
            if 'ground' in self.imgs:
                for x in range(GW): self.screen.blit(self.imgs['ground'], (mx+x*BS, my+GH*BS))
            # Ghost
            if self.mode == "play" and not self.clearing and not self.fb.game_over:
                gx, gy = self.pos[0], self.pos[1]
                while not self.collide([gx, gy+1], self.shape): gy += 1
                scol = ID_TO_COLOR[{'I':'1','O':'2','T':'3','S':'4','Z':'5','J':'6','L':'7'}[self.shape[1]]]
                for bx, by in self.shape[0]: 
                    gs = pygame.Surface((BS, BS), pygame.SRCALPHA) ; gs.fill((*scol, 80)) ; self.screen.blit(gs, (mx+(gx+bx)*BS, my+(gy+by)*BS))
            # Grid
            for y in range(GH):
                if y in self.clearing and int(time.time()*20)%2==0: pygame.draw.rect(self.screen, (255,255,255), (mx, my+y*BS, GW*BS, BS))
                else:
                    for x in range(GW):
                        c = self.grid[y][x] ; if c: self.draw_3d_b(mx+x*BS, my+y*BS, c, BS)
            if not self.clearing and self.mode == "play" and not self.fb.game_over:
                scol = ID_TO_COLOR[{'I':'1','O':'2','T':'3','S':'4','Z':'5','J':'6','L':'7'}[self.shape[1]]]
                for bx, by in self.shape[0]: self.draw_3d_b(mx+(self.pos[0]+bx)*BS, my+(self.pos[1]+by)*BS, scol, BS)
            for en in self.enemies:
                ikey = 'koopa' if en.type_id=='K' else 'red_koopa' ; eimg = self.imgs[ikey][en.anim_frame]
                if en.dir == 1: eimg = pygame.transform.flip(eimg, True, False)
                y_bob = abs(math.sin(time.time()*10))*6 ; self.screen.blit(eimg, (mx+en.x*BS, my+en.y*BS-eimg.get_height()+BS-y_bob))
            for pr in self.projectiles:
                rot = pygame.transform.rotate(pr.img, pr.angle) ; self.screen.blit(rot, (pr.x-16, pr.y-16))
            for m in self.messages:
                uf = self.huge if m.size == 'huge' else self.font ; self.draw_t(m.text, uf, m.color, m.x, m.y)
            for a in self.achievements:
                surf = self.giant.render(a.text, True, a.color) ; surf.set_alpha(a.alpha) ; self.screen.blit(surf, surf.get_rect(center=(WW//2, WH//3 + a.y_off)))
            pimg = self.imgs['mario' if self.fb.role=='p1' else 'luigi'] if 'mario' in self.imgs else None
            if pimg: self.screen.blit(pimg, (mx-52, 5))
            self.draw_t(f"SCORE: {self.score}", self.font, (255,255,255), mx, 25, False)
            self.draw_t("OBJECTIVE: STOMP TO ATTACK!", self.font, (255,255,0), mx, 45, False)
            ox, oy = 620, GRID_Y+80 ; sbs = 28 ; pygame.draw.rect(self.screen, (0,0,0,150), (ox-4, oy-4, GW*sbs+8, GH*sbs+8))
            for i, cid in enumerate(self.fb.opp_grid_raw):
                if cid != '0': oc = ID_TO_COLOR.get(cid, (200,200,200)) ; self.draw_3d_b(ox+(i%10)*sbs, oy+(i//10)*sbs, oc, sbs)
            self.draw_t(f"OPP LIVE VIEW", self.huge, (255,255,255), ox, oy-35, False)
            if self.mode == "lobby":
                status = "HIT [ENTER] TO READY" if not self.is_ready else "READY!" ; self.draw_t(status, self.font, (255,255,255), WW//2, WH-60)
            if self.fb.room_state == "countdown":
                sec = 3 - int(time.time() - self.fb.countdown_start)
                if sec >= 0: self.draw_t(str(max(1, sec)), self.giant, (255,255,255), WW//2, WH//2)
            if self.fb.game_over:
                self.draw_t("MATCH OVER!", self.giant, (255,255,255), WW//2, WH//2 - 50)
                if self.fb.winner == self.fb.role: self.draw_t("YOU WIN!", self.giant, (0,255,0), WW//2, WH//2 + 20)
                else: self.draw_t("YOU LOST!", self.giant, (255,0,0), WW//2, WH//2 + 20)
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
    try: asyncio.run(TetrisV77().run())
    except:
        with open(f"crash_v77_{PID}.txt", "w") as f: f.write(traceback.format_exc())
        input("CRASH")
