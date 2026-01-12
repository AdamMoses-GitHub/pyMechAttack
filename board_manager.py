"""
pyMechAttack - Board Manager Module
Manages the hex board creation, terrain generation, and spatial queries
"""

import random
from typing import Dict, List, Tuple, Optional
from entities import HexTile, Mech


class BoardManager:
    """Manages hex board state, terrain generation, and spatial operations"""
    
    def __init__(self, board_size: int = 20):
        """
        Initialize the board manager
        
        Args:
            board_size: Radius of the hex board
        """
        self.board_size = board_size
        self.hex_tiles: Dict[Tuple[int, int], HexTile] = {}
        
    def create_board(self):
        """Create the hex board with randomized terrain"""
        self.hex_tiles.clear()
        
        for q in range(-self.board_size, self.board_size + 1):
            for r in range(max(-self.board_size, -q - self.board_size), 
                          min(self.board_size, -q + self.board_size) + 1):
                # Add terrain variety with realistic distribution
                rand = random.random()
                if rand < 0.15:
                    terrain = "forest"
                elif rand < 0.25:
                    terrain = "shallow_water"
                elif rand < 0.30:
                    terrain = "deep_water"
                elif rand < 0.35:
                    terrain = "mountain"
                else:
                    terrain = "clear"
                
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
        suitable_positions = []
        
        # Calculate corner offset based on proximity setting
        if initial_proximity == "close":
            corner_offset = int(self.board_size * 0.25)  # Very close (25% of board radius)
        elif initial_proximity == "far":
            corner_offset = int(self.board_size * 0.95)  # Very far (95% of board radius)
        else:  # medium (default)
            corner_offset = int(self.board_size * 0.65)  # Medium distance (65% of board radius)
        
        # Define search areas for each corner
        if side == "northwest":
            # Top-left corner: negative q, negative r
            q_range = range(-self.board_size, -corner_offset)
            r_range = range(-corner_offset, 1)
        elif side == "northeast":
            # Top-right corner: positive q, negative r
            q_range = range(-corner_offset, 1)
            r_range = range(-self.board_size, -corner_offset)
        elif side == "southwest":
            # Bottom-left corner: negative q, positive r
            q_range = range(-corner_offset, 1)
            r_range = range(corner_offset, self.board_size + 1)
        elif side == "southeast":
            # Bottom-right corner: positive q, positive r
            q_range = range(corner_offset, self.board_size + 1)
            r_range = range(-corner_offset, 1)
        else:
            # Fallback for legacy left/right positions
            if side == "left":
                q_range = range(-self.board_size, -corner_offset)
                r_range = range(-corner_offset//2, corner_offset//2 + 1)
            else:  # right
                q_range = range(corner_offset, self.board_size + 1)
                r_range = range(-corner_offset//2, corner_offset//2 + 1)
        
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
            # Define safe fallback positions for each corner
            if side == "northwest":
                fallback_positions = [(-5, -2), (-5, -1), (-4, -3), (-4, -1), (-3, -2), (-3, 0)]
            elif side == "northeast":
                fallback_positions = [(5, -2), (5, -1), (4, -3), (4, -1), (3, -2), (3, 0)]
            elif side == "southwest":
                fallback_positions = [(-5, 2), (-5, 3), (-4, 1), (-4, 3), (-3, 2), (-3, 4)]
            elif side == "southeast":
                fallback_positions = [(5, 2), (5, 3), (4, 1), (4, 3), (3, 2), (3, 4)]
            elif side == "left":
                fallback_positions = [(-5, 0), (-5, 1), (-4, -1), (-4, 1), (-3, 0), (-3, 2)]
            else:  # right
                fallback_positions = [(5, 0), (5, -1), (4, 1), (4, -1), (3, 0), (3, -2)]
            
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
        stats = {}
        for tile in self.hex_tiles.values():
            terrain = tile.terrain_type
            stats[terrain] = stats.get(terrain, 0) + 1
        return stats
