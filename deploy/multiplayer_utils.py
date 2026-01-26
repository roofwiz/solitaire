
import asyncio
from src.firebase_manager import FirebaseManager
from src.config import FIREBASE_DB_URL

async def async_join_battle(game, room_id, PopupText, C_GREEN, C_RED, WINDOW_WIDTH, WINDOW_HEIGHT):
    try:
        game.firebase_manager = FirebaseManager(FIREBASE_DB_URL)
        role = await game.firebase_manager.join_room(room_id)
        if role:
            game.reset_game()
            game.game_state = 'BATTLE'
            game.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, f"JOINED AS {role.upper()}", C_GREEN))
        else:
            game.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, "CONNECTION FAILED", C_RED))
    except Exception as e:
        print(f"Async Join Error: {e}")
        game.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, "JOIN ERROR", C_RED))

def start_async_join(game, room_id, PopupText, C_GREEN, C_RED, WINDOW_WIDTH, WINDOW_HEIGHT):
    asyncio.create_task(async_join_battle(game, room_id, PopupText, C_GREEN, C_RED, WINDOW_WIDTH, WINDOW_HEIGHT))
