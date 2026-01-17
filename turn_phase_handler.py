"""
pyMechAttack - Turn Phase Handler Module
Centralized management of mech turn phase transitions and action validation
"""

from typing import Callable, Dict, Optional, List
from models import MechPhase


class InvalidPhaseTransitionException(Exception):
    """Raised when an invalid phase transition is attempted"""
    pass


class TargetValidationResult:
    """Result of target validation check"""
    def __init__(self, valid: bool, reason: str, can_laser: bool = False, can_missile: bool = False):
        self.valid = valid
        self.reason = reason
        self.can_laser = can_laser
        self.can_missile = can_missile


class TurnPhaseHandler:
    """
    Manages mech turn phase transitions with validation and callbacks.
    
    Centralizes all phase logic to:
    - Prevent invalid state transitions
    - Provide consistent validation across UI and AI
    - Enable easy extension for future phase-dependent features
    - Maintain single source of truth for phase rules
    """
    
    # Valid phase transitions (from_phase -> to_phase)
    VALID_TRANSITIONS = {
        MechPhase.MOVEMENT: [MechPhase.ATTACK, MechPhase.DONE],
        MechPhase.ATTACK: [MechPhase.DONE],
        MechPhase.DONE: []  # Terminal state
    }
    
    def __init__(self, callbacks: Optional[Dict[str, Callable]] = None):
        """
        Initialize the phase handler
        
        Args:
            callbacks: Dictionary of optional callback functions:
                - 'on_phase_changed': Function(mech, old_phase, new_phase) called when phase changes
                - 'on_movement_ended': Function(mech) called when MOVEMENT→ATTACK
                - 'on_attack_ended': Function(mech) called when ATTACK→DONE
                - 'update_display': Function() to refresh display
                - 'update_buttons': Function() to refresh button states
                - 'log': Function(message: str) to log phase transitions
                - 'get_line_of_sight': Function(hex1, hex2) -> (has_los: bool, range_modifier: int)
        """
        self.callbacks = callbacks or {}
    
    def register_callback(self, callback_name: str, callback: Callable):
        """Register or update a callback"""
        self.callbacks[callback_name] = callback
    
    def advance_to_attack(self, mech: 'Mech') -> bool:
        """
        Transition mech from MOVEMENT to ATTACK phase
        
        Args:
            mech: The mech to advance
            
        Returns:
            True if transition succeeded, False otherwise
            
        Raises:
            InvalidPhaseTransitionException if transition is invalid
        """
        if mech.current_phase != MechPhase.MOVEMENT:
            raise InvalidPhaseTransitionException(
                f"Cannot advance to ATTACK: mech is in {mech.current_phase} phase, not MOVEMENT"
            )
        
        old_phase = mech.current_phase
        mech.current_phase = MechPhase.ATTACK
        
        # Fire callbacks
        if 'log' in self.callbacks:
            self.callbacks['log'](f"{mech.stats.name} ends movement phase")
        
        if 'on_movement_ended' in self.callbacks:
            self.callbacks['on_movement_ended'](mech)
        
        if 'on_phase_changed' in self.callbacks:
            self.callbacks['on_phase_changed'](mech, old_phase, MechPhase.ATTACK)
        
        if 'update_display' in self.callbacks:
            self.callbacks['update_display']()
        
        if 'update_buttons' in self.callbacks:
            self.callbacks['update_buttons']()
        
        return True
    
    def advance_to_done(self, mech: 'Mech', reason: str = "attack") -> bool:
        """
        Transition mech from ATTACK to DONE phase (end of turn)
        
        Args:
            mech: The mech to advance
            reason: Why the phase ended ("attack", "skip", "forfeit", etc.)
            
        Returns:
            True if transition succeeded, False otherwise
            
        Raises:
            InvalidPhaseTransitionException if transition is invalid
        """
        if mech.current_phase != MechPhase.ATTACK:
            raise InvalidPhaseTransitionException(
                f"Cannot advance to DONE: mech is in {mech.current_phase} phase, not ATTACK"
            )
        
        old_phase = mech.current_phase
        mech.current_phase = MechPhase.DONE
        
        # Fire callbacks
        if 'log' in self.callbacks:
            reason_str = f" ({reason})" if reason else ""
            self.callbacks['log'](f"{mech.stats.name} ends turn{reason_str}")
        
        if 'on_attack_ended' in self.callbacks:
            self.callbacks['on_attack_ended'](mech)
        
        if 'on_phase_changed' in self.callbacks:
            self.callbacks['on_phase_changed'](mech, old_phase, MechPhase.DONE)
        
        if 'update_display' in self.callbacks:
            self.callbacks['update_display']()
        
        if 'update_buttons' in self.callbacks:
            self.callbacks['update_buttons']()
        
        return True
    
    def reset_phase(self, mech: 'Mech'):
        """
        Reset mech to MOVEMENT phase at start of turn
        
        Args:
            mech: The mech to reset
        """
        old_phase = mech.current_phase
        mech.current_phase = MechPhase.MOVEMENT
        mech.has_moved = False
        mech.has_fired = False
        mech.movement_used = 0
        
        if 'on_phase_changed' in self.callbacks:
            self.callbacks['on_phase_changed'](mech, old_phase, MechPhase.MOVEMENT)
    
    def can_perform_action(self, mech: 'Mech', action: str) -> bool:
        """
        Validate if mech can perform a specific action in their current phase
        
        Args:
            action: Type of action ("move", "attack", "end_movement", "end_turn")
            
        Returns:
            True if action is allowed, False otherwise
        """
        # Check if mech is destroyed
        if mech.is_destroyed():
            return False
        
        if action == "move":
            return (mech.current_phase == MechPhase.MOVEMENT and 
                    mech.get_remaining_movement() > 0)
        
        elif action == "attack":
            return (mech.current_phase == MechPhase.ATTACK and 
                    not mech.has_fired)
        
        elif action == "end_movement":
            return mech.current_phase == MechPhase.MOVEMENT
        
        elif action == "end_turn":
            return mech.current_phase != MechPhase.DONE
        
        return False
    
    def get_phase_instructions(self, mech: 'Mech') -> str:
        """
        Get phase-appropriate instructions for the player
        
        Args:
            mech: The active mech
            
        Returns:
            Human-readable instruction string
        """
        if mech.is_destroyed():
            return "Mech is destroyed - cannot act"
        
        if mech.current_phase == MechPhase.MOVEMENT:
            remaining = mech.get_remaining_movement()
            if remaining > 0:
                return f"Green=Easy, Yellow=Moderate, Orange=Expensive movement ({remaining} points remaining). Click hex to move or End Movement"
            else:
                return "No movement remaining. Click End Movement to proceed to attack phase"
        
        elif mech.current_phase == MechPhase.ATTACK:
            if mech.has_fired:
                return "Attack complete - click End Turn"
            else:
                return "Select target and attack, or click End Turn to skip"
        
        elif mech.current_phase == MechPhase.DONE:
            return "Turn complete - click End Turn"
        
        return "Unknown phase"
    
    def get_phase_display_name(self, phase: str) -> str:
        """
        Get human-readable phase name
        
        Args:
            phase: Phase constant from MechPhase
            
        Returns:
            Display name
        """
        display_names = {
            MechPhase.MOVEMENT: "Movement",
            MechPhase.ATTACK: "Attack",
            MechPhase.DONE: "Done"
        }
        return display_names.get(phase, phase)
    
    def get_phase_color(self, phase: str) -> str:
        """
        Get UI color for phase display
        
        Args:
            phase: Phase constant from MechPhase
            
        Returns:
            Color string
        """
        colors = {
            MechPhase.MOVEMENT: "lightblue",
            MechPhase.ATTACK: "lightcoral",
            MechPhase.DONE: "lightgray"
        }
        return colors.get(phase, "white")
    
    def validate_phase_consistency(self, mech: 'Mech') -> List[str]:
        """
        Check for inconsistencies between phase state and action flags
        
        Useful for debugging and ensuring valid mech state.
        
        Args:
            mech: The mech to validate
            
        Returns:
            List of warning/error messages (empty if all consistent)
        """
        warnings = []
        
        # Check MOVEMENT phase consistency
        if mech.current_phase == MechPhase.MOVEMENT:
            if mech.has_fired:
                warnings.append(f"Mech {mech.stats.name} is in MOVEMENT phase but has_fired=True")
        
        # Check ATTACK phase consistency
        elif mech.current_phase == MechPhase.ATTACK:
            pass  # has_fired can be True or False in ATTACK phase
        
        # Check DONE phase consistency
        elif mech.current_phase == MechPhase.DONE:
            if not mech.has_moved and not mech.has_fired:
                warnings.append(f"Mech {mech.stats.name} is in DONE phase but didn't move or fire")
        
        return warnings
