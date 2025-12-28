import os
import copy

path = r'c:\Users\eric\React Projects\Mario-Tetris-main\src\ai_player.py'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if "def get_best_move(self):" in line:
        skip = True
        # Insert the new look-ahead logic
        new_lines.append("    def get_best_move(self):\n")
        new_lines.append("        best_score = -float('inf')\n")
        new_lines.append("        best_r = 0\n")
        new_lines.append("        best_x = 0\n")
        new_lines.append("        \n")
        new_lines.append("        orig_grid = [row[:] for row in self.game.grid.grid]\n")
        new_lines.append("        next_piece_blocks = self.game.next_piece.blocks\n")
        new_lines.append("        \n")
        new_lines.append("        # 1. Iterate Rotations of CURRENT Piece\n")
        new_lines.append("        for r1 in range(4):\n")
        new_lines.append("            blocks1 = self.get_blocks_for_rotation(self.game.current_piece.blocks, r1)\n")
        new_lines.append("            for x1 in range(-2, 10):\n")
        new_lines.append("                if self.check_collision_virtual(x1, 0, blocks1, orig_grid): continue\n")
        new_lines.append("                y1 = self.drop_virtual(x1, blocks1, orig_grid)\n")
        new_lines.append("                if y1 < 0: continue\n")
        new_lines.append("                \n")
        new_lines.append("                # Simulate board after move 1\n")
        new_lines.append("                grid2 = self.put_piece_virtual(orig_grid, blocks1, x1, y1)\n")
        new_lines.append("                \n")
        new_lines.append("                # 2. Iterate Rotations of NEXT Piece (Look-ahead)\n")
        new_lines.append("                m2_best_score = -float('inf')\n")
        new_lines.append("                for r2 in range(4):\n")
        new_lines.append("                    blocks2 = self.get_blocks_for_rotation(next_piece_blocks, r2)\n")
        new_lines.append("                    for x2 in range(-2, 10):\n")
        new_lines.append("                        if self.check_collision_virtual(x2, 0, blocks2, grid2): continue\n")
        new_lines.append("                        y2 = self.drop_virtual(x2, blocks2, grid2)\n")
        new_lines.append("                        if y2 < 0: continue\n")
        new_lines.append("                        \n")
        new_lines.append("                        s = self.calculate_score(grid2, blocks2, x2, y2)\n")
        new_lines.append("                        if s > m2_best_score: m2_best_score = s\n")
        new_lines.append("                \n")
        new_lines.append("                if m2_best_score > best_score:\n")
        new_lines.append("                    best_score = m2_best_score\n")
        new_lines.append("                    best_r = r1\n")
        new_lines.append("                    best_x = x1\n")
        new_lines.append("                    \n")
        new_lines.append("        return best_x, best_r\n\n")
        
        new_lines.append("    def get_blocks_for_rotation(self, base_blocks, r):\n")
        new_lines.append("        curr = [b for b in base_blocks]\n")
        new_lines.append("        for _ in range(r):\n")
        new_lines.append("            curr = [(-y, x) for x, y in curr]\n")
        new_lines.append("        return curr\n\n")
        
        new_lines.append("    def drop_virtual(self, x, blocks, grid):\n")
        new_lines.append("        for y in range(20):\n")
        new_lines.append("            if self.check_collision_virtual(x, y, blocks, grid):\n")
        new_lines.append("                return y - 1\n")
        new_lines.append("        return 19\n\n")
        
        new_lines.append("    def put_piece_virtual(self, grid, blocks, px, py):\n")
        new_lines.append("        new_grid = [row[:] for row in grid]\n")
        new_lines.append("        for bx, by in blocks:\n")
        new_lines.append("             gx, gy = int(px + bx), int(py + by)\n")
        new_lines.append("             if 0 <= gy < 20 and 0 <= gx < 10: new_grid[gy][gx] = 1\n")
        new_lines.append("        return new_grid\n")
        continue

    if skip:
        if "def check_collision_virtual(self, px, py, blocks, grid):" in line:
            skip = False
        else:
            continue
    
    new_lines.append(line)

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
