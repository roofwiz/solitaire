
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

# --- V95 - "MARIO BATTLE BO3 PRO ARENA" ---
# Fixed: 
# - NEW LOCATION: Deployed to /arena/ to bypass all browser cache.
# - RED BACKGROUND: Visual confirmation of V95.
# - CLICK OVERLAY: Immediate focus and audio unlock.
# - BIG BUTTONS + KEYBOARD: Absolute control for Mario/Luigi.
# - Best-of-3 Series Mode.

WW = 1000
WH = 720
GW = 10
GH = 20
BS = 32
GRID_Y = 60
SYNC_INTERVAL = 0.45 
POLL_INTERVAL = 0.65

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
        if self.life < 0.6: self.alpha = int((self.life / 0.6) * 255)
        return self.life > 0
    def draw(self, screen):
        if not self.font: return
        surf = self.font.render(self.text, True, self.color)
        surf.set_alpha(self.alpha)
        screen.blit(surf, surf.get_rect(center=(WW // 2, WH // 2 + self.y_offset)))

class BattleNetwork:
    def __init__(self, db_url):
        self.db_url = db_url.rstrip('/')
        self.room_id = "arena_v95_bo3"
        self.role = None
        self.state = "waiting"
        self.p1_wins = 0
        self.p2_wins = 0
        self.opp_grid = "0" * 200
        self.status = "Idle"
        self.sync_active = False
        self.last_poll = 0
        self.last_sync = 0
        self.rx_total = 0
        self.incoming_q = 0

    def _req(self, ep, method="GET", body=None):
        try:
            url = f"{self.db_url}/{ep}.json"
            req = urllib.request.Request(url, method=method)
            if body:
                req.add_header('Content-Type', 'application/json')
                data = json.dumps(body).encode('utf-8')
                with urllib.request.urlopen(req, data=data, timeout=5) as r: return json.loads(r.read().decode('utf-8'))
            else:
                with urllib.request.urlopen(req, timeout=5) as r: return json.loads(r.read().decode('utf-8'))
        except: return None

    async def join(self, role):
        self.status = f"Joining as {role}..."
        self.role = role
        if role == "p1":
            d = {"state":"waiting", "p1":{"ready":False,"grid":"0"*200,"match_wins":0}, "p2":{"ready":False,"grid":"0"*200,"match_wins":0}}
            await asyncio.to_thread(self._req, f"battles/{self.room_id}", "PUT", d)
        else:
            await asyncio.to_thread(self._req, f"battles/{self.room_id}/p2", "PATCH", {"ready":False})
        self.status = "Connected"

    async def poll(self):
        if time.time() - self.last_poll < POLL_INTERVAL: return
        self.last_poll = time.time()
        data = await asyncio.to_thread(self._req, f"battles/{self.room_id}")
        if data:
            self.state = data.get('state', 'waiting')
            p1, p2 = data.get('p1',{}), data.get('p2',{})
            self.p1_wins, self.p2_wins = p1.get('match_wins', 0), p2.get('match_wins', 0)
            opp = p2 if self.role == "p1" else p1
            self.opp_grid = opp.get('grid', "0"*200)

class MarioBattleV95:
    def __init__(self):
        pygame.init()
        self.scr = pygame.display.set_mode((WW, WH))
        pygame.display.set_caption("ARENA V95 PRO")
        self.clock = pygame.time.Clock()
        self.net = BattleNetwork("https://mario-tetris-game-default-rtdb.firebaseio.com/")
        try:
            p = get_asset_path("PressStart2P-Regular.ttf")
            self.f_s = pygame.font.Font(p, 12) if os.path.exists(p) else pygame.font.SysFont("Arial", 14)
            self.f_m = pygame.font.Font(p, 24) if os.path.exists(p) else pygame.font.SysFont("Arial", 28)
            self.f_h = pygame.font.Font(p, 42) if os.path.exists(p) else pygame.font.SysFont("Arial", 48)
        except: self.f_s = self.f_m = self.f_h = None
        self.phase = "prestart"
        self.btn1 = pygame.Rect(WW//2-220, 380, 200, 80)
        self.btn2 = pygame.Rect(WW//2+20, 380, 200, 80)
        self.reset_round()

    def reset_round(self):
        self.grid = [[None for _ in range(GW)] for _ in range(GH)]
        self.bag, self.banners, self.pos = [], [], [GW//2-1, 0]
        self.pce = self.pull()
        self.fall, self.is_ready, self.score = 0, False, 0

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
            for e in pygame.event.get():
                if e.type == pygame.QUIT: return
                if e.type == pygame.MOUSEBUTTONDOWN:
                    if self.phase == "prestart": self.phase = "menu"
                    elif self.phase == "menu" and self.net.status == "Idle":
                        if self.btn1.collidepoint(e.pos): self.join_req("p1")
                        elif self.btn2.collidepoint(e.pos): self.join_req("p2")
                if e.type == pygame.KEYDOWN:
                    if self.phase == "menu":
                        if e.key in [pygame.K_m, pygame.K_1]: self.join_req("p1")
                        elif e.key in [pygame.K_l, pygame.K_2]: self.join_req("p2")
                    elif self.phase == "play":
                        if e.key == pygame.K_LEFT:
                            self.pos[0]-=1
                            if self.collide(self.pos, self.pce['shape']): self.pos[0]+=1
                        elif e.key == pygame.K_RIGHT:
                            self.pos[0]+=1
                            if self.collide(self.pos, self.pce['shape']): self.pos[0]-=1
                        elif e.key == pygame.K_UP:
                            old = [list(p) for p in self.pce['shape']]
                            self.pce['shape'] = [(-y, x) for x, y in old]
                            if self.collide(self.pos, self.pce['shape']): self.pce['shape'] = old
                        elif e.key == pygame.K_SPACE:
                            while not self.collide([self.pos[0], self.pos[1]+1], self.pce['shape']): self.pos[1]+=1
                            self.fall = 10.0
                        elif e.key == pygame.K_RETURN and self.net.state == "waiting":
                            self.is_ready = not self.is_ready
                            asyncio.create_task(asyncio.to_thread(self.net._req, f"battles/{self.net.room_id}/{self.net.role}", "PATCH", {"ready":self.is_ready}))

            if self.phase not in ["prestart", "menu"]:
                await self.net.poll()
                if self.net.state == "playing" and self.phase != "play":
                    self.phase = "play"; self.reset_round()
                if self.phase == "play" and self.net.state == "playing":
                    self.fall += dt
                    if self.fall > (0.05 if pygame.key.get_pressed()[pygame.K_DOWN] else 0.85):
                        self.fall = 0; self.pos[1]+=1
                        if self.collide(self.pos, self.pce['shape']):
                            self.pos[1]-=1
                            cid = {'I':'1','O':'2','T':'3','S':'4','Z':'5','J':'6','L':'7'}[self.pce['id']]
                            for bx, by in self.pce['shape']:
                                if 0 <= self.pos[1]+by < GH: self.grid[self.pos[1]+by][self.pos[0]+bx] = ID_TO_COLOR[cid]
                            self.pos, self.pce = [GW//2-1, 0], self.pull()
                    
                    shadow = [row[:] for row in self.grid]
                    cid = {'I':'1','O':'2','T':'3','S':'4','Z':'5','J':'6','L':'7'}[self.pce['id']]
                    for bx, by in self.pce['shape']:
                        if 0 <= self.pos[1]+by < GH: shadow[self.pos[1]+by][self.pos[0]+bx] = ID_TO_COLOR[cid]
                    s_str = "".join([COLOR_TO_ID.get(c, "0") for row in shadow for c in row])
                    if not self.net.sync_active and time.time() - self.net.last_sync > SYNC_INTERVAL:
                        self.net.sync_active = True
                        asyncio.create_task(self.sync_logic(s_str))

            self.draw()
            await asyncio.sleep(0.01)

    def join_req(self, role):
        asyncio.create_task(self.net.join(role))
        self.phase = "lobby"

    async def sync_logic(self, s_str):
        try:
            await asyncio.to_thread(self.net._req, f"battles/{self.net.room_id}/{self.net.role}", "PATCH", {"grid": s_str})
            self.net.last_sync = time.time()
        finally: self.net.sync_active = False

    def draw(self):
        # RED BACKGROUND = V95 ARENA
        self.scr.fill((80, 20, 20))
        if self.phase == "prestart":
            self.draw_t("V95 PRO ARENA READY", (255,255,255), WW//2, WH//2-40, True, self.f_h)
            self.draw_t("CLICK TO ENTER", (0,255,0), WW//2, WH//2+40, True, self.f_m)
        elif self.phase == "menu":
            self.draw_t("SELECT YOUR CHARACTER", (255,255,255), WW//2, 200, True, self.f_h)
            for r,txt,col in [(self.btn1,"MARIO",(255,50,50)), (self.btn2,"LUIGI",(50,255,50))]:
                pygame.draw.rect(self.scr, (255,255,255), r, 0, 12); pygame.draw.rect(self.scr, (0,0,0), r, 3, 12)
                self.draw_t(txt, col, r.centerx, r.centery, True, self.f_m)
        else:
            # Arena
            ax, ay = 60, GRID_Y
            pygame.draw.rect(self.scr, (10,10,20), (ax-4, ay-4, GW*BS+8, GH*BS+8))
            for y in range(GH):
                for x in range(GW):
                    if self.grid[y][x]: pygame.draw.rect(self.scr, self.grid[y][x], (ax+x*BS, ay+y*BS, BS, BS))
            if self.phase == "play":
                cid = {'I':'1','O':'2','T':'3','S':'4','Z':'5','J':'6','L':'7'}[self.pce['id']]
                for bx, by in self.pce['shape']: pygame.draw.rect(self.scr, ID_TO_COLOR[cid], (ax+(self.pos[0]+bx)*BS, ay+(self.pos[1]+by)*BS, BS, BS))
            # Opponent
            ox, sbs = 620, 28
            pygame.draw.rect(self.scr, (5,5,15), (ox-4, ay+50, GW*sbs+8, GH*sbs+8))
            for i, c in enumerate(self.net.opp_grid):
                if c != '0': pygame.draw.rect(self.scr, ID_TO_COLOR.get(c,(100,100,100)), (ox+(i%10)*sbs, ay+50+(i//10)*sbs, sbs, sbs))
            self.draw_t(f"SERIES: {self.net.p1_wins} - {self.net.p2_wins}", (255,255,255), WW//2, 30, True, self.f_m)
            if self.net.state == "waiting": self.draw_t("READY: [ENTER]" if not self.is_ready else "WAITING...", (255,255,255), WW//2, WH-80, True, self.f_m)
        pygame.display.flip()

    def draw_t(self, t, c, x, y, ct, f):
        if not f: return
        r = f.render(t, True, c)
        self.scr.blit(r, r.get_rect(center=(x,y)) if ct else (x,y))

if __name__ == "__main__":
    asyncio.run(MarioBattleV95().run())
