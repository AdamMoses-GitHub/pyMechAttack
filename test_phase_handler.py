"""
Test script for TurnPhaseHandler implementation
Validates phase transitions and callback system
"""

from models import MechStats, MechPhase
from entities import Mech, HexTile
from turn_phase_handler import TurnPhaseHandler, InvalidPhaseTransitionException

def test_phase_handler():
    """Test TurnPhaseHandler functionality"""
    print("Testing TurnPhaseHandler Implementation...")
    print("-" * 60)
    
    # Create test data
    hex_tile = HexTile(0, 0, "clear")
    stats = MechStats(
        name="Test Mech",
        speed=10,
        laser_attack=8,
        missile_attack=6,
        armor_hp=20,
        structure_hp=10,
        max_armor_hp=20,
        max_structure_hp=10
    )
    mech = Mech(player_id=1, stats=stats, hex_tile=hex_tile)
    
    # Track callbacks
    callbacks_fired = []
    
    def mock_log(msg):
        callbacks_fired.append(('log', msg))
        print(f"  [LOG] {msg}")
    
    def mock_update_display():
        callbacks_fired.append(('update_display',))
        print(f"  [DISPLAY] Updated")
    
    def mock_update_buttons():
        callbacks_fired.append(('update_buttons',))
        print(f"  [BUTTONS] Updated")
    
    def mock_phase_changed(mech, old, new):
        callbacks_fired.append(('phase_changed', old, new))
        print(f"  [PHASE] {old} → {new}")
    
    # Create phase handler with callbacks
    handler = TurnPhaseHandler({
        'log': mock_log,
        'update_display': mock_update_display,
        'update_buttons': mock_update_buttons,
        'on_phase_changed': mock_phase_changed
    })
    
    # Test 1: Initial state
    print("\n✓ Test 1: Initial mech state")
    assert mech.current_phase == MechPhase.MOVEMENT, "Mech should start in MOVEMENT phase"
    print(f"  Current phase: {mech.current_phase}")
    
    # Test 2: Movement to Attack transition
    print("\n✓ Test 2: MOVEMENT → ATTACK transition")
    try:
        handler.advance_to_attack(mech)
        assert mech.current_phase == MechPhase.ATTACK, "Mech should be in ATTACK phase"
        print(f"  Current phase: {mech.current_phase}")
        assert len(callbacks_fired) > 0, "Callbacks should have been fired"
        print(f"  Callbacks fired: {len(callbacks_fired)}")
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False
    
    # Test 3: Attack to Done transition
    print("\n✓ Test 3: ATTACK → DONE transition")
    callbacks_fired.clear()
    try:
        handler.advance_to_done(mech, reason="test")
        assert mech.current_phase == MechPhase.DONE, "Mech should be in DONE phase"
        print(f"  Current phase: {mech.current_phase}")
        assert len(callbacks_fired) > 0, "Callbacks should have been fired"
        print(f"  Callbacks fired: {len(callbacks_fired)}")
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False
    
    # Test 4: Invalid transition (DONE → ATTACK should fail)
    print("\n✓ Test 4: Invalid transition detection (DONE → ATTACK)")
    try:
        handler.advance_to_attack(mech)
        print(f"  ✗ FAILED: Should have raised InvalidPhaseTransitionException")
        return False
    except InvalidPhaseTransitionException as e:
        print(f"  Correctly raised exception: {str(e)[:60]}...")
    
    # Test 5: Reset phase
    print("\n✓ Test 5: Phase reset")
    handler.reset_phase(mech)
    assert mech.current_phase == MechPhase.MOVEMENT, "Mech should be back in MOVEMENT phase"
    assert mech.has_moved == False, "has_moved should be reset"
    assert mech.has_fired == False, "has_fired should be reset"
    print(f"  Current phase: {mech.current_phase}")
    print(f"  has_moved: {mech.has_moved}, has_fired: {mech.has_fired}")
    
    # Test 6: can_perform_action validation
    print("\n✓ Test 6: Action validation")
    tests = [
        ("move", True, "Can move in MOVEMENT phase"),
        ("attack", False, "Cannot attack in MOVEMENT phase"),
        ("end_movement", True, "Can end movement in MOVEMENT phase"),
        ("end_turn", True, "Can end turn in MOVEMENT phase")
    ]
    
    for action, expected, desc in tests:
        result = handler.can_perform_action(mech, action)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {action}: {result} ({desc})")
        assert result == expected, f"Expected {expected}, got {result} for action '{action}'"
    
    # Test 7: Phase instructions
    print("\n✓ Test 7: Phase-specific instructions")
    mech.current_phase = MechPhase.MOVEMENT
    instructions = handler.get_phase_instructions(mech)
    print(f"  MOVEMENT: {instructions[:50]}...")
    
    mech.current_phase = MechPhase.ATTACK
    instructions = handler.get_phase_instructions(mech)
    print(f"  ATTACK: {instructions[:50]}...")
    
    # Test 8: Phase display helpers
    print("\n✓ Test 8: Display helpers")
    display_name = handler.get_phase_display_name(MechPhase.MOVEMENT)
    color = handler.get_phase_color(MechPhase.ATTACK)
    print(f"  Display name: {display_name}")
    print(f"  Attack phase color: {color}")
    
    # Test 9: Phase consistency validation
    print("\n✓ Test 9: Phase consistency checks")
    warnings = handler.validate_phase_consistency(mech)
    print(f"  Consistency warnings: {len(warnings)}")
    for warning in warnings:
        print(f"    - {warning}")
    
    print("\n" + "=" * 60)
    print("✓ All tests passed successfully!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    try:
        success = test_phase_handler()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
