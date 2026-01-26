
import pygame
import random
import json
import asyncio
import sys
import os
import time
import traceback
import urllib.request
import subprocess

# --- V47 - THE "MARIO BATTLE" BUILD ---
# Smart injection of Mario assets into the stable V46 core.

PID = os.getpid()
LOG_FILE = f"v47_log_{PID}.txt"

def log(msg):
    try:
        ts = time.strftime('%H:%M:%S')
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
            f.flush()
    except: pass
    print(f"[MARIO-BATTLE] {msg}")

log("Application starting...")

class FirebaseManagerV47:
    def __init__(self, db_url):
        self.db_url = db_url.rstrip('/')
        self.room_id = "battle_v47"
        self.role = None 
        self.opp_role = None
        self.connected = False
        self.p1_ready = False
        self.p2_ready = False
        self.room_state = "waiting"
        self.countdown_start = 0
        self.pending_garbage = 0
        self.total_received = 0

    def _req(self, url, method="GET", data=None):
        try:
            req = urllib.request.Request(url, method=method)
            if data:
                req.add_header('Content-Type', 'application/json')
                body = json.dumps(data).encode('utf-8')
            else: body = None
            with urllib.request.urlopen(req, data=body, timeout=4) as r:
                return json.loads(r.read().decode('utf-8'))
        except: return None

    async def pick(self, role):
        self.role = role
        self.opp_role = "p2" if role == "p1" else "p1"
        url = f"{self.db_url}/battles/{self.room_id}.json"
        
        # Room Initialization
        data = await asyncio.to_thread(self._req, url)
        curr_time = time.time()
        
        if role == "p1":
            log("Initializing Room as P1.")
            d = {"state":"waiting", "p1":{"ready":False, "attack_queue":0}, "p2":{"ready":False, "attack_queue":0, "status":"offline"}, "last_update":curr_time, "countdown_start":0}
            await asyncio.to_thread(self._req, url, "PUT", d)
        else:
            log("Joining Room as P2.")
            await asyncio.to_thread(self._req, f"{self.db_url}/battles/{self.room_id}/p2.json", "PATCH", {"status":"alive", "ready":False})
            
        self.connected = True

    async def poll(self):
        if not self.connected: return
        data = await asyncio.to_thread(self._req, f"{self.db_url}/battles/{self.room_id}.json")
        if data:
            self.room_state = data.get('state', 'waiting')
            self.countdown_start = data.get('countdown_start', 0)
            self.p1_ready = data.get('p1', {}).get('ready', False)
            self.p2_ready = data.get('p2', {}).get('ready', False)
            
            opp_data = data.get(self.opp_role, {})
            remote_q = opp_data.get('attack_queue', 0)
            if remote_q > self.total_received:
                self.pending_garbage += (remote_q - self.total_received)
                self.total_received = remote_q
        
        if self.role == "p1":
             await asyncio.to_thread(self._req, f"{self.db_url}/battles/{self.room_id}.json", "PATCH", {"last_update": time.time()})

# --- CONSTANTS ---
WW, WH = 950, 650
GW, GH = 10, 20
BS = 30 # Slightly bigger blocks
T_SHAPES = {
    'I': [[(0,0),(1,0),(2,0),(3,0)], (200, 50, 50)], 
    'O': [[(0,0),(1,0),(0,1),(1,1)], (240, 240, 50)], 
    'T': [[(1,0),(0,1),(1,1),(2,1)], (160, 50, 200)], 
    'S': [[(1,0),(2,0),(0,1),(1,1)], (50, 200, 50)], 
    'Z': [[(0,0),(1,0),(1,1),(2,1)], (220, 100, 50)], 
    'J': [[(0,0),(0,1),(1,1),(2,1)], (50, 50, 220)], 
    'L': [[(2,0),(0,1),(1,1),(2,1)], (255, 160, 50)]
}

