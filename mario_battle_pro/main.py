
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

# --- V79 - "MARIO BATTLE PRO: ELITE DEPLOYMENT EDITION" ---
# Technical Specs:
# - ASYNC ENGINE: Optimized for Pygbag (Web) and Local (Desktop) play.
# - LIVE SYNC v2: Ghost pieces and falling piece projections synced at 60fps.
# - ACHIEVEMENT NOTIFIER: Premium floating banners for combat milestones.
# - SQUISH & STOMP: Physical AABB collision with column-scan reliability.
# - WIN/LOSS HUB: Cross-instance state synchronization for final results.

PID = os.getpid()

# --- ENGINE CONFIG ---
WW, WH = 1000, 720
GW, GH = 10, 20
BS = 32
GRID_Y = 60
SYNC_RATE = 0.45 

# --- ASSET MAPS ---
ID_TO_COLOR = {
    '1': (0, 240, 240),  # I
    '2': (240, 240, 0),  # O
    '3': (160, 0, 2 purple), # T
    '4': (0, 240, 0),    # S
    '5': (240, 0, 0),    # Z
    '6': (0, 0, 240),    # J
    '7': (240, 160, 0),  # L
    'G': (140, 140, 140) # Garbage
}
COLOR_TO_ID = {v: k for k, v in ID_TO_COLOR.items()}

# Fix for Purple/T-shape ID 3
ID_TO_COLOR['3'] = (160, 0, 240)

# --- UTILS ---
def get_asset_path(filename):
    """Handles path resolution for both local and web builds."""
    if os.path.exists(os.path.join('assets', filename)):
        return os.path.join('assets', filename)
    return filename

