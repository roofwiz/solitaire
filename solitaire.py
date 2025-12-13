import pygame
import sys
import random
import os

# Initialize Pygame
pygame.init()

# Screen dimensions
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 800
SCREEN = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Vegas Style Solitaire")

# Colors
BACKGROUND_COLOR = (0, 100, 0)  # Dark green
CARD_COLOR = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)

# Card constants
SUITS = ["Hearts", "Diamonds", "Clubs", "Spades"]
RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
CARD_WIDTH = 80
RANK_VALUES = {rank: i for i, rank in enumerate(RANKS, 1)}
CARD_HEIGHT = 120
CARD_MARGIN = 20
TABLEAU_START_Y = 150
FOUNDATION_START_X = 300

# Font
FONT = pygame.font.SysFont('Arial', 24)
WHITE = (255, 255, 255)
WIN_FONT = pygame.font.SysFont('Arial', 72, bold=True)

def load_card_images():
    """Loads all card images from the assets folder."""
    card_images = {}
    card_back_image = None
    path = os.path.join('assets', 'cards')
    try:
        # Load card back
        back_path = os.path.join(path, 'card_back.png')
        image = pygame.image.load(back_path).convert()
        card_back_image = pygame.transform.scale(image, (CARD_WIDTH, CARD_HEIGHT))

        # Load face cards
        for suit in SUITS:
            for rank in RANKS:
                file_name = f"{rank.lower()}_of_{suit.lower()}.png"
                image_path = os.path.join(path, file_name)
                image = pygame.image.load(image_path).convert()
                scaled_image = pygame.transform.scale(image, (CARD_WIDTH, CARD_HEIGHT))
                card_images[(suit, rank)] = scaled_image
    except pygame.error as e:
        print(f"Error loading card images: {e}")
        print("Please ensure you have an 'assets/cards' folder with images named like 'ace_of_hearts.png' and 'card_back.png'.")
        pygame.quit()
        sys.exit()
    return card_images, card_back_image

CARD_IMAGES, CARD_BACK_IMAGE = load_card_images()

class Card:
    """Represents a single playing card."""
    def __init__(self, suit, rank):
        self.suit = suit
        self.rank = rank
        self.face_up = False
        self.rect = pygame.Rect(0, 0, CARD_WIDTH, CARD_HEIGHT)

    @property
    def image(self):
        """Returns the card's image based on its state."""
        if self.face_up:
            return CARD_IMAGES[(self.suit, self.rank)]
        else:
            return CARD_BACK_IMAGE

    def flip(self):
        """Flips the card over."""
        self.face_up = not self.face_up

    def __str__(self):
        return f"{self.rank} of {self.suit}"

class Deck:
    """Represents a deck of 52 cards."""
    def __init__(self):
        self.cards = [Card(suit, rank) for suit in SUITS for rank in RANKS]
        self.shuffle()

    def shuffle(self):
        """Shuffles the deck."""
        random.shuffle(self.cards)

    def deal(self):
        """Deals one card from the top of the deck."""
        if self.cards:
            return self.cards.pop()
        return None

def deal_tableau(deck, tableau_piles):
    """Deals cards to the tableau piles."""
    for i in range(7):
        for j in range(i, 7):
            card = deck.deal()
            if card:
                if i == j:
                    card.flip()
                tableau_piles[j].append(card)