class TetrisV47:
    def __init__(self):
        pygame.init()
        # Keep mixer disabled for ultimate stability as per user's history
        try: pygame.mixer.quit()
        except: pass
        
        self.screen = pygame.display.set_mode((WW, WH))
        pygame.display.set_caption(f"MARIO TETRIS BATTLE V47")
        self.clock = pygame.time.Clock()
        self.fb = FirebaseManagerV47("https://mario-tetris-game-default-rtdb.firebaseio.com/")
        
        self.mode = "menu" # menu, lobby, play
        self.ready_state = False
        
        # Assets
        self.load_assets()
        self.reset_game()

    def load_assets(self):
        log("Loading Mario Assets...")
        try:
            # Font
            font_path = "assets/PressStart2P-Regular.ttf"
            if os.path.exists(font_path):
                self.font = pygame.font.Font(font_path, 16)
                self.huge_font = pygame.font.Font(font_path, 60)
            else:
                self.font = pygame.font.SysFont("Arial", 20)
                self.huge_font = pygame.font.SysFont("Arial", 80)
            
            # Sprites
            self.sheets = {}
            if os.path.exists("assets/marioallsprite.png"):
                self.sheets['mario'] = pygame.image.load("assets/marioallsprite.png").convert_alpha()
            if os.path.exists("assets/blocks.png"):
                self.sheets['blocks'] = pygame.image.load("assets/blocks.png").convert_alpha()
            
            # Extract Mario/Luigi Portraits
            self.portraits = {}
            if 'mario' in self.sheets:
                # Mario (red)
                self.portraits['p1'] = self.get_sprite(self.sheets['mario'], 10, 6, 12, 16, 4)
                # Luigi (green)
                # In Super Mario Bros 1 spritesheet, Luigi is often a palette swap or elsewhere.
                # For simplicity, we'll use Mario for both but tinted or a different frame if found.
                # Let's see if we can find a green one. If not, we'll tint Mario green.
                self.portraits['p2'] = self.portraits['p1'].copy()
                self.portraits['p2'].fill((100, 255, 100), special_flags=pygame.BLEND_RGB_MULT)

            # Block Sprites
            self.block_img = None
            if 'blocks' in self.sheets:
                 # We'll use the 'Question Block' as the default Tetris block skin
                 self.block_img = self.get_sprite(self.sheets['blocks'], 80, 112, 16, 16, BS/16.0)
                 self.brick_img = self.get_sprite(self.sheets['blocks'], 369, 111, 16, 16, BS/16.0)
                 self.empty_img = self.get_sprite(self.sheets['blocks'], 240, 144, 16, 16, BS/16.0)
        except Exception as e:
            log(f"Asset Error: {e}")
            self.font = pygame.font.SysFont("Arial", 20)
            self.huge_font = pygame.font.SysFont("Arial", 80)

    def get_sprite(self, sheet, x, y, w, h, scale=1.0):
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.blit(sheet, (0, 0), (x, y, w, h))
        if scale != 1.0:
            surf = pygame.transform.scale(surf, (int(w * scale), int(h * scale)))
        return surf

    def reset_game(self):
        self.grid = [[None for _ in range(GW)] for _ in range(GH)]
        self.bag = []
        self.pos = [GW//2-1, 0]
        self.shape = self.spawn()
        self.fall_dt = 0

    def spawn(self):
        if not self.bag: self.bag = list(T_SHAPES.keys()); random.shuffle(self.bag)
        s = self.bag.pop()
        return [list(T_SHAPES[s][0]), T_SHAPES[s][1]]

    def collide(self, p, s):
        for bx, by in s[0]:
            gx, gy = p[0]+bx, p[1]+by
            if gx < 0 or gx >= GW or gy >= GH or (gy >= 0 and self.grid[gy][gx]): return True
        return False

    async def run(self):
        while True:
            dt = self.clock.tick(60)/1000.0
            t_now = time.time()
            for e in pygame.event.get():
                if e.type == pygame.QUIT: return
                if e.type == pygame.KEYDOWN:
                    if self.mode == "menu":
                        if e.key == pygame.K_1: await self.fb.pick("p1"); self.mode = "lobby"
                        if e.key == pygame.K_2: await self.fb.pick("p2"); self.mode = "lobby"
                        if e.key == pygame.K_SPACE: 
                             abs_path = os.path.abspath(__file__)
                             subprocess.Popen([sys.executable, abs_path])
                    elif self.mode == "lobby" and e.key == pygame.K_RETURN:
                        r = not (self.fb.p1_ready if self.fb.role=="p1" else self.fb.p2_ready)
                        await asyncio.to_thread(self.fb._req, f"{self.fb.db_url}/battles/{self.fb.room_id}/{self.fb.role}.json", "PATCH", {"ready": r})
                    elif self.mode == "play":
                        if e.key == pygame.K_LEFT: 
                            self.pos[0]-=1
                            if self.collide(self.pos, self.shape): self.pos[0]+=1
                        if e.key == pygame.K_RIGHT: 
                            self.pos[0]+=1
                            if self.collide(self.pos, self.shape): self.pos[0]-=1
                        if e.key == pygame.K_UP:
                            old = [list(b) for b in self.shape[0]]
                            self.shape[0] = [(-by, bx) for bx, by in old]
                            if self.collide(self.pos, self.shape): self.shape[0] = old

            if self.mode != "menu":
                await self.fb.poll()
                # Transition Logic
                if self.fb.p1_ready and self.fb.p2_ready and self.fb.role == "p1" and self.fb.room_state == "waiting":
                    await asyncio.to_thread(self.fb._req, f"{self.fb.db_url}/battles/{self.fb.room_id}.json", "PATCH", {"state":"countdown", "countdown_start":time.time()})
                
                if self.fb.room_state == "countdown":
                    if self.mode == "lobby": 
                        self.mode = "play"
                        self.reset_game()
                
                if self.mode == "play":
                    # Garbage Logic
                    if self.fb.pending_garbage > 0:
                        for _ in range(int(self.fb.pending_garbage)):
                            self.grid.pop(0)
                            h = random.randint(0, GW-1)
                            # Garbage bricks
                            self.grid.append([(120, 120, 120) if x!=h else None for x in range(GW)])
                        self.fb.pending_garbage = 0

                    # Gravity
                    self.fall_dt += dt
                    if self.fall_dt > 0.6:
                        self.fall_dt = 0; self.pos[1] += 1
                        if self.collide(self.pos, self.shape):
                            self.pos[1] -= 1
                            for bx, by in self.shape[0]:
                                if 0 <= self.pos[1]+by < GH: self.grid[self.pos[1]+by][self.pos[0]+bx] = self.shape[1]
                            new_g = [r for r in self.grid if any(c is None for c in r)]
                            c = GH - len(new_g)
                            while len(new_g) < GH: new_g.insert(0, [None]*GW)
                            self.grid = new_g
                            if c > 0:
                                log(f"Cleared {c} lines!")
                                cur = (await asyncio.to_thread(self.fb._req, f"{self.fb.db_url}/battles/{self.fb.room_id}/{self.fb.role}.json")).get('attack_queue', 0)
                                await asyncio.to_thread(self.fb._req, f"{self.fb.db_url}/battles/{self.fb.room_id}/{self.fb.role}.json", "PATCH", {"attack_queue": cur + c})
                            self.pos = [GW//2-1, 0]; self.shape = self.spawn()
                            if self.collide(self.pos, self.shape): self.reset_game()

            self.draw()
            await asyncio.sleep(0.01)

    def draw(self):
        # Dark Blue Sky
        self.screen.fill((92, 148, 252)) # Mario Sky Blue
        
        if self.mode == "menu":
            self.draw_text("SUPER MARIO BATTLE", self.huge_font, (255, 255, 255), WW//2, 120)
            self.draw_text("PRESS [1] FOR MARIO (P1)", self.font, (255, 255, 0), WW//2, 250)
            self.draw_text("PRESS [2] FOR LUIGI (P2)", self.font, (50, 255, 50), WW//2, 300)
            self.draw_text("PRESS [SPACE] TO SPAWN TWIN", self.font, (255, 255, 255), WW//2, 400)
        
        else:
            # Drawing the field with a "Brick" border
            rect = (50, 50, GW*BS, GH*BS)
            pygame.draw.rect(self.screen, (0, 0, 0, 180), rect) # Transparent black background
            
            # Grid
            for y, row in enumerate(self.grid):
                for x, col in enumerate(row):
                    if col:
                        self.draw_block(x, y, col)
            
            # Current Piece
            if self.mode == "play":
                for bx, by in self.shape[0]:
                    self.draw_block(self.pos[0]+bx, self.pos[1]+by, self.shape[1])
            
            # Dashboard
            dx = GW*BS + 100
            # Player Portrait
            if self.portraits:
                p = self.portraits.get(self.fb.role, self.portraits.get('p1'))
                self.screen.blit(p, (dx, 50))
            
            self.draw_text(f"I AM: {self.fb.role.upper() if self.fb.role else '?'}", self.font, (255, 255, 255), dx + 80, 70, False)
            
            p1c = (0, 255, 0) if self.fb.p1_ready else (255, 100, 100)
            p2c = (0, 255, 0) if self.fb.p2_ready else (255, 100, 100)
            self.draw_text(f"MARIO: {'READY' if self.fb.p1_ready else 'WAIT'}", self.font, p1c, dx, 150, False)
            self.draw_text(f"LUIGI: {'READY' if self.fb.p2_ready else 'WAIT'}", self.font, p2c, dx, 180, False)
            
            if self.mode == "lobby":
                msg = "HIT ENTER TO READY!" if not self.ready_state else "WAITING FOR BRO..."
                self.draw_text(msg, self.font, (255, 255, 255), WW//2, WH-50)

            if self.fb.room_state == "countdown":
                cd = 3 - int(time.time() - self.fb.countdown_start)
                self.draw_text(str(max(1, cd)) if cd > 0 else "GO!", self.huge_font, (255, 255, 255), WW//2, WH//2)

        pygame.display.flip()

    def draw_block(self, x, y, color):
        px, py = 50 + x*BS, 50 + y*BS
        if self.block_img:
            # Special logic: If color is 'Grey' (120,120,120), use the brick sprite
            if color == (120, 120, 120):
                 self.screen.blit(self.brick_img, (px, py))
            else:
                 # Tint the question mark block with the shape color
                 temp = self.block_img.copy()
                 temp.fill(color, special_flags=pygame.BLEND_RGB_MULT)
                 self.screen.blit(temp, (px, py))
        else:
            pygame.draw.rect(self.screen, color, (px, py, BS, BS))
            pygame.draw.rect(self.screen, (255,255,255), (px, py, BS, BS), 1)

    def draw_text(self, text, font, color, x, y, center=True):
        if not font: return
        surf = font.render(text, True, color)
        rect = surf.get_rect()
        if center: rect.center = (x, y)
        else: rect.topleft = (x, y)
        self.screen.blit(surf, rect)

if __name__ == "__main__":
    try: asyncio.run(TetrisV47().run())
    except: 
        with open(f"crash_v47_{PID}.txt", "w") as f: f.write(traceback.format_exc())
        input("CRASH")
