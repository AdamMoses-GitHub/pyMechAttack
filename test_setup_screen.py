"""
Test the setup screen scrollbar functionality
"""

import tkinter as tk
from ui_setup_screen import GameSetupScreen

def on_start(config):
    """Callback for when game starts"""
    print("Game would start with config:")
    print(f"  Players: {config['num_players']}")
    print(f"  Proximity: {config['proximity']}")
    print(f"  AI Speed: {config['ai_speed']}")
    setup_window.destroy()

def on_cancel():
    """Callback for when setup is cancelled"""
    print("Setup cancelled")
    if hasattr(setup_screen, 'setup_window'):
        setup_screen.setup_window.quit()

print("Starting Setup Screen Test")
print("Instructions:")
print("1. Try changing the number of players from 2 to 3 to 4")
print("2. Verify that the scrollbar appears and works when needed")
print("3. Test mouse wheel scrolling")
print("4. Click 'Start Game' or 'Cancel' when done")
print()

setup_screen = GameSetupScreen(on_start_callback=on_start, on_cancel_callback=on_cancel)
setup_window = setup_screen.show()

try:
    setup_window.mainloop()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
