"""
pyMechAttack - Data Models Module
Contains data classes and enumerations for game entities
"""

from dataclasses import dataclass

@dataclass
class MechStats:
    """Represents the statistics of a mech"""
    name: str
    speed: int  # Movement points per turn
    laser_attack: int  # Laser weapon damage
    missile_attack: int  # Missile weapon damage
    armor_hp: int  # Armor hit points
    structure_hp: int  # Structure hit points
    max_armor_hp: int  # Maximum armor HP for display
    max_structure_hp: int  # Maximum structure HP for display

class MechPhase:
    """Enumeration for mech turn phases"""
    MOVEMENT = "movement"
    ATTACK = "attack"
    DONE = "done"