def draw_cards(screen, game, original_pile_info):
    """Draws all static cards on the screen (not currently being dragged)."""
    # Draw tableau piles
    for i, pile in enumerate(game.tableau_piles):
        # Set rects for all cards first for collision detection, even if not drawn
        base_x = CARD_MARGIN + i * (CARD_WIDTH + CARD_MARGIN)
        cards_to_draw = pile[:original_pile_info["index"]] if pile is original_pile_info["pile"] else pile
        for j, card in enumerate(cards_to_draw):
            card.rect.topleft = (base_x, TABLEAU_START_Y + j * 30)
        # Now draw them
        for card in pile:
            screen.blit(card.image, card.rect)

    # Draw foundation piles
    for i, pile in enumerate(game.foundation_piles):
        x = FOUNDATION_START_X + i * (CARD_WIDTH + CARD_MARGIN)
        y = CARD_MARGIN
        if not pile:
            pygame.draw.rect(screen, BLACK, (x, y, CARD_WIDTH, CARD_HEIGHT), 3)
        else:
            card = pile[-1]
            card.rect.topleft = (x,y)
            screen.blit(card.image, card.rect)
            
    # Draw stock pile
    if game.stock:
        # Draw card back for stock
        screen.blit(CARD_BACK_IMAGE, (CARD_MARGIN, CARD_MARGIN))
    
    # Draw waste pile
    if game.waste_pile:
        # In Draw 3, show the top 3 cards. In Draw 1, just the top one.
        # The playable card is always the last one.
        num_to_show = 3 if Game.instance.draw_mode == 3 else 1
        cards_to_show = game.waste_pile[-num_to_show:]
        
        for i, card in enumerate(cards_to_show):
            offset = i * (CARD_MARGIN // 2)
            card.rect.topleft = (CARD_MARGIN + CARD_WIDTH + CARD_MARGIN + offset, CARD_MARGIN)
            screen.blit(card.image, card.rect)
        
        # Ensure the topmost card's rect is correctly positioned for collision detection,
        # even if it was drawn underneath others.
        if cards_to_show:
            game.waste_pile[-1].rect.topleft = (CARD_MARGIN + CARD_WIDTH + CARD_MARGIN + (len(cards_to_show) - 1) * (CARD_MARGIN // 2), CARD_MARGIN)

def draw_dragged_cards(screen, dragged_cards, mouse_pos, drag_offset):
    """Draws the cards currently being dragged by the user."""
    for i, card in enumerate(dragged_cards):
        card.rect.topleft = (mouse_pos[0] - drag_offset[0], mouse_pos[1] - drag_offset[1] + i * 30)
        screen.blit(card.image, card.rect)


def draw_new_game_button(screen):
    """Draws the 'New Game' button."""
    button_rect = pygame.Rect(SCREEN_WIDTH - 160, 20, 140, 40)
    pygame.draw.rect(screen, (200, 200, 200), button_rect)
    pygame.draw.rect(screen, BLACK, button_rect, 2)
    text = FONT.render("New Game", True, BLACK)
    text_rect = text.get_rect(center=button_rect.center)
    screen.blit(text, text_rect)
    return button_rect

def draw_undo_button(screen, enabled):
    """Draws the 'Undo' button, grayed out if disabled."""
    button_rect = pygame.Rect(SCREEN_WIDTH - 160, 70, 140, 40)
    color = (200, 200, 200) if enabled else (100, 100, 100)
    text_color = BLACK if enabled else (150, 150, 150)
    pygame.draw.rect(screen, color, button_rect)
    pygame.draw.rect(screen, BLACK, button_rect, 2)
    text = FONT.render("Undo", True, text_color)
    text_rect = text.get_rect(center=button_rect.center)
    screen.blit(text, text_rect)
    return button_rect

def draw_mode_button(screen, draw_mode):
    """Draws the button to toggle draw mode."""
    button_rect = pygame.Rect(SCREEN_WIDTH - 160, 120, 140, 40)
    pygame.draw.rect(screen, (200, 200, 200), button_rect)
    pygame.draw.rect(screen, BLACK, button_rect, 2)
    text = FONT.render(f"Draw: {draw_mode}", True, BLACK)
    text_rect = text.get_rect(center=button_rect.center)
    screen.blit(text, text_rect)
    return button_rect

def draw_hint_button(screen):
    """Draws the 'Hint' button."""
    button_rect = pygame.Rect(SCREEN_WIDTH - 160, 170, 140, 40)
    pygame.draw.rect(screen, (200, 200, 200), button_rect)
    pygame.draw.rect(screen, BLACK, button_rect, 2)
    text = FONT.render("Hint", True, BLACK)
    text_rect = text.get_rect(center=button_rect.center)
    screen.blit(text, text_rect)
    return button_rect

def draw_ui(screen, score, elapsed_time):
    """Draws the game UI, like the score."""
    # Draw Score
    score_text = FONT.render(f"Score: {score}", True, WHITE)
    score_rect = score_text.get_rect(topleft=(SCREEN_WIDTH - 300, 20))
    screen.blit(score_text, score_rect)
    # Draw Timer
    minutes = elapsed_time // 60
    seconds = elapsed_time % 60
    time_str = f"Time: {minutes:02}:{seconds:02}"
    time_text = FONT.render(time_str, True, WHITE)
    time_rect = time_text.get_rect(topleft=(SCREEN_WIDTH - 300, 50))
    screen.blit(time_text, time_rect)


def draw_win_screen(screen):
    """Draws the win screen overlay."""
    # Semi-transparent overlay
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 50, 0, 180))
    screen.blit(overlay, (0, 0))

    # "YOU WIN!" text
    win_text = WIN_FONT.render("YOU WIN!", True, (255, 215, 0)) # Gold color
    win_rect = win_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2))
    screen.blit(win_text, win_rect)

