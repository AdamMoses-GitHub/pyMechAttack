"""
Combat System Module
Handles all combat-related logic including weapon ranges, targeting, and attack execution.
"""
from typing import TYPE_CHECKING, Tuple, Optional

if TYPE_CHECKING:
    from entities import Mech, HexTile
    from game_state import GameState
    import hex_utils


class CombatSystem:
    """Manages combat mechanics including weapon ranges, targeting validation, and attack execution"""
    
    # Weapon configuration constants
    WEAPON_RANGES = {
        "laser": 8,
        "missile": 12
    }
    
    def __init__(self, game_state: 'GameState', hex_utils_module):
        """
        Initialize the combat system
        
        Args:
            game_state: Reference to the game state manager
            hex_utils_module: Reference to hex_utils module for LOS checks
        """
        self.state = game_state
        self.hex_utils = hex_utils_module
    
    def get_weapon_range(self, weapon_type: str) -> int:
        """Get the base range for a weapon type"""
        return self.WEAPON_RANGES.get(weapon_type, 0)
    
    def get_mechs_in_range(self, attacking_mech: 'Mech', weapon_type: str) -> list['Mech']:
        """
        Get all enemy mechs within range of the specified weapon and with clear LOS
        
        Args:
            attacking_mech: The mech attempting to attack
            weapon_type: Type of weapon ("laser" or "missile")
            
        Returns:
            List of mechs that are valid targets
        """
        base_range = self.get_weapon_range(weapon_type)
        if base_range == 0:
            return []
        
        targets = []
        for mech in self.state.mechs:
            if mech.player_id != attacking_mech.player_id and not mech.is_destroyed():
                distance = attacking_mech.hex_tile.distance_to(mech.hex_tile)
                
                # Check line of sight
                has_los, range_modifier = self.has_line_of_sight(
                    attacking_mech.hex_tile, 
                    mech.hex_tile
                )
                
                if has_los:
                    # Apply range reduction from forests
                    effective_range = base_range - range_modifier
                    if distance <= effective_range:
                        targets.append(mech)
        
        return targets
    
    def has_line_of_sight(self, from_hex: 'HexTile', to_hex: 'HexTile') -> Tuple[bool, int]:
        """
        Check line of sight between two hexes
        
        Args:
            from_hex: Starting hex tile
            to_hex: Target hex tile
            
        Returns:
            Tuple of (has_los: bool, range_modifier: int)
        """
        return self.hex_utils.has_line_of_sight(from_hex, to_hex, self.state.hex_tiles)
    
    def can_attack_target(self, attacker: 'Mech', target: 'Mech', weapon_type: str) -> Tuple[bool, str]:
        """
        Check if an attacker can attack a target with the specified weapon
        
        Args:
            attacker: The attacking mech
            target: The target mech
            weapon_type: Type of weapon to use
            
        Returns:
            Tuple of (can_attack: bool, reason: str)
        """
        # Check if target is destroyed
        if target.is_destroyed():
            return False, "Target is destroyed"
        
        # Check if same player
        if target.player_id == attacker.player_id:
            return False, "Cannot attack friendly units"
        
        # Check if attacker has already fired
        if attacker.has_fired:
            return False, "Already fired this turn"
        
        # Get weapon range
        weapon_range = self.get_weapon_range(weapon_type)
        if weapon_range == 0:
            return False, "Invalid weapon type"
        
        # Check distance
        distance = attacker.hex_tile.distance_to(target.hex_tile)
        if distance > weapon_range:
            return False, f"Target out of range (distance: {distance}, range: {weapon_range})"
        
        # Check line of sight
        has_los, range_modifier = self.has_line_of_sight(attacker.hex_tile, target.hex_tile)
        if not has_los:
            return False, "No line of sight to target"
        
        # Check effective range after terrain modifiers
        effective_range = weapon_range - range_modifier
        if distance > effective_range:
            return False, f"Target out of effective range due to terrain"
        
        return True, "Valid target"
    
    def calculate_hit_chance(self, attacker: 'Mech', target: 'Mech', weapon_type: str) -> float:
        """
        Calculate the hit chance for an attack
        
        This is a passthrough to the Mech class method, but allows for future
        centralized combat calculation modifications
        
        Args:
            attacker: The attacking mech
            target: The target mech
            weapon_type: Type of weapon to use
            
        Returns:
            Hit chance as a float between 0.0 and 1.0
        """
        return attacker.calculate_hit_chance(target, weapon_type)
    
    def execute_attack(self, attacker: 'Mech', target: 'Mech', weapon_type: str) -> dict:
        """
        Execute an attack from attacker to target
        
        This is a passthrough to the Mech class attack method, but provides
        a centralized point for attack execution
        
        Args:
            attacker: The attacking mech
            target: The target mech
            weapon_type: Type of weapon to use
            
        Returns:
            Dictionary with attack results (from Mech.attack method)
        """
        return attacker.attack(target, weapon_type)
    
    def find_optimal_attack_target(self, attacker: 'Mech', potential_targets: list['Mech']) -> Tuple[Optional['Mech'], Optional[str]]:
        """
        AI helper: Choose the best target and weapon for attacking
        
        Args:
            attacker: The mech looking for a target
            potential_targets: List of potential enemy targets
            
        Returns:
            Tuple of (best_target: Mech or None, best_weapon: str or None)
        """
        best_target = None
        best_weapon = None
        best_score = float('-inf')
        
        for target in potential_targets:
            if target.is_destroyed():
                continue
                
            distance = attacker.hex_tile.distance_to(target.hex_tile)
            has_los, range_modifier = self.has_line_of_sight(attacker.hex_tile, target.hex_tile)
            
            if not has_los:
                continue  # Can't attack without line of sight
            
            # Try both weapons
            for weapon_type in ["laser", "missile"]:
                weapon_range = self.get_weapon_range(weapon_type)
                
                if distance > weapon_range:
                    continue  # Out of range
                
                # Calculate hit chance and expected damage
                hit_chance = self.calculate_hit_chance(attacker, target, weapon_type)
                base_damage = attacker.stats.laser_attack if weapon_type == "laser" else attacker.stats.missile_attack
                expected_damage = hit_chance * base_damage
                
                # Calculate score for this attack
                score = expected_damage
                
                # Bonus for finishing off enemies
                target_health = target.stats.armor_hp + target.stats.structure_hp
                if expected_damage >= target_health:
                    score += 200  # Big bonus for potential kill
                
                # Prefer laser over missile when both are viable (more accurate)
                if weapon_type == "laser" and distance <= 8:
                    score += 10
                
                # Range penalty
                optimal_range = weapon_range // 2
                if distance > optimal_range:
                    range_penalty = (distance - optimal_range) * 5
                    score -= range_penalty
                
                if score > best_score:
                    best_score = score
                    best_target = target
                    best_weapon = weapon_type
        
        return best_target, best_weapon
    
    def should_ai_stop_moving_for_attack(self, mech: 'Mech', enemies: list['Mech']) -> bool:
        """
        AI helper: Determine if AI should stop moving and start attacking
        
        Args:
            mech: The AI mech considering whether to stop
            enemies: List of enemy mechs
            
        Returns:
            True if AI should stop moving and attack
        """
        if mech.get_remaining_movement() <= 0:
            return True
        
        # Check if we're in good attack position
        for enemy in enemies:
            if enemy.is_destroyed():
                continue
                
            distance = mech.hex_tile.distance_to(enemy.hex_tile)
            has_los, _ = self.has_line_of_sight(mech.hex_tile, enemy.hex_tile)
            
            # Stop if we can make a good laser attack
            if distance <= 8 and has_los:
                return True
            
            # Stop if we can make a decent missile attack and enemy is low on health
            if distance <= 10 and has_los:
                health_ratio = (enemy.stats.armor_hp + enemy.stats.structure_hp) / \
                               (enemy.stats.max_armor_hp + enemy.stats.max_structure_hp)
                if health_ratio < 0.4:  # Enemy is badly damaged
                    return True
        
        return False
    
    def get_enemies_for_mech(self, mech: 'Mech') -> list['Mech']:
        """
        Get all enemy mechs for the specified mech
        
        Args:
            mech: The mech to find enemies for
            
        Returns:
            List of enemy mechs (different player_id, not destroyed)
        """
        return [m for m in self.state.mechs 
                if m.player_id != mech.player_id and not m.is_destroyed()]
