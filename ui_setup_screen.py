"""
pyMechAttack - UI Setup Screen Module
Handles the game configuration dialog for player setup
"""

import tkinter as tk
from tkinter import ttk
import random
from typing import List, Callable, Dict, Any


class GameSetupScreen:
    """Manages the game setup and configuration screen"""
    
    def __init__(self, on_start_callback: Callable[[Dict[str, Any]], None], 
                 on_cancel_callback: Callable[[], None]):
        """
        Initialize the game setup screen
        
        Args:
            on_start_callback: Callback function when game starts, receives config dict
            on_cancel_callback: Callback function when setup is cancelled
        """
        self.on_start_callback = on_start_callback
        self.on_cancel_callback = on_cancel_callback
        
        # AI names for random selection
        self.ai_names = [
            "Commander Steel", "Major Forge", "Captain Titan", "Colonel Storm",
            "General Viper", "Marshal Kane", "Admiral Rex", "Commander Nova",
            "Major Blitz", "Captain Razor", "Colonel Frost", "General Phoenix",
            "Marshal Thunder", "Admiral Hawk", "Commander Bolt", "Major Reaper"
        ]
        
        # Setup window and variables
        self.setup_window = None
        self.player_count_var = None
        self.ai_speed_var = None
        self.proximity_var = None
        self.player_name_vars = []
        self.player_type_vars = []
        self.player_config_frame = None
        
    def show(self):
        """Show the game setup screen"""
        # Create the setup window as the main window
        self.setup_window = tk.Tk()
        self.setup_window.title("pyMechAttack Game Setup")
        self.setup_window.geometry("600x700")
        self.setup_window.resizable(True, True)
        
        # Center the window on screen
        self.setup_window.update_idletasks()
        x = (self.setup_window.winfo_screenwidth() // 2) - (300)
        y = (self.setup_window.winfo_screenheight() // 2) - (350)
        self.setup_window.geometry(f"600x700+{x}+{y}")
        
        # Ensure it's visible and on top
        self.setup_window.lift()
        self.setup_window.focus_force()
        self.setup_window.attributes('-topmost', True)
        self.setup_window.after(100, lambda: self.setup_window.attributes('-topmost', False))
        
        # Main frame with scrollable content
        main_canvas = tk.Canvas(self.setup_window)
        scrollbar = ttk.Scrollbar(self.setup_window, orient="vertical", command=main_canvas.yview)
        scrollable_frame = ttk.Frame(main_canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )
        
        main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=scrollbar.set)
        
        main_canvas.pack(side="left", fill="both", expand=True, padx=20, pady=20)
        scrollbar.pack(side="right", fill="y")
        
        # Title
        title_label = ttk.Label(scrollable_frame, text="pyMechAttack Setup", 
                               font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Game Configuration
        self._create_game_config_section(scrollable_frame)
        
        # Player configuration area
        self.player_config_frame = ttk.Frame(scrollable_frame)
        self.player_config_frame.pack(fill=tk.X, pady=(0, 15))
        
        # AI Settings
        self._create_ai_settings_section(scrollable_frame)
        
        # Initial Proximity Settings
        self._create_proximity_settings_section(scrollable_frame)
        
        # Buttons
        self._create_buttons(scrollable_frame)
        
        # Initialize player configuration
        self.player_name_vars = []
        self.player_type_vars = []
        self.on_player_count_change()
        
        return self.setup_window
    
    def _create_game_config_section(self, parent):
        """Create the game configuration section"""
        game_config_frame = ttk.LabelFrame(parent, text="Game Configuration", padding="10")
        game_config_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Player count selection
        player_count_frame = ttk.Frame(game_config_frame)
        player_count_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(player_count_frame, text="Number of Players:").pack(side=tk.LEFT)
        self.player_count_var = tk.IntVar(value=2)
        for i in range(2, 5):
            ttk.Radiobutton(player_count_frame, text=str(i), variable=self.player_count_var, 
                           value=i, command=self.on_player_count_change).pack(side=tk.LEFT, padx=(10, 0))
    
    def _create_ai_settings_section(self, parent):
        """Create the AI settings section"""
        ai_settings_frame = ttk.LabelFrame(parent, text="AI Settings", padding="10")
        ai_settings_frame.pack(fill=tk.X, pady=(0, 20))
        
        speed_frame = ttk.Frame(ai_settings_frame)
        speed_frame.pack(fill=tk.X)
        
        ttk.Label(speed_frame, text="AI Action Speed (seconds):").pack(side=tk.LEFT)
        self.ai_speed_var = tk.DoubleVar(value=2.0)
        ai_speed_spinbox = ttk.Spinbox(speed_frame, from_=0.5, to=10.0, increment=0.5, 
                                      textvariable=self.ai_speed_var, width=8, format="%.1f")
        ai_speed_spinbox.pack(side=tk.LEFT, padx=(10, 0))
        
        ttk.Label(speed_frame, text="(Controls how fast AI takes actions)").pack(side=tk.LEFT, padx=(10, 0))
    
    def _create_proximity_settings_section(self, parent):
        """Create the initial proximity settings section"""
        proximity_settings_frame = ttk.LabelFrame(parent, text="Initial Proximity", padding="10")
        proximity_settings_frame.pack(fill=tk.X, pady=(0, 20))
        
        proximity_frame = ttk.Frame(proximity_settings_frame)
        proximity_frame.pack(fill=tk.X)
        
        ttk.Label(proximity_frame, text="Starting Distance Between Teams:").pack(side=tk.LEFT)
        self.proximity_var = tk.StringVar(value="medium")
        
        proximity_options = [
            ("Close", "close", "Teams start very close for immediate combat"),
            ("Medium", "medium", "Balanced starting distance (default)"),
            ("Far", "far", "Teams start at opposite ends for extended maneuvering")
        ]
        
        for text, value, tooltip in proximity_options:
            radio = ttk.Radiobutton(proximity_frame, text=text, variable=self.proximity_var, value=value)
            radio.pack(side=tk.LEFT, padx=(10, 0))
        
        ttk.Label(proximity_settings_frame, text="Controls how close teams spawn to each other at game start", 
                 font=("Arial", 9), foreground="gray").pack(pady=(5, 0))
    
    def _create_buttons(self, parent):
        """Create the action buttons"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="Start Game", command=self._on_start_game).pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Button(button_frame, text="Cancel", command=self._on_cancel).pack(side=tk.RIGHT)
    
    def on_player_count_change(self):
        """Handle player count change"""
        num_players = self.player_count_var.get()
        self._create_player_config_ui(num_players)
    
    def _create_player_config_ui(self, num_players: int):
        """Create dynamic player configuration UI based on player count"""
        # Clear existing player config
        for widget in self.player_config_frame.winfo_children():
            widget.destroy()
        
        # Reset variables
        self.player_name_vars = []
        self.player_type_vars = []
        
        # Color options for players
        player_colors = ["Neon Red", "Neon Blue", "Neon Purple", "Neon Yellow"]
        
        for i in range(num_players):
            player_id = i + 1
            color_name = player_colors[i]
            
            # Player frame
            player_frame = ttk.LabelFrame(self.player_config_frame, 
                                        text=f"Player {player_id} ({color_name} Mechs)", 
                                        padding="10")
            player_frame.pack(fill=tk.X, pady=(0, 10))
            
            # Player type (Human/AI)
            type_var = tk.BooleanVar(value=(i == 0))  # First player is human by default
            self.player_type_vars.append(type_var)
            
            ttk.Radiobutton(player_frame, text="Human Player", variable=type_var, 
                           value=True, command=lambda idx=i: self._on_player_type_change(idx)).pack(anchor=tk.W)
            ttk.Radiobutton(player_frame, text="AI Player", variable=type_var, 
                           value=False, command=lambda idx=i: self._on_player_type_change(idx)).pack(anchor=tk.W)
            
            # Player name
            name_frame = ttk.Frame(player_frame)
            name_frame.pack(fill=tk.X, pady=(10, 0))
            
            ttk.Label(name_frame, text="Name:").pack(side=tk.LEFT)
            
            if i == 0:
                default_name = "Player 1"
            else:
                default_name = self._get_random_ai_name()
            
            name_var = tk.StringVar(value=default_name)
            self.player_name_vars.append(name_var)
            
            name_entry = ttk.Entry(name_frame, textvariable=name_var)
            name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
            
            # Set initial state
            if not type_var.get():  # AI player
                name_entry.config(state=tk.DISABLED)
    
    def _on_player_type_change(self, player_index: int):
        """Handle player type change for a specific player"""
        type_var = self.player_type_vars[player_index]
        name_var = self.player_name_vars[player_index]
        
        # Find the entry widget
        player_frame = self.player_config_frame.winfo_children()[player_index]
        name_frame = None
        for child in player_frame.winfo_children():
            if isinstance(child, ttk.Frame):
                name_frame = child
                break
        
        if name_frame:
            entry_widget = None
            for child in name_frame.winfo_children():
                if isinstance(child, ttk.Entry):
                    entry_widget = child
                    break
            
            if entry_widget:
                if type_var.get():  # Human player
                    entry_widget.config(state=tk.NORMAL)
                    name_var.set(f"Player {player_index + 1}")
                else:  # AI player
                    entry_widget.config(state=tk.DISABLED)
                    name_var.set(self._get_random_ai_name())
    
    def _get_random_ai_name(self) -> str:
        """Get a random AI name"""
        return random.choice(self.ai_names)
    
    def _on_start_game(self):
        """Handle start game button click"""
        # Collect configuration
        config = {
            'num_players': self.player_count_var.get(),
            'ai_speed': self.ai_speed_var.get(),
            'proximity': self.proximity_var.get(),
            'players': []
        }
        
        # Collect player configurations
        for i in range(config['num_players']):
            player_config = {
                'name': self.player_name_vars[i].get(),
                'is_ai': not self.player_type_vars[i].get()
            }
            config['players'].append(player_config)
        
        # Call the start callback
        self.on_start_callback(config)
    
    def _on_cancel(self):
        """Handle cancel button click"""
        self.on_cancel_callback()
    
    def destroy(self):
        """Destroy the setup window"""
        if self.setup_window and self.setup_window.winfo_exists():
            self.setup_window.quit()
            self.setup_window.destroy()
