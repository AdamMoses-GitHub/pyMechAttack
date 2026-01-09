# pyMechAttack
A turn-based tactical mech combat game built with Python and Pygame. Command a lance of four distinct mechs on hex-based battlefields in intense strategic warfare.

## About
pyMechAttack is a fully-featured tactical strategy game inspired by BattleTech, where players maneuver giant war machines across varied terrain, utilizing cover, line-of-sight mechanics, and dual weapon systems to outmaneuver and destroy their opponents.

## Key Features

### Multi-Player Combat
- **2-4 player support** with any combination of human and AI opponents
- **Initiative-based turn system** where faster mechs activate first
- **Configurable AI difficulty** with adjustable turn delays and strategic decision-making
- **Color-coded factions** for easy identification on the battlefield

### Four Distinct Mech Classes (per player)
- **Atlas** - Heavy assault mech with devastating firepower and thick armor
- **Centurion** - Balanced medium mech offering versatility
- **Griffin** - Fast medium striker for flanking maneuvers
- **Locust** - Light scout with exceptional speed and mobility

### Tactical Combat System
- **Dual weapon systems**: Reliable lasers and long-range missiles with different accuracy/damage profiles
- **Dual armor layers**: Armor and internal structure for realistic damage modeling
- **Two-phase turns**: Movement phase followed by attack phase
- **Advanced combat mechanics**: Range penalties, cover bonuses, and line-of-sight calculations
- **Terrain effects**: Five terrain types (Clear, Forest, Shallow Water, Deep Water, Mountains) affecting movement and combat

### Strategic Gameplay
- **Large 20x20 hex battlefields** with dynamic terrain generation
- **Sophisticated pathfinding** showing movement costs and optimal routes
- **Cover mechanics**: Forests provide defensive bonuses and reduce weapon range
- **Line-of-sight system**: Mountains block LOS completely, forests interfere
- **Tactical positioning**: Utilize terrain, range, and mech capabilities to gain advantage

### Polish & Features
- **Smooth 60 FPS animations** with weapon effects, explosions, and movement
- **Comprehensive UI**: Initiative tracker, combat log, detailed mech stats, and target information
- **Performance optimization**: Canvas caching, dirty rectangle tracking, and FPS monitoring
- **Configurable deployment**: Choose starting positions (Close/Medium/Far) for different gameplay styles
- **In-game help system**: Complete guide accessible anytime
- **Smart AI opponents**: Evaluates damage potential, cover, range, and target priority

## Requirements
- Python 3.x
- Pygame
- tkinter (usually included with Python)

## How to Play
1. Run the game and configure your match (player count, AI settings, deployment distance)
2. Select your mechs by clicking on them during your turn
3. Move by clicking on highlighted hexes within your movement range
4. Target enemies by clicking on them, then choose Laser or Missile weapons
5. Eliminate all enemy mechs to achieve victory!

## Controls
- **Click & drag**: Pan the battlefield view
- **Click mech**: Select/deselect your units
- **Click hex**: Move to location
- **Click enemy**: Target for attack
- **F1**: Toggle FPS display
- **Help button**: Access complete game guide
