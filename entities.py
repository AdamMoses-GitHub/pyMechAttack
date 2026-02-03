"""
pyMechAttack - Entity Classes Module
Contains HexTile and Mech classes representing game entities
"""

from typing import Optional, Dict, Tuple, Callable
import random
from models import MechStats, MechPhase
from exceptions import (
    InvalidMoveException, InvalidTargetException,
    InvalidPhaseException, MechDestroyedException,
    InvalidWeaponException, InsufficientMovementException
)


class HexTile:
    """Represents a single hex tile on the board"""
    
    # Terrain properties: (movement_cost, blocks_movement, blocks_line_of_sight, provides_cover, color)
    TERRAIN_PROPERTIES = {
        "clear": {"cost": 1, "blocks_move": False, "blocks_los": False, "cover": False, "color": "lightgreen", "name": "Clear"},
        "forest": {"cost": 2, "blocks_move": False, "blocks_los": False, "cover": True, "color": "darkgreen", "name": "Forest"},
        "shallow_water": {"cost": 3, "blocks_move": False, "blocks_los": False, "cover": False, "color": "lightblue", "name": "Shallow Water"},
        "deep_water": {"cost": 999, "blocks_move": True, "blocks_los": False, "cover": False, "color": "darkblue", "name": "Deep Water"},
        "mountain": {"cost": 999, "blocks_move": True, "blocks_los": True, "cover": False, "color": "darkgray", "name": "Mountain"}
    }
    
    def __init__(self, q: int, r: int, terrain_type: str = "clear"):
        self.q = q  # Axial coordinates
        self.r = r
        self.s = -q - r  # Derived coordinate
        self.terrain_type = terrain_type
        self.mech: Optional['Mech'] = None  # Reference to mech occupying this tile
        
    def distance_to(self, other: 'HexTile') -> int:
        """Calculate hex distance to another tile"""
        return (abs(self.q - other.q) + abs(self.q + self.r - other.q - other.r) + abs(self.r - other.r)) // 2
    
    def get_movement_cost(self) -> int:
        """Get movement cost for this terrain"""
        return self.TERRAIN_PROPERTIES[self.terrain_type]["cost"]
    
    def blocks_movement(self) -> bool:
        """Check if this terrain blocks movement"""
        return self.TERRAIN_PROPERTIES[self.terrain_type]["blocks_move"]
    
    def blocks_line_of_sight(self) -> bool:
        """Check if this terrain blocks line of sight"""
        return self.TERRAIN_PROPERTIES[self.terrain_type]["blocks_los"]
    
    def provides_cover(self) -> bool:
        """Check if this terrain provides cover"""
        return self.TERRAIN_PROPERTIES[self.terrain_type]["cover"]
    
    def get_color(self) -> str:
        """Get display color for this terrain"""
        return self.TERRAIN_PROPERTIES[self.terrain_type]["color"]
    
    def get_terrain_name(self) -> str:
        """Get human-readable terrain name"""
        return self.TERRAIN_PROPERTIES[self.terrain_type]["name"]


