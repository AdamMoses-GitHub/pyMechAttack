# PyMechAttack - Installation and Usage Guide

## Feature Recap

- **Turn-based tactical combat** on a hex grid with 2-4 players
- **AI-controlled opponents** with tactical decision-making
- **Procedurally generated terrain** (forests, water, mountains)
- **Movement and attack phases** with weapon selection (lasers, missiles)
- **Line-of-sight calculations** with terrain interference
- **Visual effects** for movement, weapon fire, and explosions
- **Initiative-based activation** order with automatic turn management

---

## Installation Guide

### Method A: Standard Python Installation (Recommended)

**Requirements:** Python 3.10 or higher

```bash
# 1. Clone the repository
git clone https://github.com/AdamMoses-GitHub/pyMechAttack.git
cd pyMechAttack

# 2. Verify Python version (must be 3.10+)
python --version

# 3. No additional dependencies required - uses only Python standard library
```

### Method B: Virtual Environment (Clean Install)

```bash
# 1. Clone the repository
git clone https://github.com/AdamMoses-GitHub/pyMechAttack.git
cd pyMechAttack

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# 4. Ready to run (no pip install needed)
```

**Note:** PyMechAttack has zero external dependencies beyond Python's standard library. Tkinter is included with standard Python distributions on Windows and macOS. On Linux, you may need to install `python3-tk` via your package manager.

---

## Usage - Execution

### Launching the Game

```bash
# From the project directory
python battletech_hex_game.py
```

### First-Time Setup

1. The **Game Setup Screen** will appear
2. Configure your game:
   - **Number of Players**: 2, 3, or 4
   - **AI Speed**: Fast (0.5s), Normal (1.0s), or Slow (2.0s) delay between AI actions
   - **Starting Proximity**: Close/Medium/Far (controls starting distance between players)
3. For each player slot, select:
   - **Player Type**: Human or AI
   - **Player Name**: Custom name or randomly generated AI commander name
4. Click **Start Game** to begin

---

## Usage - Workflows

### 1. Movement Phase - Tactical Positioning

**Scenario:** Your mech is out of range to attack the enemy. You need to move closer while avoiding impassable terrain and maintaining line of sight.

**Workflow:**
1. **Analyze Movement Range**: When your mech is activated (highlighted with pulsing border), all reachable hexes within your movement points are shown in light green
2. **Select Destination**: Left-click on any green hex to move your mech there
3. **Terrain Awareness**: Clear hexes cost 1 MP, forests cost 2 MP, water costs 3 MP. Mountains and deep water are impassable (dark blue/gray)
4. **Confirm Movement**: Your mech will animate to the new position, consuming movement points
5. **End Movement Phase**: When satisfied with positioning, click **"End Movement Phase"** to transition to the attack phase

**Example Use Case:** You start at hex (-5, -2) with 6 movement points. The enemy is 8 hexes away at (3, 4). You move through 2 clear hexes and 1 forest hex (1+1+2=4 MP used) to position at hex (-1, 2), now 5 hexes from the enemy—within laser range (8 hexes).

---

### 2. Attack Phase - Weapon Selection and Targeting

**Scenario:** You've positioned your mech within weapon range. Now you need to choose the right weapon and execute an attack.

**Workflow:**
1. **Select Target**: Left-click on an enemy mech to highlight it as your target
2. **Check Range**: Lasers have 8 hex range (high accuracy), missiles have 12 hex range (lower accuracy, higher damage variance)
3. **Choose Weapon**: Click **"Attack with Laser"** or **"Attack with Missile"** button
4. **Watch Results**: Combat log will display hit/miss status and damage dealt to armor/structure
5. **End Turn**: After attacking (or choosing not to), click **"End Turn"** to pass control to the next mech in initiative order

**Example Use Case:** Your mech targets an enemy 5 hexes away. You choose lasers for their 85% base accuracy. The attack hits, dealing 8 damage to the enemy's armor. If armor is depleted, excess damage carries over to internal structure. When structure reaches 0, the mech is destroyed.

---