def is_valid_tableau_move(card_to_move, destination_card):
    """Checks if moving a card onto another in the tableau is valid."""
    if not destination_card: # Moving to an empty pile
        return card_to_move.rank == "K"

    dest_color = 'red' if destination_card.suit in ["Hearts", "Diamonds"] else 'black'
    move_color = 'red' if card_to_move.suit in ["Hearts", "Diamonds"] else 'black'

    if dest_color == move_color:
        return False

    if RANK_VALUES[destination_card.rank] != RANK_VALUES[card_to_move.rank] + 1:
        return False

    return True

def is_valid_foundation_move(card_to_move, foundation_pile):
    """Checks if moving a card to a foundation pile is valid."""
    # Case 1: Foundation is empty, only an Ace can be placed.
    if not foundation_pile:
        return card_to_move.rank == "A"
    
    # Case 2: Foundation has cards, check suit and rank.
    top_card = foundation_pile[-1]
    same_suit = card_to_move.suit == top_card.suit
    correct_rank = RANK_VALUES[card_to_move.rank] == RANK_VALUES[top_card.rank] + 1
    
    return same_suit and correct_rank

def check_win_condition(foundation_piles):
    """Checks if all 52 cards are in the foundation piles."""
    return sum(len(pile) for pile in foundation_piles) == 52

