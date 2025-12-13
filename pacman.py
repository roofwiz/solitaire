import pygame
import random

# --- Constants ---
SCREEN_WIDTH = 500
SCREEN_HEIGHT = 620
GRID_WIDTH = 10
GRID_HEIGHT = 20
BLOCK_SIZE = 30

# Top-left corner of the playfield
PLAYFIELD_X = (SCREEN_WIDTH - GRID_WIDTH * BLOCK_SIZE) // 2
PLAYFIELD_Y = SCREEN_HEIGHT - GRID_HEIGHT * BLOCK_SIZE - 10
FLASH_DURATION = 0.4 # seconds for the flash effect

# --- Colors ---
BLACK = (0, 0, 0)
NEON_PINK = (255, 0, 255)
DARK_GRAY = (40, 40, 40)
WHITE = (255, 255, 255) # Kept for reference, but UI will use pink


# Tetromino shapes and colors
SHAPES = [
    [[1, 1, 1, 1]],  # I
    [[1, 1], [1, 1]],  # O
    [[0, 1, 0], [1, 1, 1]],  # T
    [[0, 0, 1], [1, 1, 1]],  # L
    [[1, 0, 0], [1, 1, 1]],  # J
    [[0, 1, 1], [1, 1, 0]],  # S
    [[1, 1, 0], [0, 1, 1]]   # Z
]

COLORS = [
    (0, 255, 255),   # Neon Cyan
    (255, 0, 255),   # Neon Pink (O-piece)
    (150, 0, 255),   # Bright Purple
    (255, 100, 0),   # Neon Orange
    (0, 100, 255),   # Electric Blue
    (50, 255, 50),   # Neon Green
    (255, 0, 100)    # Neon Raspberry
]

class Piece:
    def __init__(self, x, y, shape_index):
        self.x = x
        self.y = y
        self.shape_index = shape_index
        self.shape = SHAPES[shape_index]
        self.color = COLORS[shape_index]
        self.rotation = 0

    def rotate(self):
        # Transpose and reverse rows to rotate clockwise
        self.shape = [list(row) for row in zip(*self.shape[::-1])]

