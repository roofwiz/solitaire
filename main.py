
import pygame
import random
import os

# Initialize Pygame
pygame.init()

# --- Constants and Configuration ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 700
BLOCK_SIZE = 30

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
LINE_COLOR = (40, 40, 40)

# Game Grid
GRID_WIDTH = 10
GRID_HEIGHT = 20
grid_offset_x = (SCREEN_WIDTH - (GRID_WIDTH * BLOCK_SIZE)) / 2
grid_offset_y = (SCREEN_HEIGHT - (GRID_HEIGHT * BLOCK_SIZE)) / 2

# Tetromino Shapes
TETROMINOES = [
    [[1, 1, 1, 1]],  # I
    [[1, 1, 0], [0, 1, 1]],  # Z
    [[0, 1, 1], [1, 1, 0]],  # S
    [[1, 1, 1], [0, 1, 0]],  # T
    [[1, 1, 1], [1, 0, 0]],  # L
    [[1, 1, 1], [0, 0, 1]],  # J
    [[1, 1], [1, 1]]  # O
]

# Scoring
SCORE_MAP = {1: 100, 2: 300, 3: 500, 4: 800}

# --- Asset Loading ---
try:
    # Load the sprite sheet
    sprite_sheet = pygame.image.load(os.path.join('assets', 'marioallsprite.png')).convert_alpha()

    # Define the regions for each sprite (x, y, width, height)
    # These are example coordinates; they might need adjustment.
    SPRITES = [
        sprite_sheet.subsurface(pygame.Rect(0, 0, 16, 16)),   # Brick Block
        sprite_sheet.subsurface(pygame.Rect(17, 0, 16, 16)),  # Question Block
        sprite_sheet.subsurface(pygame.Rect(34, 0, 16, 16)),  # Used Block
        sprite_sheet.subsurface(pygame.Rect(0, 17, 16, 16)),  # Hard Block
        sprite_sheet.subsurface(pygame.Rect(17, 17, 16, 16)), # Mushroom
        sprite_sheet.subsurface(pygame.Rect(34, 17, 16, 16)), # Goomba
    ]
    # Scale sprites to our block size
    SCALED_SPRITES = [pygame.transform.scale(sprite, (BLOCK_SIZE, BLOCK_SIZE)) for sprite in SPRITES]
except pygame.error as e:
    print(f"Error loading assets: {e}")
    SCALED_SPRITES = None

# --- Game Classes and Functions ---
class Tetromino:
    def __init__(self, x, y, shape):
        self.x = x
        self.y = y
        self.shape = shape
        # Assign a random sprite to this tetromino
        self.sprite = random.choice(SCALED_SPRITES) if SCALED_SPRITES else None
        # Fallback color if sprites fail to load
        self.color = (random.randint(100, 255), random.randint(100, 255), random.randint(100, 255))


    def draw(self, screen):
        for r, row in enumerate(self.shape):
            for c, cell in enumerate(row):
                if cell:
                    # Draw the sprite if it exists, otherwise draw a colored rect
                    if self.sprite:
                        screen.blit(self.sprite, (grid_offset_x + self.x * BLOCK_SIZE + c * BLOCK_SIZE, grid_offset_y + self.y * BLOCK_SIZE + r * BLOCK_SIZE))
                    else:
                        pygame.draw.rect(screen, self.color, (grid_offset_x + self.x * BLOCK_SIZE + c * BLOCK_SIZE + 1, grid_offset_y + self.y * BLOCK_SIZE + r * BLOCK_SIZE + 1, BLOCK_SIZE - 2, BLOCK_SIZE - 2))

    def rotate(self):
        self.shape = [list(row) for row in zip(*self.shape[::-1])]

def check_collision(grid, tetromino):
    for r, row in enumerate(tetromino.shape):
        for c, cell in enumerate(row):
            if cell:
                if tetromino.x + c < 0 or tetromino.x + c >= GRID_WIDTH or tetromino.y + r >= GRID_HEIGHT:
                    return True
                if tetromino.y + r >= 0 and grid[tetromino.y + r][tetromino.x + c] is not None:
                    return True
    return False