class Game:
    """Manages the overall game state and logic."""
    instance = None

    def __init__(self):
        Game.instance = self
        self.reset_game()

    def reset_game(self):
        deck = Deck()
        self.tableau_piles = [[] for _ in range(7)]
        self.foundation_piles = [[] for _ in range(4)]
        deal_tableau(deck, self.tableau_piles)
        self.stock = deck.cards
        self.waste_pile = []
        self.score = 0
        self.move_history = []
        self.start_time = pygame.time.get_ticks()
        self.game_won = False
        self.animations = []
        self.hint = None

    def find_hint(self):
        # 1. Check for moves from waste to foundation
        if self.waste_pile:
            card = self.waste_pile[-1]
            for i, pile in enumerate(self.foundation_piles):
                if is_valid_foundation_move(card, pile):
                    dest_rect = pygame.Rect(FOUNDATION_START_X + i * (CARD_WIDTH + CARD_MARGIN), CARD_MARGIN, CARD_WIDTH, CARD_HEIGHT)
                    self.hint = {"card_rect": card.rect, "dest_rect": dest_rect, "time": pygame.time.get_ticks()}
                    return

        # 2. Check for moves from tableau to foundation
        for pile in self.tableau_piles:
            if pile:
                card = pile[-1]
                for i, f_pile in enumerate(self.foundation_piles):
                    if is_valid_foundation_move(card, f_pile):
                        dest_rect = pygame.Rect(FOUNDATION_START_X + i * (CARD_WIDTH + CARD_MARGIN), CARD_MARGIN, CARD_WIDTH, CARD_HEIGHT)
                        self.hint = {"card_rect": card.rect, "dest_rect": dest_rect, "time": pygame.time.get_ticks()}
                        return

        # 3. Check for moves from waste to tableau
        if self.waste_pile:
            card = self.waste_pile[-1]
            for i, pile in enumerate(self.tableau_piles):
                dest_card = pile[-1] if pile else None
                if is_valid_tableau_move(card, dest_card):
                    dest_rect = dest_card.rect if dest_card else pygame.Rect(CARD_MARGIN + i * (CARD_WIDTH + CARD_MARGIN), TABLEAU_START_Y, CARD_WIDTH, CARD_HEIGHT)
                    self.hint = {"card_rect": card.rect, "dest_rect": dest_rect, "time": pygame.time.get_ticks()}
                    return

        # 4. Check for moves between tableau piles
        for i, src_pile in enumerate(self.tableau_piles):
            for j, card in enumerate(src_pile):
                if card.face_up:
                    # Check against other piles
                    for k, dest_pile in enumerate(self.tableau_piles):
                        if i == k: continue # Don't check same pile
                        dest_card = dest_pile[-1] if dest_pile else None
                        if is_valid_tableau_move(card, dest_card):
                            dest_rect = dest_card.rect if dest_card else pygame.Rect(CARD_MARGIN + k * (CARD_WIDTH + CARD_MARGIN), TABLEAU_START_Y, CARD_WIDTH, CARD_HEIGHT)
                            self.hint = {"card_rect": card.rect, "dest_rect": dest_rect, "time": pygame.time.get_ticks()}
                            return
                    break # Only need to check the top face-up card of a stack

        # 5. Check if stock can be drawn
        if self.stock:
            self.hint = {"card_rect": pygame.Rect(CARD_MARGIN, CARD_MARGIN, CARD_WIDTH, CARD_HEIGHT), "dest_rect": None, "time": pygame.time.get_ticks()}
            return

    def draw_hint(self, screen):
        if self.hint:
            # Fade hint after a short time
            if pygame.time.get_ticks() - self.hint["time"] > 1000:
                self.hint = None
                return
            
            # Draw a glowing border around the source card/pile
            pygame.draw.rect(screen, (255, 255, 0, 200), self.hint["card_rect"].inflate(6, 6), 4, border_radius=5)
            # And its destination
            if self.hint["dest_rect"]:
                pygame.draw.rect(screen, (255, 255, 0, 200), self.hint["dest_rect"].inflate(6, 6), 4, border_radius=5)

    def create_animation(self, cards, start_pos, end_pos, on_complete):
        """Generic animation creator."""
        self.animations.append({
            "cards": cards,
            "start_pos": start_pos,
            "end_pos": end_pos,
            "start_time": pygame.time.get_ticks(),
            "duration": 150, # ANIMATION_SPEED
            "on_complete": on_complete
        })

    def create_undo_animation(self):
        last_move = self.move_history.pop()
        
        def on_undo_complete():
            # Reverse the move
            cards_to_revert = last_move["dest_pile"][len(last_move["dest_pile"]) - len(last_move["cards"]):]
            last_move["source_pile"].extend(cards_to_revert)
            del last_move["dest_pile"][len(last_move["dest_pile"]) - len(last_move["cards"]):]

            # If a card was flipped, un-flip it
            if last_move["was_flip"]:
                if last_move["source_pile"]:
                    last_move["source_pile"][-1].flip()
            
            # If it was a stock draw, un-flip the cards
            if last_move.get("type") == "stock_draw":
                for card in cards_to_revert:
                    card.flip()

            # Restore score
            self.score = last_move["score_before"]

        # The cards are currently at the end position
        start_pos = last_move["cards"][0].rect.topleft
        end_pos = last_move["start_pos"]
        self.create_animation(last_move["cards"], start_pos, end_pos, on_undo_complete)

    def create_stock_draw_animation(self):
        num_to_draw = self.draw_mode
        drawn_cards_info = []

        for _ in range(num_to_draw):
            if self.stock:
                card = self.stock.pop()
                drawn_cards_info.append({"card": card})

        if not drawn_cards_info:
            return # No cards to draw

        self.move_history.append({
            "type": "stock_draw",
            "cards": [info["card"] for info in drawn_cards_info],
            "source_pile": self.stock,
            "dest_pile": self.waste_pile,
            "was_flip": False,
            "score_before": self.score,
            "start_pos": (CARD_MARGIN, CARD_MARGIN)
        })

        for i, info in enumerate(drawn_cards_info):
            card_to_draw = info["card"]
            
            def on_stock_draw_complete(card=card_to_draw):
                card.flip()
                self.waste_pile.append(card)

            end_pos = (CARD_MARGIN + CARD_WIDTH + CARD_MARGIN + i * (CARD_MARGIN // 2), CARD_MARGIN)
            anim = {
                "cards": [card_to_draw],
                "start_pos": (CARD_MARGIN, CARD_MARGIN),
                "end_pos": end_pos,
                "start_time": pygame.time.get_ticks() + i * 50, # Stagger
                "duration": 150,
                "on_complete": on_stock_draw_complete
            }
            self.animations.append(anim)

    def create_waste_reset_animation(self):
        for i, card in enumerate(reversed(self.waste_pile)):
            def on_complete(c=card):
                c.flip()
                self.stock.append(c)
            
            self.create_animation([card], card.rect.topleft, (CARD_MARGIN, CARD_MARGIN), on_complete)
        self.waste_pile.clear()

    def create_drop_animation(self, cards, src_info, dst_pile, end_pos):
        is_tableau_to_tableau = src_info["pile"] in self.tableau_piles and dst_pile in self.tableau_piles
        
        move_info = {
            "cards": cards, "source_pile": src_info["pile"], "dest_pile": dst_pile,
            "was_flip": (src_info["pile"] in self.tableau_piles and len(src_info["pile"]) > len(cards)),
            "score_before": self.score, "start_pos": cards[0].rect.topleft
        }
        self.move_history.append(move_info)

        def on_drop_complete():
            src_info["pile"][src_info["index"]:] = []
            dst_pile.extend(cards)

            # Scoring
            if dst_pile in self.foundation_piles: self.score += 10
            elif src_info["pile"] is self.waste_pile: self.score += 5
            elif src_info["pile"] in self.foundation_piles: self.score = max(0, self.score - 15)

            # Flip card
            if move_info["was_flip"] and src_info["pile"] and not src_info["pile"][-1].face_up:
                src_info["pile"][-1].flip()
                self.score += 5
            
            if check_win_condition(self.foundation_piles):
                self.game_won = True

        self.create_animation(cards, cards[0].rect.topleft, end_pos, on_drop_complete)


def main():
    """Main game loop."""
    game = Game()
    game.draw_mode = 1

    new_game_button_rect = None
    undo_button_rect = None
    mode_button_rect = None
    hint_button_rect = None

    # Clock for timing
    clock = pygame.time.Clock()

    # Double-click state
    last_click_time = 0
    DOUBLE_CLICK_INTERVAL = 500 # ms
    last_clicked_card = None

    elapsed_time = 0
    # Game state
    score_timer = pygame.time.get_ticks()
    SCORE_PENALTY_INTERVAL = 10000 # 10 seconds in ms
    SCORE_PENALTY_AMOUNT = 2

    # Drag and drop state variables
    dragging = False
    dragged_cards = []
    drag_offset = (0, 0)
    original_pile_info = {
        "pile": None,
        "index": -1
    }

    running = True
    while running:
        clock.tick(60) # Limit frame rate
        current_time = pygame.time.get_ticks()

        # Update elapsed time if game is not won
        if not game.game_won:
            elapsed_time = (current_time - game.start_time) // 1000

        # --- Animation Processing ---
        if game.animations:
            anim = game.animations[0]
            elapsed = current_time - anim["start_time"]
            if elapsed >= anim["duration"]:
                # Animation finished, execute the final logic and remove it
                anim["on_complete"]()
                game.animations.pop(0)
            # Drawing of animating cards happens in the drawing section
        # --- End Animation Processing ---


        # Apply time-based score penalty
        if not game.game_won and current_time - score_timer > SCORE_PENALTY_INTERVAL:
            game.score = max(0, game.score - SCORE_PENALTY_AMOUNT)
            score_timer = current_time

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: # Left mouse button
                    # Prevent clicks while animating
                    if game.animations:
                        continue

                    current_click_time = pygame.time.get_ticks()
                    is_double_click = (current_click_time - last_click_time) < DOUBLE_CLICK_INTERVAL

                    # If game is won, only the "New Game" button works
                    if game.game_won:
                        if new_game_button_rect and new_game_button_rect.collidepoint(event.pos):
                            game.reset_game()
                        continue # Skip other click events

                    # Undo button click
                    if undo_button_rect and undo_button_rect.collidepoint(event.pos) and game.move_history:
                        game.create_undo_animation()

                    # "New Game" button click
                    if new_game_button_rect and new_game_button_rect.collidepoint(event.pos):
                        game.reset_game()

                    # Hint button click
                    if hint_button_rect and hint_button_rect.collidepoint(event.pos):
                        game.find_hint()

                    # Stock pile click
                    stock_rect = pygame.Rect(CARD_MARGIN, CARD_MARGIN, CARD_WIDTH, CARD_HEIGHT)
                    if stock_rect.collidepoint(event.pos):
                        if dragging:
                            continue
                        if game.stock:
                            game.create_stock_draw_animation()
                        elif game.waste_pile:
                            game.create_waste_reset_animation()

                    # --- Double-Click Auto-Move Logic ---
                    clicked_card_for_double_click = None
                    source_pile_for_double_click = None

                    # Check waste pile
                    if game.waste_pile and game.waste_pile[-1].rect.collidepoint(event.pos):
                        clicked_card_for_double_click = game.waste_pile[-1]
                        source_pile_for_double_click = game.waste_pile
                    else: # Check tableau piles
                        for pile in game.tableau_piles:
                            if pile and pile[-1].rect.collidepoint(event.pos) and pile[-1].face_up:
                                clicked_card_for_double_click = pile[-1]
                                source_pile_for_double_click = pile
                                break
                    
                    if is_double_click and clicked_card_for_double_click and clicked_card_for_double_click is last_clicked_card:
                        for i, dest_pile in enumerate(game.foundation_piles):
                            if is_valid_foundation_move(clicked_card_for_double_click, dest_pile):                                
                                end_pos = (FOUNDATION_START_X + i * (CARD_WIDTH + CARD_MARGIN), CARD_MARGIN)
                                src_info = {"pile": source_pile_for_double_click, "index": len(source_pile_for_double_click) - 1}
                                game.create_drop_animation([clicked_card_for_double_click], src_info, dest_pile, end_pos)
                                break # Found a valid move, stop searching
                        
                        # Reset click tracking and exit
                        last_clicked_card = None
                        last_click_time = 0
                        continue # Skip drag logic

                    # Update click tracking for next event
                    last_click_time = current_click_time
                    last_clicked_card = clicked_card_for_double_click
                    # --- End Double-Click Logic ---

                    # Mode toggle button click
                    if mode_button_rect and mode_button_rect.collidepoint(event.pos):
                        game.draw_mode = 3 if game.draw_mode == 1 else 1
                        game.reset_game()

                    # Waste pile card click for dragging
                    if not dragging and game.waste_pile:
                        if game.waste_pile[-1].rect.collidepoint(event.pos):
                            dragging = True
                            dragged_cards = [game.waste_pile[-1]]
                            original_pile_info = {"pile": game.waste_pile, "index": len(game.waste_pile) - 1}
                            card_rect = game.waste_pile[-1].rect
                            drag_offset = (event.pos[0] - card_rect.x, event.pos[1] - card_rect.y)

                    
                    # Tableau card click for dragging
                    for i, pile in enumerate(game.tableau_piles):
                        # Iterate backwards to check top cards first
                        for j, card in reversed(list(enumerate(pile))):
                            if card.rect.collidepoint(event.pos) and card.face_up:
                                dragging = True
                                # All cards from the clicked one to the end are dragged
                                dragged_cards = pile[j:]
                                original_pile_info = {"pile": pile, "index": j}
                                
                                # Calculate offset from mouse to the top-left of the first dragged card
                                drag_offset = (event.pos[0] - card.rect.x, event.pos[1] - card.rect.y)
                                break # Found a card to drag, stop searching
                        if dragging:
                            break # Stop searching through piles
            
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1 and dragging:
                    dragging = False
                    move_made = False
                    
                    # Check for a valid drop on a foundation pile (only single cards)
                    if len(dragged_cards) == 1:
                        card_to_move = dragged_cards[0]
                        for i, pile in enumerate(game.foundation_piles):
                            foundation_rect = pygame.Rect(FOUNDATION_START_X + i * (CARD_WIDTH + CARD_MARGIN), CARD_MARGIN, CARD_WIDTH, CARD_HEIGHT)
                            if card_to_move.rect.colliderect(foundation_rect):
                                if is_valid_foundation_move(card_to_move, pile):                                    
                                    game.create_drop_animation(dragged_cards, original_pile_info, pile, foundation_rect.topleft)
                                    move_made = True
                                    break
                    if move_made: # Skip tableau check if move to foundation was successful
                        dragging = False # Ensure dragging stops

                    # Check for a valid drop on a tableau pile
                    for i, pile in enumerate(game.tableau_piles):
                        # Case 1: Dropping on an empty pile
                        if not pile:
                            # Create a placeholder rect for the empty pile
                            empty_pile_rect = pygame.Rect(CARD_MARGIN + i * (CARD_WIDTH + CARD_MARGIN), TABLEAU_START_Y, CARD_WIDTH, CARD_HEIGHT)
                            if dragged_cards[0].rect.colliderect(empty_pile_rect) and is_valid_tableau_move(dragged_cards[0], None):                                
                                end_pos = empty_pile_rect.topleft
                                move_made = True
                                break
                        # Case 2: Dropping on an existing pile
                        elif pile[-1].rect.colliderect(dragged_cards[0].rect) and pile is not original_pile_info["pile"]:
                            if is_valid_tableau_move(dragged_cards[0], pile[-1]):                                
                                end_pos = (pile[-1].rect.x, pile[-1].rect.y + 30)
                                move_made = True
                                break
                    
                    if move_made:
                        game.create_drop_animation(dragged_cards, original_pile_info, pile, end_pos)

                    dragged_cards = []
                    original_pile_info = {"pile": None, "index": -1}

            elif event.type == pygame.MOUSEMOTION:
                if dragging and not game.game_won:
                    # The cards are drawn following the mouse in the drawing section
                    pass

        # Drawing
        SCREEN.fill(BACKGROUND_COLOR)
        
        draw_cards(SCREEN, game, original_pile_info)

        if dragging:
            draw_dragged_cards(SCREEN, dragged_cards, pygame.mouse.get_pos(), drag_offset)

        # Draw animating cards on top of everything
        if game.animations:
            anim = game.animations[0]
            elapsed = current_time - anim["start_time"]
            progress = min(1.0, elapsed / anim.get("duration", 150))

            start_x, start_y = anim["start_pos"]
            end_x, end_y = anim["end_pos"]

            # Smooth interpolation (ease-out)
            progress = 1 - (1 - progress) ** 3
            
            current_x = start_x + (end_x - start_x) * progress
            current_y = start_y + (end_y - start_y) * progress

            cards_to_draw = anim.get("cards", [])
            for i, card in enumerate(cards_to_draw):
                if card:
                    SCREEN.blit(card.image, (current_x, current_y + i * 30))

        new_game_button_rect = draw_new_game_button(SCREEN)
        undo_button_rect = draw_undo_button(SCREEN, enabled=bool(game.move_history))
        mode_button_rect = draw_mode_button(SCREEN, game.draw_mode)
        hint_button_rect = draw_hint_button(SCREEN)
        draw_ui(SCREEN, game.score, elapsed_time)
        game.draw_hint(SCREEN)

        if game.game_won:
            draw_win_screen(SCREEN)

        # Update the display
        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
