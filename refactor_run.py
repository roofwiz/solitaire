import os

path = r'c:\Users\eric\React Projects\Mario-Tetris-main\main.py'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = False
for i, line in enumerate(lines):
    # Match the specific block in the run method
    if "if self.active_world == 'SHADOW': dt *= 1.25 # Gravity" in line:
        # Keep the shadow world dt boost but remove the comment
        new_lines.append(line.split("#")[0].rstrip() + "\n")
        skip = True
        continue
    
    if skip:
        # Search for the end of the gravity block (the start of update)
        if "self.update(dt)" in line:
            new_lines.append("                    if getattr(self, 'shift_cooldown', 0) > 0: self.shift_cooldown -= dt\n")
            new_lines.append("\n")
            new_lines.append(line)
            skip = False
        continue
    
    new_lines.append(line)

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print("Refactor complete.")