### 3. Line of Sight and Terrain Effects

**Scenario:** There's a mountain hex between you and your target. You need to understand whether you can attack and how terrain affects your shot.

**Workflow:**
1. **Visual Indicators**: When you select an enemy mech, the game automatically calculates line-of-sight
2. **Blocking Terrain**: Mountains completely block LOS—if a mountain is in the line, the target won't be highlighted
3. **Forest Interference**: Each forest hex in the line reduces your effective weapon range by 1
4. **Cover Bonus**: If the target is standing IN a forest hex, they receive defensive bonuses (not the same as forests in the line)
5. **Repositioning**: If LOS is blocked, move to a different angle during movement phase

**Example Use Case:** You have a laser (range 8). The enemy is 7 hexes away, but there are 2 forest hexes in the line between you. Your effective range is reduced to 6 (8 - 2), so you cannot attack. You must move 1 hex closer or reposition to avoid the forest interference.

---

### 4. AI Opponent Behavior - Playing Against the Computer

**Scenario:** You're playing a 1v1 match against "Commander Steel." Understanding AI decision-making helps you predict and counter their moves.

**Workflow:**
1. **AI Activation**: When an AI mech's turn begins, it automatically evaluates all available moves
2. **Movement Logic**: AI calculates the best position that balances closing distance to enemies while avoiding poor terrain
3. **Target Selection**: AI prioritizes damaged mechs (easier kills) over full-health targets
4. **Weapon Choice**: AI selects weapons based on range—lasers for close/medium, missiles for long range
5. **Speed Control**: Adjust AI speed in setup screen (Fast/Normal/Slow) to watch their decision-making

**Example Use Case:** Commander Steel's mech activates with 6 MP. Your mech is at medium health 10 hexes away. The AI moves 4 hexes forward into optimal missile range, then fires missiles at you (12 hex range). The combat log shows "AI Assault Mech tactically moves to (2, 3) [Cost: 4]" then "AI Assault Mech missile attacks Player Mech: Hit! 12 damage..."

---

## Development

### Project Structure

```
pyMechAttack/
├── battletech_hex_game.py      # Main game class - coordinates all subsystems
├── entities.py                 # HexTile and Mech entity classes
├── models.py                   # Data classes (MechStats, MechPhase)
├── exceptions.py               # Custom exception hierarchy
├── game_state.py               # Game state manager (turn tracking, mech lists)
├── board_manager.py            # Hex board creation and terrain generation
├── combat_system.py            # Weapon ranges, targeting, attack execution
├── ai_controller.py            # AI decision-making and tactical planning
├── turn_manager.py             # Turn flow orchestration and initiative
├── turn_phase_handler.py       # Phase transition logic (movement/attack/done)
├── hex_utils.py                # Hex math, pathfinding (A*), LOS calculations
├── animations.py               # Animation data classes
├── animation_renderer.py       # Visual effects rendering on canvas
├── ui_game_window.py           # Main game window layout
├── ui_setup_screen.py          # Game configuration dialog
├── ui_info_panels.py           # Info panels (mech stats, initiative)
├── test_*.py                   # Unit tests for placement and phases
└── LICENSE                     # MIT License
```

### Key Directories and Files

- **battletech_hex_game.py**: Entry point. Instantiates all subsystems and manages the game loop.
- **entities.py**: Contains `HexTile` (terrain properties, coordinates) and `Mech` (stats, movement, attacks).
- **combat_system.py**: Centralizes weapon configuration and damage calculations.
- **ai_controller.py**: Contains 16 AI commander names and tactical evaluation algorithms.
- **hex_utils.py**: Pure functions for hex coordinate math and A* pathfinding.
- **ui_*.py modules**: Separation of UI concerns—setup screen, main window, info panels.
- **animations.py** + **animation_renderer.py**: Decoupled animation data from rendering logic.

### Running Tests

```bash
# Run placement tests
python test_placement.py
python test_placement_detailed.py

# Run phase handler tests
python test_phase_handler.py

# Run setup screen tests
python test_setup_screen.py
```

