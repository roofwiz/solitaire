
import pygame
import random
import json
import asyncio
import math
import sys
import os
import time

# --- STANDALONE FIREBASE MANAGER ---
class FirebaseManager:
    def __init__(self, db_url):
        self.db_url = db_url.rstrip('/')
        self.room_id = None
        self.player_slot = None
        self.opponent_slot = None
        self.connected = False
        self.attack_queue = 0 
        self.lines_received_total = 0 
        self.pending_garbage = 0 
        self.last_poll_time = 0
        self.poll_interval = 0.8
        self.opponent_status = "offline"

    async def _fetch(self, url, method="GET", data=None):
        try:
            import requests # Explicit local use
            if method == "GET": return requests.get(url).json()
            elif method == "PUT": return requests.put(url, json=data).json()
            elif method == "PATCH": return requests.patch(url, json=data).json()
        except: return None

    async def join_room(self, room_id):
        self.room_id = room_id
        url = f"{self.db_url}/battles/{self.room_id}.json"
        data = await self._fetch(url)
        curr_time = time.time()
        if not data or (data.get('last_update', 0) and curr_time - data['last_update'] > 3600):
            self.player_slot, self.opponent_slot = 'p1', 'p2'
            await self._fetch(url, "PUT", {"state": "waiting", "p1": {"status": "alive", "attack_queue": 0}, "p2": {"status": "offline", "attack_queue": 0}, "last_update": curr_time})
            self.connected = True
            return 'p1'
        else:
            if data.get('p2', {}).get('status', 'offline') == 'offline':
                self.player_slot, self.opponent_slot = 'p2', 'p1'
                await self._fetch(f"{self.db_url}/battles/{self.room_id}/p2.json", "PATCH", {"status": "alive", "attack_queue": 0})
                await self._fetch(f"{self.db_url}/battles/{self.room_id}.json", "PATCH", {"state": "playing"})
                self.connected = True
                return 'p2'
            return None

    async def poll(self):
        if not self.connected: return
        if time.time() - self.last_poll_time < self.poll_interval: return
        self.last_poll_time = time.time()
        data = await self._fetch(f"{self.db_url}/battles/{self.room_id}.json")
        if not data: return
        opp_data = data.get(self.opponent_slot, {})
        self.opponent_status = opp_data.get('status', 'offline')
        remote_attacks = opp_data.get('attack_queue', 0)
        if remote_attacks > self.lines_received_total:
            self.pending_garbage += (remote_attacks - self.lines_received_total)
            self.lines_received_total = remote_attacks
        if self.player_slot == 'p1': await self._fetch(f"{self.db_url}/battles/{self.room_id}.json", "PATCH", {"last_update": time.time()})

    async def send_attack(self, lines):
        if not self.connected: return
        self.attack_queue += lines
        await self._fetch(f"{self.db_url}/battles/{self.room_id}/{self.player_slot}.json", "PATCH", {"attack_queue": self.attack_queue})

# --- GAME ENGINE ---
WINDOW_WIDTH, WINDOW_HEIGHT = 1000, 700
GRID_WIDTH, GRID_HEIGHT = 10, 20
BLOCK_SIZE = 30
PLAYFIELD_X, PLAYFIELD_Y = 50, 50
C_BLACK, C_GRID_BG, C_WHITE, C_RED, C_GREEN = (10,10,10), (30,30,50), (240,240,240), (255,50,50), (50,255,50)

