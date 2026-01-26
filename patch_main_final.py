
import os

def patch_file(path):
    if not os.path.exists(path):
        print(f"Path not found: {path}")
        return
    
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Join call patch - very specific from view_file output
    old_call = """                        # Connect and Start
                        self.firebase_manager = FirebaseManager(FIREBASE_DB_URL)
                        role = self.firebase_manager.join_room(room_id)
                        
                        if role:
                            self.reset_game()
                            self.game_state = 'BATTLE'
                            self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, f"JOINED AS {role.upper()}", C_GREEN))
                        else:
                            self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, "CONNECTION FAILED", C_RED))"""

    new_call = """                        # Async Connect
                        from multiplayer_utils import start_async_join
                        start_async_join(self, room_id, PopupText, C_GREEN, (255, 0, 0), WINDOW_WIDTH, WINDOW_HEIGHT)"""

    if old_call in content:
        content = content.replace(old_call, new_call)
        print(f"Join call patched in {path}")
    else:
        # Fuzzy match for just the connection lines
        old_mini = "role = self.firebase_manager.join_room(room_id)"
        if old_mini in content:
             content = content.replace(old_mini, "pass # await self.firebase_manager.join_room(room_id)")
             print(f"Fuzzy join patch in {path}")

    # 2. Main loop patch (if not already done)
    # We look for the common pattern of mobile actions
    old_loop_tail = """                        if das_action:
                            self._process_mobile_action(das_action)

                self.update(dt)"""
    
    # We want to insert the poll
    if "await self.firebase_manager.poll()" not in content:
        new_loop_tail = """                        if das_action:
                            self._process_mobile_action(das_action)

                if self.game_state == 'BATTLE' and hasattr(self, 'firebase_manager'):
                    await self.firebase_manager.poll()

                self.update(dt)"""
        if old_loop_tail in content:
            content = content.replace(old_loop_tail, new_loop_tail)
            print(f"Main loop patched in {path}")

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

patch_file(r'main.py')
patch_file(r'staging\main.py')
print("Done.")