def freeze_tetromino(grid, tetromino):
    for r, row in enumerate(tetromino.shape):
        for c, cell in enumerate(row):
            if cell and tetromino.y + r >= 0:
                # Store the sprite itself in the grid
                grid[tetromino.y + r][tetromino.x + c] = tetromino.sprite
    return grid

def clear_lines(grid):
    lines_to_clear = [r for r, row in enumerate(grid) if all(cell is not None for cell in row)]
    if not lines_to_clear:
        return grid, 0
    
    new_grid = [row for r, row in enumerate(grid) if r not in lines_to_clear]
    cleared_count = len(lines_to_clear)
    for _ in range(cleared_count):
        new_grid.insert(0, [None for _ in range(GRID_WIDTH)])
    return new_grid, cleared_count

def new_tetromino():
    shape = random.choice(TETROMINOES)
    return Tetromino(GRID_WIDTH // 2 - len(shape[0]) // 2, 0, shape)

def draw_grid(screen):
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            pygame.draw.rect(screen, LINE_COLOR, (grid_offset_x + x * BLOCK_SIZE, grid_offset_y + y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE), 1)

def draw_board(screen, grid):
    for r, row in enumerate(grid):
        for c, sprite in enumerate(row):
            if sprite:
                screen.blit(sprite, (grid_offset_x + c * BLOCK_SIZE, grid_offset_y + r * BLOCK_SIZE))

def main():
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Mario Tetris")

    try:
        score_font = pygame.font.Font('assets/PressStart2P-Regular.ttf', 32)
    except IOError:
        print("Font not found, using default.")
        score_font = pygame.font.Font(None, 45)

    grid = [[None for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
    current_tetromino = new_tetromino()
    
    clock = pygame.time.Clock()
    fall_time = 0
    fall_speed = 500  # milliseconds
    score = 0
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    current_tetromino.x -= 1
                    if check_collision(grid, current_tetromino): current_tetromino.x += 1
                elif event.key == pygame.K_RIGHT:
                    current_tetromino.x += 1
                    if check_collision(grid, current_tetromino): current_tetromino.x -= 1
                elif event.key == pygame.K_DOWN:
                    current_tetromino.y += 1
                    if check_collision(grid, current_tetromino): current_tetromino.y -= 1
                elif event.key == pygame.K_UP:
                    current_tetromino.rotate()
                    if check_collision(grid, current_tetromino):
                        for _ in range(3): current_tetromino.rotate()

        fall_time += clock.get_rawtime()
        clock.tick()

        if fall_time > fall_speed:
            fall_time = 0
            current_tetromino.y += 1
            if check_collision(grid, current_tetromino):
                current_tetromino.y -= 1
                grid = freeze_tetromino(grid, current_tetromino)
                
                grid, cleared_count = clear_lines(grid)
                if cleared_count > 0:
                    score += SCORE_MAP.get(cleared_count, 0)

                current_tetromino = new_tetromino()
                
                if check_collision(grid, current_tetromino):
                    running = False

        screen.fill(BLACK)
        draw_grid(screen)
        draw_board(screen, grid)
        current_tetromino.draw(screen)

        score_surface = score_font.render(f'Score: {score}', True, WHITE)
        screen.blit(score_surface, (grid_offset_x, 30))
        
        pygame.display.flip()

    # Game Over Screen
    game_over_font = pygame.font.Font('assets/PressStart2P-Regular.ttf', 50)
    game_over_surface = game_over_font.render('GAME OVER', True, WHITE)
    screen.blit(game_over_surface, (SCREEN_WIDTH/2 - game_over_surface.get_width()/2, SCREEN_HEIGHT/2 - game_over_surface.get_height()/2))
    pygame.display.flip()

    # Wait for a moment before quitting
    pygame.time.wait(2000)
    pygame.quit()

if __name__ == "__main__":
    # Add a check for the display environment
    if os.environ.get('DISPLAY'):
        main()
    else:
        print("No display found. Cannot run Pygame.")
        # We can still write the file, even if we can't run it.
        # This part is just to ensure the final code is saved.
        with open("main.py", "w") as f:
            f.write(get_file_content_as_string()) # This is a placeholder
            
# Helper function to get the content of this file as a string
def get_file_content_as_string():
    with open(__file__, 'r') as f:
        return f.read()