# --- VISUAL COMPONENTS ---
class AchievementBanner:
    def __init__(self, text, color, font):
        self.text = text
        self.color = color
        self.font = font
        self.life = 2.5
        self.alpha = 255
        self.y_offset = 0
        
    def update(self, dt):
        self.life -= dt
        self.y_offset -= 15 * dt
        if self.life < 0.6:
            self.alpha = int((self.life / 0.6) * 255)
        return self.life > 0

    def draw(self, screen):
        if not self.font: return
        surf = self.font.render(self.text, True, self.color)
        surf.set_alpha(self.alpha)
        rect = surf.get_rect(center=(WW // 2, WH // 4 + self.y_offset))
        screen.blit(surf, rect)

class CombatText:
    def __init__(self, text, color, x, y, font, duration=1.5):
        self.text = text
        self.color = color
        self.x, self.y = x, y
        self.font = font
        self.life = duration
        
    def update(self, dt):
        self.life -= dt
        self.y -= 35 * dt
        return self.life > 0

    def draw(self, screen):
        if not self.font: return
        surf = self.font.render(self.text, True, self.color)
        screen.blit(surf, (self.x, self.y))

class BlastProjectile:
    def __init__(self, x, y, tx, ty, img):
        self.x, self.y = float(x), float(y)
        self.tx, self.ty = float(tx), float(ty)
        self.img = img
        self.life = 1.0
        self.angle = 0
        
    def update(self, dt):
        self.life -= dt * 1.5
        # Interp toward target
        self.x += (self.tx - self.x) * 0.15
        self.y += (self.ty - self.y) * 0.15
        self.angle += 40
        return self.life > 0

    def draw(self, screen):
        if not self.img: return
        rotated = pygame.transform.rotate(self.img, self.angle)
        screen.blit(rotated, (self.x - 16, self.y - 16))

# --- SOUND SYSTEM ---
class AudioManager:
    def __init__(self):
        self.sounds = {}
        self.bgm_list = ['2. Bring The Noise.mp3', '06. Them and Us.mp3', '05. Ten in 2010.mp3']
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.pre_init(44100, -16, 2, 512)
                pygame.mixer.init()
            self._load_all()
        except:
            print("Audio Init Error")

    def _load_all(self):
        map_sfx = {
            'move': 'move.wav', 'rotate': 'rotate.wav', 'lock': 'lock.wav',
            'clear': 'clear.wav', 'stomp': 'stomp.wav', 'shell': 'impactGeneric_power_001.ogg',
            'hit': 'impactBell_heavy_004.ogg', 'land': 'impactGeneric_light_002.ogg', 'win': 'reward_01.wav'
        }
        for key, f in map_sfx.items():
            path = get_asset_path(f)
            if os.path.exists(path):
                try:
                    s = pygame.mixer.Sound(path)
                    s.set_volume(0.2 if key == 'move' else 0.4)
                    self.sounds[key] = s
                except: pass

    def play(self, key):
        if key in self.sounds:
            try: self.sounds[key].play()
            except: pass

    def start_bgm(self):
        try:
            track = self.bgm_list[random.randint(0, len(self.bgm_list)-1)]
            path = get_asset_path(track)
            if os.path.exists(path):
                pygame.mixer.music.load(path)
                pygame.mixer.music.set_volume(0.2)
                pygame.mixer.music.play(-1, fade_ms=2000)
        except: pass

# --- NETWORK BACKEND (REST API) ---
class BattleNetwork:
    def __init__(self, db_url):
        self.db_url = db_url.rstrip('/')
        self.room_id = "battle_v79_pro_deploy"
        self.role = self.opp_role = None
        self.state = "waiting"
        self.countdown_time = 0
        self.p1_ready = self.p2_ready = False
        self.opp_grid = "0" * 200
        self.opp_score = self.opp_stomps = 0
        self.incoming_attack = 0
        self.synced_received = 0
        self.last_poll = 0
        self.game_over = False
        self.winner = None

    def _api_call(self, endpoint, method="GET", body=None):
        try:
            url = f"{self.db_url}/{endpoint}.json"
            req = urllib.request.Request(url, method=method)
            if body is not None:
                req.add_header('Content-Type', 'application/json')
                data = json.dumps(body).encode('utf-8')
                with urllib.request.urlopen(req, data=data, timeout=3) as r:
                    return json.loads(r.read().decode('utf-8'))
            else:
                with urllib.request.urlopen(req, timeout=3) as r:
                    return json.loads(r.read().decode('utf-8'))
        except: return None

    async def join_match(self, role):
        self.role = role
        self.opp_role = "p2" if role == "p1" else "p1"
        if role == "p1":
            init_data = {
                "state": "waiting",
                "p1": {"ready": False, "attack_q": 0, "grid": "0"*200, "score": 0, "stomps": 0, "lost": False},
                "p2": {"ready": False, "attack_q": 0, "grid": "0"*200, "score": 0, "stomps": 0, "lost": False},
                "countdown": 0, "winner": ""
            }
            await asyncio.to_thread(self._api_call, f"battles/{self.room_id}", "PUT", init_data)
        else:
            await asyncio.to_thread(self._api_call, f"battles/{self.room_id}/p2", "PATCH", {"ready": False, "lost": False})

    async def poll_state(self):
        now = time.time()
        if now - self.last_poll > SYNC_RATE:
            data = await asyncio.to_thread(self._api_call, f"battles/{self.room_id}")
            if data:
                self.state = data.get('state', 'waiting')
                self.countdown_time = data.get('countdown', 0)
                self.winner = data.get('winner', "")
                
                p1 = data.get('p1', {})
                p2 = data.get('p2', {})
                self.p1_ready = p1.get('ready', False)
                self.p2_ready = p2.get('ready', False)
                
                opp_data = p2 if self.role == "p1" else p1
                self.opp_grid = opp_data.get('grid', "0"*200)
                self.opp_score = opp_data.get('score', 0)
                self.opp_stomps = opp_data.get('stomps', 0)
                
                if opp_data.get('lost') and not self.game_over:
                    self.game_over = True
                
                remote_q = opp_data.get('attack_q', 0)
                if remote_q > self.synced_received:
                    self.incoming_attack += (remote_q - self.synced_received)
                    self.synced_received = remote_q
            self.last_poll = now

    async def send_ready(self, status):
        await asyncio.to_thread(self._api_call, f"battles/{self.room_id}/{self.role}", "PATCH", {"ready": status})

    async def push_sync(self, grid, score, stomps):
        await asyncio.to_thread(self._api_call, f"battles/{self.room_id}/{self.role}", "PATCH", {"grid": grid, "score": score, "stomps": stomps})

    async def commit_attack(self, lines):
        data = await asyncio.to_thread(self._api_call, f"battles/{self.room_id}/{self.role}")
        current_q = data.get('attack_q', 0) if data else 0
        await asyncio.to_thread(self._api_call, f"battles/{self.room_id}/{self.role}", "PATCH", {"attack_q": current_q + lines})

    async def report_defeat(self):
        await asyncio.to_thread(self._api_call, f"battles/{self.room_id}/{self.role}", "PATCH", {"lost": True})
        await asyncio.to_thread(self._api_call, f"battles/{self.room_id}", "PATCH", {"winner": self.opp_role, "state": "gameover"})

# --- ENTITY PHYSICS ---
class ProfessionalEnemy:
    def __init__(self, x, type_id='K'):
        self.x, self.y = float(x), -1.0
        self.type_id = type_id
        self.state = 'falling'
        self.vy, self.vx_mod = 0, 1.8
        self.dir = random.choice([-1, 1])
        self.age = 0
        self.frame = 0

    def update(self, dt, grid, audio):
        self.age += dt
        self.frame = int(self.age * 8) % 2
        
        # Physics
        self.vy += 32 * dt
        self.y += self.vy * dt
        
        # Column Scan logic for perfect landing
        ix = int(max(0, min(9, self.x + 0.5)))
        solid_y = 19.0
        scan_start = int(max(0, self.y))
        for r in range(scan_start, 20):
            if grid[r][ix] is not None:
                solid_y = float(r - 1.0)
                break
        
        landed_now = False
        if self.y >= solid_y:
            self.y = solid_y
            self.vy = 0
            landed_now = True
            
        if landed_now:
            if self.state == 'falling':
                self.state = 'walking'
                audio.play('land')
            # Anti-Squish check
            if grid[int(self.y + 0.5)][ix] is not None:
                audio.play('hit')
                return True # Die if inside block
        else:
            self.state = 'falling'

        if self.state == 'walking':
            step = self.dir * self.vx_mod * dt
            next_x = self.x + step
            nx_idx = int(max(0, min(9, next_x + 0.5)))
            
            turn = False
            if next_x < 0 or next_x > 9: turn = True
            elif grid[int(self.y + 0.5)][nx_idx] is not None: turn = True
            
            if turn: self.dir *= -1
            else: self.x = next_x
            
            return self.age > 16.0 # Natural despawn
        return False

# --- MAIN CONTROLLER ---
class MarioBattlePro:
    def __init__(self):
        pygame.init()
        self.scr = pygame.display.set_mode((WW, WH))
        pygame.display.set_caption("MARIO BATTLE PRO: DEPLOYMENT")
        self.clock = pygame.time.Clock()
        self.net = BattleNetwork("https://mario-tetris-game-default-rtdb.firebaseio.com")
        self.audio = AudioManager()
        
        # Fonts
        try:
            p = get_asset_path("PressStart2P-Regular.ttf")
            if os.path.exists(p):
                self.f_s, self.f_m, self.f_h = pygame.font.Font(p, 12), pygame.font.Font(p, 26), pygame.font.Font(p, 48)
            else:
                self.f_s = pygame.font.SysFont("Arial", 16)
                self.f_m = pygame.font.SysFont("Arial", 32)
                self.f_h = pygame.font.SysFont("Arial", 50)
        except: self.f_s = self.f_m = self.f_h = None

        self.phase = "menu" # menu, lobby, play
        self.load_images()
        self.reset_game_state()
        
        self.banners = []
        self.comms = []
        self.bolts = []
        self.shake = 0

    def load_images(self):
        try:
            m = pygame.image.load(get_asset_path("marioallsprite.png")).convert_alpha()
            b = pygame.image.load(get_asset_path("blocks.png")).convert_alpha()
            self.img = {
                'brick': self.cut(b, 368, 112, 16, 16, 2.0),
                'koopa': [self.cut(m, 206, 242, 20, 27, 2.0), self.cut(m, 247, 242, 20, 27, 2.0)],
                'shell': self.cut(m, 360, 212, 16, 16, 2.0),
                'mario': self.cut(m, 10, 6, 12, 16, 4.0),
                'luigi': self.cut(m, 10, 6, 12, 16, 4.0),
                'ground': self.cut(b, 0, 0, 16, 16, 2.0)
            }
            if 'luigi' in self.img: self.img['luigi'].fill((100, 255, 100), special_flags=pygame.BLEND_RGB_MULT)
        except: self.img = {}

    def cut(self, sheet, x, y, w, h, s):
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.blit(sheet, (0, 0), (x, y, w, h))
        return pygame.transform.scale(surf, (int(w*s), int(h*s)))

    def reset_game_state(self):
        self.grid = [[None for _ in range(GW)] for _ in range(GH)]
        self.bag = []
        self.piece_pos = [GW//2-1, 0]
        self.piece = self.pull_piece()
        self.score = self.stomps = self.fall_count = 0
        self.enemies = []
        self.clearing_rows = []
        self.clear_timer = 0
        self.is_ready = False
        self.spawn_timer = 0

    def pull_piece(self):
        if not self.bag:
            self.bag = ['I','O','T','S','Z','J','L']
            random.shuffle(self.bag)
        t = self.bag.pop()
        map_p = {
            'I': [(0,0),(1,0),(2,0),(3,0)], 'O': [(0,0),(1,0),(0,1),(1,1)],
            'T': [(1,0),(0,1),(1,1),(2,1)], 'S': [(1,0),(2,0),(0,1),(1,1)],
            'Z': [(0,0),(1,0),(1,1),(2,1)], 'J': [(1,0),(1,1),(1,2),(0,2)],
            'L': [(1,0),(1,1),(1,2),(2,2)]
        }
        return {'shape': [list(p) for p in map_p[t]], 'id': t}

    def hit_test(self, pos, shape):
        for bx, by in shape:
            gx, gy = pos[0] + bx, pos[1] + by
            if gx < 0 or gx >= GW or gy >= GH or (gy >= 0 and self.grid[gy][gx]):
                return True
        return False

    async def main_loop(self):
        while True:
            dt = self.clock.tick(60) / 1000.0
            
            # Events
            for e in pygame.event.get():
                if e.type == pygame.QUIT: return
                if e.type == pygame.KEYDOWN:
                    if self.phase == "menu":
                        if e.key == pygame.K_1: await self.net.join_match("p1"); self.phase = "lobby"; self.audio.start_bgm()
                        if e.key == pygame.K_2: await self.net.join_match("p2"); self.phase = "lobby"; self.audio.start_bgm()
                    elif self.phase == "lobby" and e.key == pygame.K_RETURN:
                        self.is_ready = not self.is_ready
                        await self.net.send_ready(self.is_ready)
                    elif self.phase == "play" and not self.clearing_rows and not self.net.game_over:
                        if e.key == pygame.K_LEFT:
                            self.piece_pos[0] -= 1
                            if self.hit_test(self.piece_pos, self.piece['shape']): self.piece_pos[0] += 1
                            else: self.audio.play('move')
                        if e.key == pygame.K_RIGHT:
                            self.piece_pos[0] += 1
                            if self.hit_test(self.piece_pos, self.piece['shape']): self.piece_pos[0] -= 1
                            else: self.audio.play('move')
                        if e.key == pygame.K_UP:
                            old = [list(p) for p in self.piece['shape']]
                            self.piece['shape'] = [(-y, x) for x, y in old]
                            if self.hit_test(self.piece_pos, self.piece['shape']): self.piece['shape'] = old
                            else: self.audio.play('rotate')
                        if e.key == pygame.K_SPACE:
                            while not self.hit_test([self.piece_pos[0], self.piece_pos[1]+1], self.piece['shape']):
                                self.piece_pos[1] += 1
                            self.audio.play('lock') ; self.fall_count = 10.0 # Force lock

            # Logic
            if self.phase != "menu":
                await self.net.poll_state()
                
                # Match Engine
                if self.net.p1_ready and self.net.p2_ready and self.net.role == "p1" and self.net.state == "waiting":
                    await asyncio.to_thread(self.net._api_call, f"battles/{self.net.room_id}", "PATCH", {"state": "countdown", "countdown": time.time()})
                
                if self.net.state == "countdown" and self.phase == "lobby":
                    if time.time() - self.net.countdown_time >= 3.0:
                        self.phase = "play"; self.reset_game_state(); self.banners.append(AchievementBanner("FIGHT!", (0, 255, 255), self.f_h))

                if self.phase == "play":
                    self.banners = [b for b in self.banners if b.update(dt)]
                    self.comms = [c for c in self.comms if c.update(dt)]
                    self.bolts = [b for b in self.bolts if b.update(dt)]
                    if self.shake > 0: self.shake -= dt * 25
                    
                    if not self.net.game_over:
                        if self.clearing_rows:
                            self.clear_timer -= dt
                            if self.clear_timer <= 0:
                                filtered = [r for i, r in enumerate(self.grid) if i not in self.clearing_rows]
                                while len(filtered) < GH: filtered.insert(0, [None]*GW)
                                self.grid = filtered ; self.clearing_rows = [] ; self.piece_pos = [GW//2-1, 0] ; self.piece = self.pull_piece()
                                if self.hit_test(self.piece_pos, self.piece['shape']): await self.net.report_defeat()
                        else:
                            # Pro Sync String (Includes current piece for Live View)
                            shadow_grid = [row[:] for row in self.grid]
                            c_col = ID_TO_COLOR[{'I':'1','O':'2','T':'3','S':'4','Z':'5','J':'6','L':'7'}[self.piece['id']]]
                            for bx, by in self.piece['shape']:
                                gx, gy = self.piece_pos[0] + bx, self.piece_pos[1] + by
                                if 0 <= gx < 10 and 0 <= gy < 20: shadow_grid[gy][gx] = c_col
                            
                            sync_str = "".join([COLOR_TO_ID.get(c, "0") if c != (140,140,140) else "G" for row in shadow_grid for c in row])
                            asyncio.create_task(self.net.push_sync(sync_str, self.score, self.stomps))
                            
                            if self.net.incoming_attack > 0:
                                self.audio.play('hit') ; self.shake = 15
                                self.comms.append(CombatText("⚠️ RECV ATTACK!", (255, 50, 50), 320, 220, self.f_m))
                                for _ in range(int(self.net.incoming_attack)):
                                    self.grid.pop(0) ; self.grid.append([(140,140,140) if x != random.randint(0,9) else None for x in range(GW)])
                                self.net.incoming_attack = 0
                            
                            self.spawn_timer += dt
                            if self.spawn_timer > 9.0: 
                                self.spawn_timer = 0 ; self.enemies.append(ProfessionalEnemy(random.randint(0,9), random.choice(['K','R'])))
                                
                            for en in self.enemies[:]:
                                if en.update(dt, self.grid, self.audio): self.enemies.remove(en)
                                elif en.y > GH + 1: self.enemies.remove(en)
                                elif en.state == 'walking':
                                    for bx, by in self.piece['shape']:
                                        if int(en.x + 0.5) == self.piece_pos[0] + bx and int(en.y + 0.5) == self.piece_pos[1] + by:
                                            self.enemies.remove(en) ; self.stomps += 1 ; self.score += 500 ; self.audio.play('stomp')
                                            self.comms.append(CombatText("STOMP ATTACK! 🚀", (0, 255, 255), 320, 260, self.f_m))
                                            if self.stomps == 1: self.banners.append(AchievementBanner("FIRST BLOOD!", (255, 50, 50), self.f_m))
                                            elif self.stomps % 5 == 0: self.banners.append(AchievementBanner(f"STOMP STREAK: {self.stomps}!", (255, 255, 0), self.f_m))
                                            if 'shell' in self.img: self.bolts.append(BlastProjectile(60+en.x*BS, GRID_Y+en.y*BS, 620, 240, self.img['shell']))
                                            self.audio.play('shell') ; asyncio.create_task(self.net.commit_attack(1)) ; break

                            # Step
                            fall_spd = 0.85
                            if pygame.key.get_pressed()[pygame.K_DOWN]: fall_spd = 0.05
                            self.fall_count += dt
                            if self.fall_count > fall_spd:
                                self.fall_count = 0 ; self.piece_pos[1] += 1
                                if self.hit_test(self.piece_pos, self.piece['shape']):
                                    self.piece_pos[1] -= 1 ; self.audio.play('lock')
                                    cid = self.piece['id'] ; col = ID_TO_COLOR[{'I':'1','O':'2','T':'3','S':'4','Z':'5','J':'6','L':'7'}[cid]]
                                    for bx, by in self.piece['shape']:
                                        if 0 <= self.piece_pos[1]+by < GH: self.grid[self.piece_pos[1]+by][self.piece_pos[0]+bx] = col
                                    self.clearing_rows = [ri for ri, row in enumerate(self.grid) if all(cell is not None for cell in row)]
                                    if self.clearing_rows:
                                        self.audio.play('clear') ; self.score += (len(self.clearing_rows)*1000) ; self.clear_timer = 0.65 ; self.shake = 24
                                        self.banners.append(AchievementBanner(f"COMBO: {len(self.clearing_rows)} LINES!", (0, 255, 255), self.f_m))
                                        asyncio.create_task(self.net.commit_attack(len(self.clearing_rows)))
                                    else:
                                        self.piece_pos = [GW//2-1, 0] ; self.piece = self.pull_piece()
                                        if self.hit_test(self.piece_pos, self.piece['shape']): await self.net.report_defeat()
                elif self.net.state == "gameover":
                    pass

            # Draw
            self.draw_frame()
            await asyncio.sleep(0.01)

    def draw_frame(self):
        off_x = off_y = 0
        if self.shake > 0: off_x, off_y = random.randint(-int(self.shake), int(self.shake)), random.randint(-int(self.shake), int(self.shake))
        
        self.scr.fill((92, 148, 252))
        
        if self.phase == "menu":
            self.draw_t("MARIO BATTLE PRO", self.f_h, (255, 255, 255), WW//2, 200)
            self.draw_t("COMPETITIVE DEPLOYMENT BUILD v1.0", self.f_s, (255, 255, 0), WW//2, 350)
            self.draw_t("PICK ROLE: [1] OR [2]", self.f_m, (255, 255, 255), WW//2, 450)
        else:
            ax, ay = 60 + off_x, GRID_Y + off_y
            pygame.draw.rect(self.scr, (10, 10, 20), (ax-4, ay-4, GW*BS+8, GH*BS+8))
            pygame.draw.rect(self.scr, (255, 255, 255), (ax-4, ay-4, GW*BS+8, GH*BS+8), 2)
            
            if 'ground' in self.img:
                for x in range(GW): self.scr.blit(self.img['ground'], (ax + x*BS, ay + GH*BS))
            
            # GHOST
            if self.phase == "play" and not self.clearing_rows and not self.net.game_over:
                gx, gy = self.piece_pos[0], self.piece_pos[1]
                while not self.hit_test([gx, gy+1], self.piece['shape']): gy += 1
                scol = ID_TO_COLOR[{'I':'1','O':'2','T':'3','S':'4','Z':'5','J':'6','L':'7'}[self.piece['id']]]
                for bx, by in self.piece['shape']:
                    g_surf = pygame.Surface((BS, BS), pygame.SRCALPHA) ; g_surf.fill((*scol, 75))
                    self.scr.blit(g_surf, (ax + (gx+bx)*BS, ay + (gy+by)*BS))

            # GRID
            for y in range(GH):
                if y in self.clearing_rows and int(time.time()*15)%2==0: pygame.draw.rect(self.scr, (255, 255, 255), (ax, ay + y*BS, GW*BS, BS))
                else:
                    for x in range(GW):
                        c = self.grid[y][x]
                        if c: self.draw_3db(ax + x*BS, ay + y*BS, c, BS)
            
            # PIECE
            if not self.clearing_rows and self.phase == "play" and not self.net.game_over:
                scol = ID_TO_COLOR[{'I':'1','O':'2','T':'3','S':'4','Z':'5','J':'6','L':'7'}[self.piece['id']]]
                for bx, by in self.piece['shape']: self.draw_3db(ax + (self.piece_pos[0]+bx)*BS, ay + (self.piece_pos[1]+by)*BS, scol, BS)

            # ENEMIES & FX
            for en in self.enemies:
                ikey = 'koopa' if en.type_id == 'K' else 'red_koopa' ; eimg = self.img[ikey][en.frame]
                if en.dir == 1: eimg = pygame.transform.flip(eimg, True, False)
                y_bob = abs(math.sin(time.time()*10)) * 5 ; self.scr.blit(eimg, (ax + en.x*BS, ay + en.y*BS - eimg.get_height() + BS - y_bob))
            for b in self.bolts: b.draw(self.scr)
            for c in self.comms: c.draw(self.scr)
            for b in self.banners: b.draw(self.scr)

            # HUD
            p_img = self.img['mario' if self.net.role == 'p1' else 'luigi'] if 'mario' in self.img else None
            if p_img: self.scr.blit(p_img, (ax - 52, 5))
            self.draw_t(f"SCORE: {self.score}", self.f_s, (255, 255, 255), ax, 25, False)
            self.draw_t("GOAL: DEFEAT THE RIVAL!", self.f_s, (255, 255, 0), ax, 45, False)
            
            # LIVE PREVIEW
            ox, oy = 620, GRID_Y + 80 ; sbs = 28 ; pygame.draw.rect(self.scr, (5, 5, 15), (ox-4, oy-4, GW*sbs+8, GH*sbs+8))
            for i, cid in enumerate(self.net.opp_grid):
                if cid != '0': self.draw_3db(ox + (i%10)*sbs, oy + (i//10)*sbs, ID_TO_COLOR.get(cid, (100,100,100)), sbs)
            self.draw_t("OPPONENT LIVE", self.f_m, (255, 255, 255), ox, oy-35, False)
            
            # STATE OVERLAYS
            if self.phase == "lobby":
                msg = "READY UP: [ENTER]" if not self.is_ready else "WAITING FOR RIVAL..."
                self.draw_t(msg, self.f_m, (255, 255, 255), WW//2, WH - 60)
            if self.net.state == "countdown":
                sec = 3 - int(time.time() - self.net.countdown_time)
                if sec >= 0: self.draw_t(str(max(1, sec)), self.f_h, (255, 255, 255), WW//2, WH//2)
            if self.net.game_over:
                self.draw_t("MATCH TERMINATED", self.f_h, (255, 255, 255), WW//2, WH//2 - 40)
                if self.net.winner == self.net.role: self.draw_t("VICTORY IS YOURS!", self.f_m, (0, 255, 0), WW//2, WH//2 + 30)
                else: self.draw_t("YOU WERE OVERWHELMED", self.f_m, (255, 0, 0), WW//2, WH//2 + 30)
        
        pygame.display.flip()

    def draw_3db(self, x, y, c, s):
        if c == (140, 140, 140) and 'brick' in self.img:
            self.scr.blit(pygame.transform.scale(self.img['brick'], (s, s)), (x, y)) ; return
        lt, dk = [min(255, ch+75) for ch in c], [max(0, ch-75) for ch in c] ; pygame.draw.rect(self.scr, c, (x, y, s, s))
        pygame.draw.polygon(self.scr, lt, [(x,y),(x+s,y),(x+s-3,y+3),(x+3,y+3)])
        pygame.draw.polygon(self.scr, lt, [(x,y),(x+3,y+3),(x+3,y+s-3),(x,y+s)])
        pygame.draw.polygon(self.scr, dk, [(x+s,y),(x+s,y+s),(x+s-3,y+s-3),(x+s-3,y+3)])
        pygame.draw.polygon(self.scr, dk, [(x,y+s),(x+s,y+s),(x+s-3,y+s-3),(x+3,y+s-3)])

    def draw_t(self, t, f, c, x, y, ct=True):
        if not f: return
        r = f.render(t, True, c)
        if ct: rr = r.get_rect(center=(x, y))
        else: rr = r.get_rect(topleft=(x, y))
        self.scr.blit(r, rr)

if __name__ == "__main__":
    try: asyncio.run(MarioBattlePro().main_loop())
    except:
        with open(f"deploy_crash_{PID}.txt", "w") as f: f.write(traceback.format_exc())
        input("CRASH")
