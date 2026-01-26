import pygame

# --- Constants & Settings ---
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 800 # Increased to fit 32px blocks
PLAYFIELD_WIDTH = 320  # 10 blocks * 32px
PLAYFIELD_HEIGHT = 640 # 20 blocks * 32px
BLOCK_SIZE = 32
GRID_WIDTH = 10
GRID_HEIGHT = 20

# UI Layout
PLAYFIELD_X = (WINDOW_WIDTH - PLAYFIELD_WIDTH) // 2
PLAYFIELD_Y = 80 # Raised slightly

# Game Speeds
DAS_DELAY = 0.2     # Initial delay before auto-shift
DAS_REPEAT = 0.05   # Speed of auto-shift (snappier controls)
LOCK_DELAY = 0.5    # Time before piece locks

# --- Colors ---
C_BLACK = (0, 0, 0)
C_WHITE = (255, 255, 255)
C_RED = (255, 50, 50)
C_GREEN = (50, 200, 50)
C_BLUE = (50, 50, 255)
C_YELLOW = (255, 255, 0)
C_ORANGE = (255, 165, 0)
C_NEON_PINK = (255, 20, 147)
C_GOLD = (255, 215, 0)
C_GHOST = (255, 255, 255, 30) # Ghost piece alpha

# --- World Themes (Production Polish) ---
# Format: (Background Color, Block Palette Hint, Music Track)
WORLD_THEMES = {
    1: {'bg': (92, 148, 252), 'name': 'Overworld', 'music': 'music.mp3'},    # Classic Blue
    2: {'bg': (0, 0, 0),      'name': 'Underground', 'music': '02. undergroundtheme.mp3'},     # Pitch Black
    3: {'bg': (32, 56, 236),  'name': 'Water',       'music': 'music.mp3'},    # Deep Blue
    4: {'bg': (0, 0, 0),      'name': 'Castle',      'music': 'music.mp3'},    # Boss Level Black
    5: {'bg': (252, 216, 168),'name': 'Snow',        'music': 'music.mp3'},    # Pinkish/Snow
    6: {'bg': (0, 168, 0),    'name': 'Jungle',      'music': 'music.mp3'},    # Green
    7: {'bg': (252, 188, 176),'name': 'Pipe Land',   'music': 'music.mp3'},    # Salmon
    8: {'bg': (0, 0, 0),      'name': 'Dark World',  'music': 'music.mp3'},    # Final
}

# --- Tetromino Definitions with Sprite Mapping ---
TETROMINO_DATA = {
    'I': {'shape': [[0,0,0,0], [1,1,1,1], [0,0,0,0], [0,0,0,0]], 'color': (0, 240, 240), 'sprite': 'brick', 'category': 'blocks'},
    'J': {'shape': [[1,0,0], [1,1,1], [0,0,0]], 'color': (0, 0, 240), 'sprite': 'star_1', 'category': 'items'},
    'L': {'shape': [[0,0,1], [1,1,1], [0,0,0]], 'color': (240, 160, 0), 'sprite': 'mushroom_super', 'category': 'items'},
    'O': {'shape': [[1,1], [1,1]], 'color': (240, 240, 0), 'sprite': 'question_1', 'category': 'blocks'},
    'S': {'shape': [[0,1,1], [1,1,0], [0,0,0]], 'color': (0, 240, 0), 'sprite': 'walk_1', 'category': 'koopa_green'},
    'T': {'shape': [[0,1,0], [1,1,1], [0,0,0]], 'color': (160, 0, 240), 'sprite': 'mushroom_poison', 'category': 'items'},
    'Z': {'shape': [[1,1,0], [0,1,1], [0,0,0]], 'color': (240, 0, 0), 'sprite': 'walk_1', 'category': 'koopa_red'}
}

# --- Multiplayer ---
FIREBASE_DB_URL = "https://mario-tetris-game-default-rtdb.firebaseio.com/"
