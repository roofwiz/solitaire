
import pygame
import random
import json
import asyncio
import sys
import os
import time

# --- LOGGING ---
def log(msg):
    with open("v26_debug.txt", "a") as f:
        f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    print(f"[V26] {msg}")

with open("v26_debug.txt", "w") as f: f.write("--- V26 LOG ---\n")

# --- STANDALONE FIREBASE ---
class FirebaseManager:
    def __init__(self):
        self.db_url = "https://mario-tetris-game-default-rtdb.firebaseio.com/"
        self.connected = False
        self.role = "IDLE"
        self.opp_status = "unknown"
        self.pending_garbage = 0
        self.last_poll = 0

    async def join(self):
        try:
            import requests
            log("Joining room battle_v26...")
            r = requests.get(f"{self.db_url}/battles/battle_v26.json", timeout=10)
            data = r.json()
            curr_time = time.time()
            if not data or (data.get('last_update',0) and curr_time - data['last_update'] > 3600):
                requests.put(f"{self.db_url}/battles/battle_v26.json", json={"p1":{"status":"alive"}, "p2":{"status":"offline"}, "last_update":curr_time}, timeout=5)
                self.role, self.slot, self.opp_slot = "P1", "p1", "p2"
            else:
                requests.patch(f"{self.db_url}/battles/battle_v26/p2.json", json={"status":"alive"}, timeout=5)
                self.role, self.slot, self.opp_slot = "P2", "p2", "p1"
            self.connected = True
            log(f"Joined as {self.role}")
            return self.role
        except Exception as e:
            log(f"Join error: {e}")
            return f"ERR: {str(e)[:20]}"

    async def poll(self):
        if not self.connected: return
        if time.time() - self.last_poll < 1.0: return
        self.last_poll = time.time()
        try:
            import requests
            r = requests.get(f"{self.db_url}/battles/battle_v26.json", timeout=3)
            data = r.json()
            self.opp_status = data.get(self.opp_slot, {}).get('status', 'offline')
        except: pass

# --- THE GAME ---
class BattleGame:
    def __init__(self):
        log("Init Pygame...")
        pygame.init()
        self.screen = pygame.display.set_mode((800, 600))
        pygame.display.set_caption("MARIO TETRIS V26 - LOCAL TEST")
        self.font = pygame.font.SysFont("Arial", 24)
        self.fb = FirebaseManager()
        self.status = "READY"
        self.connecting = False

    async def run(self):
        log("Run start.")
        while True:
            self.screen.fill((20, 20, 40))
            
            for e in pygame.event.get():
                if e.type == pygame.QUIT: return
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_RETURN and not self.fb.connected and not self.connecting:
                        self.connecting = True
                        self.status = "CONNECTING..."
                        log("User triggered connection.")
                        asyncio.create_task(self.connect_flow())
            
            # Draw UI
            self.screen.blit(self.font.render("MARIO TETRIS V26 - LOCAL DIAGNOSTIC", True, (255,255,255)), (50, 50))
            self.screen.blit(self.font.render(f"STATUS: {self.status}", True, (255, 255, 0)), (50, 100))
            
            if not self.fb.connected:
                self.screen.blit(self.font.render(">> PRESS ENTER TO CONNECT TO FIREBASE <<", True, (0, 255, 0)), (50, 200))
                self.screen.blit(self.font.render("(This proves your graphics/pygame works)", True, (150, 150, 150)), (50, 240))
            else:
                self.screen.blit(self.font.render(f"YOUR ROLE: {self.fb.role}", True, (255, 255, 255)), (50, 200))
                self.screen.blit(self.font.render(f"OPPONENT: {self.fb.opp_status}", True, (0, 255, 0)), (50, 240))
                self.screen.blit(self.font.render("Connection Successful! Controls: Arrows", True, (100, 200, 255)), (50, 300))
                await self.fb.poll()

            pygame.display.flip()
            await asyncio.sleep(0.02)

    async def connect_flow(self):
        res = await self.fb.join()
        self.status = f"JOINED: {res}"
        self.connecting = False

if __name__ == "__main__":
    try:
        game = BattleGame()
        asyncio.run(game.run())
    except Exception as e:
        log(f"TOP LEVEL CRASH: {e}")
        with open("v26_crash.txt", "w") as f: f.write(str(e))
        print(f"CRASH: {e}")
        input("Press Enter...")
