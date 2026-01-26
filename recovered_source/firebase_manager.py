
import requests
import json
import time
import threading
import random
from src.config import *

class FirebaseManager:
    """
    Handles communication with Firebase Realtime Database for Battle Mode.
    
    Database Structure:
    /battles/[room_id]/
        state: "waiting", "playing", "finished"
        p1: { status: "alive", wins: 0, attack_queue: 0 }
        p2: { status: "alive", wins: 0, attack_queue: 0 }
        last_update: timestamp
    """
    
    def __init__(self, db_url):
        self.db_url = db_url.rstrip('/')
        self.room_id = None
        self.player_slot = None # 'p1' or 'p2'
        self.opponent_slot = None
        self.session = requests.Session()
        self.connected = False
        
        self.state = 'idle'
        self.wins = 0
        self.opponent_wins = 0
        self.attack_queue = 0 # Outgoing attacks we want to send (Total count)
        self.lines_received_total = 0 # Total lines we have processed from opponent
        self.pending_garbage = 0 # Incoming garbage we need to process this frame
        
        self.last_poll_time = 0
        self.poll_interval = 0.5 # 500ms
        
        # State tracking
        self.remote_state = "waiting"
        self.opponent_status = "offline"
        
    def join_room(self, room_id):
        self.room_id = room_id
        url = f"{self.db_url}/battles/{self.room_id}.json"
        
        try:
            # Check if room exists
            print(f"[Firebase] Connecting to {url}...")
            resp = self.session.get(url)
            data = resp.json()
            
            curr_time = time.time()
            
            # Logic: If room empty or stale (> 1 hour old), Reset it
            is_stale = False
            if data and 'last_update' in data:
                if curr_time - data['last_update'] > 3600:
                    is_stale = True
                    
            if not data or is_stale:
                # Create Room -> P1
                self.player_slot = 'p1'
                self.opponent_slot = 'p2'
                init_data = {
                    "state": "waiting",
                    "p1": {"status": "alive", "wins": 0, "attack_queue": 0},
                    "p2": {"status": "offline", "wins": 0, "attack_queue": 0},
                    "last_update": curr_time
                }
                self.session.put(url, json=init_data)
                print(f"[Firebase] Created room {room_id} as P1")
                self.connected = True
                return 'p1'
            else:
                # Room exists. Try to find a slot.
                p1_status = data.get('p1', {}).get('status', 'offline')
                p2_status = data.get('p2', {}).get('status', 'offline')
                
                # Check for stale player (Assume offline if no update/heartbeat, but strictly we use status)
                # For simplicity, if status is 'offline', we take it.
                
                if p2_status == 'offline':
                    self.player_slot = 'p2'
                    self.opponent_slot = 'p1'
                    
                    # Update P2 status
                    self.session.patch(f"{self.db_url}/battles/{self.room_id}/p2.json", 
                                     json={"status": "alive", "wins": 0, "attack_queue": 0})
                                     
                    # If P1 is alive, set game to playing!
                    if p1_status == 'alive':
                         self.session.patch(f"{self.db_url}/battles/{self.room_id}.json", json={"state": "playing"})
                         self.remote_state = "playing"
                    
                    print(f"[Firebase] Joined room {room_id} as P2")
                    self.connected = True
                    return 'p2'
                    
                elif p1_status == 'offline':
                    self.player_slot = 'p1'
                    self.opponent_slot = 'p2'
                    
                    self.session.patch(f"{self.db_url}/battles/{self.room_id}/p1.json", 
                                     json={"status": "alive", "wins": 0, "attack_queue": 0})
                    
                    if p2_status == 'alive':
                         self.session.patch(f"{self.db_url}/battles/{self.room_id}.json", json={"state": "playing"})
                         self.remote_state = "playing"

                    print(f"[Firebase] Re-joined room {room_id} as P1")
                    self.connected = True
                    return 'p1'
                else:
                    print("[Firebase] Room is full!")
                    return None
                    
        except Exception as e:
            print(f"[Firebase] Connection Join Error: {e}")
            return None

    def reset_room_state(self):
        """Reset game state for new round but keep players connected"""
        if not self.connected: return
        # Set self to alive
        try:
             url = f"{self.db_url}/battles/{self.room_id}/{self.player_slot}.json"
             self.session.patch(url, json={"status": "alive", "attack_queue": 0})
             # Reset local
             self.attack_queue = 0
             self.pending_garbage = 0
        except: pass

    def send_attack(self, lines):
        """Increment our attack count in DB"""
        if not self.connected or not self.room_id: return
        
        self.attack_queue += lines
        
        # Non-blocking patch
        def _update():
            try:
                url = f"{self.db_url}/battles/{self.room_id}/{self.player_slot}.json"
                self.session.patch(url, json={"attack_queue": self.attack_queue})
            except: pass
        
        threading.Thread(target=_update).start()
        
    def report_loss(self):
        """Report that we lost this round"""
        if not self.connected: return
        try:
            url = f"{self.db_url}/battles/{self.room_id}/{self.player_slot}.json"
            self.session.patch(url, json={"status": "dead"})
        except: pass

    def report_win(self):
         """We update our win count locally and allow next round"""
         self.wins += 1
         try:
            url = f"{self.db_url}/battles/{self.room_id}/{self.player_slot}.json"
            self.session.patch(url, json={"wins": self.wins, "status": "alive"})
         except: pass

    def poll(self):
        """Called every frame, but only executes every poll_interval"""
        if not self.connected: return
        
        curr_time = time.time()
        if curr_time - self.last_poll_time < self.poll_interval:
            return
            
        self.last_poll_time = curr_time
        
        def _fetch():
            try:
                resp = self.session.get(f"{self.db_url}/battles/{self.room_id}.json")
                data = resp.json()
                if not data: return
                
                # 1. Check Game State
                self.remote_state = data.get('state', 'waiting')
                
                # 2. Check Opponent
                opp_data = data.get(self.opponent_slot, {})
                opp_status = opp_data.get('status', 'offline')
                self.opponent_status = opp_status # UPDATE PUBLIC STATUS
                
                # Check for incoming attacks
                # Opponent's "attack_queue" total
                remote_attacks = opp_data.get('attack_queue', 0)
                
                # If remote > lines_received_total, we have NEW trash
                if remote_attacks > self.lines_received_total:
                    diff = remote_attacks - self.lines_received_total
                    # Only accept positive diffs (resets don't kill us)
                    if diff > 0 and diff < 100: 
                        self.pending_garbage += diff # Main thread will consume this
                        print(f"[Firebase] Receiving {diff} garbage lines!")
                    self.lines_received_total = remote_attacks
                
                self.opponent_wins = opp_data.get('wins', 0)
                
                # Keep Alive / Heartbeat (Update last_update)
                # Only P1 updates timestamp to reduce writes? Or whoever.
                if self.player_slot == 'p1':
                     self.session.patch(f"{self.db_url}/battles/{self.room_id}.json", json={"last_update": time.time()})
                     
            except Exception as e:
                print(f"[Firebase] Poll Error: {e}")

        threading.Thread(target=_fetch).start()
