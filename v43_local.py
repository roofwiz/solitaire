
import pygame
import random
import json
import asyncio
import sys
import os
import time
import traceback
import urllib.request

# --- V43 THE "SECOND WINDOW" FIX ---
PID = os.getpid()
LOG_FILE = f"v43_launch_{PID}.log"

def log(msg):
    try:
        ts = time.strftime('%H:%M:%S')
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
            f.flush()
    except: pass
    print(f"[PID {PID}] {msg}")

log("Process started successfully.")

class FirebaseManagerV43:
    def __init__(self, db_url):
        self.db_url = db_url.rstrip('/')
        self.room_id = "battle_v43"
        self.role = None 
        self.connected = False
        self.p1_ready = False
        self.p2_ready = False
        self.room_state = "waiting"
        self.countdown_start = 0

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
        log(f"Attempting role {role}")
        self.role = role
        url = f"{self.db_url}/battles/{self.room_id}.json"
        if role == "p1":
            d = {"state":"waiting", "p1":{"ready":False}, "p2":{"ready":False, "status":"offline"}, "last_update":time.time(), "countdown_start":0}
            await asyncio.to_thread(self._req, url, "PUT", d)
        else:
            await asyncio.to_thread(self._req, f"{self.db_url}/battles/{self.room_id}/p2.json", "PATCH", {"status":"alive"})
        self.connected = True

    async def poll(self):
        if not self.connected: return
        data = await asyncio.to_thread(self._req, f"{self.db_url}/battles/{self.room_id}.json")
        if data:
            self.room_state = data.get('state', 'waiting')
            self.countdown_start = data.get('countdown_start', 0)
            self.p1_ready = data.get('p1', {}).get('ready', False)
            self.p2_ready = data.get('p2', {}).get('ready', False)

WW, WH = 900, 600
GW, GH = 10, 20
BS = 26

class TetrisV43:
    def __init__(self):
        log("Init Pygame (No Mixer)")
        pygame.init()
        try: pygame.mixer.quit()
        except: pass
        self.screen = pygame.display.set_mode((WW, WH))
        pygame.display.set_caption(f"MARIO TETRIS V43 - PID:{PID}")
        self.clock = pygame.time.Clock()
        self.fb = FirebaseManagerV43("https://mario-tetris-game-default-rtdb.firebaseio.com/")
        self.mode = "menu" # menu, lobby, play
        self.font = pygame.font.SysFont("Arial", 24)

    async def run(self):
        log("Run loop starting.")
        while True:
            dt = self.clock.tick(60)/1000.0
            for e in pygame.event.get():
                if e.type == pygame.QUIT: return
                if e.type == pygame.KEYDOWN:
                    if self.mode == "menu":
                        if e.key == pygame.K_1: await self.fb.pick("p1"); self.mode = "lobby"
                        if e.key == pygame.K_2: await self.fb.pick("p2"); self.mode = "lobby"
                        if e.key == pygame.K_SPACE: # SPAWN SECOND ONE
                            log("Spawning sibling...")
                            os.startfile(sys.executable, arguments=f' "{__file__}"')
                    elif self.mode == "lobby" and e.key == pygame.K_RETURN:
                        r = not (self.fb.p1_ready if self.fb.role=="p1" else self.fb.p2_ready)
                        await asyncio.to_thread(self.fb._req, f"{self.fb.db_url}/battles/{self.fb.room_id}/{self.fb.role}.json", "PATCH", {"ready": r})

            if self.mode != "menu":
                await self.fb.poll()
                if self.fb.p1_ready and self.fb.p2_ready and self.fb.role == "p1" and self.fb.room_state == "waiting":
                    await asyncio.to_thread(self.fb._req, f"{self.fb.db_url}/battles/{self.fb.room_id}.json", "PATCH", {"state":"countdown", "countdown_start":time.time()})
                if self.fb.room_state == "countdown" and time.time() - self.fb.countdown_start > 3:
                     self.mode = "play" # Simpified transition

            self.draw()
            await asyncio.sleep(0.01)

    def draw(self):
        self.screen.fill((20, 20, 30))
        if self.mode == "menu":
            self.screen.blit(self.font.render("V43 - MULTIPlayer TEST", True, (255,255,255)), (100, 100))
            self.screen.blit(self.font.render("Press [1] for P1, [2] for P2", True, (255,255,0)), (100, 150))
            self.screen.blit(self.font.render("Press [SPACE] to open 2nd window!", True, (0,255,255)), (100, 200))
        else:
            self.screen.blit(self.font.render(f"I AM: {self.fb.role}", True, (255,255,255)), (50, 50))
            self.screen.blit(self.font.render(f"P1: {'READY' if self.fb.p1_ready else 'WAIT'}", True, (255,255,255)), (50, 100))
            self.screen.blit(self.font.render(f"P2: {'READY' if self.fb.p2_ready else 'WAIT'}", True, (255,255,255)), (50, 150))
            if self.fb.room_state == "countdown":
                self.screen.blit(self.font.render("COUNTDOWN STARTING...", True, (255,0,0)), (100, 300))
        pygame.display.flip()

if __name__ == "__main__":
    try: asyncio.run(TetrisV43().run())
    except Exception as e:
        with open(f"v43_crash_{PID}.log", "w") as f: f.write(traceback.format_exc())
        input("CRASH")
