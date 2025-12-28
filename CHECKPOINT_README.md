# Project Checkpoint - Dark World Polish

**Date:** December 21, 2025
**Status:** Dark World Scene Fully Playable & Polished

## 🌟 Key Features Implemented

### 1. Visual Overhaul
- **Background:** Integration of `dark_world_clean.png`.
- **Platforms:** Grid-aligned with thick cyan outlines (5px) for high visibility.
- **Intro Screen:** Polished with gradient sky, clouds, and rolling hills.
- **Zoom:** Adjusted to 1.8x to see more of the level ahead.

### 2. Character & Sprites (Custom Selection)
- **Big Mario:** Replaced default sprite with 8 specific high-res frames selected by user (Stand, Walk 1-3, Jump, Skid, Crouch, Climb).
  - Source: `marioallsprite.png` around Y=80.
  - Scale: 64x64 pixels.
- **Animated Coins:**
  - Idle: 3-frame spinning animation (6 FPS).
  - Collection: 9-frame sparkle animation (10 FPS) when touched.
  - Source: `items-coins.png`.

### 3. Gameplay Mechanics
- **Physics:** 
  - "Super Jump" enabled (-900 force) to reach all platforms.
  - Auto-respawn system if player falls into the void (Y > 850).
- **Enemies:** 
  - Goombas and Koopa Troopers (Turtles) spawn on platforms.
  - Mechanics: Stomp to kill, kick shells.
- **Victory:**
  - Flagpole with large hitbox (80px width).
  - Victory sequence: Slide down -> 'WORLD_CLEAR' signal.

### 4. Files Created/Modified
- `src/scene_dark_world.py`: Core logic for the Dark World.
- `view_coins.py`: Utility to view and select coin sprites.
- `clicked_sprites.txt`: Log of selected sprite coordinates.
- `src/scene_dark_world_backup_v1.py`: Backup of the current working code.

## How to Resume
Run `main.py` and select "Play Mario Dark".
- Controls: Arrow Keys (Move), Space/Z (Jump), R (Respawn).
