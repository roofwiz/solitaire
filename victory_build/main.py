
import pygame
import random
import json
import asyncio
import sys
import os
import time
import urllib.request

# --- V102 - "THE VICTORY BUILD" ---
# - NEW FOLDER: /victory/
# - NEW ENGINE: victory_engine.data
# - FIXED PATHING: Uses standard mount points.
# - BO3 SERIES LOGIC: Mario vs Luigi best of 3.

WW, WH = 1000, 720
GW, GH = 10, 20
BS = 32
GRID_Y = 60

COLORS = {
    '1': (0, 240, 240), '2': (240, 240, 0), '3': (160, 0, 240),
    '4': (0, 240, 0), '5': (240, 0, 0), '6': (0, 0, 240),
    '7': (240, 160, 0), 'G': (140, 140, 140)
}
ID_MAP = {v: k for k, v in COLORS.items()}

def get_asset(filename):
    for d in ['assets', 'sounds', '.']:
        p = os.path.join(d, filename)
        if os.path.exists(p): return p
    return filename

class BattleNet:
    def __init__(self, db):
        self.db = db.rstrip('/')
        self.room = "series_victory_v102"
        self.role = None
        self.state = "waiting"
        self.wins = [0, 0]
        self.opp_grid = "0" * 200
        self.status = "IDLE"

    async def req(self, ep, method="GET", body=None):
        try:
            url = f"{self.db}/{ep}.json?nocache={time.time()}"
            req = urllib.request.Request(url, method=method)
            if body:
                d = json.dumps(body).encode('utf-8')
                with urllib.request.urlopen(req, data=d, timeout=3) as r: return json.loads(r.read().decode('utf-8'))
            with urllib.request.urlopen(req, timeout=3) as r: return json.loads(r.read().decode('utf-8'))
        except: return None

    async def join(self, role):
        self.role = role
        self.status = f"JOINED {role.upper()}"
        if role == "p1":
            init = {"state":"waiting", "p1":{"ready":False,"grid":"0"*200,"wins":0}, "p2":{"ready":False,"grid":"0"*200,"wins":0}}
            await self.req(f"battles/{self.room}", "PUT", init)
        else:
            await self.req(f"battles/{self.room}/p2", "PATCH", {"ready":False})

    async def poll(self):
        while True:
            if self.role:
                d = await self.req(f"battles/{self.room}")
                if d:
                    self.state = d.get('state', 'waiting')
                    p1, p2 = d.get('p1',{}), d.get('p2',{})
                    self.wins = [p1.get('wins',0), p2.get('wins',0)]
                    opp = p2 if self.role == "p1" else p1
                    self.opp_grid = opp.get('grid', "0"*200)
            await asyncio.sleep(1.0)