**Linter:** This project does not enforce a specific linter, but follows PEP 8 conventions. You can run:

```bash
# Optional: Check code style with flake8
pip install flake8
flake8 *.py --max-line-length=120
```

---

## Requirements

### Core Dependencies

- **Python 3.10+**: Uses structural pattern matching and enhanced type hints
- **Tkinter**: Bundled with Python on Windows/macOS. On Linux: `sudo apt install python3-tk`

### Standard Library Modules Used

- `tkinter` / `tkinter.ttk` - GUI framework
- `math` - Trigonometry for hex coordinate conversions
- `random` - Terrain generation and AI name selection
- `heapq` - Priority queue for A* pathfinding
- `time` - Performance metrics and FPS tracking
- `typing` - Type hints for code safety
- `dataclasses` - MechStats and WeaponConfig definitions
- `enum` - WeaponType and phase enumerations

**No external packages required.** This is intentional for portability and easy deployment.

---

## Gameplay Tips

### Strategic Considerations

1. **Initiative Matters**: Mechs with higher rolls activate first. Sometimes it's worth holding position to see what enemies do.
2. **Terrain is Your Friend**: Use forests for cover bonuses. Avoid deep water and mountains (impassable).
3. **Weapon Selection**: Lasers for consistency (high accuracy, low variance). Missiles for high-risk/high-reward (longer range, more variable damage).
4. **Armor vs. Structure**: Armor absorbs damage first. Once armor is gone, internal structure damage destroys the mech quickly.
5. **Movement Conservation**: You don't have to use all movement points. Sometimes staying still is better than overextending.

### AI Difficulty

The AI is competent but not unbeatable:
- **Strengths**: Never wastes movement points, always targets optimally, perfect LOS calculations
- **Weaknesses**: Predictable patterns (always closes distance), no feinting or psychological tactics
- **Counter Strategy**: Use terrain to force AI into suboptimal positions, focus fire to eliminate AI mechs quickly

---

## Troubleshooting

### "ImportError: No module named '_tkinter'"
- **Solution**: Install Tkinter for your OS:
  - **Ubuntu/Debian**: `sudo apt-get install python3-tk`
  - **Fedora**: `sudo dnf install python3-tkinter`
  - **macOS/Windows**: Should be bundled with Python

### Game Window Not Appearing
- **Solution**: Ensure you're running Python 3.10+ and that Tkinter is installed. Try running the setup screen test: `python test_setup_screen.py`

### Slow Performance
- **Solution**: The game includes canvas object caching and dirty-rectangle tracking. If still slow, reduce window size or disable animations (feature not yet exposed in UI—requires code modification in `battletech_hex_game.py`).

---

## Advanced Configuration

### Modifying Weapon Stats

Edit [combat_system.py](combat_system.py#L16-L23):

```python
CONFIGS = {
    "laser": WeaponConfig("Laser", 8, 0.85, 0.1, "high"),  # range, accuracy, variance
    "missile": WeaponConfig("Missile", 12, 0.70, 0.5, "low")
}
```

### Adjusting Terrain Distribution

Edit [board_manager.py](board_manager.py#L13-L19):

```python
TERRAIN_DISTRIBUTION = {
    "forest": 0.15,      # 15% forests
    "shallow_water": 0.10,
    "deep_water": 0.05,
    "mountain": 0.05,
    "clear": 0.65        # 65% clear terrain
}
```

### Adding New AI Names

Edit [ai_controller.py](ai_controller.py#L16-L21) or modify the setup screen's name list.

---

## Future Development Roadmap

- **Multiplayer Networking**: TCP/IP support for remote opponents
- **Save/Load Game State**: Persist games across sessions
- **More Mech Types**: Light/Medium/Heavy/Assault with different stats
- **Advanced Terrain**: Hills (elevation), lava, smoke effects
- **Sound Effects**: Audio feedback for weapons and movement
- **Replay System**: Review past turns and record matches

---

For bug reports or feature requests, please open an issue on [GitHub](https://github.com/AdamMoses-GitHub/pyMechAttack/issues).
