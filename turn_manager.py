"""
Turn Manager Module
Handles turn flow orchestration, initiative ordering, mech activation, and phase transitions.
"""
from typing import TYPE_CHECKING, Optional, Callable, Dict, List, Tuple
from tkinter import messagebox

if TYPE_CHECKING:
    from entities import Mech
    from game_state import GameState

from models import MechPhase
from turn_phase_handler import TurnPhaseHandler


class TurnManager:
    """Manages turn flow, initiative, and mech activation"""
    
    def __init__(self, game_state: 'GameState', callbacks: Dict[str, Callable]):
        """
        Initialize the turn manager
        
        Args:
            game_state: Reference to the game state manager
            callbacks: Dictionary of callback functions:
                - 'log': Function(message: str) to log messages
                - 'on_turn_changed': Function(turn_number: int) to update turn UI
                - 'on_mech_activated': Function(mech: Mech) to update active mech UI
                - 'on_initiative_updated': Function(initiative_data: list) to refresh initiative display
                - 'on_mech_selected': Function(mech: Mech) to start pulse animation
                - 'on_mech_deselected': Function(mech: Mech) to stop pulse animation
                - 'update_display': Function() to refresh game display
                - 'update_attack_buttons': Function() to refresh button states
                - 'check_victory': Function() to check win conditions
                - 'is_ai_player': Function(player_id: int) -> bool to check if player is AI
                - 'schedule_ai_action': Function(callback: Callable) to schedule AI turn
                - 'clear_ai_cache': Function() to clear AI decision cache
        """
        self.state = game_state
        self.callbacks = callbacks
        
        # Initialize phase handler with shared callbacks
        phase_handler_callbacks = {
            'log': callbacks.get('log'),
            'update_display': callbacks.get('update_display'),
            'update_buttons': callbacks.get('update_attack_buttons')
        }
        self.phase_handler = TurnPhaseHandler(phase_handler_callbacks)
    
    def initialize_first_turn(self):
        """
        Initialize the first turn without incrementing turn counter
        
        This is called at game start to set up turn 1.
        """
        # Reset all mechs for their first turn
        for mech in self.state.mechs:
            if not mech.is_destroyed():
                mech.start_turn()
        
        # Calculate initial initiative order
        self.state.update_initiative_order()
        
        # Clear selections
        self.state.clear_selection()
        
        # Clear AI cache for new turn
        self.callbacks['clear_ai_cache']()
        
        self.callbacks['log'](f"=== TURN {self.state.current_turn} ===")
        self.callbacks['log']("Initial initiative order calculated!")
        
        # Update initiative display
        self._update_initiative_ui()
        
        # Activate the first mech
        self.activate_next_mech()
    
    def start_new_turn(self):
        """
        Start a new turn (increment counter, reset mechs, recalculate initiative)
        
        This is called when all mechs have completed their turns.
        """
        if self.state.game_over:
            return
        
        # Clear AI cache for new turn
        self.callbacks['clear_ai_cache']()
        
        # Increment turn counter via state manager
        self.state.start_new_turn()
        
        # Update turn UI
        self.callbacks['on_turn_changed'](self.state.current_turn)
        
        # Reset all living mechs for the new turn
        for mech in self.state.mechs:
            if not mech.is_destroyed():
                mech.start_turn()
        
        # Recalculate initiative order (includes destroyed mechs at bottom)
        self.state.update_initiative_order()
        
        # Check if any alive mechs remain
        alive_mechs = self.state.get_alive_mechs()
        if not alive_mechs:
            self.callbacks['log']("All mechs destroyed!")
            self.state.game_over = True
            return
        
        self.callbacks['log'](f"=== TURN {self.state.current_turn} ===")
        
        # Activate the first mech in new turn
        self.activate_next_mech()
    
    def end_current_turn(self):
        """
        End the current mech's turn and advance to next mech or start new turn
        
        This handles the progression after a mech completes their actions.
        """
        try:
            if self.state.game_over:
                return
            
            # Use state manager to advance to next mech
            if not self.state.advance_to_next_mech():
                # All mechs have acted, start new turn
                self.start_new_turn()
            else:
                # Continue with next mech in current turn
                self.activate_next_mech()
        except Exception as e:
            messagebox.showerror("Turn Error", f"Error ending turn: {str(e)}")
            print(f"Error in end_current_turn: {str(e)}")
    
    def activate_next_mech(self):
        """
        Activate the next mech in initiative order
        
        Skips destroyed mechs and sets up the active mech for their turn.
        Handles both AI and human player mechs differently.
        """
        # Skip destroyed mechs in activation
        while (self.state.current_mech_index < len(self.state.initiative_order) and 
               self.state.initiative_order[self.state.current_mech_index].is_destroyed()):
            self.state.current_mech_index += 1
        
        if self.state.current_mech_index < len(self.state.initiative_order):
            current_mech = self.state.initiative_order[self.state.current_mech_index]
            
            # Update active mech UI
            self.callbacks['on_mech_activated'](current_mech)
            
            # Clear previous target selection
            self.state.set_target(None)
            
            # Check if current mech belongs to an AI player
            player_info = self.state.players[current_mech.player_id - 1]
            is_ai_player = self.callbacks['is_ai_player'](current_mech.player_id)
            
            if is_ai_player:
                # AI turn - handle selection and animation
                if self.state.selected_mech:
                    self.callbacks['on_mech_deselected'](self.state.selected_mech)
                self.state.select_mech(current_mech)
                self.callbacks['on_mech_selected'](current_mech)
                
                player_name = player_info["name"]
                self.callbacks['log'](f"AI {player_name}: {current_mech.stats.name}'s turn")
                
                # Schedule AI action via callback
                self.callbacks['schedule_ai_action'](current_mech)
            else:
                # Human player turn - no AI scheduling
                if self.state.selected_mech:
                    self.callbacks['on_mech_deselected'](self.state.selected_mech)
                self.state.select_mech(current_mech)
                self.callbacks['on_mech_selected'](current_mech)
                
                player_name = player_info["name"]
                self.callbacks['log'](f"{player_name}: {current_mech.stats.name}'s turn")
        
        # Update initiative display
        self._update_initiative_ui()
        
        # Refresh game display
        self.callbacks['update_display']()
    
    def end_movement_phase(self):
        """
        End movement phase for current mech and advance to attack phase
        
        This is called when player clicks "End Movement" button.
        Uses TurnPhaseHandler to validate and execute the transition.
        """
        if self.state.game_over:
            return
        
        if self.state.current_mech_index < len(self.state.initiative_order):
            current_mech = self.state.initiative_order[self.state.current_mech_index]
            try:
                self.phase_handler.advance_to_attack(current_mech)
            except Exception as e:
                messagebox.showerror("Phase Error", f"Cannot advance to attack phase: {str(e)}")
                print(f"Error advancing to attack phase: {str(e)}")
    
    def get_current_mech(self) -> Optional['Mech']:
        """
        Get the currently active mech
        
        Returns:
            The active mech, or None if no mech is active
        """
        if 0 <= self.state.current_mech_index < len(self.state.initiative_order):
            return self.state.initiative_order[self.state.current_mech_index]
        return None
    
    def is_current_mech(self, mech: 'Mech') -> bool:
        """
        Check if given mech is the currently active one
        
        Args:
            mech: The mech to check
            
        Returns:
            True if this is the active mech
        """
        current = self.get_current_mech()
        return current is not None and current == mech
    
    def can_mech_act(self, mech: 'Mech') -> bool:
        """
        Check if a mech can currently act
        
        A mech can act if it's the current mech and not done with its turn.
        
        Args:
            mech: The mech to check
            
        Returns:
            True if mech can act
        """
        if not self.is_current_mech(mech):
            return False
        if mech.is_destroyed():
            return False
        if mech.current_phase == MechPhase.DONE:
            return False
        return True
    
    def _update_initiative_ui(self):
        """
        Update the initiative display UI
        
        Prepares initiative data and calls the callback to update the display.
        """
        initiative_data = self._prepare_initiative_display_data()
        self.callbacks['on_initiative_updated'](initiative_data)
    
    def _prepare_initiative_display_data(self) -> List[Tuple[int, 'Mech', str, str, str]]:
        """
        Prepare data for initiative display rendering
        
        Returns:
            List of tuples: (index, mech, text, color, bg_color)
        """
        display_data = []
        
        for i, mech in enumerate(self.state.initiative_order):
            # Determine if this is the active mech
            is_active = (i == self.state.current_mech_index and not mech.is_destroyed())
            
            # Set colors based on mech status
            if mech.is_destroyed():
                color = "red"
                bg_color = "#ffeeee"  # Light red background
            elif is_active:
                color = "green"
                bg_color = "lightgreen"
            else:
                color = "black"
                bg_color = ""  # No background
            
            # Build display text
            if mech.is_destroyed():
                text = f"{i+1}. {mech.stats.name} (P{mech.player_id}) [DESTROYED]"
            else:
                text = f"{i+1}. {mech.stats.name} (P{mech.player_id})"
                if mech.has_moved and mech.has_fired:
                    text += " [Done]"
                elif mech.has_moved:
                    text += " [Moved]"
                elif mech.has_fired:
                    text += " [Fired]"
            
            # Add active indicator
            if is_active:
                text = "→ " + text + " ←"
            
            display_data.append((i, mech, text, color, bg_color))
        
        return display_data
    
    def get_initiative_order(self) -> List['Mech']:
        """Get the current initiative order"""
        return self.state.initiative_order.copy()
    
    def get_current_turn_number(self) -> int:
        """Get the current turn number"""
        return self.state.current_turn
