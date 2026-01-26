
import pygame
import random
import json
import asyncio
import sys
import os
import time
import urllib.request
import math
import traceback

# --- V92 - "MARIO BATTLE BO3 PRO (CLICK & PLAY)" ---
# Fixed: 
# - MOUSE SUPPORT: Clickable buttons for role selection (Mario/Luigi).
# - NUMPAD SUPPORT: Works with top-row and num-pad keys.
# - UI RECOVERY: Status text shows real-time network states.
# - ASYNC JOIN: Join logic runs in background to prevent browser freezing.
# - Best-of-3 Series Mode.

PID = os.getpid()

WW = 1000
WH = 720
GW = 10
GH = 20
BS = 32
GRID_Y = 60
SYNC_INTERVAL = 0.40 
POLL_INTERVAL = 0.60

ID_TO_COLOR = {
    '1': (0, 240, 240),
    '2': (240, 240, 0),
    '3': (160, 0, 240),
    '4': (0, 240, 0),
    '5': (240, 0, 0),
    '6': (0, 0, 240),
    '7': (240, 160, 0),
    'G': (140, 140, 140)
}
COLOR_TO_ID = {v: k for k, v in ID_TO_COLOR.items()}

def get_asset_path(filename):
    if os.path.exists(os.path.join('assets', filename)):
        return os.path.join('assets', filename)
    if os.path.exists(os.path.join('sounds', filename)):
        return os.path.join('sounds', filename)
    return filename

