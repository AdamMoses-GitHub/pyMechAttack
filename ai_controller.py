"""
AI Controller Module
Handles all AI decision-making, turn execution, movement evaluation, and tactical planning.
"""
from typing import TYPE_CHECKING, Tuple, Optional, Callable, Dict, Any

if TYPE_CHECKING:
    from entities import Mech, HexTile
    from game_state import GameState
    from combat_system import CombatSystem
    import hex_utils

from models import MechPhase


class AIController:
    """Manages AI tactical decision-making and turn execution"""
    
    # AI Commander names for random selection
    AI_NAMES = [
        "Commander Steel", "Major Forge", "Captain Titan", "Colonel Storm",
        "General Viper", "Marshal Kane", "Admiral Rex", "Commander Nova",
        "Major Blitz", "Captain Razor", "Colonel Frost", "General Phoenix",
        "Marshal Thunder", "Admiral Hawk", "Commander Bolt", "Major Reaper"
    ]
    
    def __init__(self, game_state: 'GameState', combat_system: 'CombatSystem', 
                 hex_utils_module, ui_callbacks: Dict[str, Callable]):
        """
        Initialize the AI controller
        
        Args:
            game_state: Reference to the game state manager
            combat_system: Reference to the combat system
            hex_utils_module: Reference to hex_utils module for pathfinding/LOS
            ui_callbacks: Dictionary of UI callback functions:
                - 'log': Function to log messages
                - 'end_turn': Function to end the current turn
                - 'update_display': Function to refresh UI
                - 'check_victory': Function to check win conditions
                - 'schedule_action': Function to schedule delayed actions (root.after wrapper)
                - 'calculate_reachable': Function to calculate reachable hexes
                - 'has_line_of_sight': Function to check LOS between hexes
                - 'advance_to_attack': Function(mech) to transition from movement to attack phase
                - 'advance_to_done': Function(mech) to transition from attack to done phase
        """
        self.state = game_state
        self.combat = combat_system
        self.hex_utils = hex_utils_module
        self.callbacks = ui_callbacks
        
        # AI decision caching for performance optimization
        self.cache = {
            'position_scores': {},  # Maps (mech_id, q, r, enemies_hash) -> score
            'target_evaluations': {},  # Reserved for future use
            'cache_hits': 0,  # Performance metric
            'cache_misses': 0  # Performance metric
        }
    
    def clear_cache(self):
        """Clear AI decision cache (called at start of each turn)"""
        self.cache['position_scores'].clear()
        self.cache['target_evaluations'].clear()
    
    def get_ai_names(self) -> list[str]:
        """Get list of available AI commander names"""
        return self.AI_NAMES.copy()
    
    def execute_turn(self, mech: 'Mech'):
        """
        Execute a complete AI turn for the specified mech
        
        This is the main AI controller method that handles movement and attack phases.
        
        Args:
            mech: The AI mech executing its turn
        """
        if mech.is_destroyed():
            self.callbacks['end_turn']()
            return
            
        # Find enemies (mechs from all other players)
        enemies = self.get_enemies_for_mech(mech)
        if not enemies:
            self.callbacks['end_turn']()
            return
        
        self.callbacks['log'](f"AI {mech.stats.name} begins turn")
        
        # Phase 1: Movement Phase
        if mech.current_phase == MechPhase.MOVEMENT:
            self._execute_movement_phase(mech, enemies)
            return  # May schedule continuation, so return early
        
        # Phase 2: Attack Phase
        if mech.current_phase == MechPhase.ATTACK:
            self._execute_attack_phase(mech, enemies)
        
        # End AI turn
        self.callbacks['log'](f"AI {mech.stats.name} ends turn")
        self.callbacks['end_turn']()
    
    def _execute_movement_phase(self, mech: 'Mech', enemies: list['Mech']):
        """Execute the movement phase for an AI mech"""
        best_position = self.find_optimal_position(mech, enemies)
        if best_position:
            target_hex = self.state.hex_tiles[best_position]
            reachable = self.callbacks['calculate_reachable'](mech.hex_tile, mech.get_remaining_movement())
            if best_position in reachable:
                move_cost = reachable[best_position]
                if mech.move_to(target_hex, move_cost):
                    self.callbacks['log'](
                        f"AI {mech.stats.name} tactically moves to "
                        f"({best_position[0]}, {best_position[1]}) [Cost: {move_cost}]"
                    )
                    
                    # Check if should continue moving or advance to attack
                    if mech.get_remaining_movement() <= 0 or self.should_stop_moving(mech, enemies):
                        self.callbacks['advance_to_attack'](mech)
                        # Continue to attack phase immediately
                        self._execute_attack_phase(mech, enemies)
                        self.callbacks['log'](f"AI {mech.stats.name} ends turn")
                        self.callbacks['end_turn']()
                    else:
                        # Continue movement next update cycle with half speed for visual feedback
                        self.schedule_action(lambda: self.execute_turn(mech), 0.5)
                    return
                else:
                    self.callbacks['advance_to_attack'](mech)
            else:
                self.callbacks['advance_to_attack'](mech)
        else:
            self.callbacks['advance_to_attack'](mech)
        
        # If we didn't return above, movement phase is complete
        self._execute_attack_phase(mech, enemies)
        self.callbacks['log'](f"AI {mech.stats.name} ends turn")
        self.callbacks['end_turn']()
    
    def _execute_attack_phase(self, mech: 'Mech', enemies: list['Mech']):
        """Execute the attack phase for an AI mech"""
        target, weapon = self.choose_target_and_weapon(mech, enemies)
        if target and weapon and not mech.has_fired:
            result = mech.attack(target, weapon)
            weapon_name = "laser" if weapon == "laser" else "missile"
            self.callbacks['log'](
                f"AI {mech.stats.name} {weapon_name} attacks {target.stats.name}: {result['message']}"
            )
            
            if target.is_destroyed():
                self.callbacks['log'](f"{target.stats.name} is destroyed!")
                self.callbacks['check_victory']()
    
    def schedule_action(self, action_func: Callable, delay_multiplier: float = 1.0):
        """
        Schedule an AI action with appropriate delay
        
        Args:
            action_func: Function to execute after delay
            delay_multiplier: Multiplier for AI action speed (0.5 = half speed, 1.0 = full speed)
        """
        self.callbacks['schedule_action'](action_func, delay_multiplier)
    
    def find_optimal_position(self, mech: 'Mech', enemies: list['Mech']) -> Optional[Tuple[int, int]]:
        """
        Find the best position for the AI mech to move to
        
        Args:
            mech: The AI mech looking for a position
            enemies: List of enemy mechs
            
        Returns:
            Tuple of (q, r) coordinates for best position, or None if no good move
        """
        reachable = self.callbacks['calculate_reachable'](mech.hex_tile, mech.get_remaining_movement())
        best_position = None
        best_score = float('-inf')
        
        current_position = (mech.hex_tile.q, mech.hex_tile.r)
        
        for (q, r), cost in reachable.items():
            if (q, r) == current_position:
                continue  # Skip current position
                
            if (q, r) in self.state.hex_tiles:
                hex_tile = self.state.hex_tiles[(q, r)]
                if hex_tile.mech:  # Occupied
                    continue
                    
                score = self.evaluate_position(hex_tile, mech, enemies)
                if score > best_score:
                    best_score = score
                    best_position = (q, r)
        
        return best_position
    
    def evaluate_position(self, position: 'HexTile', mech: 'Mech', enemies: list['Mech']) -> float:
        """
        Evaluate how good a position is for the AI mech
        
        Uses caching to avoid redundant calculations for performance.
        
        Args:
            position: The hex position to evaluate
            mech: The AI mech considering this position
            enemies: List of enemy mechs
            
        Returns:
            Numerical score for the position (higher is better)
        """
        # Create cache key based on position and enemy positions/health
        enemies_hash = hash(tuple(
            (e.hex_tile.q, e.hex_tile.r, e.stats.armor_hp, e.stats.structure_hp) 
            for e in enemies
        ))
        cache_key = (id(mech), position.q, position.r, enemies_hash)
        
        # Check cache first
        if cache_key in self.cache['position_scores']:
            self.cache['cache_hits'] += 1
            return self.cache['position_scores'][cache_key]
        
        self.cache['cache_misses'] += 1
        
        score = 0.0
        
        # Find the best target from this position
        best_target = None
        best_target_score = float('-inf')
        
        for enemy in enemies:
            distance = position.distance_to(enemy.hex_tile)
            
            # Target prioritization
            target_score = 0.0
            
            # Prefer damaged enemies (easier to destroy)
            health_ratio = (enemy.stats.armor_hp + enemy.stats.structure_hp) / \
                          (enemy.stats.max_armor_hp + enemy.stats.max_structure_hp)
            target_score += (1.0 - health_ratio) * 100  # Up to 100 points for low health
            
            # Prefer closer enemies
            if distance <= 12:  # In missile range
                target_score += (12 - distance) * 10  # Closer is better
            
            # Prefer enemies we can attack effectively
            has_los, _ = self.callbacks['has_line_of_sight'](position, enemy.hex_tile)
            if has_los:
                if distance <= 8:  # Laser range - preferred
                    target_score += 50
                elif distance <= 12:  # Missile range
                    target_score += 30
            else:
                target_score -= 50  # Penalize no line of sight
            
            if target_score > best_target_score:
                best_target_score = target_score
                best_target = enemy
        
        if best_target:
            distance_to_target = position.distance_to(best_target.hex_tile)
            
            # Range considerations
            if distance_to_target <= 8:
                score += 60  # Excellent - in laser range
            elif distance_to_target <= 10:
                score += 40  # Good - close to laser range
            elif distance_to_target <= 12:
                score += 20  # OK - in missile range
            else:
                score -= 20  # Poor - out of range
            
            # Line of sight bonus
            has_los, range_modifier = self.callbacks['has_line_of_sight'](position, best_target.hex_tile)
            if has_los:
                score += 30
            else:
                score -= 40
            
            # Cover considerations
            if position.provides_cover():
                score += 25  # Defensive bonus
            
            # Avoid clustering with friendly mechs
            for friendly in self.state.mechs:
                if friendly.player_id == mech.player_id and not friendly.is_destroyed() and friendly != mech:
                    friendly_distance = position.distance_to(friendly.hex_tile)
                    if friendly_distance <= 2:
                        score -= 15  # Penalize clustering
            
            # Terrain movement cost penalty
            score -= position.get_movement_cost() * 2
        
        # Cache the result
        self.cache['position_scores'][cache_key] = score
        
        return score
    
    def should_stop_moving(self, mech: 'Mech', enemies: list['Mech']) -> bool:
        """
        Determine if AI should stop moving and start attacking
        
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
            has_los, _ = self.callbacks['has_line_of_sight'](mech.hex_tile, enemy.hex_tile)
            
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
    
    def choose_target_and_weapon(self, mech: 'Mech', enemies: list['Mech']) -> Tuple[Optional['Mech'], Optional[str]]:
        """
        Choose the best target and weapon for attacking
        
        Args:
            mech: The AI mech choosing a target
            enemies: List of potential enemy targets
            
        Returns:
            Tuple of (best_target: Mech or None, best_weapon: str or None)
        """
        best_target = None
        best_weapon = None
        best_score = float('-inf')
        
        for target in enemies:
            if target.is_destroyed():
                continue
                
            distance = mech.hex_tile.distance_to(target.hex_tile)
            has_los, range_modifier = self.callbacks['has_line_of_sight'](mech.hex_tile, target.hex_tile)
            
            if not has_los:
                continue  # Can't attack without line of sight
            
            # Try both weapons
            for weapon_type in ["laser", "missile"]:
                weapon_range = self.combat.get_weapon_range(weapon_type)
                
                if distance > weapon_range:
                    continue  # Out of range
                
                # Calculate hit chance and expected damage
                hit_chance = self.combat.calculate_hit_chance(mech, target, weapon_type)
                base_damage = mech.stats.laser_attack if weapon_type == "laser" else mech.stats.missile_attack
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
