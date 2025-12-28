# Slot Machine Bonus Game - Implementation Plan

## Feature Overview
**Trigger:** Kill 3+ turtles with a single Tetris move (line clear or hard drop)  
**Reward:** Spin a 3-reel slot machine with Mario character symbols  
**Win Condition:** Match 3 symbols for prizes  
**Jackpot:** Special grand prize available

---

## Design Specs

### Slot Reel Symbols
```python
SLOT_SYMBOLS = [
    'mario',      # Common - 100 points
    'luigi',      # Common - 100 points
    'mushroom',   # Uncommon - 250 points
    'star',       # Uncommon - 250 points
    'koopa',      # Uncommon - 200 points
    'coin',       # Common - 150 points
    'flower',     # Rare - 500 points
    '1up',        # Rare - 1 Extra Life
    'jackpot',    # Ultra Rare - 1000 points + bonus
]
```

### Win Conditions
- **3 Mario** = 500 points
- **3 Luigi** = 500 points
- **3 Mushroom** = 1000 points
- **3 Star** = Invincibility mode for 10 seconds
- **3 Coin** = 750 points
- **3 Flower** = 2000 points
- **3 1UP** = 3 Extra Lives
- **3 JACKPOT** = 5000 points + 5 lives + invincibility

### Animation Sequence
1. **Trigger Detection** - Flash screen, play fanfare sound
2. **Slot Intro** - Slide in slot machine graphic
3. **Spinning** - All 3 reels spin rapidly (2 seconds)
4. **Stop Sequence** - Reels stop left-to-right with sound
5. **Result** - Flash matching symbols, show prize popup
6. **Resume** - Return to gameplay with rewards applied

---

## Code Structure

### New Class: `SlotMachine`
```python
class SlotMachine:
    def __init__(self, sprite_manager):
        self.sprites = sprite_manager
        self.reels = [0, 0, 0]  # Current symbol index for each reel
        self.spinning = False
        self.spin_speed = 30  # Symbols per second
        self.stop_timers = [0, 0, 0]  # When each reel stops
        
    def trigger(self):
        """Start the slot machine"""
        self.spinning = True
        self.stop_timers = [2.0, 2.3, 2.6]  # Stagger stops
        
    def update(self, dt):
        """Update spinning animation"""
        if self.spinning:
            for i in range(3):
                if self.stop_timers[i] > 0:
                    self.stop_timers[i] -= dt
                    self.reels[i] = (self.reels[i] + 1) % len(SLOT_SYMBOLS)
                else:
                    # Reel stopped - lock in final value
                    pass
                    
    def draw(self, surface):
        """Draw the slot machine"""
        # Background
        # 3 Reel windows
        # Current symbols
        # Win highlights
        
    def check_win(self):
        """Check if player won"""
        if self.reels[0] == self.reels[1] == self.reels[2]:
            return SLOT_SYMBOLS[self.reels[0]]
        return None
```

### Integration Points

**1. Tetris.update() - Detection**
```python
# Track turtles killed in current action
turtles_killed_this_turn = 0

# When clearing lines or hard drop:
if turtles_killed_this_turn >= 3:
    self.trigger_slot_machine()
```

**2. Tetris.trigger_slot_machine()**
```python
def trigger_slot_machine(self):
    self.game_state = 'SLOT_MACHINE'
    self.slot_machine.trigger()
    self.sound_manager.play('slot_fanfare')
```

**3. New Game State**
```python
# In Tetris.update()
elif self.game_state == 'SLOT_MACHINE':
    self.slot_machine.update(dt)
    if self.slot_machine.finished:
        prize = self.slot_machine.check_win()
        self.award_prize(prize)
        self.game_state = 'PLAYING'
```

---

## Assets Needed

### Graphics
- [ ] Slot machine frame graphic
- [ ] Reel window backgrounds
- [ ] Symbol sprites (Mario, Luigi, Mushroom, etc.)
- [ ] Win effect sparkles/highlights
- [ ] "JACKPOT" banner

### Sounds
- [ ] Slot machine spin loop sound
- [ ] Reel stop "CLUNK" sound
- [ ] Win fanfare (different for regular vs jackpot)
- [ ] Trigger activation sound

---

## Implementation Steps

### Phase 1: Basic Detection (15 min)
1. Add counter for turtles killed per action
2. Add detection logic for 3+ kills
3. Add popup message "BONUS UNLOCKED!"

### Phase 2: Slot Machine Class (30 min)
1. Create SlotMachine class with basic structure
2. Implement spinning animation
3. Add reel stop sequence

### Phase 3: Visuals (30 min)
1. Design slot machine layout
2. Draw reels and symbols
3. Add win highlighting

### Phase 4: Rewards (15 min)
1. Implement win detection
2. Add reward distribution
3. Connect to player stats (score, lives, etc.)

### Phase 5: Polish (20 min)
1. Add sound effects
2. Smooth animations
3. Screen transitions
4. Testing and balancing

**Total Estimate: ~2 hours**

---

## Future Enhancements
- [ ] Near-miss animations (2 matching, 1 off)
- [ ] Progressive jackpot that grows over time
- [ ] Different slot themes for different worlds
- [ ] Combo bonuses for multiple slot wins in one game
- [ ] Leaderboard for biggest slot wins

---

## Testing Checklist
- [ ] 3 turtle kill triggers slot machine
- [ ] All symbols display correctly
- [ ] Reels spin smoothly
- [ ] Reels stop in sequence
- [ ] Wins detected correctly
- [ ] Rewards applied properly
- [ ] Game resumes normally after slot
- [ ] No crashes or freezes

---

**Status:** Ready to implement! 🎰
**Priority:** Medium (fun bonus feature)
**Complexity:** Medium (new mini-game system)
