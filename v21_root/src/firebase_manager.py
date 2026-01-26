
import json
import time
import asyncio
import sys
from src.config import *

class FirebaseManager:
    """
    Handles communication with Firebase Realtime Database for Battle Mode.
    Async version for Pygbag/Browser compatibility.
    """
    
    def __init__(self, db_url):
        self.db_url = db_url.rstrip('/')
        self.room_id = None
        self.player_slot = None # 'p1' or 'p2'
        self.opponent_slot = None
        self.connected = False
        
        self.state = 'idle'
        self.wins = 0
        self.opponent_wins = 0
        self.attack_queue = 0 
        self.lines_received_total = 0 
        self.pending_garbage = 0 
        
        self.last_poll_time = 0
        self.poll_interval = 0.8
        
        self.remote_state = "waiting"
        self.opponent_status = "offline"

    async def _fetch(self, url, method="GET", data=None):
        """Web-optimized fetch using Pygbag asyncio bridge"""
        try:
            if sys.platform == 'emscripten':
                # Use Pygbag's async wrapper or direct js fetch if needed
                import platform
                options = {"method": method}
                if data:
                    options["body"] = json.dumps(data)
                    options["headers"] = {"Content-Type": "application/json"}
                
                # In pygbag, platform.window.fetch returns a promise
                # but we usually use the 'embed' module helper if it exists
                # Fallback to direct js if needed
                try:
                    import embed
                    resp = await embed.fetch(url, options)
                    return json.loads(resp)
                except:
                    # Direct JS call if embed fails
                    from platform import window
                    promise = window.fetch(url, window.JSON.parse(json.dumps(options)))
                    response = await promise
                    text = await response.text()
                    return json.loads(text)
            else:
                import requests
                if method == "GET":
                    return requests.get(url).json()
                elif method == "PUT":
                    return requests.put(url, json=data).json()
                elif method == "PATCH":
                    return requests.patch(url, json=data).json()
        except Exception as e:
            print(f"[Firebase] Fetch Error: {e}")
            return None

    async def join_room(self, room_id):
        self.room_id = room_id
        url = f"{self.db_url}/battles/{self.room_id}.json"
        
        try:
            print(f"[Firebase] Connecting to {room_id}...")
            data = await self._fetch(url)
            
            curr_time = time.time()
            if not data or (data.get('last_update', 0) and curr_time - data['last_update'] > 3600):
                self.player_slot = 'p1'
                self.opponent_slot = 'p2'
                init_data = {
                    "state": "waiting",
                    "p1": {"status": "alive", "wins": 0, "attack_queue": 0},
                    "p2": {"status": "offline", "wins": 0, "attack_queue": 0},
                    "last_update": curr_time
                }
                await self._fetch(url, "PUT", init_data)
                self.connected = True
                return 'p1'
            else:
                p1_status = data.get('p1', {}).get('status', 'offline')
                p2_status = data.get('p2', {}).get('status', 'offline')
                
                if p2_status == 'offline':
                    self.player_slot = 'p2'
                    self.opponent_slot = 'p1'
                    await self._fetch(f"{self.db_url}/battles/{self.room_id}/p2.json", "PATCH", 
                                   {"status": "alive", "wins": 0, "attack_queue": 0})
                    if p1_status == 'alive':
                         await self._fetch(f"{self.db_url}/battles/{self.room_id}.json", "PATCH", {"state": "playing"})
                    self.connected = True
                    return 'p2'
                elif p1_status == 'offline':
                    self.player_slot = 'p1'
                    self.opponent_slot = 'p2'
                    await self._fetch(f"{self.db_url}/battles/{self.room_id}/p1.json", "PATCH", 
                                   {"status": "alive", "wins": 0, "attack_queue": 0})
                    self.connected = True
                    return 'p1'
                return None
        except Exception as e:
            print(f"[Firebase] Join Error: {e}")
            return None

    async def send_attack(self, lines):
        if not self.connected: return
        self.attack_queue += lines
        await self._fetch(f"{self.db_url}/battles/{self.room_id}/{self.player_slot}.json", "PATCH", 
                        {"attack_queue": self.attack_queue})

    async def report_loss(self):
        if not self.connected: return
        await self._fetch(f"{self.db_url}/battles/{self.room_id}/{self.player_slot}.json", "PATCH", {"status": "dead"})

    async def report_win(self):
        if not self.connected: return
        self.wins += 1
        await self._fetch(f"{self.db_url}/battles/{self.room_id}/{self.player_slot}.json", "PATCH", 
                        {"wins": self.wins, "status": "alive"})

    async def poll(self):
        if not self.connected: return
        
        curr_time = time.time()
        if curr_time - self.last_poll_time < self.poll_interval:
            return
            
        self.last_poll_time = curr_time
        data = await self._fetch(f"{self.db_url}/battles/{self.room_id}.json")
        if not data: return
        
        self.remote_state = data.get('state', 'waiting')
        opp_data = data.get(self.opponent_slot, {})
        self.opponent_status = opp_data.get('status', 'offline')
        
        remote_attacks = opp_data.get('attack_queue', 0)
        if remote_attacks > self.lines_received_total:
            diff = remote_attacks - self.lines_received_total
            if 0 < diff < 100: 
                self.pending_garbage += diff
            self.lines_received_total = remote_attacks
        
        self.opponent_wins = opp_data.get('wins', 0)
        if self.player_slot == 'p1':
             await self._fetch(f"{self.db_url}/battles/{self.room_id}.json", "PATCH", {"last_update": time.time()})
