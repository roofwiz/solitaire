
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

# --- V99 - "MARIO BATTLE ULTIMATE (BYPASS EDITION)" ---
# Fixed: 
# - HTML BUTTON BYPASS: Added real HTML buttons to the page to ensure input works.
# - DUAL-INPUT: Both Python Rect buttons AND HTML buttons work.
# - NO-BLOCKING NETWORK: Initial join is asynchronous and won't hang the screen.
# - BRIGHT PINK BACKGROUND: Absolute proof of V99.
# - NEW ROOM: fresh_arena_v99 for a clean state.

WW, WH = 1000, 720
GW, GH = 10, 20
BS = 32
GRID_Y = 60

ID_TO_COLOR = {
    '1': (0, 240, 240), '2': (240, 240, 0), '3': (160, 0, 240),
    '4': (0, 240, 0), '5': (240, 0, 0), '6': (0, 0, 240),
    '7': (240, 160, 0), 'G': (140, 140, 140)
}
COLOR_TO_ID = {v: k for k, v in ID_TO_COLOR.items()}

def get_asset_path(filename):
    for d in ['assets', 'sounds']:
        p = os.path.join(d, filename)
        if os.path.exists(p): return p
    return filename

class Network:
    def __init__(self, db_url):
        self.db_url = db_url.rstrip('/')
        self.room_id = "fresh_arena_v99"
        self.role = None
        self.state, self.status = "waiting", "IDLE"
        self.p1_wins, self.p2_wins = 0, 0
        self.opp_grid = "0" * 200
        self.last_poll = 0

    def _req(self, ep, method="GET", body=None):
        try:
            url = f"{self.db_url}/{ep}.json?nocache={time.time()}"
            req = urllib.request.Request(url, method=method)
            if body:
                d = json.dumps(body).encode('utf-8')
                with urllib.request.urlopen(req, data=d, timeout=5) as r: return json.loads(r.read().decode('utf-8'))
            with urllib.request.urlopen(req, timeout=5) as r: return json.loads(r.read().decode('utf-8'))
        except: return None

    async def join(self, role):
        self.status = f"CONNECTING {role.upper()}"
        self.role = role
        if role == "p1":
            d = {"state":"waiting", "p1":{"ready":False,"grid":"0"*200,"match_wins":0}, "p2":{"ready":False,"grid":"0"*200,"match_wins":0}}
            await asyncio.to_thread(self._req, f"battles/{self.room_id}", "PUT", d)
        else:
            await asyncio.to_thread(self._req, f"battles/{self.room_id}/p2", "PATCH", {"ready":False})
        self.status = "ONLINE"

    async def poll(self):
        if time.time() - self.last_poll < 0.7: return
        self.last_poll = time.time()
        d = await asyncio.to_thread(self._req, f"battles/{self.room_id}")
        if d:
            self.state = d.get('state', 'waiting')
            p1, p2 = d.get('p1',{}), d.get('p2',{})
            self.p1_wins, self.p2_wins = p1.get('match_wins',0), p2.get('match_wins',0)
            o = p2 if self.role=="p1" else p1
            self.opp_grid = o.get('grid', "0"*200)