class Mech:
    """Represents a mech unit"""
    def __init__(self, player_id: int, stats: MechStats, hex_tile: HexTile):
        self.player_id = player_id
        self.stats = stats
        self.hex_tile = hex_tile
        self.has_moved = False  # Track if mech has moved this turn
        self.has_fired = False
        self.current_phase = MechPhase.MOVEMENT  # Current phase of the turn
        self.movement_used = 0  # Track movement points used
        # Color will be set by game instance when creating mechs
        self.color = "gray"  # Default color, will be overridden
        
        # Callbacks for game interactions (replaces _game_ref)
        self.on_move_animation: Optional[Callable] = None  # Callback for starting movement animation
        self.on_hex_dirty: Optional[Callable] = None  # Callback for marking hexes dirty
        self.get_line_of_sight: Optional[Callable] = None  # Callback for LOS checks
        
        hex_tile.mech = self
        
    def move_to(self, new_hex: HexTile, path_cost: int) -> bool:
        """Move mech to a new hex tile if the path cost is within speed limit"""
        # Enhanced input validation with exceptions
        if not isinstance(new_hex, HexTile):
            raise InvalidMoveException(f"new_hex must be HexTile, got {type(new_hex)}")
        if not isinstance(path_cost, int) or path_cost < 0:
            raise InvalidMoveException(f"path_cost must be non-negative integer, got {path_cost}")
            
        if self.current_phase != MechPhase.MOVEMENT:
            raise InvalidPhaseException(f"Cannot move during {self.current_phase} phase")
            
        if new_hex.mech is not None:
            raise InvalidMoveException(f"Hex ({new_hex.q}, {new_hex.r}) is occupied by {new_hex.mech.stats.name}")
            
        if new_hex.blocks_movement():
            raise InvalidMoveException(f"Terrain type '{new_hex.terrain_type}' blocks movement")
            
        # Check if the total path cost would exceed remaining movement
        if self.movement_used + path_cost > self.stats.speed:
            remaining = self.stats.speed - self.movement_used
            raise InsufficientMovementException(f"Need {path_cost} movement, have {remaining} remaining")
            
        # Update positions
        old_hex = self.hex_tile
        self.hex_tile.mech = None
        self.hex_tile = new_hex
        new_hex.mech = self
        self.movement_used += path_cost
        
        # Trigger callbacks if they exist
        if self.on_move_animation:
            self.on_move_animation(self, old_hex, new_hex)
        if self.on_hex_dirty:
            self.on_hex_dirty(old_hex.q, old_hex.r)
            self.on_hex_dirty(new_hex.q, new_hex.r)
        
        # Mark as moved if any movement was used
        if self.movement_used > 0:
            self.has_moved = True
        
        return True
    
    def can_attack(self, target: 'Mech') -> bool:
        """Check if this mech can attack the target"""
        if self.has_fired:
            return False
        distance = self.hex_tile.distance_to(target.hex_tile)
        # Laser range: 8 hexes, Missile range: 12 hexes
        return distance <= 12
    
    def attack(self, target: 'Mech', weapon_type: str) -> Dict:
        """Attack another mech"""
        # Enhanced input validation with exceptions
        if not isinstance(target, Mech):
            raise InvalidTargetException(f"Invalid target type: {type(target)}")
        if not isinstance(weapon_type, str):
            raise InvalidWeaponException(f"Invalid weapon type: {type(weapon_type)}")
        if target.is_destroyed():
            raise MechDestroyedException("Cannot attack destroyed mech")
        if self.is_destroyed():
            raise MechDestroyedException("Destroyed mech cannot attack")
            
        if not self.can_attack(target):
            raise InvalidTargetException("Cannot attack target")
            
        distance = self.hex_tile.distance_to(target.hex_tile)
        
        # Determine weapon range and base damage
        if weapon_type == "laser":
            if distance > 8:
                return {"hit": False, "damage": 0, "message": "Target out of laser range"}
            base_damage = self.stats.laser_attack
        elif weapon_type == "missile":
            if distance > 12:
                return {"hit": False, "damage": 0, "message": "Target out of missile range"}
            base_damage = self.stats.missile_attack
        else:
            return {"hit": False, "damage": 0, "message": "Invalid weapon type"}
        
        # Check line of sight - this will be checked in calculate_hit_chance
        # Calculate hit chance (includes LOS check)
        hit_chance = self.calculate_hit_chance(target, weapon_type)
        
        # If hit chance is 0, it means no LOS or out of range
        if hit_chance <= 0:
            self.has_fired = True
            return {"hit": False, "damage": 0, "message": "No line of sight to target or out of range!"}
        
        # Cover message
        cover_message = " (target in cover)" if target.hex_tile.provides_cover() else ""
        
        # Roll for hit/miss and log the result
        random_roll = random.randint(1, 100)  # Roll 1-100 for percentage
        hit_chance_percent = int(hit_chance * 100)  # Convert to integer percentage
        
        if random_roll > hit_chance_percent:
            self.has_fired = True
            return {"hit": False, "damage": 0, "message": f"Attack missed! (Rolled {random_roll}%, needed ≤{hit_chance_percent}%){cover_message}"}
        
        # Calculate damage based on weapon type
        if weapon_type == "laser":
            # Lasers do consistent damage (minimal variance)
            damage_dealt = base_damage + random.randint(-1, 1)  # Very consistent
            damage_type = "Laser"
        else:  # missile
            # Missiles do highly variable damage (explosive effect)
            variance = base_damage // 2  # 50% variance range
            damage_dealt = base_damage + random.randint(-variance, variance * 2)  # Can do up to 150% damage
            damage_dealt = max(1, damage_dealt)  # Minimum 1 damage
            damage_type = "Missile"
        
        # Apply damage (armor first, then structure)
        armor_damage = min(damage_dealt, target.stats.armor_hp)
        target.stats.armor_hp -= armor_damage
        remaining_damage = damage_dealt - armor_damage
        
        structure_damage = 0
        if remaining_damage > 0:
            structure_damage = min(remaining_damage, target.stats.structure_hp)
            target.stats.structure_hp -= structure_damage
        
        self.has_fired = True
        
        # Create damage message with weapon-specific flavor and roll info
        if weapon_type == "laser":
            if damage_dealt >= base_damage:
                hit_quality = "Clean hit!"
            else:
                hit_quality = "Glancing hit."
        else:  # missile
            if damage_dealt >= base_damage * 1.3:
                hit_quality = "Critical hit! Explosions rock the target!"
            elif damage_dealt >= base_damage:
                hit_quality = "Solid hit!"
            else:
                hit_quality = "Partial hit - some missiles missed."
        
        message = f"{damage_type} - {hit_quality} {damage_dealt} damage! (Rolled {random_roll}%, needed ≤{hit_chance_percent}%)"
        if structure_damage > 0:
            message += f" ({armor_damage} armor, {structure_damage} structure)"
        else:
            message += f" ({armor_damage} armor)"
        
        if target.hex_tile.provides_cover():
            message += " [Cover penetrated]"
            
        return {
            "hit": True, 
            "damage": damage_dealt,
            "armor_damage": armor_damage,
            "structure_damage": structure_damage,
            "message": message
        }
    
    def round_hex_coords(self, q: float, r: float) -> Tuple[int, int]:
        """Round fractional hex coordinates to nearest hex"""
        s = -q - r
        rq = round(q)
        rr = round(r)
        rs = round(s)
        
        q_diff = abs(rq - q)
        r_diff = abs(rr - r)
        s_diff = abs(rs - s)
        
        if q_diff > r_diff and q_diff > s_diff:
            rq = -rr - rs
        elif r_diff > s_diff:
            rr = -rq - rs
        
        return rq, rr
    
    def is_destroyed(self) -> bool:
        """Check if mech is destroyed"""
        return self.stats.structure_hp <= 0
    
    def start_turn(self):
        """Reset turn-based variables"""
        self.has_moved = False
        self.has_fired = False
        self.current_phase = MechPhase.MOVEMENT
        self.movement_used = 0
    
    def get_remaining_movement(self) -> int:
        """Get remaining movement points for this turn"""
        return max(0, self.stats.speed - self.movement_used)
    
    def can_still_move(self) -> bool:
        """Check if mech has movement points remaining"""
        return self.current_phase == MechPhase.MOVEMENT and self.get_remaining_movement() > 0
    
    def calculate_hit_chance(self, target: 'Mech', weapon_type: str) -> float:
        """
        Calculate probability of hitting target with specified weapon.
        
        Combat Formula:
        - Base accuracy: 0.85 for lasers (85%), 0.70 for missiles (70%)
        - Range penalty: -5% per hex beyond optimal range (half of weapon's max range)
        - Cover penalty: -30% if target is in forest terrain
        - Forest LOS penalty: -10% per forest hex in line of sight
        - LOS requirement: Returns 0.0 if no line of sight or out of range
        
        Args:
            target: The Mech being targeted
            weapon_type: "laser" (range 8, accurate) or "missile" (range 12, less accurate)
            
        Returns:
            Float between 0.0 and 1.0 representing hit probability
            
        Example:
            >>> mech.calculate_hit_chance(enemy, "laser")  # 6 hexes away, in forest
            0.50  # 85% base - 10% range penalty - 30% cover - 10% forest LOS
        """
        distance = self.hex_tile.distance_to(target.hex_tile)
        
        # Check line of sight using callback if available
        range_modifier = 0
        if self.get_line_of_sight:
            has_los, range_modifier = self.get_line_of_sight(self.hex_tile, target.hex_tile)
            if not has_los:
                return 0.0  # No line of sight = no hit possible
        else:
            # Fallback: assume clear LOS if callback not available
            range_modifier = 0
        
        # Get weapon stats
        if weapon_type == "laser":
            base_range = 8
            base_accuracy = 0.85  # Lasers are more accurate
        elif weapon_type == "missile":
            base_range = 12
            base_accuracy = 0.70  # Missiles are less accurate but longer range
        else:
            return 0.0
        
        # Apply range reduction from forests
        effective_range = base_range - range_modifier
        
        # Check if target is within effective range
        if distance > effective_range:
            return 0.0
        
        # Calculate hit chance
        hit_chance = base_accuracy
        
        # Range penalty: -5% per hex beyond optimal range (half of max range)
        optimal_range = effective_range // 2
        if distance > optimal_range:
            range_penalty = (distance - optimal_range) * 0.05
            hit_chance -= range_penalty
        
        # Cover bonus for target
        if target.hex_tile.provides_cover():
            hit_chance -= 0.30
        
        # Forest LOS penalty - additional accuracy reduction for each forest hex
        if range_modifier > 0:
            forest_penalty = range_modifier * 0.10  # -10% per forest hex
            hit_chance -= forest_penalty
        
        return max(0.0, min(1.0, hit_chance))