class SoundManager:
    def __init__(self):
        self.sounds = {}
        self.music_loaded = False
        try:
            pygame.mixer.init()
            # User will need to provide these files in a 'sounds' folder
            self.sounds['rotate'] = pygame.mixer.Sound('sounds/rotate.wav')
            self.sounds['clear'] = pygame.mixer.Sound('sounds/clear.wav')
            self.sounds['lock'] = pygame.mixer.Sound('sounds/lock.wav')
            self.sounds['gameover'] = pygame.mixer.Sound('sounds/gameover.wav')
            print("SoundManager initialized successfully.")
        except pygame.error as e:
            print(f"SoundManager Error: {e}. Could not load sounds. Check paths and audio device.")
            self.sounds = None # Disable sounds if there's an error

    def play(self, sound_name):
        if self.sounds and sound_name in self.sounds:
            self.sounds[sound_name].play()

    def play_music(self):
        if self.sounds and not self.music_loaded: # Check if mixer initialized and music isn't already loaded
            try:
                pygame.mixer.music.load('sounds/music.mp3') # Or .wav
                self.music_loaded = True
                print("Background music loaded.")
            except pygame.error as e:
                print(f"Could not load music file: {e}")
        if self.music_loaded:
            # The -1 argument makes the music loop indefinitely
            pygame.mixer.music.play(loops=-1)

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Tetris")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.game_over_font = pygame.font.Font(None, 74)

        self.sound_manager = SoundManager()

        self.high_score = 0
        self.load_high_score()
        self.reset_game()

    def load_high_score(self):
        try:
            with open("highscore.txt", "r") as f:
                self.high_score = int(f.read())
        except (FileNotFoundError, ValueError):
            self.high_score = 0

    def save_high_score(self):
        with open("highscore.txt", "w") as f:
            f.write(str(self.high_score))

    def reset_game(self):
        self.score = 0
        self.grid = [[0 for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.level = 1
        self.total_lines_cleared = 0
        self.game_over = False
        self.paused = False
        self.fall_time = 0
        self.fall_speed = 0.5  # seconds per step
        self.current_piece = self.new_piece()
        self.next_piece = self.new_piece()
        self.held_piece = None
        self.can_hold = True
        self.ghost_piece = None
        self.flash_effect_timer = 0

    def check_and_set_high_score(self):
        if self.score > self.high_score:
            self.high_score = self.score
            self.save_high_score()

    def new_piece(self):
        shape_index = random.randint(0, len(SHAPES) - 1)
        # Start piece in the middle-top of the grid
        return Piece(GRID_WIDTH // 2 - 1, 0, shape_index)

    def check_collision(self, piece, offset_x, offset_y):
        for y, row in enumerate(piece.shape):
            for x, cell in enumerate(row):
                if cell:
                    grid_x = piece.x + x + offset_x
                    grid_y = piece.y + y + offset_y
                    if not (0 <= grid_x < GRID_WIDTH and 0 <= grid_y < GRID_HEIGHT and self.grid[grid_y][grid_x] == 0):
                        return True
        return False

    def lock_piece(self):
        for y, row in enumerate(self.current_piece.shape):
            for x, cell in enumerate(row):
                if cell:
                    self.grid[self.current_piece.y + y][self.current_piece.x + x] = self.current_piece.shape_index + 1
        self.sound_manager.play('lock')
        self.clear_lines()
        self.can_hold = True # Allow holding the next piece
        self.current_piece = self.next_piece
        self.next_piece = self.new_piece()
        if self.check_collision(self.current_piece, 0, 0):
            self.game_over = True
            self.check_and_set_high_score()
            self.sound_manager.play('gameover')

    def hold_piece(self):
        if not self.can_hold:
            return

        self.can_hold = False

        if self.held_piece is None:
            self.held_piece = self.current_piece
            self.current_piece = self.next_piece
            self.next_piece = self.new_piece()
        else:
            # Swap pieces
            self.current_piece, self.held_piece = self.held_piece, self.current_piece

        # Reset the position of the new current piece
        self.current_piece.x = GRID_WIDTH // 2 - 1
        self.current_piece.y = 0

        # If the new piece collides, it's game over
        if self.check_collision(self.current_piece, 0, 0):
            self.game_over = True
            self.check_and_set_high_score()
            self.sound_manager.play('gameover')

    def clear_lines(self):
        lines_cleared = 0
        new_grid = [row for row in self.grid if any(cell == 0 for cell in row)]
        lines_cleared = GRID_HEIGHT - len(new_grid)
        # Add new empty rows at the top
        for _ in range(lines_cleared):
            new_grid.insert(0, [0 for _ in range(GRID_WIDTH)])
        self.grid = new_grid

        if lines_cleared > 0:
            self.score += (lines_cleared ** 2) * 100 # Bonus for multi-line clears
            self.total_lines_cleared += lines_cleared
            self.level = self.total_lines_cleared // 10 + 1
            # Increase speed: decrease fall_speed, with a minimum cap
            self.fall_speed = max(0.1, 0.5 - (self.level - 1) * 0.04)
            if lines_cleared == 4: # Tetris!
                self.flash_effect_timer = FLASH_DURATION
            self.sound_manager.play('clear')

    def update_ghost_piece(self):
        if not self.current_piece:
            return
        # Create a copy of the current piece to act as the ghost
        self.ghost_piece = Piece(self.current_piece.x, self.current_piece.y, self.current_piece.shape_index)
        self.ghost_piece.shape = self.current_piece.shape
        # Drop it down until it collides
        while not self.check_collision(self.ghost_piece, 0, 1):
            self.ghost_piece.y += 1

    def draw_grid(self):
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                pygame.draw.rect(self.screen, DARK_GRAY, (PLAYFIELD_X + x * BLOCK_SIZE, PLAYFIELD_Y + y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE), 1)

    def draw_pieces(self):
        # Draw locked pieces
        for y, row in enumerate(self.grid):
            for x, cell in enumerate(row):
                if cell > 0:
                    color = COLORS[cell - 1]
                    pygame.draw.rect(self.screen, color, (PLAYFIELD_X + x * BLOCK_SIZE, PLAYFIELD_Y + y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE))

        # Draw ghost piece
        if self.ghost_piece:
            for y, row in enumerate(self.ghost_piece.shape):
                for x, cell in enumerate(row):
                    if cell:
                        # Draw a transparent outline for the ghost
                        pygame.draw.rect(self.screen, self.ghost_piece.color, (PLAYFIELD_X + (self.ghost_piece.x + x) * BLOCK_SIZE, PLAYFIELD_Y + (self.ghost_piece.y + y) * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE), 2)

        # Draw current piece
        if self.current_piece:
            for y, row in enumerate(self.current_piece.shape):
                for x, cell in enumerate(row):
                    if cell:
                        pygame.draw.rect(self.screen, self.current_piece.color, (PLAYFIELD_X + (self.current_piece.x + x) * BLOCK_SIZE, PLAYFIELD_Y + (self.current_piece.y + y) * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE))

    def draw_ui(self):
        # Draw score
        score_text = self.font.render(f"Score: {self.score}", True, NEON_PINK)
        self.screen.blit(score_text, (20, 20))

        # Draw High Score
        high_score_text = self.font.render(f"High Score: {self.high_score}", True, NEON_PINK)
        self.screen.blit(high_score_text, (PLAYFIELD_X + GRID_WIDTH * BLOCK_SIZE + 20, 180))

        # Draw Level
        level_text = self.font.render(f"Level: {self.level}", True, NEON_PINK)
        self.screen.blit(level_text, (20, 60))

        # Draw Lines to Next Level
        lines_to_next = 10 - (self.total_lines_cleared % 10)
        lines_text = self.font.render(f"Lines: {lines_to_next}", True, NEON_PINK)
        self.screen.blit(lines_text, (20, 90))

        # Draw "Hold" piece
        hold_text = self.font.render("Hold:", True, NEON_PINK)
        self.screen.blit(hold_text, (20, 120))
        if self.held_piece:
            for y, row in enumerate(self.held_piece.shape):
                for x, cell in enumerate(row):
                    if cell:
                        # Position the held piece in its own box
                        pygame.draw.rect(self.screen, self.held_piece.color, (30 + x * BLOCK_SIZE, 160 + y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE))

        # Draw "Next" piece
        next_text = self.font.render("Next:", True, NEON_PINK)
        self.screen.blit(next_text, (PLAYFIELD_X + GRID_WIDTH * BLOCK_SIZE + 20, 20))
        if self.next_piece:
            for y, row in enumerate(self.next_piece.shape):
                for x, cell in enumerate(row):
                    if cell:
                        pygame.draw.rect(self.screen, self.next_piece.color, (PLAYFIELD_X + GRID_WIDTH * BLOCK_SIZE + 30 + x * BLOCK_SIZE, 70 + y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE))

        if self.game_over:
            # Create a semi-transparent overlay
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))  # Black with ~70% opacity
            self.screen.blit(overlay, (0, 0))

            # "GAME OVER" text
            game_over_text = self.game_over_font.render("GAME OVER", True, NEON_PINK)
            game_over_rect = game_over_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 80))
            self.screen.blit(game_over_text, game_over_rect)

            # Final Score text
            final_score_text = self.font.render(f"Final Score: {self.score}", True, WHITE)
            final_score_rect = final_score_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2))
            self.screen.blit(final_score_text, final_score_rect)

            # Final Level text
            final_level_text = self.font.render(f"Final Level: {self.level}", True, WHITE)
            final_level_rect = final_level_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 40))
            self.screen.blit(final_level_text, final_level_rect)

            # Restart prompt
            restart_text = self.font.render("Press R to Restart", True, WHITE)
            restart_rect = restart_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 100))
            self.screen.blit(restart_text, restart_rect)

        if self.paused and not self.game_over:
            paused_text = self.game_over_font.render("PAUSED", True, NEON_PINK)
            text_rect = paused_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2))
            self.screen.blit(paused_text, text_rect)

    def draw_flash_effect(self):
        if self.flash_effect_timer > 0:
            # Calculate alpha based on remaining time for a fade-out effect
            alpha = int(255 * (self.flash_effect_timer / FLASH_DURATION))
            flash_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            flash_surface.fill((255, 255, 255, alpha))
            self.screen.blit(flash_surface, (0, 0))


    def run(self):
        running = True
        self.sound_manager.play_music()
        while running:
            delta_time = self.clock.tick(60) / 1000.0
            self.fall_time += delta_time

            if self.flash_effect_timer > 0:
                self.flash_effect_timer -= delta_time

            # --- Event Handling ---
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_p:
                        self.paused = not self.paused
                        if self.paused:
                            pygame.mixer.music.pause()
                        else:
                            pygame.mixer.music.unpause()

                    if self.game_over:
                        if event.key == pygame.K_r:
                            self.check_and_set_high_score()
                            self.reset_game()
                        continue
                    
                    if not self.paused:
                        self.handle_player_input(event.key)

            # --- Game Logic ---
            if not self.game_over and not self.paused:
                self.update_ghost_piece()

                # Gravity
                if self.fall_time >= self.fall_speed:
                    self.fall_time = 0
                    if not self.check_collision(self.current_piece, 0, 1):
                        self.current_piece.y += 1
                    else:
                        self.lock_piece()
    
    def handle_player_input(self, key):
        if key == pygame.K_LEFT:
            if not self.check_collision(self.current_piece, -1, 0):
                self.current_piece.x -= 1
        elif key == pygame.K_RIGHT:
            if not self.check_collision(self.current_piece, 1, 0):
                self.current_piece.x += 1
        elif key == pygame.K_DOWN:
            if not self.check_collision(self.current_piece, 0, 1):
                self.current_piece.y += 1
                self.score += 1 # Score for soft drop
        elif key == pygame.K_UP:
            # Rotation
            rotated_piece = Piece(self.current_piece.x, self.current_piece.y, self.current_piece.shape_index)
            rotated_piece.shape = self.current_piece.shape
            rotated_piece.rotate()
            if not self.check_collision(rotated_piece, 0, 0):
                self.current_piece.rotate()
                self.sound_manager.play('rotate')
        elif key == pygame.K_c:
            self.hold_piece()
        elif key == pygame.K_SPACE:
            # Hard drop
            while not self.check_collision(self.current_piece, 0, 1):
                self.current_piece.y += 1
                self.score += 2 # Score for hard drop
            self.lock_piece()

if __name__ == "__main__":
    game = Game()
    game.run()
