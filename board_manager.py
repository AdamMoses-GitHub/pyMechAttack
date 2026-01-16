"""
pyMechAttack - Board Manager Module
Manages the hex board creation, terrain generation, and spatial queries
"""

import random
from typing import Dict, List, Tuple, Optional
from entities import HexTile, Mech


class BoardManager:
    """Manages hex board state, terrain generation, and spatial operations"""
    
    # Terrain distribution configuration (cumulative probabilities)
    TERRAIN_DISTRIBUTION = {
        "forest": 0.15,
        "shallow_water": 0.10,
        "deep_water": 0.05,
        "mountain": 0.05,
        "clear": 0.65
    }
    
    # Corner range definitions for spawn positions
    CORNER_RANGES = {
        "northwest": {"q_sign": -1, "r_sign": -1},
        "northeast": {"q_sign": 1, "r_sign": -1},
        "southwest": {"q_sign": -1, "r_sign": 1},
        "southeast": {"q_sign": 1, "r_sign": 1},
        "left": {"q_sign": -1, "r_sign": 0},
        "right": {"q_sign": 1, "r_sign": 0}
    }
    
    # Fallback spawn positions for each corner
    FALLBACK_POSITIONS = {
        "northwest": [(-5, -2), (-5, -1), (-4, -3), (-4, -1), (-3, -2), (-3, 0)],
        "northeast": [(5, -2), (5, -1), (4, -3), (4, -1), (3, -2), (3, 0)],
        "southwest": [(-5, 2), (-5, 3), (-4, 1), (-4, 3), (-3, 2), (-3, 4)],
        "southeast": [(5, 2), (5, 3), (4, 1), (4, 3), (3, 2), (3, 4)],
        "left": [(-5, 0), (-5, 1), (-4, -1), (-4, 1), (-3, 0), (-3, 2)],
        "right": [(5, 0), (5, -1), (4, 1), (4, -1), (3, 0), (3, -2)]
    }
    
    def __init__(self, board_size: int = 20):
        """
        Initialize the board manager
        
        Args:
            board_size: Radius of the hex board
        """
        self.board_size = board_size
        self.hex_tiles: Dict[Tuple[int, int], HexTile] = {}
        self._terrain_stats_cache: Optional[Dict[str, int]] = None
    
    def _select_terrain(self, rand_value: float) -> str:
        """
        Select terrain type based on random value and distribution config
        
        Args:
            rand_value: Random float between 0.0 and 1.0
            
        Returns:
            Terrain type string
        """
        cumulative = 0.0
        for terrain, probability in self.TERRAIN_DISTRIBUTION.items():
            cumulative += probability
            if rand_value < cumulative:
                return terrain
        return "clear"  # Fallback
        
    def create_board(self):
        """Create the hex board with randomized terrain"""
        self.hex_tiles.clear()
        self._terrain_stats_cache = None  # Invalidate cache
        
        for q in range(-self.board_size, self.board_size + 1):
            for r in range(max(-self.board_size, -q - self.board_size), 
                          min(self.board_size, -q + self.board_size) + 1):
                # Select terrain based on probability distribution
                terrain = self._select_terrain(random.random())
                hex_tile = HexTile(q, r, terrain)
                self.hex_tiles[(q, r)] = hex_tile
    
    def get_hex(self, q: int, r: int) -> Optional[HexTile]:
        """
        Get a hex tile at the specified coordinates
        
        Args:
            q: Q coordinate (axial)
            r: R coordinate (axial)
            
        Returns:
            HexTile if it exists, None otherwise
        """
        return self.hex_tiles.get((q, r))
    
    def validate_coordinates(self, q: int, r: int) -> bool:
        """
        Check if hex coordinates are valid (within board bounds)
        
        Args:
            q: Q coordinate
            r: R coordinate
            
        Returns:
            True if coordinates are valid
        """
        return (q, r) in self.hex_tiles
    
    def get_all_hexes(self) -> Dict[Tuple[int, int], HexTile]:
        """
        Get all hex tiles on the board
        
        Returns:
            Dictionary mapping (q, r) coordinates to HexTile objects
        """
        return self.hex_tiles
    
    def _get_corner_ranges(self, side: str, corner_offset: int) -> Tuple[range, range]:
        """
        Get coordinate ranges for a specific corner/side
        
        Args:
            side: Starting side name
            corner_offset: Offset distance from board edge
            
        Returns:
            Tuple of (q_range, r_range)
        """
        if side not in self.CORNER_RANGES:
            side = "left"  # Default fallback
        
        corner = self.CORNER_RANGES[side]
        q_sign = corner["q_sign"]
        r_sign = corner["r_sign"]
        
        if r_sign == 0:  # Left/right side (special case)
            q_end = q_sign * self.board_size + (1 if q_sign > 0 else -1)
            q_range = range(q_sign * corner_offset, q_end)
            r_range = range(-corner_offset // 2, corner_offset // 2 + 1)
        else:  # Diagonal corners
            if q_sign > 0:
                q_range = range(corner_offset, self.board_size + 1)
            else:
                q_range = range(-self.board_size, -corner_offset + 1)
            
            if r_sign > 0:
                r_range = range(corner_offset, self.board_size + 1)
            else:
                r_range = range(-self.board_size, -corner_offset + 1)
        
        return q_range, r_range
    
    def find_starting_positions(
        self, 
        side: str, 
        num_mechs: int = 4,
        initial_proximity: str = "medium"
    ) -> List[Tuple[int, int]]:
        """
        Find suitable starting positions on clear terrain or forests in corner areas
        
        Args:
            side: Starting side ("northwest", "northeast", "southwest", "southeast", "left", "right")
            num_mechs: Number of mechs to find positions for
            initial_proximity: Spacing between mechs ("close", "medium", "far")
            
        Returns:
            List of (q, r) coordinate tuples for starting positions
        """
        if num_mechs <= 0:
            raise ValueError("num_mechs must be greater than 0")
        if initial_proximity not in ["close", "medium", "far"]:
            raise ValueError("initial_proximity must be 'close', 'medium', or 'far'")
        if side not in self.CORNER_RANGES and side not in self.FALLBACK_POSITIONS:
            raise ValueError(f"Invalid side: {side}")
        
        suitable_positions = []
        
        # Calculate corner offset based on proximity setting
        if initial_proximity == "close":
            corner_offset = int(self.board_size * 0.25)  # Very close (25% of board radius)
        elif initial_proximity == "far":
            corner_offset = int(self.board_size * 0.95)  # Very far (95% of board radius)
        else:  # medium (default)
            corner_offset = int(self.board_size * 0.65)  # Medium distance (65% of board radius)
        
        # Get search ranges using corner mapping
        q_range, r_range = self._get_corner_ranges(side, corner_offset)
        
        # Find all suitable hexes (clear or forest terrain) in the focused area
        candidates = []
        for q in q_range:
            for r in r_range:
                if (q, r) in self.hex_tiles:
                    hex_tile = self.hex_tiles[(q, r)]
                    # Only allow clear terrain or forests for starting positions
                    if hex_tile.terrain_type in ["clear", "forest"]:
                        candidates.append((q, r))
        
        # If we have candidates, select them with reasonable spacing
        if candidates:
            # Sort by distance from center r=0 for better formation
            candidates.sort(key=lambda pos: (abs(pos[1]), abs(pos[0])))
            
            selected = []
            # Set minimum distance between mechs based on proximity setting
            if initial_proximity == "close":
                min_distance = 1  # Mechs can be adjacent for close formation
            elif initial_proximity == "far":
                min_distance = 3  # Larger spacing for far formation
            else:  # medium
                min_distance = 2  # Standard spacing
            
            # Try to select well-spaced positions
            for candidate in candidates:
                if not selected:
                    # Always take the first candidate (closest to center)
                    selected.append(candidate)
                else:
                    # Check if this position has reasonable spacing
                    too_close = False
                    for selected_pos in selected:
                        distance = self.hex_tiles[candidate].distance_to(self.hex_tiles[selected_pos])
                        if distance < min_distance:
                            too_close = True
                            break
                    
                    if not too_close:
                        selected.append(candidate)
                        if len(selected) >= num_mechs:
                            break
            
            # If we don't have enough well-spaced positions, add closest remaining candidates
            if len(selected) < num_mechs:
                for candidate in candidates:
                    if candidate not in selected:
                        selected.append(candidate)
                        if len(selected) >= num_mechs:
                            break
            
            suitable_positions = selected[:num_mechs]
        
        # Enhanced fallback with guaranteed visible positions
        if len(suitable_positions) < num_mechs:
            # Get fallback positions for this corner
            fallback_positions = self.FALLBACK_POSITIONS.get(side, self.FALLBACK_POSITIONS["left"])
            
            # Add fallback positions that exist on the map and have suitable terrain
            for pos in fallback_positions:
                if len(suitable_positions) >= num_mechs:
                    break
                if pos in self.hex_tiles and pos not in suitable_positions:
                    hex_tile = self.hex_tiles[pos]
                    if hex_tile.terrain_type in ["clear", "forest"]:
                        suitable_positions.append(pos)
        
        return suitable_positions
    
    def get_board_bounds(self) -> Tuple[int, int, int, int]:
        """
        Get the bounding box of the board in axial coordinates
        
        Returns:
            Tuple of (min_q, max_q, min_r, max_r)
        """
        if not self.hex_tiles:
            return (0, 0, 0, 0)
        
        coords = list(self.hex_tiles.keys())
        qs = [q for q, r in coords]
        rs = [r for q, r in coords]
        
        return (min(qs), max(qs), min(rs), max(rs))
    
    def count_terrain_type(self, terrain_type: str) -> int:
        """
        Count hexes of a specific terrain type
        
        Args:
            terrain_type: Type of terrain to count
            
        Returns:
            Number of hexes with that terrain type
        """
        return sum(1 for tile in self.hex_tiles.values() if tile.terrain_type == terrain_type)
    
    def get_terrain_statistics(self) -> Dict[str, int]:
        """
        Get statistics about terrain distribution
        
        Returns:
            Dictionary mapping terrain types to counts
        """
        if self._terrain_stats_cache is None:
            stats = {}
            for tile in self.hex_tiles.values():
                terrain = tile.terrain_type
                stats[terrain] = stats.get(terrain, 0) + 1
            self._terrain_stats_cache = stats
        return self._terrain_stats_cache
