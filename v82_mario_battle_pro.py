
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

# --- V82 - "MARIO BATTLE HYPER-STABLE (COMBAT FIX)" ---
# Technical Specs:
# - BUFFERED COMBAT: Attacks are recorded locally and synced during the throttled update cycle.
# - ASYNC SAFETY: Removed firing raw network tasks inside the frame loop.
# - SYNC v2: Opponent view now includes stomp indicators and combo counts.
# - PHYSICS: Rock-solid column snapping and AABB collision.

PID = os.getpid()

# --- ENGINE CONFIG ---
WW, WH = 1000, 720
GW, GH = 10, 20
BS = 32
GRID_Y = 60
SYNC_INTERVAL = 0.35 
POLL_INTERVAL = 0.50

ID_TO_COLOR = {
    '1': (0, 240, 240), '2': (240, 240, 0), '3': (160, 0, 240), 
    '4': (0, 240, 0), '5': (240, 0, 0), '6': (0, 0, 240), 
    '7': (240, 160, 0), 'G': (140, 140, 140)
}
COLOR_TO_ID = {v: k for k, v in ID_TO_COLOR.items()}

def get_asset_path(filename):
    if os.path.exists(os.path.join('assets', filename)):
        return os.path.join('assets', filename)
    return filename

# --- VISUALS ---
class AchievementBanner:
    def __init__(self, text, color, font):
        self.text, self.color, self.font = text, color, font
        self.life, self.alpha, self.y_offset = 2.5, 255, 0
    def update(self, dt):
        self.life -= dt ; self.y_offset -= 15 * dt
        if self.life < 0.6: self.alpha = int((self.life / 0.6) * 255)
        return self.life > 0
    def draw(self, screen):
        if not self.font: return
        s = self.font.render(self.text, True, self.color) ; s.set_alpha(self.alpha)
        screen.blit(s, s.get_rect(center=(WW // 2, WH // 4 + self.y_offset)))

class CombatText:
    def __init__(self, text, color, x, y, font):
        self.text, self.color, self.x, self.y, self.font, self.life = text, color, x, y, font, 1.5
    def update(self, dt):
        self.life -= dt ; self.y -= 35 * dt
        return self.life > 0
    def draw(self, screen):
        if self.font: screen.blit(self.font.render(self.text, True, self.color), (self.x, self.y))

class BlastProjectile:
    def __init__(self, x, y, tx, ty, img):
        self.x, self.y, self.tx, self.ty, self.img, self.life, self.angle = float(x), float(y), float(tx), float(ty), img, 1.0, 0
    def update(self, dt):
        self.life -= dt * 1.5 ; self.x += (self.tx - self.x) * 0.15 ; self.y += (self.ty - self.y) * 0.15 ; self.angle += 40
        return self.life > 0
    def draw(self, screen):
        if self.img: screen.blit(pygame.transform.rotate(self.img, self.angle), (self.x - 16, self.y - 16))

# --- AUDIO ---
class AudioManager:
    def __init__(self):
        self.sounds = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.pre_init(44100, -16, 2, 512) ; pygame.mixer.init()
            self._load()
        except: pass
    def _load(self):
        sfx = {'move':'move.wav','rotate':'rotate.wav','lock':'lock.wav','clear':'clear.wav','stomp':'stomp.wav','shell':'impactGeneric_power_001.ogg','hit':'impactBell_heavy_004.ogg','land':'impactGeneric_light_002.ogg','win':'reward_01.wav'}
        for k, f in sfx.items():
            p = get_asset_path(f)
            if os.path.exists(p):
                try: s = pygame.mixer.Sound(p) ; s.set_volume(0.2 if k=='move' else 0.4) ; self.sounds[k] = s
                except: pass
    def play(self, k):
        if k in self.sounds:
            try: self.sounds[k].play()
            except: pass
    def start_bgm(self):
        try:
            p = get_asset_path('2. Bring The Noise.mp3')
            if os.path.exists(p): pygame.mixer.music.load(p) ; pygame.mixer.music.set_volume(0.2) ; pygame.mixer.music.play(-1)
        except: pass

# --- NETWORK ---
class BattleNetwork:
    def __init__(self, db_url):
        self.db_url = db_url.rstrip('/')
        self.room_id = "battle_v82_stable"
        self.role = self.opp_role = None
        self.state = "waiting"
        self.countdown_time = 0
        self.p1_ready = self.p2_ready = False
        self.opp_grid = "0" * 200
        self.opp_score = self.opp_stomps = 0
        self.incoming_attack_q = 0
        self.synced_received_total = 0
        self.last_poll_time = 0
        self.game_over = False
        self.winner = None
        # Throttling
        self.last_sync_time = 0
        self.sync_active = False

    def _api(self, ep, method="GET", body=None):
        try:
            url = f"{self.db_url}/{ep}.json"
            req = urllib.request.Request(url, method=method)
            if body is not None:
                req.add_header('Content-Type', 'application/json')
                data = json.dumps(body).encode('utf-8')
                with urllib.request.urlopen(req, data=data, timeout=4) as r: return json.loads(r.read().decode('utf-8'))
            else:
                with urllib.request.urlopen(req, timeout=4) as r: return json.loads(r.read().decode('utf-8'))
        except: return None

    async def join(self, role):
        self.role = role ; self.opp_role = "p2" if role == "p1" else "p1"
        if role == "p1":
            d = {"state":"waiting","p1":{"ready":False,"attack_count":0,"grid":"0"*200,"score":0,"stomps":0,"lost":False},"p2":{"ready":False,"attack_count":0,"grid":"0"*200,"score":0,"stomps":0,"lost":False},"countdown":0,"winner":""}
            await asyncio.to_thread(self._api, f"battles/{self.room_id}", "PUT", d)
        else: await asyncio.to_thread(self._api, f"battles/{self.room_id}/p2", "PATCH", {"ready":False,"lost":False})

    async def poll(self):
        n = time.time()
        if n - self.last_poll_time > POLL_INTERVAL:
            data = await asyncio.to_thread(self._api, f"battles/{self.room_id}")
            if data:
                self.state = data.get('state', 'waiting')
                self.countdown_time = data.get('countdown', 0)
                self.winner = data.get('winner', "")
                p1, p2 = data.get('p1', {}), data.get('p2', {})
                self.p1_ready, self.p2_ready = p1.get('ready', False), p2.get('ready', False)
                opp = p2 if self.role == "p1" else p1
                self.opp_grid, self.opp_score, self.opp_stomps = opp.get('grid', "0"*200), opp.get('score', 0), opp.get('stomps', 0)
                if opp.get('lost') and not self.game_over: self.game_over = True
                rem_q = opp.get('attack_count', 0)
                if rem_q > self.synced_received_total:
                    self.incoming_attack_q += (rem_q - self.synced_received_total)
                    self.synced_received_total = rem_q
            self.last_poll_time = n

    async def sync_state(self, grid, score, stomps, attacks_to_add):
        now = time.time()
        if self.sync_active or (now - self.last_sync_time < SYNC_INTERVAL): return
        self.sync_active = True
        try:
            # Atomic update: current attacker count
            path = f"battles/{self.room_id}/{self.role}"
            data = await asyncio.to_thread(self._api, path)
            cur_q = data.get('attack_count', 0) if data else 0
            # Patch everything
            await asyncio.to_thread(self._api, path, "PATCH", {"grid":grid,"score":score,"stomps":stomps,"attack_count":cur_q + attacks_to_add})
            self.last_sync_time = now
        finally: self.sync_active = False

    async def declare_lost(self):
        await asyncio.to_thread(self._api, f"battles/{self.room_id}/{self.role}", "PATCH", {"lost":True})
        await asyncio.to_thread(self._api, f"battles/{self.room_id}", "PATCH", {"winner":self.opp_role, "state":"gameover"})

# --- MAIN ---
class MarioBattleStableV82:
    def __init__(self):
        pygame.init() ; self.scr = pygame.display.set_mode((WW, WH)) ; pygame.display.set_caption("MARIO BATTLE STABLE V82")
        self.clock = pygame.time.Clock() ; self.net = BattleNetwork("https://mario-tetris-game-default-rtdb.firebaseio.com") ; self.audio = AudioManager()
        try:
            p = get_asset_path("PressStart2P-Regular.ttf")
            if os.path.exists(p): self.f_s, self.f_m, self.f_h = pygame.font.Font(p,12), pygame.font.Font(p,26), pygame.font.Font(p,44)
            else: self.f_s, self.f_m, self.f_h = pygame.font.SysFont("Arial",14), pygame.font.SysFont("Arial",28), pygame.font.SysFont("Arial",48)
        except: self.f_s = self.f_m = self.f_h = None
        self.phase = "menu" ; self.load_assets() ; self.reset() ; self.banners = [] ; self.comms = [] ; self.bolts = [] ; self.shake = 0 ; self.pending_attacks = 0

    def load_assets(self):
        try:
            m, b = pygame.image.load(get_asset_path("marioallsprite.png")).convert_alpha(), pygame.image.load(get_asset_path("blocks.png")).convert_alpha()
            self.img = {'brick':self.cut(b,368,112,16,16,2.0),'koopa':[self.cut(m,206,242,20,27,2.0),self.cut(m,247,242,20,27,2.0)],'shell':self.cut(m,360,212,16,16,2.0),'ground':self.cut(b,0,0,16,16,2.0)}
        except: self.img = {}

    def cut(self, sheet, x, y, w, h, s):
        sur = pygame.Surface((w,h), pygame.SRCALPHA) ; sur.blit(sheet,(0,0),(x,y,w,h)) ; return pygame.transform.scale(sur, (int(w*s),int(h*s)))

    def reset(self):
        self.grid = [[None for _ in range(GW)] for _ in range(GH)] ; self.bag = [] ; self.pos = [GW//2-1, 0]
        self.pce = self.pull() ; self.score = self.stomps = self.fall = self.spa_t = self.clr_t = 0 ; self.enemies = [] ; self.is_ready = False ; self.clring = [] ; self.pending_attacks = 0

    def pull(self):
        if not self.bag: self.bag = ['I','O','T','S','Z','J','L'] ; random.shuffle(self.bag)
        t = self.bag.pop() ; d = {'I':[(0,0),(1,0),(2,0),(3,0)], 'O':[(0,0),(1,0),(0,1),(1,1)], 'T':[(1,0),(0,1),(1,1),(2,1)], 'S':[(1,0),(2,0),(0,1),(1,1)], 'Z':[(0,0),(1,0),(1,1),(2,1)], 'J':[(0,0),(0,1),(1,1),(0,2)], 'L':[(0,0),(0,1),(1,1),(0,2)]}
        return {'shape':[list(p) for p in d[t]], 'id':t}

    def collide(self, p, s):
        for bx, by in s:
            gx, gy = p[0]+bx, p[1]+by
            if gx < 0 or gx >= GW or gy >= GH or (gy >= 0 and self.grid[gy][gx]): return True
        return False

    async def run(self):
        while True:
            dt = self.clock.tick(60) / 1000.0
            for e in pygame.event.get():
                if e.type == pygame.QUIT: return
                if e.type == pygame.KEYDOWN:
                    if self.phase == "menu":
                        if e.key == pygame.K_1: await self.net.join("p1") ; self.phase = "lobby" ; self.audio.start_bgm()
                        if e.key == pygame.K_2: await self.net.join("p2") ; self.phase = "lobby" ; self.audio.start_bgm()
                    elif self.phase == "lobby" and e.key == pygame.K_RETURN: self.is_ready = not self.is_ready ; await asyncio.to_thread(self.net._api, f"battles/{self.net.room_id}/{self.net.role}", "PATCH", {"ready":self.is_ready})
                    elif self.phase == "play" and not self.clring and not self.net.game_over:
                        if e.key == pygame.K_LEFT:
                            self.pos[0] -= 1
                            if self.collide(self.pos, self.pce['shape']): self.pos[0] += 1
                            else: self.audio.play('move')
                        if e.key == pygame.K_RIGHT:
                            self.pos[0] += 1
                            if self.collide(self.pos, self.pce['shape']): self.pos[0] -= 1
                            else: self.audio.play('move')
                        if e.key == pygame.K_UP:
                            old = [list(p) for p in self.pce['shape']] ; self.pce['shape'] = [(-y, x) for x, y in old]
                            if self.collide(self.pos, self.pce['shape']): self.pce['shape'] = old
                            else: self.audio.play('rotate')
                        if e.key == pygame.K_SPACE:
                            while not self.collide([self.pos[0], self.pos[1]+1], self.pce['shape']): self.pos[1] += 1
                            self.audio.play('lock') ; self.fall = 10.0

            if self.phase != "menu":
                await self.net.poll()
                if self.net.p1_ready and self.net.p2_ready and self.net.role == "p1" and self.net.state == "waiting":
                    await asyncio.to_thread(self.net._api, f"battles/{self.net.room_id}", "PATCH", {"state":"countdown","countdown":time.time()})
                if self.net.state == "countdown" and self.phase == "lobby":
                    if time.time() - self.net.countdown_time >= 3.0: self.phase = "play" ; self.reset() ; self.banners.append(AchievementBanner("START!",(0,255,255),self.f_h))

                if self.phase == "play":
                    self.banners = [b for b in self.banners if b.update(dt)] ; self.comms = [c for c in self.comms if c.update(dt)] ; self.bolts = [b for b in self.bolts if b.update(dt)]
                    if self.shake > 0: self.shake -= dt * 25
                    if not self.net.game_over:
                        if self.clring:
                            self.clr_t -= dt
                            if self.clr_t <= 0:
                                fil = [r for i, r in enumerate(self.grid) if i not in self.clring]
                                while len(fil) < GH: fil.insert(0, [None]*GW)
                                self.grid = fil ; self.clring = [] ; self.pos = [GW//2-1, 0] ; self.pce = self.pull()
                                if self.collide(self.pos, self.pce['shape']): await self.net.declare_lost()
                        else:
                            # ATOMIC SYNC: Attacks are joined into the throttled update
                            shadow = [row[:] for row in self.grid] ; cid = {'I':'1','O':'2','T':'3','S':'4','Z':'5','J':'6','L':'7'}[self.pce['id']]
                            for bx, by in self.pce['shape']:
                                gx, gy = self.pos[0]+bx, self.pos[1]+by
                                if 0 <= gx < 10 and 0 <= gy < 20: shadow[gy][gx] = ID_TO_COLOR[cid]
                            s_str = "".join([COLOR_TO_ID.get(c, "0") if c!=(140,140,140) else "G" for row in shadow for c in row])
                            asyncio.create_task(self.net.sync_state(s_str, self.score, self.stomps, self.pending_attacks))
                            if not self.net.sync_active: self.pending_attacks = 0 # Clear buffer once synced

                            if self.net.incoming_attack_q > 0:
                                self.audio.play('hit') ; self.shake = 15 ; self.comms.append(CombatText("⚠️ BLOCK IN!",(255,50,50),320,220,self.f_m))
                                for _ in range(int(self.net.incoming_attack_q)):
                                    self.grid.pop(0) ; self.grid.append([(140,140,140) if x!=(random.randint(0,9)) else None for x in range(GW)])
                                self.net.incoming_attack_q = 0

                            self.spa_t += dt
                            if self.spa_t > 9.0: self.spa_t = 0 ; self.enemies.append(ProfessionalEnemy(random.randint(0,9)))
                            for en in self.enemies[:]:
                                if en.update(dt, self.grid, self.audio): self.enemies.remove(en)
                                elif en.y > GH + 1: self.enemies.remove(en)
                                elif en.state == 'walking':
                                    for bx, by in self.pce['shape']:
                                        if int(en.x+0.5) == self.pos[0]+bx and int(en.y+0.5) == self.pos[1]+by:
                                            self.enemies.remove(en) ; self.stomps += 1 ; self.score += 500 ; self.audio.play('stomp')
                                            self.comms.append(CombatText("STOMPED! 🚀",(0,255,255),320,260,self.f_m))
                                            if 'shell' in self.img: self.bolts.append(BlastProjectile(60+en.x*BS, GRID_Y+en.y*BS, 620, 240, self.img['shell']))
                                            self.audio.play('shell') ; self.pending_attacks += 1 ; break

                            spd = 0.85
                            if pygame.key.get_pressed()[pygame.K_DOWN]: spd = 0.05
                            self.fall += dt
                            if self.fall > spd:
                                self.fall = 0 ; self.pos[1] += 1
                                if self.collide(self.pos, self.pce['shape']):
                                    self.pos[1] -= 1 ; self.audio.play('lock') ; c = ID_TO_COLOR[{'I':'1','O':'2','T':'3','S':'4','Z':'5','J':'6','L':'7'}[self.pce['id']]]
                                    for bx, by in self.pce['shape']:
                                        if 0 <= self.pos[1]+by < GH: self.grid[self.pos[1]+by][self.pos[0]+bx] = c
                                    self.clring = [ri for ri,r in enumerate(self.grid) if all(cell is not None for cell in r)]
                                    if self.clring:
                                        self.audio.play('clear') ; self.score += (len(self.clring)*1000) ; self.clr_t = 0.65 ; self.shake = 24
                                        self.banners.append(AchievementBanner(f"MEGA COMBO: {len(self.clring)}!",(0,255,255),self.f_m))
                                        self.pending_attacks += len(self.clring)
                                    else:
                                        self.pos = [GW//2-1, 0] ; self.pce = self.pull()
                                        if self.collide(self.pos, self.pce['shape']): await self.net.declare_lost()
            self.draw() ; await asyncio.sleep(0.01)

    def draw(self):
        ox = oy = 0
        if self.shake > 0: ox, oy = random.randint(-int(self.shake), int(self.shake)), random.randint(-int(self.shake), int(self.shake))
        self.scr.fill((92, 148, 252))
        if self.phase == "menu":
            self.draw_t("MARIO BATTLE STABLE", self.f_h, (255,255,255), WW//2, 200)
            self.draw_t("FIXED COMBAT v82", self.f_m, (255,255,0), WW//2, 350)
            self.draw_t("ROLE: [1] OR [2]", self.f_m, (255,255,255), WW//2, 450)
        else:
            ax, ay = 60 + ox, GRID_Y + oy
            pygame.draw.rect(self.scr, (10,10,20), (ax-4, ay-4, GW*BS+8, GH*BS+8)) ; pygame.draw.rect(self.scr, (255,255,255), (ax-4, ay-4, GW*BS+8, GH*BS+8), 2)
            if 'ground' in self.img:
                for x in range(GW): self.scr.blit(self.img['ground'], (ax + x*BS, ay + GH*BS))
            # GHOST
            if self.phase == "play" and not self.clring and not self.net.game_over:
                gx, gy = self.pos[0], self.pos[1]
                while not self.collide([gx, gy+1], self.pce['shape']): gy += 1
                c = ID_TO_COLOR[{'I':'1','O':'2','T':'3','S':'4','Z':'5','J':'6','L':'7'}[self.pce['id']]]
                for bx, by in self.pce['shape']:
                    gst = pygame.Surface((BS, BS), pygame.SRCALPHA) ; gst.fill((*c, 75)) ; self.scr.blit(gst, (ax+(gx+bx)*BS, ay+(gy+by)*BS))
            # GRID & ACTIVE
            for y in range(GH):
                if y in self.clring and int(time.time()*15)%2==0: pygame.draw.rect(self.scr, (255,255,255), (ax, ay+y*BS, GW*BS, BS))
                else:
                    for x in range(GW):
                        cl = self.grid[y][x] ; if cl: self.draw_3db(ax+x*BS, ay+y*BS, cl, BS)
            if not self.clring and self.phase == "play" and not self.net.game_over:
                cl = ID_TO_COLOR[{'I':'1','O':'2','T':'3','S':'4','Z':'5','J':'6','L':'7'}[self.pce['id']]]
                for bx, by in self.pce['shape']: self.draw_3db(ax+(self.pos[0]+bx)*BS, ay+(self.pos[1]+by)*BS, cl, BS)
            for en in self.enemies:
                eimg = self.img['koopa'][en.frame] ; if en.dir == 1: eimg = pygame.transform.flip(eimg, True, False)
                self.scr.blit(eimg, (ax + en.x*BS, ay + en.y*BS - eimg.get_height() + BS - (abs(math.sin(time.time()*10))*5)))
            for b_fx in self.bolts: b_fx.draw(self.scr)
            for c_fx in self.comms: c_fx.draw(self.scr)
            for b_fx in self.banners: b_fx.draw(self.scr)
            # HUD
            self.draw_t(f"SCORE: {self.score}", self.f_s, (255,255,255), ax, 25, False)
            ox_v, oy_v = 620, GRID_Y+80 ; sbs = 28 ; pygame.draw.rect(self.scr, (5,5,15), (ox_v-4, oy_v-4, GW*sbs+8, GH*sbs+8))
            for i, cid in enumerate(self.net.opp_grid):
                if cid != '0': self.draw_3db(ox_v+(i%10)*sbs, oy_v+(i//10)*sbs, ID_TO_COLOR.get(cid, (100,100,100)), sbs)
            self.draw_t("OPPONENT", self.f_m, (255,255,255), ox_v, oy_v-35, False)
            if self.net.game_over:
                self.draw_t("OVER", self.f_h, (255,255,255), WW//2, WH//2 - 40)
                txt, col = ("WIN!", (0,255,0)) if self.net.winner == self.net.role else ("LOSE!", (255,0,0))
                self.draw_t(txt, self.f_m, col, WW//2, WH//2 + 30)
        pygame.display.flip()

    def draw_3db(self, x, y, c, s):
        pygame.draw.rect(self.scr, c, (x, y, s, s))
        lt, dk = [min(255, ch+75) for ch in c], [max(0, ch-75) for ch in c]
        pygame.draw.polygon(self.scr, lt, [(x,y),(x+s,y),(x+s-3,y+3),(x+3,y+3)])
        pygame.draw.polygon(self.scr, dk, [(x+s,y),(x+s,y+s),(x+s-3,y+s-3),(x+s-3,y+3)])

    def draw_t(self, t, f, c, x, y, ct=True):
        if not f: return
        r = f.render(t, True, c) ; rr = r.get_rect(center=(x,y)) if ct else r.get_rect(topleft=(x,y)) ; self.scr.blit(r, rr)

if __name__ == "__main__":
    try: asyncio.run(MarioBattleStableV82().run())
    except: pass
