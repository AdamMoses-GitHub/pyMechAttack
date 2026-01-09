"""
pyMechAttack - Hex Coordinate & Pathfinding Utilities Module
Contains pure functions for hex grid mathematics, coordinate conversions,
pathfinding algorithms, and line-of-sight calculations
"""

from typing import Tuple, Dict
import math
import heapq
from entities import HexTile


def hex_to_pixel(q: int, r: int, hex_size: int, canvas_width: int, 
                 canvas_height: int, view_offset_x: float, view_offset_y: float) -> Tuple[float, float]:
    """Convert hex coordinates to pixel coordinates with view offset"""
    x = hex_size * (3/2 * q)
    y = hex_size * (math.sqrt(3)/2 * q + math.sqrt(3) * r)
    
    # Apply view offset for panning
    x += canvas_width / 2 + view_offset_x
    y += canvas_height / 2 + view_offset_y
    
    return x, y


def pixel_to_hex(x: float, y: float, hex_size: int, canvas_width: int, 
                 canvas_height: int, view_offset_x: float, view_offset_y: float) -> Tuple[int, int]:
    """Convert pixel coordinates to hex coordinates accounting for view offset"""
    # Adjust for canvas center and view offset
    x -= canvas_width / 2 + view_offset_x
    y -= canvas_height / 2 + view_offset_y
    
    q = (2/3 * x) / hex_size
    r = (-1/3 * x + math.sqrt(3)/3 * y) / hex_size
    
    return round_hex(q, r)


def round_hex(q: float, r: float) -> Tuple[int, int]:
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


def has_line_of_sight(from_hex: HexTile, to_hex: HexTile, hex_tiles: Dict[Tuple[int, int], HexTile]) -> tuple[bool, int]:
    """Check if there's a clear line of sight between two hexes.
    Returns (has_los, effective_range_modifier)
    Mountains block LOS completely.
    Forests reduce effective range by 1 per forest hex in the line.
    """
    if from_hex == to_hex:
        return True, 0
    
    # Get all hexes in the line between source and target
    line_hexes = get_line_hexes(from_hex, to_hex)
    
    # Don't include the source and target hexes in LOS check
    intermediate_hexes = line_hexes[1:-1]
    
    range_modifier = 0
    
    for hex_coord in intermediate_hexes:
        if hex_coord in hex_tiles:
            hex_tile = hex_tiles[hex_coord]
            
            # Mountains completely block line of sight
            if hex_tile.terrain_type == "mountain":
                return False, 0
            
            # Forests reduce effective range
            elif hex_tile.terrain_type == "forest":
                range_modifier += 1
    
    return True, range_modifier


def get_line_hexes(from_hex: HexTile, to_hex: HexTile) -> list[tuple[int, int]]:
    """Get all hex coordinates along a line between two hexes using hex line drawing."""
    # Convert to cube coordinates for easier line calculation
    def axial_to_cube(q, r):
        x = q
        z = r
        y = -x - z
        return x, y, z
    
    def cube_to_axial(x, y, z):
        q = x
        r = z
        return q, r
    
    def cube_lerp(a, b, t):
        return (
            a[0] + (b[0] - a[0]) * t,
            a[1] + (b[1] - a[1]) * t,
            a[2] + (b[2] - a[2]) * t
        )
    
    def cube_round(x, y, z):
        rx = round(x)
        ry = round(y)
        rz = round(z)
        
        x_diff = abs(rx - x)
        y_diff = abs(ry - y)
        z_diff = abs(rz - z)
        
        if x_diff > y_diff and x_diff > z_diff:
            rx = -ry - rz
        elif y_diff > z_diff:
            ry = -rx - rz
        else:
            rz = -rx - ry
        
        return rx, ry, rz
    
    # Convert to cube coordinates
    start_cube = axial_to_cube(from_hex.q, from_hex.r)
    end_cube = axial_to_cube(to_hex.q, to_hex.r)
    
    # Calculate distance
    distance = max(abs(start_cube[0] - end_cube[0]), 
                  abs(start_cube[1] - end_cube[1]), 
                  abs(start_cube[2] - end_cube[2]))
    
    # Generate line points
    line_points = []
    for i in range(distance + 1):
        t = i / distance if distance > 0 else 0
        cube_point = cube_lerp(start_cube, end_cube, t)
        rounded_cube = cube_round(*cube_point)
        axial_point = cube_to_axial(*rounded_cube)
        line_points.append(axial_point)
    
    return line_points


def calculate_path_cost(from_hex: HexTile, to_hex: HexTile) -> int:
    """Calculate movement cost between hexes (simplified)"""
    distance = from_hex.distance_to(to_hex)
    return distance * to_hex.get_movement_cost()


def calculate_reachable_hexes(from_hex: HexTile, max_movement: int, 
                               hex_tiles: Dict[Tuple[int, int], HexTile],
                               selected_mech=None) -> Dict[Tuple[int, int], int]:
    """Calculate all reachable hexes and their movement costs using Dijkstra's algorithm
    
    Args:
        from_hex: Starting hex tile
        max_movement: Maximum movement points available
        hex_tiles: Dictionary of all hex tiles on the board
        selected_mech: Optional mech to use remaining movement instead of max
    
    Returns:
        Dictionary mapping hex coordinates to movement cost to reach them
    """
    # For active mech, use remaining movement; for AI planning, use full movement
    if selected_mech and from_hex == selected_mech.hex_tile:
        actual_max_movement = selected_mech.get_remaining_movement()
    else:
        actual_max_movement = max_movement
        
    # Dictionary to store the minimum cost to reach each hex
    costs = {(from_hex.q, from_hex.r): 0}
    # Priority queue: (cost, hex_coords)
    queue = [(0, (from_hex.q, from_hex.r))]
    visited = set()
    
    while queue:
        current_cost, (q, r) = heapq.heappop(queue)
        
        if (q, r) in visited:
            continue
        visited.add((q, r))
        
        # If we've exceeded max movement, skip
        if current_cost > actual_max_movement:
            continue
        
        # Check all 6 neighbors of current hex
        neighbors = [
            (q + 1, r), (q - 1, r),           # East, West
            (q, r + 1), (q, r - 1),           # Southeast, Northwest  
            (q + 1, r - 1), (q - 1, r + 1)    # Northeast, Southwest
        ]
        
        for nq, nr in neighbors:
            if (nq, nr) not in hex_tiles:
                continue
                
            neighbor_hex = hex_tiles[(nq, nr)]
            
            # Skip if terrain blocks movement or hex is occupied by another mech
            if neighbor_hex.blocks_movement() or (neighbor_hex.mech and neighbor_hex.mech != from_hex.mech):
                continue
            
            # Calculate cost to move to this neighbor
            move_cost = neighbor_hex.get_movement_cost()
            new_cost = current_cost + move_cost
            
            # Skip if this path exceeds max movement
            if new_cost > actual_max_movement:
                continue
            
            # If we found a better path to this hex, update it
            if (nq, nr) not in costs or new_cost < costs[(nq, nr)]:
                costs[(nq, nr)] = new_cost
                heapq.heappush(queue, (new_cost, (nq, nr)))
    
    # Remove the starting hex from results
    if (from_hex.q, from_hex.r) in costs:
        del costs[(from_hex.q, from_hex.r)]
    
    return costs
