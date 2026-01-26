
import os
import re

main_path = r'c:\Users\eric\React Projects\Mario-Tetris-main\main.py'
with open(main_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Join call patch (REDUX)
# Target the specific role assignment block
join_pattern = r'(elif self\.btn_battle_rect\.collidepoint\(mouse_pos\):.*?)self\.firebase_manager = FirebaseManager\(FIREBASE_DB_URL\)\s+role = self\.firebase_manager\.join_room\(room_id\)\s+if role:.*?(\s+else:.*?self\.popups\.append\(PopupText\(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, "CONNECTION FAILED", C_RED\)\))'

new_join = r'\1start_async_join(self, room_id, PopupText, C_GREEN, (255, 0, 0), WINDOW_WIDTH, WINDOW_HEIGHT)'

# Alternative Join Pattern (simpler)
if "role = self.firebase_manager.join_room(room_id)" in content:
    print("Found join call. Patching...")
    # Replace the block from firebase_manager = ... down to the end of the if role: block
    block_pattern = r'self\.firebase_manager = FirebaseManager\(FIREBASE_DB_URL\)\s+role = self\.firebase_manager\.join_room\(room_id\)\s+if role:.*?self\.popups\.append\(PopupText\(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, "CONNECTION FAILED", C_RED\)\)'
    content = re.sub(block_pattern, 'start_async_join(self, room_id, PopupText, C_GREEN, (255, 0, 0), WINDOW_WIDTH, WINDOW_HEIGHT)', content, flags=re.DOTALL)
else:
    print("Join call NOT found.")

# 2. Main Loop Polling patch (REDUX)
# Target the self.update(dt) call in the loop
loop_pattern = r'(if self\.game_state == \'PLAYING\':.*?self\.update\(dt\))'
if "if self.game_state == 'PLAYING':" in content:
    print("Found main loop. Patching...")
    # Find the specific run of code that includes mobile actions and ends with update(dt)
    # We want to insert the poll BEFORE self.update(dt) or after it
    # Let's insert it before the self.update(dt) that is inside the loop
    
    # We look for the last await asyncio.sleep(0) and go back
    poll_code = """
                if self.game_state == 'BATTLE' and hasattr(self, 'firebase_manager'):
                    await self.firebase_manager.poll()
                
                self.update(dt)"""
                
    content = content.replace("self.update(dt)", poll_code)
    print("Main loop poll added.")
else:
    print("Main loop NOT found.")

with open(main_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Done.")
