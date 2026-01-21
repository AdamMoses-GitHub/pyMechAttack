"""
pyMechAttack - Game State Management Module
Centralized game state storage and management
"""

from typing import List, Dict, Tuple, Optional
from entities import HexTile, Mech
from models import MechPhase


class GameState:
    """Manages all game state including board, mechs, turns, and players"""
    
    def __init__(self):
        # Board configuration
        self.board_size = 20  # Default board size
        self.hex_tiles: Dict[Tuple[int, int], HexTile] = {}
        
        # Player configuration (2-4 players)
        self.num_players = 2  # Default to 2 players
        self.players = [
            {"name": "Player 1", "is_ai": False, "color": "#FF073A"},  # Neon Red
            {"name": "Player 2", "is_ai": True, "color": "#00D9FF"},    # Neon Blue
            {"name": "Player 3", "is_ai": False, "color": "#BC13FE"},  # Neon Purple
            {"name": "Player 4", "is_ai": True, "color": "#FFFF00"}    # Neon Yellow
        ]
        
        # Mech management
        self.mechs: List[Mech] = []
        
        # Turn and initiative management
        self.current_turn = 1
        self.initiative_order: List[Mech] = []
        self.current_mech_index = 0
        
        # Game status
        self.game_over = False
        self.game_initialized = False
        
        # Selection state
        self.selected_mech: Optional[Mech] = None
        self.target_mech: Optional[Mech] = None
        
        # Game settings
        self.ai_action_speed = 2.0  # Default AI action speed in seconds
        self.initial_proximity = "medium"  # Starting position proximity
        self.sound_effects_enabled = True  # Sound effects toggle
        
        # Game statistics
        self.stats = {
            "mechs_destroyed": [0] * 4,  # Count per player (up to 4 players)
            "total_damage_dealt": [0] * 4,
            "total_damage_taken": [0] * 4,
            "kills": [0] * 4,  # Number of mechs destroyed by each player
        }
        
    def configure_players(self, num_players: int, player_configs: List[Dict]):
        """Configure the number of players and their settings"""
        if not (2 <= num_players <= 4):
            raise ValueError("Number of players must be between 2 and 4")
        
        self.num_players = num_players
        self.players = player_configs[:num_players]
        
        # Reset stats for configured player count
        self.stats = {
            "mechs_destroyed": [0] * num_players,
            "total_damage_dealt": [0] * num_players,
            "total_damage_taken": [0] * num_players,
            "kills": [0] * num_players,
        }
        
    def add_mech(self, mech: Mech):
        """Add a mech to the game"""
        if mech not in self.mechs:
            self.mechs.append(mech)
    
    def remove_mech(self, mech: Mech):
        """Remove a mech from the game"""
        if mech in self.mechs:
            self.mechs.remove(mech)
            
        # Clean up initiative order
        if mech in self.initiative_order:
            self.initiative_order.remove(mech)
    
    def get_active_mech(self) -> Optional[Mech]:
        """Get the currently active mech in turn order"""
        if 0 <= self.current_mech_index < len(self.initiative_order):
            return self.initiative_order[self.current_mech_index]
        return None
    
    def get_alive_mechs(self) -> List[Mech]:
        """Get all non-destroyed mechs"""
        return [mech for mech in self.mechs if not mech.is_destroyed()]
    
    def get_player_mechs(self, player_id: int) -> List[Mech]:
        """Get all mechs belonging to a specific player"""
        return [mech for mech in self.mechs if mech.player_id == player_id]
    
    def get_enemy_mechs(self, player_id: int) -> List[Mech]:
        """Get all mechs belonging to other players"""
        return [mech for mech in self.mechs 
                if mech.player_id != player_id and not mech.is_destroyed()]
    
    def calculate_initiative_order(self) -> List[Mech]:
        """
        Calculate initiative order for mechs based on speed
        Alive mechs first (sorted by speed), then destroyed mechs
        """
        alive_mechs = self.get_alive_mechs()
        destroyed_mechs = [mech for mech in self.mechs if mech.is_destroyed()]
        
        # Sort alive mechs by speed (faster first)
        alive_sorted = sorted(alive_mechs, key=lambda m: m.stats.speed, reverse=True)
        
        # Sort destroyed mechs by speed as well for consistency
        destroyed_sorted = sorted(destroyed_mechs, key=lambda m: m.stats.speed, reverse=True)
        
        # Return alive mechs first, then destroyed mechs
        return alive_sorted + destroyed_sorted
    
    def update_initiative_order(self):
        """Recalculate and update the initiative order"""
        self.initiative_order = self.calculate_initiative_order()
    
    def advance_to_next_mech(self) -> bool:
        """
        Advance to the next mech in initiative order
        Returns True if successful, False if turn should end
        """
        self.current_mech_index += 1
        
        # Skip destroyed mechs
        while (self.current_mech_index < len(self.initiative_order) and 
               self.initiative_order[self.current_mech_index].is_destroyed()):
            self.current_mech_index += 1
        
        # Check if we've gone through all mechs
        if (self.current_mech_index >= len(self.initiative_order) or
            all(m.is_destroyed() for m in self.initiative_order[self.current_mech_index:])):
            return False  # Turn should end
        
        return True  # Continue with next mech
    
    def start_new_turn(self):
        """Initialize a new turn"""
        self.current_turn += 1
        
        # Reset all living mechs
        for mech in self.mechs:
            if not mech.is_destroyed():
                mech.start_turn()
        
        # Recalculate initiative
        self.update_initiative_order()
        self.current_mech_index = 0
        
        # Clear selections
        self.selected_mech = None
        self.target_mech = None
    
    def reset_turn_state(self):
        """Reset turn-specific state"""
        self.current_mech_index = 0
        self.selected_mech = None
        self.target_mech = None
    
    def check_victory(self) -> Optional[Dict]:
        """
        Check victory conditions
        Returns victory info dict if game is over, None otherwise
        """
        # Count players with living mechs
        players_alive = []
        for player_id in range(1, self.num_players + 1):
            if any(m.player_id == player_id and not m.is_destroyed() for m in self.mechs):
                players_alive.append(player_id)
        
        # Victory if only one player remains
        if len(players_alive) <= 1:
            self.game_over = True
            
            if len(players_alive) == 1:
                winner_id = players_alive[0]
                winner_name = self.players[winner_id - 1]["name"]
                return {
                    "type": "victory",
                    "winner_id": winner_id,
                    "winner_name": winner_name,
                    "message": f"{winner_name} Wins!"
                }
            else:
                return {
                    "type": "draw",
                    "message": "Draw - All Players Eliminated!"
                }
        
        return None
    
    def get_player_info(self, player_id: int) -> Dict:
        """Get player information by ID"""
        if 1 <= player_id <= self.num_players:
            return self.players[player_id - 1]
        return {"name": "Unknown", "is_ai": False, "color": "gray"}
    
    def is_ai_player(self, player_id: int) -> bool:
        """Check if a player is AI controlled"""
        player_info = self.get_player_info(player_id)
        return player_info.get("is_ai", False)
    
    def validate_hex_coordinates(self, q: int, r: int) -> bool:
        """Validate hex coordinates are within board bounds"""
        return (isinstance(q, int) and isinstance(r, int) and 
                abs(q) <= self.board_size and abs(r) <= self.board_size and 
                abs(-q-r) <= self.board_size)
    
    def get_hex(self, q: int, r: int) -> Optional[HexTile]:
        """Get hex tile at coordinates, or None if invalid"""
        if self.validate_hex_coordinates(q, r):
            return self.hex_tiles.get((q, r))
        return None
    
    def clear_selection(self):
        """Clear current mech selection"""
        self.selected_mech = None
        self.target_mech = None
    
    def select_mech(self, mech: Optional[Mech]):
        """Select a mech"""
        self.selected_mech = mech
        self.target_mech = None  # Clear target when changing selection
    
    def set_target(self, target: Optional[Mech]):
        """Set target mech"""
        self.target_mech = target
    
    def get_game_status_summary(self) -> Dict:
        """Get a summary of current game status"""
        alive_mechs = self.get_alive_mechs()
        return {
            "turn": self.current_turn,
            "total_mechs": len(self.mechs),
            "alive_mechs": len(alive_mechs),
            "active_mech": self.get_active_mech(),
            "game_over": self.game_over,
            "players_alive": len([p for p in range(1, self.num_players + 1) 
                                 if self.get_player_mechs(p)])
        }
    
    def record_damage(self, attacker_id: int, defender_id: int, damage_amount: int):
        """Record damage dealt and taken"""
        if 1 <= attacker_id <= len(self.stats["total_damage_dealt"]):
            self.stats["total_damage_dealt"][attacker_id - 1] += damage_amount
        if 1 <= defender_id <= len(self.stats["total_damage_taken"]):
            self.stats["total_damage_taken"][defender_id - 1] += damage_amount
    
    def record_mech_destroyed(self, destroyed_player_id: int, destroyer_player_id: int):
        """Record when a mech is destroyed"""
        if 1 <= destroyed_player_id <= len(self.stats["mechs_destroyed"]):
            self.stats["mechs_destroyed"][destroyed_player_id - 1] += 1
        if 1 <= destroyer_player_id <= len(self.stats["kills"]):
            self.stats["kills"][destroyer_player_id - 1] += 1
    
    def get_final_scoreboard(self) -> Dict:
        """Get final game statistics for scoreboard"""
        scoreboard = {}
        for player_id in range(1, self.num_players + 1):
            player_info = self.get_player_info(player_id)
            idx = player_id - 1
            scoreboard[player_id] = {
                "name": player_info["name"],
                "color": player_info["color"],
                "kills": self.stats["kills"][idx],
                "mechs_destroyed": self.stats["mechs_destroyed"][idx],
                "damage_dealt": self.stats["total_damage_dealt"][idx],
                "damage_taken": self.stats["total_damage_taken"][idx],
            }
        return scoreboard