class VictoryGame:
    def __init__(self):
        pygame.init()
        self.scr = pygame.display.set_mode((WW, WH))
        self.clock = pygame.time.Clock()
        self.net = BattleNet("https://mario-tetris-game-default-rtdb.firebaseio.com/")
        try:
            self.f_m = pygame.font.SysFont("Arial", 30, bold=True)
            self.f_h = pygame.font.SysFont("Arial", 50, bold=True)
        except: self.f_m = self.f_h = None
        self.phase = "menu"
        self.btn1 = pygame.Rect(WW//2-300, 300, 260, 150)
        self.btn2 = pygame.Rect(WW//2+40, 300, 260, 150)
        self.reset()
        asyncio.create_task(self.net.poll())

    def reset(self):
        self.grid = [[None for _ in range(GW)] for _ in range(GH)]
        self.bag, self.pos = [], [GW//2-1, 1]
        self.pce = self.pull()
        self.fall, self.ready = 0, False

    def pull(self):
        if not self.bag: self.bag = list('IOTSHZL'); random.shuffle(self.bag)
        t = self.bag.pop()
        d = {'I':[(0,0),(1,0),(2,0),(3,0)], 'O':[(0,0),(1,0),(0,1),(1,1)], 'T':[(1,0),(0,1),(1,1),(2,1)], 'S':[(1,0),(2,0),(0,1),(1,1)], 'H':[(0,0),(1,0),(1,1),(2,1)], 'Z':[(0,0),(1,0),(1,1),(2,1)], 'L':[(2,0),(0,1),(1,1),(2,1)]}
        return {'shape':[list(p) for p in d.get(t, d['I'])], 'id':t}

    async def run(self):
        while True:
            dt = self.clock.tick(60)/1000.0
            
            # Hybrid selection
            try:
                import platform
                c = getattr(platform.window, 'multiplayer_choice', 'none')
                if c in ['p1', 'p2']:
                    platform.window.multiplayer_choice = 'none'
                    await self.net.join(c); self.phase = "lobby"
            except: pass

            for e in pygame.event.get():
                if e.type == pygame.QUIT: return
                if e.type == pygame.MOUSEBUTTONDOWN:
                    if self.phase == "menu":
                        if self.btn1.collidepoint(e.pos): 
                            await self.net.join("p1"); self.phase = "lobby"
                        elif self.btn2.collidepoint(e.pos): 
                            await self.net.join("p2"); self.phase = "lobby"
                if e.type == pygame.KEYDOWN:
                    if self.phase == "menu":
                        if e.key in [pygame.K_1, pygame.K_m]: await self.net.join("p1"); self.phase = "lobby"
                        if e.key in [pygame.K_2, pygame.K_l]: await self.net.join("p2"); self.phase = "lobby"
                    elif self.phase in ["lobby", "play"]:
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
                        elif e.key == pygame.K_RETURN:
                            self.ready = not self.ready
                            asyncio.create_task(self.net.req(f"battles/{self.net.room}/{self.net.role}", "PATCH", {"ready":self.ready}))

            if self.phase == "lobby" and self.net.state == "playing":
                self.phase = "play"; self.reset()

            if self.phase == "play":
                self.fall += dt
                spd = 0.05 if pygame.key.get_pressed()[pygame.K_DOWN] else 0.85
                if self.fall > spd:
                    self.fall = 0; self.pos[1]+=1
                    if self.collide(self.pos, self.pce['shape']):
                        self.pos[1]-=1
                        cid = {'I':'1','O':'2','T':'3','S':'4','H':'5','Z':'6','L':'7'}.get(self.pce['id'],'1')
                        for bx,by in self.pce['shape']:
                            if 0<=self.pos[1]+by<GH: self.grid[self.pos[1]+by][self.pos[0]+bx] = COLORS[cid]
                        self.pos, self.pce = [GW//2-1, 1], self.pull()
                
                # Update Grid
                shadow = [row[:] for row in self.grid]
                cid = {'I':'1','O':'2','T':'3','S':'4','H':'5','Z':'6','L':'7'}.get(self.pce['id'],'1')
                for bx,by in self.pce['shape']:
                    if 0<=self.pos[1]+by<GH: shadow[self.pos[1]+by][self.pos[0]+bx] = COLORS[cid]
                s_str = "".join([ID_MAP.get(c, "0") for r in shadow for c in r])
                asyncio.create_task(self.net.req(f"battles/{self.net.room}/{self.net.role}", "PATCH", {"grid":s_str}))

            self.draw()
            await asyncio.sleep(0.01)

    def collide(self, p, s):
        for bx,by in s:
            gx, gy = p[0]+bx, p[1]+by
            if gx<0 or gx>=GW or gy>=GH or (gy>=0 and self.grid[gy][gx]): return True
        return False

    def draw(self):
        self.scr.fill((20, 20, 40)) # DEEP BLUE
        if self.phase == "menu":
            self.draw_t("VICTORY V102",(255,255,255),WW//2,100,True,self.f_h)
            pygame.draw.rect(self.scr,(200,50,50),self.btn1,0,12)
            pygame.draw.rect(self.scr,(50,200,50),self.btn2,0,12)
            self.draw_t("MARIO (1)",(255,255,255),self.btn1.centerx,self.btn1.centery,True,self.f_m)
            self.draw_t("LUIGI (2)",(255,255,255),self.btn2.centerx,self.btn2.centery,True,self.f_m)
        elif self.phase == "lobby":
            self.draw_t("LOBBY ACTIVE",(0,255,255),WW//2,WH//2-50,True,self.f_h)
            st = "READY (ENTER)" if not self.ready else "WAITING..."
            self.draw_t(st,(255,255,0),WW//2,WH//2+50,True,self.f_m)
        else:
            ax, ay = 60, GRID_Y
            pygame.draw.rect(self.scr,(0,0,0),(ax-4,ay-4,GW*BS+8,GH*BS+8))
            for y in range(GH):
                for x in range(GW):
                    if self.grid[y][x]: pygame.draw.rect(self.scr,self.grid[y][x],(ax+x*BS,ay+y*BS,BS,BS))
            if self.phase == "play":
                cid = {'I':'1','O':'2','T':'3','S':'4','H':'5','Z':'6','L':'7'}.get(self.pce['id'],'1')
                for bx,by in self.pce['shape']:
                    if 0<=self.pos[1]+by<GH: pygame.draw.rect(self.scr,COLORS[cid],(ax+(self.pos[0]+bx)*BS,ay+(self.pos[1]+by)*BS,BS,BS))
            
            ox, sbs = 620, 28
            pygame.draw.rect(self.scr,(5,5,15),(ox-4,ay+50,GW*sbs+8,GH*sbs+8))
            for i, c in enumerate(self.net.opp_grid):
                if c != '0': pygame.draw.rect(self.scr,COLORS.get(c,(100,100,100)),(ox+(i%10)*sbs,ay+50+(i//10)*sbs,sbs,sbs))
            self.draw_t(f"SERIES: {self.net.wins[0]} - {self.net.wins[1]}",(255,255,255),WW//2,30,True,self.f_m)
        
        pygame.display.flip()

    def draw_t(self, t, c, x, y, ct, f):
        if not f: return
        r = f.render(t, True, c)
        self.scr.blit(r, r.get_rect(center=(x,y)) if ct else (x,y))

if __name__ == "__main__": asyncio.run(VictoryGame().run())
