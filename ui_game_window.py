"""
pyMechAttack - Game Window UI Module
Handles the main game window layout and UI components
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Any


class GameWindowUI:
    """Manages the main game window UI layout and components"""
    
    def __init__(self, root: tk.Tk):
        """
        Initialize the game window UI
        
        Args:
            root: The main Tkinter window
        """
        self.root = root
        
        # UI component references
        self.canvas = None
        self.combat_log = None
        self.turn_label = None
        self.current_mech_label = None
        self.initiative_frame = None
        self.mech_info_frame = None
        self.target_info_frame = None
        self.instruction_label = None
        self.status_label = None
        self.size_label = None
        self.left_frame = None
        
        # Button references
        self.attack_laser_btn = None
        self.attack_missile_btn = None
        self.end_movement_btn = None
        self.end_turn_btn = None
        self.help_btn = None
        
    def setup(self, on_help_click: Callable[[], None]) -> tk.Canvas:
        """
        Setup the user interface and return the game canvas
        
        Args:
            on_help_click: Callback for help button
            
        Returns:
            The game canvas widget
        """
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Help link at the very top
        self._create_help_link(main_frame, on_help_click)
        
        # Top section with map and turn info
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left panel for game board
        self.left_frame = self._create_left_panel(top_frame)
        
        # Right panel for turn and initiative info
        self._create_right_panel(top_frame)
        
        # Bottom panel for mech information and buttons
        self._create_bottom_panel(main_frame)
        
        # Status bar at the very bottom
        self._create_status_bar(main_frame)
        
        return self.canvas
    
    def _create_help_link(self, parent, on_help_click: Callable[[], None]):
        """Create the help link at the top"""
        help_link_frame = ttk.Frame(parent)
        help_link_frame.pack(fill=tk.X, pady=(0, 5))
        
        help_label = tk.Label(help_link_frame, text="📖 Click here for gaming guide and instructions", 
                             font=("Arial", 10, "bold"), foreground="#0066CC", cursor="hand2")
        help_label.pack()
        help_label.bind("<Button-1>", lambda e: on_help_click())
        
        # Underline effect on hover
        help_label.bind("<Enter>", lambda e: help_label.config(font=("Arial", 10, "bold underline")))
        help_label.bind("<Leave>", lambda e: help_label.config(font=("Arial", 10, "bold")))
    
    def _create_left_panel(self, parent) -> ttk.Frame:
        """Create the left panel with map legend and game board"""
        left_frame = ttk.Frame(parent)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Map Legend at the top
        self._create_map_legend(left_frame)
        
        # Canvas for hex board with dynamic sizing
        self.canvas = tk.Canvas(left_frame, bg="darkgreen")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        return left_frame
    
    def _create_map_legend(self, parent):
        """Create the map legend section"""
        legend_title_frame = ttk.Frame(parent)
        legend_title_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(legend_title_frame, text="Map Legend:", font=("Arial", 12, "bold")).pack(side=tk.LEFT)
        ttk.Label(legend_title_frame, text="| Click & Drag to Pan View", font=("Arial", 9), 
                 foreground="blue").pack(side=tk.LEFT, padx=(20, 0))
        
        legend_frame = ttk.Frame(parent)
        legend_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Create legend items in horizontal layout
        terrain_types = [
            ("lightgreen", "Clear (1)"),
            ("darkgreen", "Forest (2, Cover)"),
            ("lightblue", "Shallow Water (3)"),
            ("darkblue", "Deep Water (X)"),
            ("darkgray", "Mountain (X, Blocks LOS)")
        ]
        
        for i, (color, description) in enumerate(terrain_types):
            item_frame = ttk.Frame(legend_frame)
            item_frame.pack(side=tk.LEFT, padx=(0, 15))
            
            # Color square
            color_canvas = tk.Canvas(item_frame, width=15, height=15, highlightthickness=0)
            color_canvas.pack(side=tk.LEFT, padx=(0, 3))
            color_canvas.create_rectangle(0, 0, 15, 15, fill=color, outline="black")
            
            # Description
            ttk.Label(item_frame, text=description, font=("Arial", 9)).pack(side=tk.LEFT)
    
    def _create_right_panel(self, parent):
        """Create the right panel with turn info and combat log"""
        right_frame = ttk.Frame(parent, width=250)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        right_frame.pack_propagate(False)
        
        # Turn info section
        ttk.Label(right_frame, text="Turn Information", font=("Arial", 14, "bold")).pack(pady=(0, 10))
        
        self.turn_label = ttk.Label(right_frame, text="Turn 1", font=("Arial", 12, "bold"))
        self.turn_label.pack(pady=2)
        
        self.current_mech_label = ttk.Label(right_frame, text="Active: None", font=("Arial", 10))
        self.current_mech_label.pack(pady=2)
        
        # Initiative order display
        ttk.Label(right_frame, text="Initiative Order:", font=("Arial", 11, "bold")).pack(anchor=tk.W, pady=(15, 5))
        self.initiative_frame = ttk.Frame(right_frame)
        self.initiative_frame.pack(fill=tk.X, pady=5)
        
        # Combat log in right panel
        ttk.Label(right_frame, text="Combat Log:", font=("Arial", 11, "bold")).pack(anchor=tk.W, pady=(20, 5))
        
        log_frame = ttk.Frame(right_frame)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.combat_log = tk.Text(log_frame, height=12, state=tk.DISABLED, font=("Arial", 8))
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.combat_log.yview)
        self.combat_log.configure(yscrollcommand=scrollbar.set)
        
        self.combat_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _create_bottom_panel(self, parent):
        """Create the bottom panel with mech info and action buttons"""
        bottom_frame = ttk.Frame(parent)
        bottom_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Create a tabbed info panel
        info_notebook = ttk.Notebook(bottom_frame)
        info_notebook.pack(fill=tk.X, pady=2)
        
        # Tab 1: Selected Mech Information
        self._create_mech_info_tab(info_notebook)
        
        # Tab 2: Target Information
        self._create_target_info_tab(info_notebook)
        
        # Action buttons below tabs
        self._create_action_buttons(bottom_frame)
    
    def _create_mech_info_tab(self, notebook):
        """Create the selected mech information tab"""
        mech_tab = ttk.Frame(notebook)
        notebook.add(mech_tab, text="Selected Mech")
        
        mech_info_frame = ttk.Frame(mech_tab)
        mech_info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.mech_info_frame = ttk.Frame(mech_info_frame)
        self.mech_info_frame.pack(fill=tk.X, pady=2)
        
        # Instruction label
        self.instruction_label = ttk.Label(mech_info_frame, text="Select a mech to see options", 
                                         font=("Arial", 9), foreground="gray")
        self.instruction_label.pack(anchor=tk.W, pady=(2, 0))
    
    def _create_target_info_tab(self, notebook):
        """Create the target information tab"""
        target_tab = ttk.Frame(notebook)
        notebook.add(target_tab, text="Target")
        
        target_info_frame = ttk.Frame(target_tab)
        target_info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.target_info_frame = ttk.Frame(target_info_frame)
        self.target_info_frame.pack(fill=tk.X, pady=2)
    
    def _create_action_buttons(self, parent):
        """Create the action buttons"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Label(button_frame, text="Actions:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(5, 10))
        
        self.attack_laser_btn = ttk.Button(button_frame, text="🔫 Laser", 
                                         state=tk.DISABLED, width=15)
        self.attack_laser_btn.pack(side=tk.LEFT, padx=2)
        
        self.attack_missile_btn = ttk.Button(button_frame, text="🚀 Missile", 
                                           state=tk.DISABLED, width=15)
        self.attack_missile_btn.pack(side=tk.LEFT, padx=2)
        
        self.end_movement_btn = ttk.Button(button_frame, text="End Movement", 
                                         state=tk.DISABLED, width=15)
        self.end_movement_btn.pack(side=tk.LEFT, padx=2)
        
        self.end_turn_btn = ttk.Button(button_frame, text="End Turn", width=12)
        self.end_turn_btn.pack(side=tk.LEFT, padx=2)
        
        self.help_btn = ttk.Button(button_frame, text="Help", width=10)
        self.help_btn.pack(side=tk.RIGHT, padx=(10, 5))
    
    def _create_status_bar(self, parent):
        """Create the status bar at the bottom"""
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Add a separator line
        separator = ttk.Separator(status_frame, orient='horizontal')
        separator.pack(fill=tk.X, pady=(2, 5))
        
        self.status_label = ttk.Label(status_frame, text="Game initialized. Select a mech to begin.", 
                                    font=("Arial", 9), foreground="darkblue")
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        # Add window size info
        self.size_label = ttk.Label(status_frame, text="", font=("Arial", 8), foreground="gray")
        self.size_label.pack(side=tk.RIGHT, padx=5)
    
    def set_button_command(self, button_name: str, command: Callable[[], None]):
        """
        Set a command for a button
        
        Args:
            button_name: Name of the button ('laser', 'missile', 'end_movement', 'end_turn', 'help')
            command: Callback function
        """
        button_map = {
            'laser': self.attack_laser_btn,
            'missile': self.attack_missile_btn,
            'end_movement': self.end_movement_btn,
            'end_turn': self.end_turn_btn,
            'help': self.help_btn
        }
        
        if button_name in button_map and button_map[button_name]:
            button_map[button_name].config(command=command)
    
    def set_button_state(self, button_name: str, enabled: bool):
        """
        Enable or disable a button
        
        Args:
            button_name: Name of the button
            enabled: True to enable, False to disable
        """
        button_map = {
            'laser': self.attack_laser_btn,
            'missile': self.attack_missile_btn,
            'end_movement': self.end_movement_btn,
            'end_turn': self.end_turn_btn,
            'help': self.help_btn
        }
        
        if button_name in button_map and button_map[button_name]:
            state = tk.NORMAL if enabled else tk.DISABLED
            button_map[button_name].config(state=state)
    
    def update_status(self, message: str):
        """Update the status bar message"""
        if self.status_label:
            self.status_label.config(text=message)
    
    def update_window_size_info(self, width: int, height: int):
        """Update the window size information display"""
        if self.size_label:
            self.size_label.config(text=f"Window: {width}x{height}")
    
    def log_message(self, message: str):
        """Add a message to the combat log"""
        if self.combat_log:
            self.combat_log.config(state=tk.NORMAL)
            self.combat_log.insert(tk.END, message + "\n")
            self.combat_log.see(tk.END)
            self.combat_log.config(state=tk.DISABLED)
