"""
Test script to validate mech placement for different player counts and proximities
"""

from board_manager import BoardManager
from entities import HexTile

def test_placement(num_players, proximity):
    """Test placement for a given number of players and proximity setting"""
    print(f"\n{'='*60}")
    print(f"Testing {num_players} players with '{proximity}' proximity")
    print(f"{'='*60}")
    
    # Create board
    board = BoardManager(board_size=20)
    board.create_board()
    
    # Starting sides for each player
    starting_sides = ["northwest", "southeast", "northeast", "southwest"]
    
    # Track results
    all_positions = {}
    
    for player_id in range(1, num_players + 1):
        side = starting_sides[player_id - 1]
        print(f"\nPlayer {player_id} (side: {side}):")
        
        try:
            positions = board.find_starting_positions(
                side=side,
                num_mechs=4,
                initial_proximity=proximity
            )
            
            all_positions[player_id] = positions
            print(f"  Found {len(positions)} positions: {positions}")
            
            # Check terrain types
            for i, pos in enumerate(positions):
                hex_tile = board.get_hex(pos[0], pos[1])
                if hex_tile:
                    print(f"    Mech {i+1}: {pos} - Terrain: {hex_tile.terrain_type}")
                else:
                    print(f"    Mech {i+1}: {pos} - ERROR: Hex not found!")
            
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    # Calculate distances between players
    print("\n" + "-"*60)
    print("Inter-player distances:")
    print("-"*60)
    
    for p1 in range(1, num_players + 1):
        for p2 in range(p1 + 1, num_players + 1):
            if p1 in all_positions and p2 in all_positions:
                if all_positions[p1] and all_positions[p2]:
                    # Use first mech of each player
                    pos1 = all_positions[p1][0]
                    pos2 = all_positions[p2][0]
                    
                    hex1 = board.get_hex(pos1[0], pos1[1])
                    hex2 = board.get_hex(pos2[0], pos2[1])
                    
                    if hex1 and hex2:
                        distance = hex1.distance_to(hex2)
                        print(f"  Player {p1} -> Player {p2}: {distance} hexes")
    
    # Calculate intra-player distances
    print("\n" + "-"*60)
    print("Within-player distances (between own mechs):")
    print("-"*60)
    
    for player_id in range(1, num_players + 1):
        if player_id in all_positions and len(all_positions[player_id]) >= 2:
            positions = all_positions[player_id]
            print(f"\nPlayer {player_id}:")
            for i in range(len(positions)):
                for j in range(i + 1, len(positions)):
                    pos1 = positions[i]
                    pos2 = positions[j]
                    hex1 = board.get_hex(pos1[0], pos1[1])
                    hex2 = board.get_hex(pos2[0], pos2[1])
                    if hex1 and hex2:
                        distance = hex1.distance_to(hex2)
                        print(f"  Mech {i+1} -> Mech {j+1}: {distance} hexes")

def main():
    """Run all test cases"""
    print("MECH PLACEMENT VALIDATION TEST")
    print("="*60)
    
    # Test all combinations
    player_counts = [2, 3, 4]
    proximities = ["close", "medium", "far"]
    
    for num_players in player_counts:
        for proximity in proximities:
            test_placement(num_players, proximity)
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)

if __name__ == "__main__":
    main()