class Tetris:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Mario Tetris V23 - STANDALONE BATTLE")
        self.clock = pygame.time.Clock()
        self.grid = [[None for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.bag = []
        self.current_pos = [GRID_WIDTH//2-1, 0]
        self.current_shape = self.get_new_piece()
        self.opponent_grid = [[None for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.firebase = FirebaseManager("https://mario-tetris-game-default-rtdb.firebaseio.com/")
        self.role = None
        self.fall_time = 0
        self.popups = []
        self.font = pygame.font.SysFont("Arial", 22)

    def get_new_piece(self):
        if not self.bag: self.bag = list("IOTSLJZ"); random.shuffle(self.bag)
        s = self.bag.pop()
        shapes = {'I': [[(0,0),(1,0),(2,0),(3,0)],(0,255,255)], 'O': [[(0,0),(1,0),(0,1),(1,1)],(255,255,0)], 'T': [[(1,0),(0,1),(1,1),(2,1)],(128,0,128)], 'S': [[(1,0),(2,0),(0,1),(1,1)],(0,255,0)], 'Z': [[(0,0),(1,0),(1,1),(2,1)],(255,0,0)], 'J': [[(0,0),(0,1),(1,1),(2,1)],(0,0,255)], 'L': [[(2,0),(0,1),(1,1),(2,1)],(255,165,0)]}
        return shapes[s]

    def check_collision(self, pos, shape):
        for bx, by in shape[0]:
            gx, gy = pos[0]+bx, pos[1]+by
            if gx<0 or gx>=GRID_WIDTH or gy>=GRID_HEIGHT or (gy>=0 and self.grid[gy][gx]): return True
        return False

    async def run(self):
        self.role = await self.firebase.join_room("battle_v23")
        while True:
            dt = self.clock.tick(60)/1000.0
            for e in pygame.event.get():
                if e.type == pygame.QUIT: return
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_LEFT: 
                        self.current_pos[0]-=1
                        if self.check_collision(self.current_pos, self.current_shape): self.current_pos[0]+=1
                    if e.key == pygame.K_RIGHT: 
                        self.current_pos[0]+=1
                        if self.check_collision(self.current_pos, self.current_shape): self.current_pos[0]-=1
                    if e.key == pygame.K_UP:
                        old = self.current_shape[0]
                        self.current_shape[0] = [(-by, bx) for bx, by in old]
                        if self.check_collision(self.current_pos, self.current_shape): self.current_shape[0] = old

            await self.firebase.poll()
            if self.firebase.pending_garbage > 0:
                for _ in range(self.firebase.pending_garbage):
                    self.grid.pop(0); row = [(100,100,100) for _ in range(GRID_WIDTH)]; row[random.randint(0,9)] = None; self.grid.append(row)
                self.firebase.pending_garbage = 0

            self.fall_time += dt
            if self.fall_time > 0.5:
                self.fall_time = 0; self.current_pos[1]+=1
                if self.check_collision(self.current_pos, self.current_shape):
                    self.current_pos[1]-=1
                    for bx, by in self.current_shape[0]:
                        if self.current_pos[1]+by >= 0: self.grid[self.current_pos[1]+by][self.current_pos[0]+bx] = self.current_shape[1]
                    cleared = 0; new_grid = [r for r in self.grid if any(c is None for c in r)]
                    cleared = GRID_HEIGHT - len(new_grid)
                    for _ in range(cleared): new_grid.insert(0, [None]*GRID_WIDTH)
                    self.grid = new_grid
                    if cleared > 0: await self.firebase.send_attack(cleared)
                    self.current_pos = [GRID_WIDTH//2-1, 0]; self.current_shape = self.get_new_piece()
                    if self.check_collision(self.current_pos, self.current_shape): self.grid = [[None]*GRID_WIDTH]*GRID_HEIGHT # Reset

            self.draw(); await asyncio.sleep(0)

    def draw(self):
        self.screen.fill(C_BLACK)
        pygame.draw.rect(self.screen, C_GRID_BG, (PLAYFIELD_X, PLAYFIELD_Y, GRID_WIDTH*BLOCK_SIZE, GRID_HEIGHT*BLOCK_SIZE))
        for y, r in enumerate(self.grid):
            for x, c in enumerate(r):
                if c: pygame.draw.rect(self.screen, c, (PLAYFIELD_X+x*BLOCK_SIZE, PLAYFIELD_Y+y*BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE)); pygame.draw.rect(self.screen, C_WHITE, (PLAYFIELD_X+x*BLOCK_SIZE, PLAYFIELD_Y+y*BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE), 1)
        for bx, by in self.current_shape[0]:
            pygame.draw.rect(self.screen, self.current_shape[1], (PLAYFIELD_X+(self.current_pos[0]+bx)*BLOCK_SIZE, PLAYFIELD_Y+(self.current_pos[1]+by)*BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE)); pygame.draw.rect(self.screen, C_WHITE, (PLAYFIELD_X+(self.current_pos[0]+bx)*BLOCK_SIZE, PLAYFIELD_Y+(self.current_pos[1]+by)*BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE), 1)
        self.screen.blit(self.font.render(f"ROLE: {self.role}", True, C_WHITE), (10, 10))
        self.screen.blit(self.font.render(f"OPPONENT: {self.firebase.opponent_status}", True, C_GREEN if self.firebase.opponent_status=='alive' else C_RED), (10, 40))
        pygame.display.flip()

if __name__ == "__main__":
    try:
        Tetris_game = Tetris(); asyncio.run(Tetris_game.run())
    except Exception:
        import traceback; traceback.print_exc(); input("CRASH! Press Enter to exit...")
