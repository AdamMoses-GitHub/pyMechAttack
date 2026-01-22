"""
Detailed placement test with distance from center analysis
"""

from board_manager import BoardManager
from entities import HexTile

def test_all_configurations():
    """Test all player counts and proximities"""
    player_counts = [2, 3, 4]
    proximities = ["close", "medium", "far"]
    starting_sides = ["northwest", "southeast", "northeast", "southwest"]
    
    for num_players in player_counts:
        for proximity in proximities:
            print(f"\n{'='*70}")
            print(f"Testing {num_players} players with '{proximity}' proximity")
            print('='*70)
            
            # Create board
            board = BoardManager(board_size=20)
            board.create_board()
            
            all_distances = []
            
            for player_id in range(1, num_players + 1):
                side = starting_sides[player_id - 1]
                positions = board.find_starting_positions(
                    side=side,
                    num_mechs=4,
                    initial_proximity=proximity
                )
                
                # Calculate distances from center
                distances_from_center = []
                for pos in positions:
                    q, r = pos
                    dist = (abs(q) + abs(q + r) + abs(r)) // 2
                    distances_from_center.append(dist)
                
                avg_dist = sum(distances_from_center) / len(distances_from_center) if distances_from_center else 0
                all_distances.append(avg_dist)
                
                print(f"Player {player_id} ({side:10s}): {len(positions)} mechs, "
                      f"avg dist from center: {avg_dist:5.1f} hexes, "
                      f"range: {min(distances_from_center) if distances_from_center else 0}-"
                      f"{max(distances_from_center) if distances_from_center else 0}")
            
            # Calculate standard deviation to check symmetry
            if all_distances:
                mean_dist = sum(all_distances) / len(all_distances)
                variance = sum((d - mean_dist) ** 2 for d in all_distances) / len(all_distances)
                std_dev = variance ** 0.5
                
                print(f"\nOverall: Mean distance = {mean_dist:.1f}, Std Dev = {std_dev:.2f}")
                if std_dev < 1.0:
                    print("✓ EXCELLENT - All players equidistant from center")
                elif std_dev < 2.0:
                    print("✓ GOOD - Players reasonably balanced")
                else:
                    print("⚠ WARNING - Significant asymmetry in placement")

if __name__ == "__main__":
    test_all_configurations()