class AchievementBanner:
    def __init__(self, text, color, font, duration=2.5):
        self.text = text
        self.color = color
        self.font = font
        self.life = duration
        self.alpha = 255
        self.y_offset = 0
    def update(self, dt):
        self.life -= dt
        self.y_offset -= 10 * dt
        if self.life < 0.6:
            self.alpha = int((self.life / 0.6) * 255)
        return self.life > 0
    def draw(self, screen):
        if not self.font:
            return
        surf = self.font.render(self.text, True, self.color)
        surf.set_alpha(self.alpha)
        rect = surf.get_rect(center=(WW // 2, WH // 2 + self.y_offset))
        screen.blit(surf, rect)

class CombatText:
    def __init__(self, text, color, x, y, font):
        self.text = text
        self.color = color
        self.x = x
        self.y = y
        self.font = font
        self.life = 1.5
    def update(self, dt):
        self.life -= dt
        self.y -= 35 * dt
        return self.life > 0
    def draw(self, screen):
        if self.font:
            s = self.font.render(self.text, True, self.color)
            screen.blit(s, (self.x, self.y))

class BlastProjectile:
    def __init__(self, x, y, tx, ty, img):
        self.x = float(x)
        self.y = float(y)
        self.tx = float(tx)
        self.ty = float(ty)
        self.img = img
        self.life = 1.0
        self.angle = 0
    def update(self, dt):
        self.life -= dt * 1.5
        self.x += (self.tx - self.x) * 0.15
        self.y += (self.ty - self.y) * 0.15
        self.angle += 40
        return self.life > 0
    def draw(self, screen):
        if self.img:
            r = pygame.transform.rotate(self.img, self.angle)
            screen.blit(r, (self.x - 16, self.y - 16))

class AudioManager:
    def __init__(self):
        self.sounds = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.pre_init(44100, -16, 2, 512)
                pygame.mixer.init()
            self._load()
        except:
            pass
    def _load(self):
        sfx = {
            'move': 'move.wav',
            'rotate': 'rotate.wav',
            'lock': 'lock.wav',
            'clear': 'clear.wav',
            'stomp': 'stomp.wav',
            'shell': 'impactGeneric_power_001.ogg',
            'hit': 'impactBell_heavy_004.ogg',
            'win': 'reward_01.wav'
        }
        for k, f in sfx.items():
            p = get_asset_path(f)
            if os.path.exists(p):
                try:
                    s = pygame.mixer.Sound(p)
                    if k == 'move':
                        s.set_volume(0.2)
                    else:
                        s.set_volume(0.4)
                    self.sounds[k] = s
                except:
                    pass
    def play(self, k):
        if k in self.sounds:
            try:
                self.sounds[k].play()
            except:
                pass
    def start_bgm(self):
        try:
            p = get_asset_path('2. Bring The Noise.mp3')
            if os.path.exists(p):
                pygame.mixer.music.load(p)
                pygame.mixer.music.set_volume(0.2)
                pygame.mixer.music.play(-1)
        except:
            pass

class BattleNetwork:
    def __init__(self, db_url):
        self.db_url = db_url.rstrip('/')
        self.room_id = "battle_v92_bo3"
        self.role = None
        self.opp_role = None
        self.state = "waiting"
        self.countdown_time = 0
        self.p1_ready = False
        self.p2_ready = False
        self.p1_wins = 0
        self.p2_wins = 0
        self.opp_grid = "0" * 200
        self.opp_score = 0
        self.opp_stomps = 0
        self.incoming_attack_q = 0
        self.synced_received_total = 0
        self.last_poll_time = 0
        self.game_over = False
        self.winner = None
        self.last_sync_time = 0
        self.sync_active = False
        self.status = "Idle"

    def _api(self, ep, method="GET", body=None):
        try:
            url = f"{self.db_url}/{ep}.json"
            req = urllib.request.Request(url, method=method)
            if body is not None:
                req.add_header('Content-Type', 'application/json')
                data = json.dumps(body).encode('utf-8')
                with urllib.request.urlopen(req, data=data, timeout=5) as r:
                    return json.loads(r.read().decode('utf-8'))
            else:
                with urllib.request.urlopen(req, timeout=5) as r:
                    return json.loads(r.read().decode('utf-8'))
        except:
            return None

    async def join(self, role):
        self.status = f"Connecting as {role}..."
        self.role = role
        self.opp_role = "p2" if role == "p1" else "p1"
        if role == "p1":
            d = {
                "state": "waiting",
                "p1": {"ready": False, "attack_count": 0, "grid": "0"*200, "score": 0, "stomps": 0, "lost": False, "match_wins": 0},
                "p2": {"ready": False, "attack_count": 0, "grid": "0"*200, "score": 0, "stomps": 0, "lost": False, "match_wins": 0},
                "countdown": 0
            }
            await asyncio.to_thread(self._api, f"battles/{self.room_id}", "PUT", d)
        else:
            await asyncio.to_thread(self._api, f"battles/{self.room_id}/p2", "PATCH", {"ready": False, "lost": False})
        self.status = "Connected"

    async def poll(self):
        n = time.time()
        if n - self.last_poll_time > POLL_INTERVAL:
            data = await asyncio.to_thread(self._api, f"battles/{self.room_id}")
            if data:
                self.state = data.get('state', 'waiting')
                self.countdown_time = data.get('countdown', 0)
                p1 = data.get('p1', {})
                p2 = data.get('p2', {})
                self.p1_ready = p1.get('ready', False)
                self.p2_ready = p2.get('ready', False)
                self.p1_wins = p1.get('match_wins', 0)
                self.p2_wins = p2.get('match_wins', 0)
                
                opp = p2 if self.role == "p1" else p1
                self.opp_grid = opp.get('grid', "0"*200)
                self.opp_score = opp.get('score', 0)
                self.opp_stomps = opp.get('stomps', 0)
                
                if (self.p1_wins >= 2 or self.p2_wins >= 2) and self.state == "match_over":
                    self.game_over = True
                    self.winner = "p1" if self.p1_wins >= 2 else "p2"
                elif opp.get('lost') and self.state == "playing":
                    self.state = "round_over"
                    self.winner = self.role
                    
                rem_q = opp.get('attack_count', 0)
                if rem_q > self.synced_received_total:
                    self.incoming_attack_q += (rem_q - self.synced_received_total)
                    self.synced_received_total = rem_q
            self.last_poll_time = n

    async def sync_state(self, grid, score, stomps, attacks_to_add):
        now = time.time()
        if self.sync_active or (now - self.last_sync_time < SYNC_INTERVAL):
            return
        self.sync_active = True
        try:
            path = f"battles/{self.room_id}/{self.role}"
            data = await asyncio.to_thread(self._api, path)
            cur_q = data.get('attack_count', 0) if data else 0
            payload = {"grid": grid, "score": score, "stomps": stomps, "attack_count": cur_q + attacks_to_add}
            await asyncio.to_thread(self._api, path, "PATCH", payload)
            self.last_sync_time = now
        finally:
            self.sync_active = False

    async def report_round_loss(self):
        await asyncio.to_thread(self._api, f"battles/{self.room_id}/{self.role}", "PATCH", {"lost": True})
        path_opp = f"battles/{self.room_id}/{self.opp_role}"
        opp_data = await asyncio.to_thread(self._api, path_opp)
        new_wins = (opp_data.get('match_wins', 0) + 1) if opp_data else 1
        await asyncio.to_thread(self._api, path_opp, "PATCH", {"match_wins": new_wins})
        if new_wins >= 2:
            await asyncio.to_thread(self._api, f"battles/{self.room_id}", "PATCH", {"state": "match_over"})
        else:
            await asyncio.to_thread(self._api, f"battles/{self.room_id}", "PATCH", {"state": "waiting"})
            await asyncio.to_thread(self._api, f"battles/{self.room_id}/{self.role}", "PATCH", {"lost": False, "ready": False})
            await asyncio.to_thread(self._api, f"battles/{self.room_id}/{self.opp_role}", "PATCH", {"ready": False})

class ProfessionalEnemy:
    def __init__(self, x):
        self.x = float(x)
        self.y = -1.0
        self.state = 'falling'
        self.vy, self.vx_mod = 0, 1.8
        self.dir = random.choice([-1, 1])
        self.age, self.frame = 0, 0
    def update(self, dt, grid, audio):
        self.age += dt
        self.frame = int(self.age * 8) % 2
        self.vy += 32 * dt
        self.y += self.vy * dt
        ix = int(max(0, min(9, self.x + 0.5)))
        solid_y = 19.0
        for r in range(int(max(0, self.y)), 20):
            if grid[r][ix] is not None:
                solid_y = float(r - 1.0)
                break
        if self.y >= solid_y:
            self.y = solid_y
            self.vy = 0
            self.state = 'walking'
            if 0 <= int(self.y + 0.5) < 20 and grid[int(self.y + 0.5)][ix] is not None:
                audio.play('hit')
                return True
        else:
            self.state = 'falling'
        if self.state == 'walking':
            next_x = self.x + self.dir * self.vx_mod * dt
            nx_idx = int(max(0, min(9, next_x + 0.5)))
            if next_x < 0 or next_x > 9 or (0 <= int(self.y+0.5) < 20 and grid[int(self.y+0.5)][nx_idx] is not None):
                self.dir *= -1
            else:
                self.x = next_x
            return self.age > 16.0
        return False

class MarioBattleV92:
    def __init__(self):
        pygame.init()
        self.scr = pygame.display.set_mode((WW, WH))
        pygame.display.set_caption("MARIO BATTLE BO3 v92")
        self.clock = pygame.time.Clock()
        self.net = BattleNetwork("https://mario-tetris-game-default-rtdb.firebaseio.com/")
        self.audio = AudioManager()
        try:
            p = get_asset_path("PressStart2P-Regular.ttf")
            self.f_s = pygame.font.Font(p, 12) if os.path.exists(p) else pygame.font.SysFont("Arial", 14)
            self.f_m = pygame.font.Font(p, 26) if os.path.exists(p) else pygame.font.SysFont("Arial", 28)
            self.f_h = pygame.font.Font(p, 44) if os.path.exists(p) else pygame.font.SysFont("Arial", 48)
        except: self.f_s = self.f_m = self.f_h = None
        self.phase = "menu"
        self.load_assets()
        self.reset_round()
        self.banners, self.comms, self.bolts = [], [], []
        self.shake, self.pending_attacks = 0, 0
        self.btn1 = pygame.Rect(WW//2-220, 420, 200, 60)
        self.btn2 = pygame.Rect(WW//2+20, 420, 200, 60)

    def load_assets(self):
        try:
            m = pygame.image.load(get_asset_path("marioallsprite.png")).convert_alpha()
            b = pygame.image.load(get_asset_path("blocks.png")).convert_alpha()
            self.img = {
                'brick': self.cut(b, 368, 112, 16, 16, 2.0),
                'koopa': [self.cut(m, 206, 242, 20, 27, 2.0), self.cut(m, 247, 242, 20, 27, 2.0)],
                'shell': self.cut(m, 360, 212, 16, 16, 2.0),
                'ground': self.cut(b, 0, 0, 16, 16, 2.0)
            }
        except: self.img = {}

    def cut(self, sheet, x, y, w, h, s):
        sur = pygame.Surface((w,h), pygame.SRCALPHA)
        sur.blit(sheet,(0,0),(x,y,w,h))
        return pygame.transform.scale(sur, (int(w*s),int(h*s)))

    def reset_round(self):
        self.grid = [[None for _ in range(GW)] for _ in range(GH)]
        self.bag, self.enemies = [], []
        self.pos = [GW//2-1, 0]
        self.pce = self.pull()
        self.fall, self.spa_t, self.clr_t, self.is_ready = 0, 0, 0, False
        self.clring, self.pending_attacks, self.stomps, self.score = [], 0, 0, 0

    def pull(self):
        if not self.bag:
            self.bag = ['I','O','T','S','Z','J','L']
            random.shuffle(self.bag)
        t = self.bag.pop()
        d = {'I':[(0,0),(1,0),(2,0),(3,0)], 'O':[(0,0),(1,0),(0,1),(1,1)], 'T':[(1,0),(0,1),(1,1),(2,1)], 'S':[(1,0),(2,0),(0,1),(1,1)], 'Z':[(0,0),(1,0),(1,1),(2,1)], 'J':[(0,0),(0,1),(1,1),(2,1)], 'L':[(2,0),(0,1),(1,1),(2,1)]}
        return {'shape':[list(p) for p in d[t]], 'id':t}

    def collide(self, p, s):
        for bx, by in s:
            gx, gy = p[0]+bx, p[1]+by
            if gx < 0 or gx >= GW or gy >= GH or (gy >= 0 and self.grid[gy][gx]): return True
        return False

    async def run(self):
        while True:
            dt = self.clock.tick(60) / 1000.0
            mv = pygame.mouse.get_pos()
            for e in pygame.event.get():
                if e.type == pygame.QUIT: return
                if e.type == pygame.MOUSEBUTTONDOWN:
                    if self.phase == "menu" and self.net.status == "Idle":
                        if self.btn1.collidepoint(mv): self.join_task("p1")
                        elif self.btn2.collidepoint(mv): self.join_task("p2")
                if e.type == pygame.KEYDOWN:
                    if self.phase == "menu" and self.net.status == "Idle":
                        if e.key in [pygame.K_1, pygame.K_KP1]: self.join_task("p1")
                        elif e.key in [pygame.K_2, pygame.K_KP2]: self.join_task("p2")
                    elif (self.phase == "lobby" or self.net.state == "waiting") and e.key == pygame.K_RETURN:
                        self.is_ready = not self.is_ready
                        asyncio.create_task(asyncio.to_thread(self.net._api, f"battles/{self.net.room_id}/{self.net.role}", "PATCH", {"ready":self.is_ready}))
                    elif self.phase == "play" and not self.clring and self.net.state == "playing":
                        if e.key == pygame.K_LEFT:
                            self.pos[0] -= 1
                            if self.collide(self.pos, self.pce['shape']): self.pos[0] += 1
                            else: self.audio.play('move')
                        elif e.key == pygame.K_RIGHT:
                            self.pos[0] += 1
                            if self.collide(self.pos, self.pce['shape']): self.pos[0] -= 1
                            else: self.audio.play('move')
                        elif e.key == pygame.K_UP:
                            old = [list(p) for p in self.pce['shape']]
                            self.pce['shape'] = [(-y, x) for x, y in old]
                            if self.collide(self.pos, self.pce['shape']): self.pce['shape'] = old
                            else: self.audio.play('rotate')
                        elif e.key == pygame.K_SPACE:
                            while not self.collide([self.pos[0], self.pos[1]+1], self.pce['shape']): self.pos[1] += 1
                            self.audio.play('lock')
                            self.fall = 10.0

            if self.phase != "menu":
                await self.net.poll()
                if self.net.p1_ready and self.net.p2_ready and self.net.role == "p1" and self.net.state == "waiting":
                    asyncio.create_task(asyncio.to_thread(self.net._api, f"battles/{self.net.room_id}", "PATCH", {"state":"countdown","countdown":time.time()}))
                if (self.phase == "lobby" or self.net.state == "countdown") and self.net.state == "playing":
                    self.phase, self.score, self.stomps = "play", 0, 0
                    self.reset_round()
                    self.banners.append(AchievementBanner("FIGHT!",(0,255,255),self.f_h))
                elif self.net.state == "countdown":
                    if time.time() - self.net.countdown_time >= 3.0:
                        if self.net.role == "p1": asyncio.create_task(asyncio.to_thread(self.net._api, f"battles/{self.net.room_id}", "PATCH", {"state":"playing"}))
                        self.phase = "play"
                        self.reset_round()
                        self.banners.append(AchievementBanner("FIGHT!",(0,255,255),self.f_h))
                if self.phase == "play":
                    self.banners = [b for b in self.banners if b.update(dt)]
                    self.comms = [c for c in self.comms if c.update(dt)]
                    self.bolts = [b for b in self.bolts if b.update(dt)]
                    if self.shake > 0: self.shake -= dt * 25
                    if self.net.state == "playing":
                        if self.clring:
                            self.clr_t -= dt
                            if self.clr_t <= 0:
                                fil = [r for idx, r in enumerate(self.grid) if idx not in self.clring]
                                while len(fil) < GH: fil.insert(0, [None]*GW)
                                self.grid, self.clring, self.pos, self.pce = fil, [], [GW//2-1, 0], self.pull()
                                if self.collide(self.pos, self.pce['shape']): await self.net.report_round_loss()
                        else:
                            shadow = [row[:] for row in self.grid]
                            c_id = {'I':'1','O':'2','T':'3','S':'4','Z':'5','J':'6','L':'7'}[self.pce['id']]
                            for bx, by in self.pce['shape']:
                                gx, gy = self.pos[0]+bx, self.pos[1]+by
                                if 0 <= gx < GW and 0 <= gy < GH: shadow[gy][gx] = ID_TO_COLOR[c_id]
                            s_str = "".join([COLOR_TO_ID.get(c, "0") if c!=(140,140,140) else "G" for row in shadow for c in row])
                            if not self.net.sync_active:
                                atk_v = self.pending_attacks
                                self.pending_attacks = 0
                                asyncio.create_task(self.net.sync_state(s_str, self.score, self.stomps, atk_v))
                            if self.net.incoming_attack_q > 0:
                                self.audio.play('hit')
                                self.shake = 15
                                self.comms.append(CombatText("⚠️ ATTACK!",(255,50,50),320,220,self.f_m))
                                for _ in range(int(self.net.incoming_attack_q)):
                                    self.grid.pop(0)
                                    self.grid.append([(140,140,140) if x!=(random.randint(0,9)) else None for x in range(GW)])
                                self.net.incoming_attack_q = 0
                            self.spa_t += dt
                            if self.spa_t > 8.0:
                                self.spa_t = 0
                                self.enemies.append(ProfessionalEnemy(random.randint(0,9)))
                            for en in self.enemies[:]:
                                if en.update(dt, self.grid, self.audio): self.enemies.remove(en)
                                elif en.y > GH + 1: self.enemies.remove(en)
                                elif en.state == 'walking':
                                    for bx, by in self.pce['shape']:
                                        if int(en.x+0.5) == self.pos[0]+bx and int(en.y+0.5) == self.pos[1]+by:
                                            self.enemies.remove(en)
                                            self.stomps, self.score, self.pending_attacks = self.stomps+1, self.score+500, self.pending_attacks+1
                                            self.audio.play('stomp')
                                            self.comms.append(CombatText("STOMP! 🚀",(0,255,255),320,260,self.f_m))
                                            if 'shell' in self.img: self.bolts.append(BlastProjectile(60+en.x*BS, GRID_Y+en.y*BS, 620, 240, self.img['shell']))
                                            self.audio.play('shell')
                                            break
                            spd = 0.05 if pygame.key.get_pressed()[pygame.K_DOWN] else 0.85
                            self.fall += dt
                            if self.fall > spd:
                                self.fall = 0
                                self.pos[1] += 1
                                if self.collide(self.pos, self.pce['shape']):
                                    self.pos[1] -= 1
                                    self.audio.play('lock')
                                    cid_c = {'I':'1','O':'2','T':'3','S':'4','Z':'5','J':'6','L':'7'}[self.pce['id']]
                                    for bx, by in self.pce['shape']:
                                        if 0 <= self.pos[1]+by < GH: self.grid[self.pos[1]+by][self.pos[0]+bx] = ID_TO_COLOR[cid_c]
                                    self.clring = [ri for ri,r in enumerate(self.grid) if all(cell is not None for cell in r)]
                                    if self.clring:
                                        self.audio.play('clear')
                                        self.score, self.clr_t, self.shake, self.pending_attacks = self.score+(len(self.clring)*1000), 0.65, 24, self.pending_attacks+len(self.clring)
                                        self.banners.append(AchievementBanner(f"COMBO: {len(self.clring)}!",(0,255,255),self.f_m))
                                    else:
                                        self.pos, self.pce = [GW//2-1, 0], self.pull()
                                        if self.collide(self.pos, self.pce['shape']): await self.net.report_round_loss()
            self.draw()
            await asyncio.sleep(0.01)

    def join_task(self, role):
        asyncio.create_task(self.net.join(role))
        self.phase = "lobby"
        self.audio.start_bgm()

    def draw(self):
        ox = random.randint(-int(self.shake), int(self.shake)) if self.shake > 0 else 0
        oy = random.randint(-int(self.shake), int(self.shake)) if self.shake > 0 else 0
        self.scr.fill((92, 148, 252))
        if self.phase != "menu":
            self.draw_t(f"SERIES: {self.net.p1_wins} - {self.net.p2_wins}", self.f_m, (255,255,255), WW//2, 30)
            self.draw_t("BEST OF 3", self.f_s, (255,255,0), WW//2, 55)
            if self.net.status != "Connected": self.draw_t(f"STATUS: {self.net.status}", self.f_s, (255,255,255), WW//2, WH-20)
        
        if self.phase == "menu":
            self.draw_t("MARIO BATTLE BEST OF 3", self.f_h, (255,255,255), WW//2, 180)
            self.draw_t("CLICK A ROLE TO START", self.f_m, (255,255,0), WW//2, 330)
            for r,txt,col in [(self.btn1,"MARIO", (255,50,50)), (self.btn2,"LUIGI", (50,255,50))]:
                pygame.draw.rect(self.scr, (255,255,255), r, 0, 8)
                pygame.draw.rect(self.scr, (0,0,0), r, 3, 8)
                self.draw_t(txt, self.f_m, col, r.centerx, r.centery)
            if self.net.status != "Idle": self.draw_t(self.net.status, self.f_s, (255,255,255), WW//2, 520)
        else:
            ax, ay = 60 + ox, GRID_Y + oy
            pygame.draw.rect(self.scr, (10,10,20), (ax-4, ay-4, GW*BS+8, GH*BS+8))
            pygame.draw.rect(self.scr, (255,255,255), (ax-4, ay-4, GW*BS+8, GH*BS+8), 2)
            if 'ground' in self.img:
                for x in range(GW): self.scr.blit(self.img['ground'], (ax + x*BS, ay + GH*BS))
            if self.phase == "play" and not self.clring and self.net.state == "playing":
                gx, gy = self.pos[0], self.pos[1]
                while not self.collide([gx, gy+1], self.pce['shape']): gy += 1
                c_col = ID_TO_COLOR[{'I':'1','O':'2','T':'3','S':'4','Z':'5','J':'6','L':'7'}[self.pce['id']]]
                for bx, by in self.pce['shape']:
                    gst = pygame.Surface((BS, BS), pygame.SRCALPHA)
                    gst.fill((*c_col, 50))
                    self.scr.blit(gst, (ax+(gx+bx)*BS, ay+(gy+by)*BS))
            for y in range(GH):
                if y in self.clring and int(time.time()*15)%2==0: pygame.draw.rect(self.scr, (255,255,255), (ax, ay+y*BS, GW*BS, BS))
                else:
                    for x in range(GW):
                        if self.grid[y][x]: self.draw_3db(ax+x*BS, ay+y*BS, self.grid[y][x], BS)
            if not self.clring and self.phase == "play" and self.net.state == "playing":
                cid = {'I':'1','O':'2','T':'3','S':'4','Z':'5','J':'6','L':'7'}[self.pce['id']]
                for bx, by in self.pce['shape']: self.draw_3db(ax+(self.pos[0]+bx)*BS, ay+(self.pos[1]+by)*BS, ID_TO_COLOR[cid], BS)
            for en in self.enemies:
                eimg = self.img['koopa'][en.frame]
                if en.dir == 1: eimg = pygame.transform.flip(eimg, True, False)
                self.scr.blit(eimg, (ax + en.x*BS, ay + en.y*BS - eimg.get_height() + BS - (abs(math.sin(time.time()*10))*4)))
            for fx in self.bolts + self.comms + self.banners: fx.draw(self.scr)
            self.draw_t(f"SCORE: {self.score}", self.f_s, (255,255,255), ax, 25, False)
            ox_v, oy_v, sbs = 620, GRID_Y+80, 28
            pygame.draw.rect(self.scr, (5,5,15), (ox_v-4, oy_v-4, GW*sbs+8, GH*sbs+8))
            for i, cid in enumerate(self.net.opp_grid):
                if cid != '0': self.draw_3db(ox_v+(i%10)*sbs, oy_v+(i//10)*sbs, ID_TO_COLOR.get(cid, (100,100,100)), sbs)
            self.draw_t("OPPONENT", self.f_m, (255,255,255), ox_v, oy_v-35, False)
            if self.net.state == "match_over":
                self.draw_t("SERIES OVER!", self.f_h, (255,255,255), WW//2, WH//2 - 40)
                self.draw_t(f"WINNER: {'MARIO (P1)' if self.net.p1_wins >= 2 else 'LUIGI (P2)'}", self.f_m, (0, 255, 0), WW//2, WH//2 + 30)
            elif self.net.state == "waiting": self.draw_t("READY: [ENTER]" if not self.is_ready else "WAITING...", self.f_m, (255,255,255), WW//2, WH - 80)
            elif self.net.state == "countdown":
                sec = 3 - int(time.time() - self.net.countdown_time)
                if sec >= 0: self.draw_t(str(max(1, sec)), self.f_h, (255,255,255), WW//2, WH//2)
            elif self.net.state == "round_over": self.draw_t("ROUND OVER!", self.f_h, (255,255,255), WW//2, WH//2)
        pygame.display.flip()

    def draw_3db(self, x, y, c, s):
        pygame.draw.rect(self.scr, c, (x, y, s, s))
        pygame.draw.polygon(self.scr, [min(255, ch+75) for ch in c], [(x, y), (x + s, y), (x + s - 3, y + 3), (x + 3, y + 3)])
        pygame.draw.polygon(self.scr, [max(0, ch-75) for ch in c], [(x + s, y), (x + s, y + s), (x + s - 3, y + s - 3), (x + s - 3, y + 3)])

    def draw_t(self, t, f, c, x, y, ct=True):
        if not f: return
        r = f.render(t, True, c)
        self.scr.blit(r, r.get_rect(center=(x,y)) if ct else r.get_rect(topleft=(x,y)))

if __name__ == "__main__":
    asyncio.run(MarioBattleV92().run())