class Game:
    def __init__(self):
        pygame.init()
        self.scr = pygame.display.set_mode((WW, WH))
        self.clock = pygame.time.Clock()
        self.net = Network("https://mario-tetris-game-default-rtdb.firebaseio.com/")
        try:
            p = get_asset_path("PressStart2P-Regular.ttf")
            self.f_m = pygame.font.Font(p, 28) if os.path.exists(p) else pygame.font.SysFont("Arial", 30)
            self.f_h = pygame.font.Font(p, 48) if os.path.exists(p) else pygame.font.SysFont("Arial", 50)
            self.f_s = pygame.font.Font(p, 14) if os.path.exists(p) else pygame.font.SysFont("Arial", 16)
        except: self.f_m = self.f_h = self.f_s = None
        self.phase = "menu"
        self.btn1 = pygame.Rect(WW//2-350, 300, 310, 160)
        self.btn2 = pygame.Rect(WW//2+40, 300, 310, 160)
        self.reset()
        self.debug_msg = "READY TO START"

    def reset(self):
        self.grid = [[None for _ in range(GW)] for _ in range(GH)]
        self.bag, self.pos = [], [GW//2-1, 1]
        self.pce = self.pull()
        self.fall, self.is_ready = 0, False

    def pull(self):
        if not self.bag: self.bag = list('IOTSHZL'); random.shuffle(self.bag)
        t = self.bag.pop()
        d = {'I':[(0,0),(1,0),(2,0),(3,0)], 'O':[(0,0),(1,0),(0,1),(1,1)], 'T':[(1,0),(0,1),(1,1),(2,1)], 'S':[(1,0),(2,0),(0,1),(1,1)], 'H':[(0,0),(1,0),(1,1),(2,1)], 'Z':[(0,0),(1,0),(1,1),(2,1)], 'L':[(2,0),(0,1),(1,1),(2,1)]}
        return {'shape':[list(p) for p in d.get(t, d['I'])], 'id':t}

    async def run(self):
        while True:
            dt = self.clock.tick(60)/1000.0
            
            # --- PLATFORM BYPASS: CHECK GLOBAL WINDOW FOR EXTERNAL CLICKS ---
            try:
                import platform
                ext_choice = platform.window.multiplayer_choice
                if ext_choice in ["p1", "p2"]:
                    platform.window.multiplayer_choice = "none" # Clear it
                    self.join(ext_choice)
            except: pass

            for e in pygame.event.get():
                if e.type == pygame.QUIT: return
                if e.type == pygame.MOUSEBUTTONDOWN:
                    self.debug_msg = f"CLICK AT {e.pos}"
                    if self.phase == "menu":
                        if self.btn1.collidepoint(e.pos): self.join("p1")
                        elif self.btn2.collidepoint(e.pos): self.join("p2")
                if e.type == pygame.KEYDOWN:
                    self.debug_msg = f"KEY: {pygame.key.name(e.key)}"
                    if self.phase == "menu":
                        if e.key in [pygame.K_1, pygame.K_m]: self.join("p1")
                        if e.key in [pygame.K_2, pygame.K_l]: self.join("p2")
                    elif self.phase == "play":
                        if e.key == pygame.K_LEFT:
                            self.pos[0]-=1
                            if self.collide(self.pos, self.pce['shape']): self.pos[0]+=1
                        elif e.key == pygame.K_RIGHT:
                            self.pos[0]+=1
                            if self.collide(self.pos, self.pce['shape']): self.pos[0]-=1
                        elif e.key == pygame.K_UP:
                            old = [list(p) for p in self.pce['shape']]
                            self.pce['shape'] = [(-y,x) for x,y in old]
                            if self.collide(self.pos, self.pce['shape']): self.pce['shape']=old
                        elif e.key == pygame.K_SPACE:
                            while not self.collide([self.pos[0],self.pos[1]+1], self.pce['shape']): self.pos[1]+=1
                            self.fall = 10
                        elif e.key == pygame.K_RETURN and self.net.state == "waiting":
                            self.is_ready = not self.is_ready
                            asyncio.create_task(asyncio.to_thread(self.net._req, f"battles/{self.net.room_id}/{self.net.role}", "PATCH", {"ready":self.is_ready}))

            if self.phase not in ["splash", "menu"]:
                await self.net.poll()
                if self.net.state == "playing" and self.phase != "play":
                    self.phase = "play"; self.reset()
                if self.phase == "play" and self.net.state == "playing":
                    self.fall += dt
                    slow_fall = 0.85 if not pygame.key.get_pressed()[pygame.K_DOWN] else 0.05
                    if self.fall > slow_fall:
                        self.fall = 0; self.pos[1]+=1
                        if self.collide(self.pos, self.pce['shape']):
                            self.pos[1]-=1
                            cid = {'I':'1','O':'2','T':'3','S':'4','H':'5','Z':'6','L':'7'}.get(self.pce['id'],'1')
                            for bx,by in self.pce['shape']:
                                if 0<=self.pos[1]+by<GH: self.grid[self.pos[1]+by][self.pos[0]+bx] = ID_TO_COLOR[cid]
                            self.pos, self.pce = [GW//2-1, 1], self.pull()
                    
                    if time.time() - self.net.last_poll > 0.6:
                        shadow = [row[:] for row in self.grid]
                        cid = {'I':'1','O':'2','T':'3','S':'4','H':'5','Z':'6','L':'7'}.get(self.pce['id'],'1')
                        for bx,by in self.pce['shape']:
                            if 0<=self.pos[1]+by<GH: shadow[self.pos[1]+by][self.pos[0]+bx] = ID_TO_COLOR[cid]
                        s_str = "".join([COLOR_TO_ID.get(c, "0") for r in shadow for c in r])
                        asyncio.create_task(asyncio.to_thread(self.net._req, f"battles/{self.net.room_id}/{self.net.role}", "PATCH", {"grid":s_str}))

            self.draw()
            await asyncio.sleep(0.01)

    def collide(self, p, s):
        for bx,by in s:
            gx, gy = p[0]+bx, p[1]+by
            if gx<0 or gx>=GW or gy>=GH or (gy>=0 and self.grid[gy][gx]): return True
        return False

    def join(self, role):
        if self.net.status == "IDLE": 
            asyncio.create_task(self.net.join(role))
            self.phase = "lobby"

    def draw(self):
        # BRIGHT PINK = V99 ULTIMATE
        self.scr.fill((255, 100, 200)) 
        
        if self.debug_msg:
            self.draw_t(self.debug_msg, (255,255,255), 10, WH-30, False, self.f_s)

        if self.phase == "menu":
            self.draw_t("SELECT PLAYER",(255,255,255),WW//2, 100, True, self.f_h)
            pygame.draw.rect(self.scr, (255,255,255), self.btn1, 0, 30); pygame.draw.rect(self.scr, (0,0,0), self.btn1, 4, 30)
            pygame.draw.rect(self.scr, (255,255,255), self.btn2, 0, 30); pygame.draw.rect(self.scr, (0,0,0), self.btn2, 4, 30)
            self.draw_t("MARIO (1)", (255,0,0), self.btn1.centerx, self.btn1.centery, True, self.f_m)
            self.draw_t("LUIGI (2)", (0,180,0), self.btn2.centerx, self.btn2.centery, True, self.f_m)
        else:
            ax, ay = 60, GRID_Y
            pygame.draw.rect(self.scr, (0,0,0), (ax-4, ay-4, GW*BS+8, GH*BS+8))
            for y in range(GH):
                for x in range(GW):
                    if self.grid[y][x]: pygame.draw.rect(self.scr, self.grid[y][x], (ax+x*BS, ay+y*BS, BS, BS))
            if self.phase == "play":
                cid = {'I':'1','O':'2','T':'3','S':'4','H':'5','Z':'6','L':'7'}.get(self.pce['id'],'1')
                for bx,by in self.pce['shape']: pygame.draw.rect(self.scr, ID_TO_COLOR[cid], (ax+(self.pos[0]+bx)*BS, ay+(self.pos[1]+by)*BS, BS, BS))
            
            ox, sbs = 620, 28
            pygame.draw.rect(self.scr, (5,5,15), (ox-4, ay+50, GW*sbs+8, GH*sbs+8))
            for i, c in enumerate(self.net.opp_grid):
                if c != '0': pygame.draw.rect(self.scr, ID_TO_COLOR.get(c,(120,120,120)), (ox+(i%10)*sbs, ay+50+(i//10)*sbs, sbs, sbs))
            
            self.draw_t(f"SCORE: {self.net.p1_wins} - {self.net.p2_wins}", (255,255,255), WW//2, 30, True, self.f_m)
            if self.net.state == "waiting": self.draw_t("READY: [ENTER]" if not self.is_ready else "WAITING...", (255,255,255), WW//2, WH-100, True, self.f_m)
            self.draw_t(self.net.status, (255,0,255), WW//2, WH-40, True, self.f_s)

        pygame.display.flip()

    def draw_t(self, t, c, x, y, ct, f):
        if not f: return
        r = f.render(t, True, c)
        self.scr.blit(r, r.get_rect(center=(x,y)) if ct else (x,y))

if __name__ == "__main__": asyncio.run(Game().run())
