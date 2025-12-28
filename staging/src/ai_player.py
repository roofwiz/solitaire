import pygame
import random
import copy

class TetrisBot:
    def __init__(self, game):
        self.game = game
        self.best_move_queue = [] # List of inputs to execute
        self.move_timer = 0
        self.thinking = False
        self.active = False
        self.debug_font = pygame.font.SysFont('Arial', 12)

    def update(self, dt):
        if not self.active: return
        if not self.game.current_piece: return
        if self.game.game_state != 'PLAYING': return

        # If we have a plan, execute it
        if self.best_move_queue:
            self.move_timer += dt
            if self.move_timer > 0.05: # Fast AI moves (50ms)
                self.move_timer = 0
                action = self.best_move_queue.pop(0)
                self.execute_action(action)
        elif not self.thinking:
            # Plan a move immediately when piece spawns or queue empty
            self.plan_move()
            
    def execute_action(self, action):
        if action == 'left': self.game.action_move(-1)
        elif action == 'right': self.game.action_move(1)
        elif action == 'rotate': self.game.action_rotate()
        elif action == 'drop': self.game.action_hard_drop()
        
    def plan_move(self):
        self.thinking = True
        bx, br = self.get_best_move()
        
        self.best_move_queue = []
        
        # 1. Rotate
        # Assuming spawn rotation is 0. We blindly rotate 'br' times.
        # REALITY CHECK: If piece is generic, we just send 'rotate' inputs.
        for _ in range(br):
             self.best_move_queue.append('rotate')
             
        # 2. Move X
        # Current X is usually 4 or 5 at spawn.
        # We need the X of the piece AFTER rotation potentially? 
        # Ideally we calculate dx relative to spawn position.
        
        # Simplified: We assume piece starts at game.current_piece.x
        current_x = self.game.current_piece.x
        dx = bx - current_x
        
        if dx > 0:
            for _ in range(int(dx)): self.best_move_queue.append('right')
        elif dx < 0:
            for _ in range(int(abs(dx))): self.best_move_queue.append('left')
            
        # 3. Drop
        self.best_move_queue.append('drop')
        
        self.thinking = False # Done planning

    def get_best_move(self):
        best_score = -float('inf')
        best_r = 0
        best_x = 0
        
        orig_grid = [row[:] for row in self.game.grid.grid]
        next_piece_blocks = self.game.next_piece.blocks
        
        # 1. Iterate Rotations of CURRENT Piece
        for r1 in range(4):
            blocks1 = self.get_blocks_for_rotation(self.game.current_piece.blocks, r1)
            for x1 in range(-2, 10):
                if self.check_collision_virtual(x1, 0, blocks1, orig_grid): continue
                y1 = self.drop_virtual(x1, blocks1, orig_grid)
                if y1 < 0: continue
                
                # Simulate board after move 1
                grid2 = self.put_piece_virtual(orig_grid, blocks1, x1, y1)
                
                # 2. Iterate Rotations of NEXT Piece (Look-ahead)
                m2_best_score = -float('inf')
                for r2 in range(4):
                    blocks2 = self.get_blocks_for_rotation(next_piece_blocks, r2)
                    for x2 in range(-2, 10):
                        if self.check_collision_virtual(x2, 0, blocks2, grid2): continue
                        y2 = self.drop_virtual(x2, blocks2, grid2)
                        if y2 < 0: continue
                        
                        s = self.calculate_score(grid2, blocks2, x2, y2)
                        if s > m2_best_score: m2_best_score = s
                
                if m2_best_score > best_score:
                    best_score = m2_best_score
                    best_r = r1
                    best_x = x1
                    
        return best_x, best_r

    def get_blocks_for_rotation(self, base_blocks, r):
        curr = [b for b in base_blocks]
        for _ in range(r):
            curr = [(-y, x) for x, y in curr]
        return curr

    def drop_virtual(self, x, blocks, grid):
        for y in range(20):
            if self.check_collision_virtual(x, y, blocks, grid):
                return y - 1
        return 19

    def put_piece_virtual(self, grid, blocks, px, py):
        new_grid = [row[:] for row in grid]
        for bx, by in blocks:
             gx, gy = int(px + bx), int(py + by)
             if 0 <= gy < 20 and 0 <= gx < 10: new_grid[gy][gx] = 1
        return new_grid
    def check_collision_virtual(self, px, py, blocks, grid):
        for bx, by in blocks:
            gx = int(px + bx)
            gy = int(py + by)
            
            if gx < 0 or gx >= 10: return True # Wall
            if gy >= 20: return True # Floor
            if gy >= 0:
                if grid[gy][gx] is not None: return True
        return False

    def calculate_score(self, grid, blocks, px, py):
        # 1. Place Piece on Temp Grid
        # Deepcopy is slow? Let's try to do it in-place using a 'visited' or just Copy
        temp_grid = [row[:] for row in grid]
        
        for bx, by in blocks:
             gx = int(px + bx)
             gy = int(py + by)
             if 0 <= gy < 20 and 0 <= gx < 10:
                 temp_grid[gy][gx] = 1 # Mark solid
        
        # 2. Heuristics
        # Score = (Lines * 10) - (Height * 0.5) - (Holes * 5) - (Bumpiness * 0.2)
        
        # A. Lines
        lines = 0
        for row in temp_grid:
            if None not in row: lines += 1
            
        # B. Aggregate Height & Bumpiness
        heights = []
        for cx in range(10):
            h = 0
            for cy in range(20):
                if temp_grid[cy][cx] is not None:
                    h = 20 - cy
                    break
            heights.append(h)
            
        agg_height = sum(heights)
        
        bumpiness = 0
        for i in range(9):
            bumpiness += abs(heights[i] - heights[i+1])
            
        # C. Holes
        holes = 0
        for cx in range(10):
            block_found = False
            for cy in range(20):
                if temp_grid[cy][cx] is not None:
                    block_found = True
                elif block_found and temp_grid[cy][cx] is None:
                    holes += 1
        
        # Professional weighted formula
        lines_weight = 10.0
        height_weight = -0.5
        holes_weight = -10.0 # High penalty for holes
        bumpiness_weight = -0.2
        
        score = (lines * lines_weight) + (agg_height * height_weight) + (holes * holes_weight) + (bumpiness * bumpiness_weight)
        return score

    def draw_debug(self, surface):
        if self.active:
            lbl = self.debug_font.render("BOT ACTIVE", True, (255, 0, 0))
            surface.blit(lbl, (10, 10))
