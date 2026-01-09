import tkinter as tk
from tkinter import ttk, messagebox
import math
import random
import heapq
import json
import traceback
import gc
import time
import logging
from typing import List, Tuple, Optional, Dict, Union, TYPE_CHECKING

# Import from new modular files
from exceptions import (
    BattleTechException, InvalidMoveException, InvalidTargetException,
    OutOfRangeException, NoLineOfSightException, InvalidPhaseException,
    MechDestroyedException, InvalidWeaponException, InsufficientMovementException,
    ConfigurationException
)
from models import MechStats, MechPhase
from animations import Animation, MoveAnimation, WeaponFireAnimation, ExplosionAnimation, PulseAnimation
from entities import HexTile, Mech
import hex_utils
from animation_renderer import AnimationRenderer

if TYPE_CHECKING:
    from __main__ import BattleTechGame


class BattleTechGame:
    """Main game class"""
    def __init__(self):
        # Don't create root window yet - will be created after setup
        self.root = None
        
        # Validate and set multi-player configuration (2-4 players)
        self.num_players = 2  # Default to 2 players
        if not (2 <= self.num_players <= 4):
            raise ValueError("Number of players must be between 2 and 4")
            
        self.players = [
            {"name": "Player 1", "is_ai": False, "color": "#FF073A"},  # Neon Red
            {"name": "Player 2", "is_ai": True, "color": "#00D9FF"},    # Neon Blue
            {"name": "Player 3", "is_ai": False, "color": "#BC13FE"},  # Neon Purple
            {"name": "Player 4", "is_ai": True, "color": "#FFFF00"}    # Neon Yellow
        ]
        
        # Validate AI action speed
        self.ai_action_speed = 2.0  # Default 2 seconds delay for AI actions
        if self.ai_action_speed < 0.1:
            self.ai_action_speed = 0.1  # Minimum speed limit
        
        # Initial proximity setting
        self.initial_proximity = "medium"  # Default proximity setting
        
        # AI names for random selection
        self.ai_names = [
            "Commander Steel", "Major Forge", "Captain Titan", "Colonel Storm",
            "General Viper", "Marshal Kane", "Admiral Rex", "Commander Nova",
            "Major Blitz", "Captain Razor", "Colonel Frost", "General Phoenix",
            "Marshal Thunder", "Admiral Hawk", "Commander Bolt", "Major Reaper"
        ]
        
        # Game state - initialize to None/empty, will be set up after player configuration
        self.board_size = 20  # Increased from 15 to 20 for larger battlefield
        self.hex_tiles: Dict[Tuple[int, int], HexTile] = {}
        self.mechs: List[Mech] = []
        self.initiative_order: List[Mech] = []  # Order of mech activation
        self.current_mech_index = 0  # Index in initiative order
        self.current_turn = 1
        self.selected_mech: Optional[Mech] = None
        self.game_over = False
        
        # Validate configuration after initialization
        self._validate_configuration()
        
        # Performance optimization: Canvas object caching
        self.canvas_objects_cache = {
            'hex_objects': {},  # Cache hex canvas objects
            'mech_objects': {},  # Cache mech canvas objects
            'effect_objects': {}  # Cache effect objects
        }
        self.dirty_hexes = set()  # Track which hexes need redrawing
        self.last_draw_time = 0
        self.draw_times = []  # Track performance
        
        # AI decision caching for performance
        self.ai_cache = {
            'position_scores': {},
            'target_evaluations': {},
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        # Animation system
        self.animations = []  # List of active animations
        self.animation_id = 0  # Unique ID counter for animations
        self.animation_effects = {}  # Store active visual effects
        self.last_animation_update = 0  # Control animation frame rate
        self.animation_fps = 60  # Target FPS for animations
        
        # Performance monitoring
        self.show_fps = False
        self.fps_counter = 0
        self.fps_last_time = time.time()
        self.fps_display = 0.0
        self.performance_metrics = {
            'frame_times': [],
            'animation_count': 0,
            'ui_updates': 0
        }
        
        # Display constants for responsive board (will be updated in setup_ui)
        self.hex_size = 25
        self.canvas_width = 650  # Will be set properly in setup_ui
        self.canvas_height = 450  # Will be set properly in setup_ui
        
        # Pan/scroll state
        self.pan_start_x = 0
        self.pan_start_y = 0
        self.is_panning = False
        self.total_drag_distance = 0
        self.view_offset_x = 0  # Camera offset
        self.view_offset_y = 0
        
        # Calculate total map size (much larger than visible area)
        self.total_map_width = self.hex_size * 3 * self.board_size
        self.total_map_height = self.hex_size * 2 * self.board_size
        
        # Game not initialized yet - this will happen after player setup
        self.game_initialized = False
        
    def _validate_hex_coordinates(self, q: int, r: int) -> bool:
        """Validate hex coordinates are within board bounds"""
        return (isinstance(q, int) and isinstance(r, int) and 
                abs(q) <= self.board_size and abs(r) <= self.board_size and 
                abs(-q-r) <= self.board_size)
                
    def _safe_destroy_widget(self, widget):
        """Safely destroy a tkinter widget"""
        try:
            if widget and widget.winfo_exists():
                widget.destroy()
        except tk.TclError:
            pass  # Widget already destroyed
            
    def _record_draw_time(self, time_ms: float):
        """Record canvas draw time for performance monitoring"""
        self.draw_times.append(time_ms)
        if len(self.draw_times) > 100:  # Keep last 100 measurements
            self.draw_times.pop(0)
            
    def _get_avg_draw_time(self) -> float:
        """Get average draw time in milliseconds"""
        return sum(self.draw_times) / len(self.draw_times) if self.draw_times else 0
        
    def _clear_canvas_cache(self):
        """Clear canvas object cache when needed"""
        self.canvas_objects_cache = {
            'hex_objects': {},
            'mech_objects': {},
            'effect_objects': {}
        }
        self.dirty_hexes.clear()
        
    def _mark_hex_dirty(self, q: int, r: int):
        """Mark a hex as needing redraw"""
        if self._validate_hex_coordinates(q, r):
            self.dirty_hexes.add((q, r))
            
    def _clear_ai_cache(self):
        """Clear AI decision cache at start of each turn"""
        self.ai_cache['position_scores'].clear()
        self.ai_cache['target_evaluations'].clear()
        
    def _validate_configuration(self):
        """Validate game configuration parameters"""
        # Only validate if we have players configured
        if not hasattr(self, 'players') or not self.players:
            return  # Skip validation if players not set up yet
            
        # Validate player count
        if not (2 <= self.num_players <= 4):
            raise ConfigurationException(f"Invalid player count: {self.num_players}. Must be 2-4.")
        
        # Validate board size
        if hasattr(self, 'board_size') and not (10 <= self.board_size <= 50):
            raise ConfigurationException(f"Invalid board size: {self.board_size}. Must be 10-50.")
        
        # Validate AI speed
        if hasattr(self, 'ai_action_speed') and not (0.1 <= self.ai_action_speed <= 10.0):
            raise ConfigurationException(f"Invalid AI speed: {self.ai_action_speed}. Must be 0.1-10.0.")
        
        # Validate proximity setting
        valid_proximities = ["close", "medium", "far"]
        if hasattr(self, 'initial_proximity') and self.initial_proximity not in valid_proximities:
            raise ConfigurationException(f"Invalid proximity: {self.initial_proximity}. Must be one of {valid_proximities}.")
        
        # Validate player colors
        for i, player in enumerate(self.players):
            if "color" not in player:
                raise ConfigurationException(f"Player {i+1} missing color configuration.")
            # Basic hex color validation
            color = player["color"]
            if not (color.startswith("#") and len(color) == 7):
                raise ConfigurationException(f"Invalid color format for player {i+1}: {color}")
        
        print("✓ Configuration validation passed")
        
    def _update_performance_metrics(self):
        """Update performance metrics and FPS counter"""
        current_time = time.time()
        
        # Update FPS counter
        self.fps_counter += 1
        time_since_last_fps = current_time - self.fps_last_time
        
        if time_since_last_fps >= 1.0:  # Update FPS display every second
            self.fps_display = self.fps_counter / time_since_last_fps
            self.fps_counter = 0
            self.fps_last_time = current_time
        
        # Track frame times (keep last 60 frames)
        if hasattr(self, 'last_frame_time'):
            frame_time = current_time - self.last_frame_time
            self.performance_metrics['frame_times'].append(frame_time)
            if len(self.performance_metrics['frame_times']) > 60:
                self.performance_metrics['frame_times'].pop(0)
        
        self.last_frame_time = current_time
        
        # Count active animations
        self.performance_metrics['animation_count'] = len(self.animations)
        
    def toggle_fps_display(self):
        """Toggle FPS display on/off"""
        self.show_fps = not self.show_fps
        if self.show_fps:
            print(f"FPS display enabled. Current FPS: {self.fps_display:.1f}")
        else:
            print("FPS display disabled")
            # Clear FPS display when disabled
            if hasattr(self, 'canvas'):
                self.canvas.delete("fps_display")
    
    def show_performance_stats(self):
        """Display detailed performance statistics"""
        frame_times = self.performance_metrics['frame_times']
        if frame_times:
            avg_frame_time = sum(frame_times) / len(frame_times)
            min_frame_time = min(frame_times)
            max_frame_time = max(frame_times)
            
            stats = f"""Performance Statistics:
• Current FPS: {self.fps_display:.1f}
• Average frame time: {avg_frame_time*1000:.1f}ms
• Min frame time: {min_frame_time*1000:.1f}ms  
• Max frame time: {max_frame_time*1000:.1f}ms
• Active animations: {self.performance_metrics['animation_count']}
• UI updates: {self.performance_metrics['ui_updates']}
• Memory cache hits: {self.ai_cache['cache_hits']}
• Memory cache misses: {self.ai_cache['cache_misses']}

Hotkeys:
F1 - Toggle FPS display
F2 - Show performance stats"""
            
            messagebox.showinfo("Performance Statistics", stats)
            print("Performance stats displayed")
        else:
            messagebox.showinfo("Performance Statistics", "No performance data available yet.")
        
    def _setup_logging(self):
        """Setup game logging"""
        logger = logging.getLogger('BattleTech')
        if not logger.handlers:  # Avoid duplicate handlers
            logger.setLevel(logging.INFO)
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger

    def initialize_first_turn(self):
        """Initialize the first turn without showing popup immediately"""
        # Reset all mechs
        for mech in self.mechs:
            if not mech.is_destroyed():
                mech.start_turn()
        
        # Calculate initial initiative order
        self.initiative_order = self.calculate_initiative_order()
        self.current_mech_index = 0
        
        # Clear selections
        self.selected_mech = None
        if hasattr(self, 'target_mech'):
            delattr(self, 'target_mech')
        
        self.log(f"=== TURN {self.current_turn} ===")
        self.log("Initial initiative order calculated!")
        
        self.update_initiative_display()
        self.activate_next_mech()
        
    def setup_ui(self):
        """Setup the user interface"""
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Help link at the very top
        help_link_frame = ttk.Frame(main_frame)
        help_link_frame.pack(fill=tk.X, pady=(0, 5))
        
        help_label = tk.Label(help_link_frame, text="📖 Click here for gaming guide and instructions", 
                             font=("Arial", 10, "bold"), foreground="#0066CC", cursor="hand2")
        help_label.pack()
        help_label.bind("<Button-1>", lambda e: self.show_readme_popup())
        
        # Underline effect on hover
        help_label.bind("<Enter>", lambda e: help_label.config(font=("Arial", 10, "bold underline")))
        help_label.bind("<Leave>", lambda e: help_label.config(font=("Arial", 10, "bold")))
        
        # Top section with map and turn info
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left panel for game board
        left_frame = ttk.Frame(top_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Map Legend at the top
        legend_title_frame = ttk.Frame(left_frame)
        legend_title_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(legend_title_frame, text="Map Legend:", font=("Arial", 12, "bold")).pack(side=tk.LEFT)
        ttk.Label(legend_title_frame, text="| Click & Drag to Pan View", font=("Arial", 9), foreground="blue").pack(side=tk.LEFT, padx=(20, 0))
        
        legend_frame = ttk.Frame(left_frame)
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
        
        # Canvas for hex board with dynamic sizing
        # Initial size will be set in calculate_canvas_size() after UI is ready
        self.canvas_width = 650  # Initial value, will be updated dynamically
        self.canvas_height = 450  # Initial value, will be updated dynamically
        self.canvas = tk.Canvas(left_frame, bg="darkgreen", 
                               scrollregion=(0, 0, self.total_map_width, self.total_map_height))
        self.canvas.pack(fill=tk.BOTH, expand=True)  # Allow canvas to expand
        
        # Store reference to left_frame for canvas sizing calculations
        self.left_frame = left_frame
        
        # Bind canvas events for pan controls and game interaction
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_press)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<Motion>", self.on_canvas_motion)  # For hover tooltips
        
        # Center the initial view on the battlefield
        self.center_view()
        
        # Initialize animation renderer
        self.animation_renderer = AnimationRenderer(self.canvas, self.hex_to_pixel)
        
        # Start animation loop
        self.start_animation_loop()
        
        # Right panel for turn and initiative info
        right_frame = ttk.Frame(top_frame, width=250)
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
        
        # Bottom panel for current mech information - use a more compact layout
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Create a collapsible info panel with tabs or compact layout
        info_notebook = ttk.Notebook(bottom_frame)
        info_notebook.pack(fill=tk.X, pady=2)
        
        # Tab 1: Mech Information
        mech_tab = ttk.Frame(info_notebook)
        info_notebook.add(mech_tab, text="Selected Mech")
        
        mech_info_frame = ttk.Frame(mech_tab)
        mech_info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.mech_info_frame = ttk.Frame(mech_info_frame)
        self.mech_info_frame.pack(fill=tk.X, pady=2)
        
        # Instruction label
        self.instruction_label = ttk.Label(mech_info_frame, text="Select a mech to see options", 
                                         font=("Arial", 9), foreground="gray")
        self.instruction_label.pack(anchor=tk.W, pady=(2, 0))
        
        # Tab 2: Target Information
        target_tab = ttk.Frame(info_notebook)
        info_notebook.add(target_tab, text="Target")
        
        target_info_frame = ttk.Frame(target_tab)
        target_info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.target_info_frame = ttk.Frame(target_info_frame)
        self.target_info_frame.pack(fill=tk.X, pady=2)
        
        # Action buttons in a separate frame below tabs
        button_frame = ttk.Frame(bottom_frame)
        button_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Create a more compact button layout
        ttk.Label(button_frame, text="Actions:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(5, 10))
        
        self.attack_laser_btn = ttk.Button(button_frame, text="🔫 Laser", 
                                         command=self.laser_attack, state=tk.DISABLED, width=15)
        self.attack_laser_btn.pack(side=tk.LEFT, padx=2)
        
        self.attack_missile_btn = ttk.Button(button_frame, text="🚀 Missile", 
                                           command=self.missile_attack, state=tk.DISABLED, width=15)
        self.attack_missile_btn.pack(side=tk.LEFT, padx=2)
        
        self.end_movement_btn = ttk.Button(button_frame, text="End Movement", 
                                         command=self.end_movement_phase, state=tk.DISABLED, width=15)
        self.end_movement_btn.pack(side=tk.LEFT, padx=2)
        
        self.end_turn_btn = ttk.Button(button_frame, text="End Turn", command=self.end_turn, width=12)
        self.end_turn_btn.pack(side=tk.LEFT, padx=2)
        
        self.help_btn = ttk.Button(button_frame, text="Help", command=self.show_readme_popup, width=10)
        self.help_btn.pack(side=tk.RIGHT, padx=(10, 5))
        
        # Status bar at the very bottom
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Add a separator line
        separator = ttk.Separator(status_frame, orient='horizontal')
        separator.pack(fill=tk.X, pady=(2, 5))
        
        self.status_label = ttk.Label(status_frame, text="Game initialized. Select a mech to begin.", 
                                    font=("Arial", 9), foreground="darkblue")
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        # Add window size info (helpful for debugging layout issues)
        self.size_label = ttk.Label(status_frame, text="", font=("Arial", 8), foreground="gray")
        self.size_label.pack(side=tk.RIGHT, padx=5)
        
        # Update size info when window changes (will be bound after window creation)
        self.update_window_size_info()
        
        # Initialize status
        self.update_status("Game initialized. Select a mech to begin.")
        
    def create_board(self):
        """Create the hex board"""
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
    
    def setup_mechs(self):
        """Setup initial mechs for all players"""
        # Validate game state
        if not self.hex_tiles:
            raise RuntimeError("Board must be created before setting up mechs")
        if not (2 <= self.num_players <= 4):
            raise ValueError(f"Invalid number of players: {self.num_players}")
            
        # Define starting positions for each player (up to 4 players)
        starting_sides = ["northwest", "southeast", "northeast", "southwest"]
        
        # Predefined mech types (same for all players but with different names)
        base_mech_types = [
            ("Atlas", 3, 25, 30, 80, 60),      # Heavy assault mech
            ("Centurion", 4, 20, 25, 60, 45),  # Medium mech
            ("Griffin", 5, 18, 28, 50, 40),    # Fast medium mech
            ("Locust", 8, 12, 15, 30, 25),    # Light scout mech
        ]
        
        for player_id in range(1, self.num_players + 1):
            player_info = self.players[player_id - 1]
            player_name = player_info["name"]
            player_color = player_info["color"]
            
            # Create mech types for this player
            player_mech_types = [
                MechStats(f"{player_name} {name}", speed, laser, missile, armor, structure, armor, structure)
                for name, speed, laser, missile, armor, structure in base_mech_types
            ]
            
            # Find suitable starting positions
            side = starting_sides[player_id - 1]
            player_positions = self.find_starting_positions(player_id=player_id, side=side)
            
            # Create and place mechs
            for i, pos in enumerate(player_positions):
                if i < len(player_mech_types):
                    stats = player_mech_types[i]
                    mech = Mech(player_id, stats, self.hex_tiles[pos])
                    mech.color = player_color  # Set the proper color
                    
                    # Set up callbacks for game interactions (replaces _game_ref)
                    mech.on_move_animation = lambda m, old, new: self.start_move_animation(m, old, new)
                    mech.on_hex_dirty = lambda q, r: self._mark_hex_dirty(q, r)
                    mech.get_line_of_sight = lambda from_h, to_h: hex_utils.has_line_of_sight(from_h, to_h, self.hex_tiles)
                    
                    self.mechs.append(mech)
    
    def find_starting_positions(self, player_id: int, side: str, num_mechs: int = 4) -> list[tuple[int, int]]:
        """Find suitable starting positions on clear terrain or forests in corner areas"""
        suitable_positions = []
        
        # Define search areas for each corner - use outer regions of the board
        # Board size is 20, corners are at the vertices of the hex-shaped board
        # Need to respect cube coordinate constraint: abs(q) + abs(r) + abs(s) <= board_size * 2
        # where s = -q - r
        
        # Calculate corner offset based on proximity setting
        if self.initial_proximity == "close":
            corner_offset = int(self.board_size * 0.25)  # Very close (25% of board radius)
        elif self.initial_proximity == "far":
            corner_offset = int(self.board_size * 0.95)  # Very far (95% of board radius)
        else:  # medium (default)
            corner_offset = int(self.board_size * 0.65)  # Medium distance (65% of board radius)
        
        if side == "northwest":
            # Top-left corner: negative q, negative r, but s = -q-r must be valid
            # For corner, want q ≈ -board_size, r ≈ 0 (top edge)
            q_range = range(-self.board_size, -corner_offset)
            r_range = range(-corner_offset, 1)
        elif side == "northeast":
            # Top-right corner: positive q, negative r
            # For corner, want q ≈ 0, r ≈ -board_size (right-top edge)
            q_range = range(-corner_offset, 1)
            r_range = range(-self.board_size, -corner_offset)
        elif side == "southwest":
            # Bottom-left corner: negative q, positive r
            # For corner, want q ≈ 0, r ≈ board_size (left-bottom edge)
            q_range = range(-corner_offset, 1)
            r_range = range(corner_offset, self.board_size + 1)
        elif side == "southeast":
            # Bottom-right corner: positive q, positive r, but s must be valid
            # For corner, want q ≈ board_size, r ≈ 0 (bottom edge)
            q_range = range(corner_offset, self.board_size + 1)
            r_range = range(-corner_offset, 1)
        else:
            # Fallback for legacy left/right positions (shouldn't be used)
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
            if self.initial_proximity == "close":
                min_distance = 1  # Mechs can be adjacent for close formation
            elif self.initial_proximity == "far":
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
            self.log(f"Warning: Limited suitable terrain for Player {player_id}, using fallback positions")
            
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
                    # Accept any passable terrain in fallback (not just clear/forest)
                    if hex_tile.terrain_type != "deep_water" and hex_tile.terrain_type != "mountain":
                        suitable_positions.append(pos)
        
        # Final safety check - ensure we have at least some positions
        if not suitable_positions:
            self.log(f"Critical: No valid positions found for Player {player_id}, using emergency fallback")
            # Emergency positions based on player ID
            if player_id == 1:
                suitable_positions = [(-3, -1), (-3, 0), (-2, -2), (-2, 0)]
            elif player_id == 2:
                suitable_positions = [(3, -1), (3, 0), (2, -2), (2, 0)]
            elif player_id == 3:
                suitable_positions = [(0, -3), (1, -3), (-1, -2), (1, -2)]
            else:  # player_id == 4
                suitable_positions = [(0, 3), (1, 3), (-1, 2), (1, 2)]
            
            # Filter to only existing positions
            suitable_positions = [pos for pos in suitable_positions if pos in self.hex_tiles]
        
        return suitable_positions[:num_mechs]
    
    def center_view(self):
        """Center the view on the battlefield"""
        # Set view offset to center the battlefield
        self.view_offset_x = 0
        self.view_offset_y = 0
        
        self.draw_board()
    
    def calculate_canvas_size(self):
        """Calculate and update canvas size based on available space"""
        if not hasattr(self, 'left_frame') or not self.left_frame.winfo_exists():
            return
            
        # Update the frame to get current dimensions
        self.left_frame.update_idletasks()
        
        # Get available space in the left frame
        frame_width = self.left_frame.winfo_width()
        frame_height = self.left_frame.winfo_height()
        
        # Account for legend and other elements above the canvas
        # Approximate height used by legend and spacing
        reserved_height = 80  # Legend + padding
        
        # Calculate available canvas space
        available_width = max(400, frame_width - 20)  # Minimum width with padding
        available_height = max(300, frame_height - reserved_height)  # Minimum height
        
        # Update canvas size if it has changed significantly
        if (abs(self.canvas_width - available_width) > 10 or 
            abs(self.canvas_height - available_height) > 10):
            
            self.canvas_width = available_width
            self.canvas_height = available_height
            
            # Update canvas size
            self.canvas.config(width=self.canvas_width, height=self.canvas_height)
            
            # Redraw the map to fit new canvas size
            self.update_display()
    
    def on_window_configure(self, event):
        """Handle window resize events"""
        # Only update for the main window, not child widgets
        if event.widget == self.root:
            self.update_window_size_info()
            # Schedule canvas resize after a short delay to avoid excessive updates
            if self.root:  # Check if root exists
                if hasattr(self, '_resize_after_id'):
                    self.root.after_cancel(self._resize_after_id)
                self._resize_after_id = self.root.after(100, self.calculate_canvas_size)
    
    def update_window_size_info(self):
        """Update the window size information in the status bar"""
        if hasattr(self, 'size_label') and self.root:
            width = self.root.winfo_width()
            height = self.root.winfo_height()
            self.size_label.config(text=f"{width}×{height}")
    
    def update_status(self, message):
        """Update the status bar with a message"""
        if hasattr(self, 'status_label'):
            self.status_label.config(text=message)
    
    def on_canvas_press(self, event):
        """Handle mouse press for starting pan operation or game click"""
        self.pan_start_x = event.x
        self.pan_start_y = event.y
        self.is_panning = False
        self.total_drag_distance = 0
    
    def on_canvas_drag(self, event):
        """Handle mouse drag for panning the view"""
        # Calculate how far the mouse has moved
        dx = event.x - self.pan_start_x
        dy = event.y - self.pan_start_y
        
        # Track total drag distance
        self.total_drag_distance += abs(dx) + abs(dy)
        
        # If mouse has moved significantly, start panning
        if self.total_drag_distance > 5:
            self.is_panning = True
            
            # Update view offset
            self.view_offset_x += dx
            self.view_offset_y += dy
            
            # Limit panning to reasonable bounds
            max_offset = 500
            self.view_offset_x = max(-max_offset, min(max_offset, self.view_offset_x))
            self.view_offset_y = max(-max_offset, min(max_offset, self.view_offset_y))
            
            # Update pan start position for smooth dragging
            self.pan_start_x = event.x
            self.pan_start_y = event.y
            
            # Force complete redraw with new view
            self.update_display()
    
    def on_canvas_release(self, event):
        """Handle mouse release - either complete pan or process game click"""
        if not self.is_panning and self.total_drag_distance <= 5:
            # This was a click, not a pan - process as game interaction
            self.on_canvas_click(event)
        
        # Reset panning state
        self.is_panning = False
        self.total_drag_distance = 0
    
    # ============== ANIMATION SYSTEM ==============
    
    def start_animation_loop(self):
        """Start the main animation loop"""
        # Initialize timing
        self.last_animation_update = time.time()
        # Add error recovery
        try:
            self.update_animations()
        except Exception as e:
            print(f"Error starting animation loop: {e}")
            # Continue without animations rather than crash
        
    def update_animations(self):
        """Update all active animations"""
        current_time = time.time()
        
        # Update performance metrics
        self._update_performance_metrics()
        
        # Update all animations with error handling
        active_animations = []
        for animation in self.animations:
            try:
                if animation.update():
                    active_animations.append(animation)
                else:
                    # Animation completed, clean up safely
                    try:
                        animation.cleanup(self.canvas)
                    except Exception as e:
                        print(f"Warning: Animation cleanup failed: {e}")
            except Exception as e:
                print(f"Warning: Animation update failed: {e}")
                # Force cleanup on failed animation
                try:
                    animation.cleanup(self.canvas)
                except:
                    pass
                
        self.animations = active_animations
        
        # Update visual effects using renderer
        try:
            self.animation_renderer.update_animation_effects(self.animations, self.selected_mech)
        except Exception as e:
            print(f"Warning: Animation effects update failed: {e}")
        
        # Draw FPS counter if enabled
        if self.show_fps:
            try:
                # Clear previous FPS display
                self.canvas.delete("fps_display")
                
                # Draw current FPS
                fps_text = f"FPS: {self.fps_display:.1f} | Animations: {len(self.animations)}"
                self.canvas.create_text(10, 10, text=fps_text, anchor="nw", 
                                      fill="white", font=("Arial", 10), tags="fps_display")
            except Exception as e:
                print(f"Warning: FPS display failed: {e}")
        
        # Schedule next update with frame rate control
        if hasattr(self, 'root') and self.root:
            try:
                # Control frame rate - skip frames if running behind
                current_time = time.time()
                target_interval = 1.0 / self.animation_fps  # 60 FPS = 16.67ms
                elapsed = current_time - self.last_animation_update
                
                if elapsed >= target_interval:
                    self.last_animation_update = current_time
                    self.root.after(16, self.update_animations)
                else:
                    # Skip this frame to maintain target FPS
                    delay = int((target_interval - elapsed) * 1000)
                    self.root.after(max(1, delay), self.update_animations)
            except tk.TclError:
                # Window destroyed, stop animation loop
                pass
    
    def start_move_animation(self, mech, start_hex: HexTile, end_hex: HexTile):
        """Start a movement animation"""
        start_pos = self.hex_to_pixel(start_hex.q, start_hex.r)
        end_pos = self.hex_to_pixel(end_hex.q, end_hex.r)
        
        # Convert to integers
        start_pos = (int(start_pos[0]), int(start_pos[1]))
        end_pos = (int(end_pos[0]), int(end_pos[1]))
        
        animation = MoveAnimation(self.animation_id, mech, start_pos, end_pos)
        self.animation_id += 1
        self.animations.append(animation)
        return animation
    
    def start_weapon_animation(self, weapon_type: str, start_hex: HexTile, end_hex: HexTile):
        """Start a weapon firing animation"""
        start_pos = self.hex_to_pixel(start_hex.q, start_hex.r)
        end_pos = self.hex_to_pixel(end_hex.q, end_hex.r)
        
        # Convert to integers
        start_pos = (int(start_pos[0]), int(start_pos[1]))
        end_pos = (int(end_pos[0]), int(end_pos[1]))
        
        animation = WeaponFireAnimation(self.animation_id, weapon_type, start_pos, end_pos)
        self.animation_id += 1
        self.animations.append(animation)
        return animation
    
    def start_explosion_animation(self, target_hex: HexTile, hit_type: str = "hit"):
        """Start an explosion animation"""
        pos = self.hex_to_pixel(target_hex.q, target_hex.r)
        
        # Convert to integers
        pos = (int(pos[0]), int(pos[1]))
        
        animation = ExplosionAnimation(self.animation_id, pos, hit_type)
        self.animation_id += 1
        self.animations.append(animation)
        return animation
    
    def start_pulse_animation(self, mech):
        """Start a pulsing highlight animation for selected mech"""
        # Remove any existing pulse for this mech
        self.stop_pulse_animation(mech)
        
        animation = PulseAnimation(self.animation_id, mech)
        self.animation_id += 1
        self.animations.append(animation)
        return animation
    
    def stop_pulse_animation(self, mech):
        """Stop pulsing animation for a specific mech"""
        for animation in self.animations[:]:  # Create a copy to iterate
            if isinstance(animation, PulseAnimation) and animation.mech == mech:
                animation.cleanup(self.canvas)
                self.animations.remove(animation)
    
    # ============== END ANIMATION SYSTEM ==============
    
    def on_canvas_motion(self, event):
        """Handle mouse motion for hover tooltips"""
        # Clear any existing hover tooltip
        self.canvas.delete("hover_tooltip")
        
        # Convert pixel coordinates to hex coordinates
        q, r = self.pixel_to_hex(event.x, event.y)
        
        # Check if there's a mech at this hex
        if (q, r) in self.hex_tiles:
            hex_tile = self.hex_tiles[(q, r)]
            if hex_tile.mech and not hex_tile.mech.is_destroyed():
                mech = hex_tile.mech
                
                # Get mech position on canvas
                x, y = self.hex_to_pixel(mech.hex_tile.q, mech.hex_tile.r)
                
                # Get mech color
                mech_color = mech.color
                
                # Build tooltip text with name and health info
                tooltip_lines = [
                    mech.stats.name,
                    f"Armor: {mech.stats.armor_hp}/{mech.stats.max_armor_hp}",
                    f"Structure: {mech.stats.structure_hp}/{mech.stats.max_structure_hp}"
                ]
                
                # Draw tooltip above the mech
                tooltip_y = y - 50
                line_height = 14
                
                # Calculate tooltip size
                max_text_width = max(len(line) for line in tooltip_lines) * 7
                tooltip_height = len(tooltip_lines) * line_height
                padding = 8
                
                # Create background rectangle for tooltip
                self.canvas.create_rectangle(
                    x - max_text_width//2 - padding, tooltip_y - padding,
                    x + max_text_width//2 + padding, tooltip_y + tooltip_height - padding,
                    fill="black", outline=mech_color, width=2, tags="hover_tooltip"
                )
                
                # Create text labels for each line
                for i, line in enumerate(tooltip_lines):
                    text_y = tooltip_y + i * line_height
                    font = ("Arial", 10, "bold") if i == 0 else ("Arial", 9)
                    self.canvas.create_text(
                        x, text_y,
                        text=line,
                        font=font,
                        fill=mech_color,
                        tags="hover_tooltip"
                    )
    
    # Wrapper methods for hex_utils functions (for convenience)
    def hex_to_pixel(self, q: int, r: int) -> Tuple[float, float]:
        """Convert hex coordinates to pixel coordinates"""
        return hex_utils.hex_to_pixel(q, r, self.hex_size, self.canvas_width, 
                                       self.canvas_height, self.view_offset_x, self.view_offset_y)
    
    def pixel_to_hex(self, x: float, y: float) -> Tuple[int, int]:
        """Convert pixel coordinates to hex coordinates"""
        return hex_utils.pixel_to_hex(x, y, self.hex_size, self.canvas_width, 
                                       self.canvas_height, self.view_offset_x, self.view_offset_y)
    
    def has_line_of_sight(self, from_hex: HexTile, to_hex: HexTile) -> tuple[bool, int]:
        """Check line of sight between two hexes"""
        return hex_utils.has_line_of_sight(from_hex, to_hex, self.hex_tiles)
    
    def calculate_reachable_hexes(self, from_hex: HexTile, max_movement: int) -> Dict[Tuple[int, int], int]:
        """Calculate reachable hexes with movement costs"""
        return hex_utils.calculate_reachable_hexes(from_hex, max_movement, self.hex_tiles, 
                                                     self.selected_mech if hasattr(self, 'selected_mech') else None)
    
    def show_game_setup(self):
        """Show the game setup screen for player configuration"""
        # Create the setup window as the main window
        setup_window = tk.Tk()
        setup_window.title("BattleTech Game Setup")
        setup_window.geometry("600x700")  # Larger to accommodate more players
        setup_window.resizable(True, True)  # Allow resizing
        
        # Center the window on screen
        setup_window.update_idletasks()
        x = (setup_window.winfo_screenwidth() // 2) - (300)
        y = (setup_window.winfo_screenheight() // 2) - (350)
        setup_window.geometry(f"600x700+{x}+{y}")
        
        # Store reference to setup window
        self.setup_window = setup_window
        
        # Ensure it's visible and on top
        setup_window.lift()
        setup_window.focus_force()
        setup_window.attributes('-topmost', True)
        setup_window.after(100, lambda: setup_window.attributes('-topmost', False))
        
        # Main frame with scrollable content
        main_canvas = tk.Canvas(setup_window)
        scrollbar = ttk.Scrollbar(setup_window, orient="vertical", command=main_canvas.yview)
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
        title_label = ttk.Label(scrollable_frame, text="BattleTech Hex Battle Setup", 
                               font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Game Configuration
        game_config_frame = ttk.LabelFrame(scrollable_frame, text="Game Configuration", padding="10")
        game_config_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Player count selection
        player_count_frame = ttk.Frame(game_config_frame)
        player_count_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(player_count_frame, text="Number of Players:").pack(side=tk.LEFT)
        self.player_count_var = tk.IntVar(value=2)
        for i in range(2, 5):
            ttk.Radiobutton(player_count_frame, text=str(i), variable=self.player_count_var, 
                           value=i, command=self.on_player_count_change).pack(side=tk.LEFT, padx=(10, 0))
        
        # Player configuration area
        self.player_config_frame = ttk.Frame(scrollable_frame)
        self.player_config_frame.pack(fill=tk.X, pady=(0, 15))
        
        # AI Settings
        ai_settings_frame = ttk.LabelFrame(scrollable_frame, text="AI Settings", padding="10")
        ai_settings_frame.pack(fill=tk.X, pady=(0, 20))
        
        speed_frame = ttk.Frame(ai_settings_frame)
        speed_frame.pack(fill=tk.X)
        
        ttk.Label(speed_frame, text="AI Action Speed (seconds):").pack(side=tk.LEFT)
        self.ai_speed_var = tk.DoubleVar(value=2.0)
        ai_speed_spinbox = ttk.Spinbox(speed_frame, from_=0.5, to=10.0, increment=0.5, 
                                      textvariable=self.ai_speed_var, width=8, format="%.1f")
        ai_speed_spinbox.pack(side=tk.LEFT, padx=(10, 0))
        
        ttk.Label(speed_frame, text="(Controls how fast AI takes actions)").pack(side=tk.LEFT, padx=(10, 0))
        
        # Initial Proximity Settings
        proximity_settings_frame = ttk.LabelFrame(scrollable_frame, text="Initial Proximity", padding="10")
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
        
        # Buttons
        button_frame = ttk.Frame(scrollable_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="Start Game", command=lambda: self.start_game_from_setup(setup_window)).pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Button(button_frame, text="Cancel", command=self.cancel_setup).pack(side=tk.RIGHT)
        
        # Initialize player configuration
        self.player_name_vars = []
        self.player_type_vars = []
        self.on_player_count_change()
    
    def cancel_setup(self):
        """Cancel setup and exit application"""
        if hasattr(self, 'setup_window'):
            self.setup_window.quit()
            self.setup_window.destroy()
    
    def on_player_count_change(self):
        """Handle player count change"""
        self.num_players = self.player_count_var.get()
        self.create_player_config_ui()
    
    def create_player_config_ui(self):
        """Create dynamic player configuration UI based on player count"""
        # Clear existing player config
        for widget in self.player_config_frame.winfo_children():
            widget.destroy()
        
        # Reset variables
        self.player_name_vars = []
        self.player_type_vars = []
        
        # Color options for players
        player_colors = ["Neon Red", "Neon Blue", "Neon Purple", "Neon Yellow"]
        
        for i in range(self.num_players):
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
                           value=True, command=lambda idx=i: self.on_player_type_change(idx)).pack(anchor=tk.W)
            ttk.Radiobutton(player_frame, text="AI Player", variable=type_var, 
                           value=False, command=lambda idx=i: self.on_player_type_change(idx)).pack(anchor=tk.W)
            
            # Player name
            name_frame = ttk.Frame(player_frame)
            name_frame.pack(fill=tk.X, pady=(10, 0))
            
            ttk.Label(name_frame, text="Name:").pack(side=tk.LEFT)
            
            if i == 0:
                default_name = "Player 1"
            else:
                default_name = self.get_random_ai_name()
            
            name_var = tk.StringVar(value=default_name)
            self.player_name_vars.append(name_var)
            
            name_entry = ttk.Entry(name_frame, textvariable=name_var)
            name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
            
            # Set initial state
            if not type_var.get():  # AI player
                name_entry.config(state=tk.DISABLED)
    
    def on_player_type_change(self, player_index):
        """Handle player type change for a specific player"""
        type_var = self.player_type_vars[player_index]
        name_var = self.player_name_vars[player_index]
        
        # Find the entry widget (bit hacky but works)
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
                    name_var.set(self.get_random_ai_name())
    
    def get_random_ai_name(self) -> str:
        """Get a random AI name"""
        return random.choice(self.ai_names)
    

    def start_game_from_setup(self, setup_window):
        """Start the game with the configured settings"""
        try:
            # Save player configuration from UI
            self.num_players = self.player_count_var.get()
            self.ai_action_speed = self.ai_speed_var.get()
            self.initial_proximity = self.proximity_var.get()
            
            # Update player configuration
            for i in range(self.num_players):
                player_name = self.player_name_vars[i].get().strip() or f"Player {i+1}"
                is_ai = not self.player_type_vars[i].get()
                
                self.players[i]["name"] = player_name
                self.players[i]["is_ai"] = is_ai
            
            # Create the main game window with intelligent sizing
            self.root = tk.Tk()
            self.root.title("BattleTech Hex Battle")
            
            # Get screen dimensions for intelligent sizing
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            # Calculate optimal window size (80% of screen, but with reasonable limits)
            optimal_width = min(1000, int(screen_width * 0.8))
            optimal_height = min(700, int(screen_height * 0.8))
            
            # Ensure minimum usable size
            window_width = max(900, optimal_width)
            window_height = max(600, optimal_height)
            
            # Center the window
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2
            
            self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
            self.root.minsize(900, 600)    # Minimum size to ensure usability
            self.root.resizable(True, True)  # Allow resizing
            
            # Close setup window
            setup_window.destroy()
            
            # Initialize the actual game for the first time
            self.setup_ui()
            self.create_board()
            self.setup_mechs()
            
            # Log initial deployment
            self.log("=== MISSION DEPLOYMENT ===")
            for player_id in range(1, self.num_players + 1):
                player_mechs = [m for m in self.mechs if m.player_id == player_id]
                player_name = self.players[player_id - 1]["name"]
                
                self.log(f"{player_name} Force:")
                for mech in player_mechs:
                    terrain = mech.hex_tile.get_terrain_name()
                    self.log(f"  {mech.stats.name} deployed at ({mech.hex_tile.q}, {mech.hex_tile.r}) [{terrain}]")
            
            self.log("All mechs deployed on suitable terrain (Clear or Forest only)")
            
            # Initialize turn
            self.initialize_first_turn()
            
            # Calculate initiative and start game
            self.initiative_order = self.calculate_initiative_order()
            self.activate_next_mech()
            
            self.game_initialized = True
            
            # Bind window events after everything is set up
            self.root.bind('<Configure>', self.on_window_configure)
            
            # Bind keyboard shortcuts
            self.root.bind('<F1>', lambda e: self.toggle_fps_display())
            self.root.bind('<F2>', lambda e: self.show_performance_stats())
            
            # Set focus to root so keyboard events work
            self.root.focus_set()
            self.update_window_size_info()
            
            # Calculate initial canvas size after UI is ready
            self.root.after(100, self.calculate_canvas_size)
            
            # Start the main game loop
            self.root.mainloop()
            
        except Exception as e:
            error_msg = f"Failed to start game: {str(e)}"
            traceback.print_exc()
            try:
                messagebox.showerror("Game Initialization Error", error_msg)
            except Exception as msg_error:
                print(f"Failed to show error dialog: {msg_error}")
                print(error_msg)  # Fallback if messagebox fails
            if hasattr(self, 'root') and self.root:
                try:
                    self.root.quit()
                except tk.TclError:
                    pass
    
    def get_mechs_in_range(self, attacking_mech: Mech, weapon_type: str) -> list[Mech]:
        """Get all enemy mechs within range of the specified weapon and with clear LOS"""
        if weapon_type == "laser":
            base_range = 8
        elif weapon_type == "missile":
            base_range = 12
        else:
            return []
        
        targets = []
        for mech in self.mechs:
            if mech.player_id != attacking_mech.player_id and not mech.is_destroyed():
                distance = attacking_mech.hex_tile.distance_to(mech.hex_tile)
                
                # Check line of sight
                has_los, range_modifier = self.has_line_of_sight(attacking_mech.hex_tile, mech.hex_tile)
                
                if has_los:
                    # Apply range reduction from forests
                    effective_range = base_range - range_modifier
                    if distance <= effective_range:
                        targets.append(mech)
        
        return targets

    def draw_board(self):
        """Draw the hex board and all game elements with performance optimization"""
        start_time = time.time()
        
        # Calculate visible hex range based on current view offset
        visible_margin = 8  # Draw more extra hexes to ensure visibility
        
        # Always clear canvas to prevent artifacts during panning and updates
        self.canvas.delete("all")
        
        # Clear animation objects that might not have proper tags
        try:
            self.canvas.delete("weapon_effect", "explosion_effect", "pulse_effect", "hover_tooltip")
        except tk.TclError:
            pass
        
        # Initialize first draw flag
        if not hasattr(self, '_first_draw_done'):
            self._clear_canvas_cache()
            self._first_draw_done = True
        
        # Estimate visible hex coordinates
        top_left_x = -self.view_offset_x - visible_margin * self.hex_size
        top_left_y = -self.view_offset_y - visible_margin * self.hex_size
        bottom_right_x = self.canvas_width - self.view_offset_x + visible_margin * self.hex_size
        bottom_right_y = self.canvas_height - self.view_offset_y + visible_margin * self.hex_size
        
        # Convert to approximate hex ranges
        min_q = int((top_left_x - self.canvas_width/2) / (self.hex_size * 1.5)) - visible_margin
        max_q = int((bottom_right_x - self.canvas_width/2) / (self.hex_size * 1.5)) + visible_margin
        min_r = int((top_left_y - self.canvas_height/2) / (self.hex_size * math.sqrt(3))) - visible_margin
        max_r = int((bottom_right_y - self.canvas_height/2) / (self.hex_size * math.sqrt(3))) + visible_margin
        
        # Clamp to actual board bounds
        min_q = max(min_q, -self.board_size)
        max_q = min(max_q, self.board_size)
        min_r = max(min_r, -self.board_size)
        max_r = min(max_r, self.board_size)
        
        # Draw visible hex tiles
        for q in range(min_q, max_q + 1):
            for r in range(min_r, max_r + 1):
                if (q, r) in self.hex_tiles:
                    self.draw_hex(self.hex_tiles[(q, r)])
        
        # Always draw ALL mechs to ensure they're visible
        for mech in self.mechs:
            if not mech.is_destroyed():
                self.draw_mech(mech)
        
        # Highlight movement range when mech is selected and can still move
        if self.selected_mech and self.selected_mech.can_still_move():
            self.highlight_movement_range()
        
        # Highlight enemies in range when mech is selected and in attack phase
        if (self.selected_mech and 
            self.selected_mech.current_phase == MechPhase.ATTACK and 
            not self.selected_mech.has_fired):
            self.highlight_enemies_in_range()
        
        # Highlight targeted mech with enhanced targeting graphics
        if hasattr(self, 'target_mech') and self.target_mech and self.selected_mech:
            # Draw enhanced targeting line
            self.draw_targeting_line(self.selected_mech, self.target_mech)
            
            # Draw enhanced targeting reticle
            x, y = self.hex_to_pixel(self.target_mech.hex_tile.q, self.target_mech.hex_tile.r)
            
            # Animated targeting circles
            for i, radius in enumerate([25, 30, 35]):
                alpha = 1.0 - (i * 0.3)
                color_intensity = int(255 * alpha)
                circle_color = f"#{color_intensity:02x}0000"  # Red with varying intensity
                
                self.canvas.create_oval(x - radius, y - radius, x + radius, y + radius, 
                                      outline=circle_color, width=2, fill="")
            
            # Target label with background
            self.canvas.create_rectangle(x - 25, y - 45, x + 25, y - 35, 
                                       fill="red", outline="white")
            self.canvas.create_text(x, y - 40, text="TARGET", 
                                  font=("Arial", 8, "bold"), fill="white")
        
        # Highlight selected mech's movement range
        if self.selected_mech and self.selected_mech.can_still_move():
            self.highlight_movement_range()
    
    def draw_hex(self, hex_tile: HexTile):
        """Draw a single hex tile"""
        x, y = self.hex_to_pixel(hex_tile.q, hex_tile.r)
        
        # Calculate hex vertices
        points = []
        for i in range(6):
            angle = math.pi / 3 * i
            hx = x + self.hex_size * math.cos(angle)
            hy = y + self.hex_size * math.sin(angle)
            points.extend([hx, hy])
        
        # Draw hex with terrain color
        color = hex_tile.get_color()
        self.canvas.create_polygon(points, fill=color, outline="black", width=1)
        
        # Add terrain symbol in center
        if hex_tile.terrain_type == "forest":
            self.canvas.create_text(x, y, text="🌲", font=("Arial", 12))
        elif hex_tile.terrain_type == "shallow_water":
            self.canvas.create_text(x, y, text="~", font=("Arial", 14), fill="blue")
        elif hex_tile.terrain_type == "deep_water":
            self.canvas.create_text(x, y, text="≈", font=("Arial", 16), fill="darkblue")
        elif hex_tile.terrain_type == "mountain":
            self.canvas.create_text(x, y, text="▲", font=("Arial", 14), fill="gray")
    
    def draw_mech(self, mech: Mech):
        """Draw a mech on the board"""
        x, y = self.hex_to_pixel(mech.hex_tile.q, mech.hex_tile.r)
        
        # Draw mech as a circle
        radius = 15
        outline_color = "gold" if mech == self.selected_mech else "black"
        outline_width = 3 if mech == self.selected_mech else 2
        
        if mech.is_destroyed():
            fill_color = "gray"
        else:
            # Use the mech's assigned color
            fill_color = mech.color
        
        self.canvas.create_oval(x - radius, y - radius, x + radius, y + radius,
                               fill=fill_color, outline=outline_color, width=outline_width)
        
        # Draw mech icon inside the circle
        if mech.is_destroyed():
            # Draw X for destroyed mech
            self.canvas.create_text(x, y, text="✗", font=("Arial", 16, "bold"), fill="white")
        else:
            # Draw mech icon - simplified robot/mech shape
            icon_color = "white" if fill_color != "white" else "black"
            
            # Main body (rectangle)
            body_width = 8
            body_height = 10
            self.canvas.create_rectangle(
                x - body_width//2, y - body_height//2,
                x + body_width//2, y + body_height//2,
                fill=icon_color, outline=""
            )
            
            # Head (small circle)
            head_radius = 3
            self.canvas.create_oval(
                x - head_radius, y - body_height//2 - head_radius,
                x + head_radius, y - body_height//2 + head_radius,
                fill=icon_color, outline=""
            )
            
            # Arms (small rectangles)
            arm_width = 3
            arm_height = 6
            # Left arm
            self.canvas.create_rectangle(
                x - body_width//2 - arm_width, y - arm_height//2,
                x - body_width//2, y + arm_height//2,
                fill=icon_color, outline=""
            )
            # Right arm
            self.canvas.create_rectangle(
                x + body_width//2, y - arm_height//2,
                x + body_width//2 + arm_width, y + arm_height//2,
                fill=icon_color, outline=""
            )
            
            # Legs (small rectangles)
            leg_width = 3
            leg_height = 4
            # Left leg
            self.canvas.create_rectangle(
                x - leg_width - 1, y + body_height//2,
                x - 1, y + body_height//2 + leg_height,
                fill=icon_color, outline=""
            )
            # Right leg
            self.canvas.create_rectangle(
                x + 1, y + body_height//2,
                x + leg_width + 1, y + body_height//2 + leg_height,
                fill=icon_color, outline=""
            )
        
        # Draw health bars
        self.draw_health_bars(x, y, mech)
    
    def draw_health_bars(self, x, y, mech):
        """Draw larger health bars for mech without text labels"""
        bar_width = 30  # Increased from 20
        bar_height = 6  # Increased from 4
        armor_y = y + 20
        structure_y = y + 28
        
        # Calculate ratios
        armor_ratio = mech.stats.armor_hp / max(mech.stats.max_armor_hp, 1)
        structure_ratio = mech.stats.structure_hp / max(mech.stats.max_structure_hp, 1)
        
        # Armor bar background
        self.canvas.create_rectangle(x - bar_width//2, armor_y,
                                   x + bar_width//2, armor_y + bar_height,
                                   fill="darkblue", outline="black")
        
        # Armor bar fill
        if armor_ratio > 0:
            armor_width = int(bar_width * armor_ratio)
            if armor_width > 0:
                self.canvas.create_rectangle(x - bar_width//2, armor_y,
                                           x - bar_width//2 + armor_width, armor_y + bar_height,
                                           fill="blue", outline="")
        
        # Structure bar background
        self.canvas.create_rectangle(x - bar_width//2, structure_y,
                                   x + bar_width//2, structure_y + bar_height,
                                   fill="darkred", outline="black")
        
        # Structure bar fill
        if structure_ratio > 0:
            structure_width = int(bar_width * structure_ratio)
            if structure_width > 0:
                self.canvas.create_rectangle(x - bar_width//2, structure_y,
                                           x - bar_width//2 + structure_width, structure_y + bar_height,
                                           fill="red", outline="")
    
    def draw_targeting_line(self, shooter: Mech, target: Mech):
        """Draw targeting line between mechs"""
        # Clear previous targeting line
        self.canvas.delete("targeting_line")
        self.canvas.delete("los_marker")
        
        if not shooter or not target:
            return
        
        from_x, from_y = self.hex_to_pixel(shooter.hex_tile.q, shooter.hex_tile.r)
        to_x, to_y = self.hex_to_pixel(target.hex_tile.q, target.hex_tile.r)
        
        # Check line of sight
        has_los, range_modifier = self.has_line_of_sight(shooter.hex_tile, target.hex_tile)
        
        # Draw targeting line
        if has_los:
            self.canvas.create_line(from_x, from_y, to_x, to_y, 
                                  fill="red", width=2, tags="targeting_line")
        else:
            # Dashed line for blocked LOS
            self.canvas.create_line(from_x, from_y, to_x, to_y, 
                                  fill="red", width=2, dash=(5, 5), tags="targeting_line")
        
        # Mark LOS obstacles
        if not has_los or range_modifier > 0:
            line_hexes = hex_utils.get_line_hexes(shooter.hex_tile, target.hex_tile)
            intermediate_hexes = line_hexes[1:-1]  # Exclude source and target
            
            for hex_coord in intermediate_hexes:
                if hex_coord in self.hex_tiles:
                    hex_tile = self.hex_tiles[hex_coord]
                    
                    if hex_tile.terrain_type == "mountain":
                        # Blocked LOS indicator
                        x, y = self.hex_to_pixel(hex_tile.q, hex_tile.r)
                        self.canvas.create_oval(x - 8, y - 8, x + 8, y + 8,
                                              fill="red", outline="darkred", width=1,
                                              tags="los_marker")
                        self.canvas.create_text(x, y, text="X", font=("Arial", 10, "bold"), 
                                              fill="white", tags="los_marker")
                    elif hex_tile.terrain_type == "forest":
                        # Forest LOS indicator
                        x, y = self.hex_to_pixel(hex_tile.q, hex_tile.r)
                        self.canvas.create_oval(x - 6, y - 6, x + 6, y + 6,
                                              fill="orange", outline="darkorange", width=1,
                                              tags="los_marker")
                        self.canvas.create_text(x, y, text="F", font=("Arial", 8, "bold"), 
                                              fill="darkgreen", tags="los_marker")
    
    def log(self, message: str):
        """Add message to combat log"""
        # Check if combat log exists (UI might not be set up yet)
        if hasattr(self, 'combat_log'):
            self.combat_log.config(state=tk.NORMAL)
            self.combat_log.insert(tk.END, message + "\n")
            self.combat_log.see(tk.END)
            self.combat_log.config(state=tk.DISABLED)
        else:
            # If UI isn't set up yet, messages go to console during initialization
            pass  # Silent during initialization
    
    def calculate_initiative_order(self) -> List[Mech]:
        """Calculate initiative order for mechs - alive mechs first, then destroyed mechs"""
        alive_mechs = [mech for mech in self.mechs if not mech.is_destroyed()]
        destroyed_mechs = [mech for mech in self.mechs if mech.is_destroyed()]
        
        # Sort alive mechs by speed (faster first)
        alive_sorted = sorted(alive_mechs, key=lambda m: m.stats.speed, reverse=True)
        
        # Sort destroyed mechs by speed as well for consistency
        destroyed_sorted = sorted(destroyed_mechs, key=lambda m: m.stats.speed, reverse=True)
        
        # Return alive mechs first, then destroyed mechs
        return alive_sorted + destroyed_sorted
    
    def update_initiative_display(self):
        """Update the initiative display panel"""
        # Check if UI exists yet
        if not hasattr(self, 'initiative_frame'):
            return
            
        # Clear existing display
        for widget in self.initiative_frame.winfo_children():
            widget.destroy()
        
        # Show current initiative order
        alive_count = len([m for m in self.initiative_order if not m.is_destroyed()])
        
        for i, mech in enumerate(self.initiative_order):
            # Determine if this is the active mech
            is_active = (i == self.current_mech_index and not mech.is_destroyed())
            
            # Set colors based on mech status
            if mech.is_destroyed():
                color = "red"
                bg_color = "#ffeeee"  # Light red background
            elif is_active:
                color = "green"
                bg_color = "lightgreen"
            else:
                color = "black"
                bg_color = None
                
            # Build display text
            if mech.is_destroyed():
                text = f"{i+1}. {mech.stats.name} (P{mech.player_id}) [DESTROYED]"
            else:
                text = f"{i+1}. {mech.stats.name} (P{mech.player_id})"
                if mech.has_moved and mech.has_fired:
                    text += " [Done]"
                elif mech.has_moved:
                    text += " [Moved]"
                elif mech.has_fired:
                    text += " [Fired]"
                
            # Add active indicator
            if is_active:
                text = "→ " + text + " ←"
            
            # Create and configure label
            label = ttk.Label(self.initiative_frame, text=text, foreground=color)
            if bg_color:
                label.configure(background=bg_color)
            label.pack(anchor=tk.W, fill=tk.X, pady=1)
    
    def activate_next_mech(self):
        """Activate the next mech in initiative order"""
        # Skip destroyed mechs in activation
        while (self.current_mech_index < len(self.initiative_order) and 
               self.initiative_order[self.current_mech_index].is_destroyed()):
            self.current_mech_index += 1
            
        if self.current_mech_index < len(self.initiative_order):
            current_mech = self.initiative_order[self.current_mech_index]
            self.current_mech_label.config(text=f"Active: {current_mech.stats.name} (Player {current_mech.player_id})")
            
            # Clear previous selection and targeting
            if hasattr(self, 'target_mech'):
                delattr(self, 'target_mech')
            
            # Check if current mech belongs to an AI player
            player_info = self.players[current_mech.player_id - 1]
            is_ai_player = player_info["is_ai"]
            
            if is_ai_player:
                # AI turn for any AI player - enforce AI action speed consistently
                if self.selected_mech:
                    self.stop_pulse_animation(self.selected_mech)
                self.selected_mech = current_mech
                self.start_pulse_animation(current_mech)
                player_name = player_info["name"]
                self.log(f"AI {player_name}: {current_mech.stats.name}'s turn")
                # Always apply AI action speed delay for any AI player
                self.schedule_ai_action(lambda: self.ai_turn(current_mech))
            else:
                # Human player turn - no delay needed
                if self.selected_mech:
                    self.stop_pulse_animation(self.selected_mech)
                self.selected_mech = current_mech
                self.start_pulse_animation(current_mech)
                player_name = player_info["name"]
                self.log(f"{player_name}: {current_mech.stats.name}'s turn")
        
        self.update_display()
    
    def schedule_ai_action(self, action_func, delay_multiplier: float = 1.0):
        """Helper method to consistently apply AI action speed to any AI action"""
        if self.root:
            delay_ms = int(self.ai_action_speed * delay_multiplier * 1000)
            self.root.after(delay_ms, action_func)
        else:
            # Fallback for testing without UI
            action_func()
    
    def ai_turn(self, mech: Mech):
        """Advanced tactical AI for any AI player mech"""
        if mech.is_destroyed():
            self.end_turn()
            return
            
        # Find enemies (mechs from all other players)
        enemies = [m for m in self.mechs if m.player_id != mech.player_id and not m.is_destroyed()]
        if not enemies:
            self.end_turn()
            return
        
        self.log(f"AI {mech.stats.name} begins turn")
        
        # Phase 1: Movement Phase
        if mech.current_phase == MechPhase.MOVEMENT:
            best_position = self.ai_find_optimal_position(mech, enemies)
            if best_position:
                target_hex = self.hex_tiles[best_position]
                reachable = self.calculate_reachable_hexes(mech.hex_tile, mech.get_remaining_movement())
                if best_position in reachable:
                    move_cost = reachable[best_position]
                    if mech.move_to(target_hex, move_cost):
                        self.log(f"AI {mech.stats.name} tactically moves to ({best_position[0]}, {best_position[1]}) [Cost: {move_cost}]")
                        
                        # Check if should continue moving or advance to attack
                        if mech.get_remaining_movement() <= 0 or self.ai_should_stop_moving(mech, enemies):
                            mech.end_movement_phase()
                            self.log(f"AI {mech.stats.name} ends movement phase")
                        else:
                            # Continue movement next update cycle with consistent AI speed
                            self.schedule_ai_action(lambda: self.ai_turn(mech), 0.5)  # Half speed for movement
                            return
                    else:
                        mech.end_movement_phase()
                else:
                    mech.end_movement_phase()
            else:
                mech.end_movement_phase()
        
        # Phase 2: Attack Phase
        if mech.current_phase == MechPhase.ATTACK:
            target, weapon = self.ai_choose_target_and_weapon(mech, enemies)
            if target and weapon and not mech.has_fired:
                result = mech.attack(target, weapon)
                weapon_name = "laser" if weapon == "laser" else "missile"
                self.log(f"AI {mech.stats.name} {weapon_name} attacks {target.stats.name}: {result['message']}")
                
                if target.is_destroyed():
                    self.log(f"{target.stats.name} is destroyed!")
                    self.check_victory()
                
                mech.end_attack_phase()
        
        # End AI turn
        self.log(f"AI {mech.stats.name} ends turn")
        self.end_turn()
    
    def ai_find_optimal_position(self, mech: Mech, enemies) -> tuple[int, int] | None:
        """Find the best position for the AI mech to move to"""
        reachable = self.calculate_reachable_hexes(mech.hex_tile, mech.get_remaining_movement())
        best_position = None
        best_score = float('-inf')
        
        current_position = (mech.hex_tile.q, mech.hex_tile.r)
        
        for (q, r), cost in reachable.items():
            if (q, r) == current_position:
                continue  # Skip current position
                
            if (q, r) in self.hex_tiles:
                hex_tile = self.hex_tiles[(q, r)]
                if hex_tile.mech:  # Occupied
                    continue
                    
                score = self.ai_evaluate_position(hex_tile, mech, enemies)
                if score > best_score:
                    best_score = score
                    best_position = (q, r)
        
        return best_position
    
    def ai_evaluate_position(self, position: HexTile, mech: Mech, enemies) -> float:
        """Evaluate how good a position is for the AI mech with caching"""
        # Create cache key based on position and enemy positions
        enemies_hash = hash(tuple((e.hex_tile.q, e.hex_tile.r, e.stats.armor_hp, e.stats.structure_hp) for e in enemies))
        cache_key = (id(mech), position.q, position.r, enemies_hash)
        
        # Check cache first
        if cache_key in self.ai_cache['position_scores']:
            self.ai_cache['cache_hits'] += 1
            return self.ai_cache['position_scores'][cache_key]
        
        self.ai_cache['cache_misses'] += 1
        
        score = 0.0
        
        # Find the best target from this position
        best_target = None
        best_target_score = float('-inf')
        
        for enemy in enemies:
            distance = position.distance_to(enemy.hex_tile)
            
            # Target prioritization
            target_score = 0.0
            
            # Prefer damaged enemies (easier to destroy)
            health_ratio = (enemy.stats.armor_hp + enemy.stats.structure_hp) / (enemy.stats.max_armor_hp + enemy.stats.max_structure_hp)
            target_score += (1.0 - health_ratio) * 100  # Up to 100 points for low health
            
            # Prefer closer enemies
            if distance <= 12:  # In missile range
                target_score += (12 - distance) * 10  # Closer is better
            
            # Prefer enemies we can attack effectively
            has_los, _ = self.has_line_of_sight(position, enemy.hex_tile)
            if has_los:
                if distance <= 8:  # Laser range - preferred
                    target_score += 50
                elif distance <= 12:  # Missile range
                    target_score += 30
            else:
                target_score -= 50  # Penalize no line of sight
            
            if target_score > best_target_score:
                best_target_score = target_score
                best_target = enemy
        
        if best_target:
            distance_to_target = position.distance_to(best_target.hex_tile)
            
            # Range considerations
            if distance_to_target <= 8:
                score += 60  # Excellent - in laser range
            elif distance_to_target <= 10:
                score += 40  # Good - close to laser range
            elif distance_to_target <= 12:
                score += 20  # OK - in missile range
            else:
                score -= 20  # Poor - out of range
            
            # Line of sight bonus
            has_los, range_modifier = self.has_line_of_sight(position, best_target.hex_tile)
            if has_los:
                score += 30
            else:
                score -= 40
            
            # Cover considerations
            if position.provides_cover():
                score += 25  # Defensive bonus
            
            # Avoid clustering with friendly mechs
            for friendly in self.mechs:
                if friendly.player_id == mech.player_id and not friendly.is_destroyed() and friendly != mech:
                    friendly_distance = position.distance_to(friendly.hex_tile)
                    if friendly_distance <= 2:
                        score -= 15  # Penalize clustering
            
            # Terrain movement cost penalty
            score -= position.get_movement_cost() * 2
        
        return score
    
    def ai_should_stop_moving(self, mech: Mech, enemies) -> bool:
        """Determine if AI should stop moving and start attacking"""
        if mech.get_remaining_movement() <= 0:
            return True
        
        # Check if we're in good attack position
        for enemy in enemies:
            distance = mech.hex_tile.distance_to(enemy.hex_tile)
            has_los, _ = self.has_line_of_sight(mech.hex_tile, enemy.hex_tile)
            
            # Stop if we can make a good laser attack
            if distance <= 8 and has_los:
                return True
            
            # Stop if we can make a decent missile attack and enemy is low on health
            if distance <= 10 and has_los:
                health_ratio = (enemy.stats.armor_hp + enemy.stats.structure_hp) / (enemy.stats.max_armor_hp + enemy.stats.max_structure_hp)
                if health_ratio < 0.4:  # Enemy is badly damaged
                    return True
        
        return False
    
    def ai_choose_target_and_weapon(self, mech: Mech, enemies) -> tuple[Mech | None, str | None]:
        """Choose the best target and weapon for attacking"""
        best_target = None
        best_weapon = None
        best_score = float('-inf')
        
        for enemy in enemies:
            distance = mech.hex_tile.distance_to(enemy.hex_tile)
            has_los, range_modifier = self.has_line_of_sight(mech.hex_tile, enemy.hex_tile)
            
            if not has_los:
                continue  # Can't attack without line of sight
            
            # Try both weapons
            for weapon_type in ["laser", "missile"]:
                weapon_range = 8 if weapon_type == "laser" else 12
                
                if distance > weapon_range:
                    continue  # Out of range
                
                # Calculate hit chance and expected damage
                hit_chance = mech.calculate_hit_chance(enemy, weapon_type)
                base_damage = mech.stats.laser_attack if weapon_type == "laser" else mech.stats.missile_attack
                expected_damage = hit_chance * base_damage
                
                # Calculate score for this attack
                score = expected_damage
                
                # Bonus for finishing off enemies
                enemy_health = enemy.stats.armor_hp + enemy.stats.structure_hp
                if expected_damage >= enemy_health:
                    score += 200  # Big bonus for potential kill
                
                # Prefer laser over missile when both are viable (more accurate)
                if weapon_type == "laser" and distance <= 8:
                    score += 10
                
                # Range penalty
                optimal_range = weapon_range // 2
                if distance > optimal_range:
                    range_penalty = (distance - optimal_range) * 5
                    score -= range_penalty
                
                if score > best_score:
                    best_score = score
                    best_target = enemy
                    best_weapon = weapon_type
        
        return best_target, best_weapon
    
    def on_canvas_click(self, event):
        """Handle canvas click events"""
        # Validate event object
        if not hasattr(event, 'x') or not hasattr(event, 'y'):
            return
            
        try:
            q, r = self.pixel_to_hex(event.x, event.y)
        except (TypeError, ValueError) as e:
            print(f"Error converting pixel to hex: {e}")
            return
        
        # Validate coordinates before proceeding
        if not self._validate_hex_coordinates(q, r) or (q, r) not in self.hex_tiles:
            return
        
        clicked_hex = self.hex_tiles[(q, r)]
        
        # Check if clicked on a mech
        if clicked_hex.mech:
            clicked_mech = clicked_hex.mech
            
            # Check if it's a human player's mech that can be selected
            player_info = self.players[clicked_mech.player_id - 1]
            if not player_info["is_ai"]:  # Human player mech
                # Check if it's this mech's turn
                can_select = True
                if (hasattr(self, 'initiative_order') and 
                    hasattr(self, 'current_mech_index') and 
                    self.current_mech_index < len(self.initiative_order)):
                    active_mech = self.initiative_order[self.current_mech_index]
                    active_player_info = self.players[active_mech.player_id - 1]
                    
                    if clicked_mech != active_mech and not active_player_info["is_ai"]:
                        self.log(f"It's {active_mech.stats.name}'s turn, not {clicked_mech.stats.name}'s turn!")
                        can_select = False
                
                if can_select:
                    old_selected = self.selected_mech
                    if self.selected_mech == clicked_mech:
                        self.selected_mech = None  # Deselect
                        # Stop pulse animation for deselected mech
                        if old_selected:
                            self.stop_pulse_animation(old_selected)
                    else:
                        # Stop pulse animation for previously selected mech
                        if old_selected:
                            self.stop_pulse_animation(old_selected)
                        self.selected_mech = clicked_mech
                        # Start pulse animation for newly selected mech
                        self.start_pulse_animation(clicked_mech)
                    if hasattr(self, 'target_mech'):
                        delattr(self, 'target_mech')
            else:  # Enemy mech or AI mech - set as target if valid
                if self.selected_mech:
                    selected_player_info = self.players[self.selected_mech.player_id - 1]
                    if not selected_player_info["is_ai"] and clicked_mech.player_id != self.selected_mech.player_id:
                        # Check if selected mech is active
                        if (hasattr(self, 'initiative_order') and 
                            hasattr(self, 'current_mech_index') and 
                            self.current_mech_index < len(self.initiative_order)):
                            active_mech = self.initiative_order[self.current_mech_index]
                            if self.selected_mech == active_mech:
                                self.target_mech = clicked_mech
                            else:
                                self.log(f"It's {active_mech.stats.name}'s turn to attack!")
                        else:
                            self.target_mech = clicked_mech
        else:
            # Clicked on empty hex - try to move selected mech
            if self.selected_mech:
                selected_player_info = self.players[self.selected_mech.player_id - 1]
                if not selected_player_info["is_ai"]:  # Only human players can move manually
                    
                    # Check if it's the selected mech's turn and they're in movement phase
                    if (hasattr(self, 'initiative_order') and 
                        hasattr(self, 'current_mech_index') and 
                        self.current_mech_index < len(self.initiative_order)):
                        active_mech = self.initiative_order[self.current_mech_index]
                        if self.selected_mech != active_mech:
                            self.log(f"It's {active_mech.stats.name}'s turn, not {self.selected_mech.stats.name}'s turn!")
                            self.update_display()
                            return
                        if active_mech.current_phase != MechPhase.MOVEMENT:
                            self.log(f"{active_mech.stats.name} is not in movement phase!")
                            self.update_display()
                            return
                        if not active_mech.can_still_move():
                            self.log(f"{active_mech.stats.name} has no movement points remaining!")
                            self.update_display()
                            return
                
                # Use pathfinding to check if hex is reachable with remaining movement
                remaining_movement = self.selected_mech.get_remaining_movement()
                reachable = self.calculate_reachable_hexes(self.selected_mech.hex_tile, remaining_movement)
                target_coords = (q, r)
                
                if target_coords in reachable:
                    move_cost = reachable[target_coords]
                    try:
                        if self.selected_mech.move_to(clicked_hex, move_cost):
                            remaining_after_move = self.selected_mech.get_remaining_movement()
                            self.log(f"{self.selected_mech.stats.name} moves to ({q}, {r}) [Cost: {move_cost}, Remaining: {remaining_after_move}]")
                            
                            # Check if movement is exhausted and auto-advance to attack phase
                            if remaining_after_move <= 0 or not self.selected_mech.can_still_move():
                                self.log(f"{self.selected_mech.stats.name} has used all movement - advancing to attack phase")
                                self.selected_mech.end_movement_phase()
                                self.update_attack_buttons()
                            
                            # Always update display to recalculate movement indicators
                            self.update_display()
                            return  # Important: return here to avoid double update_display call
                    except InvalidMoveException as e:
                        messagebox.showwarning("Invalid Move", str(e))
                    except InvalidPhaseException as e:
                        messagebox.showwarning("Invalid Phase", str(e))
                    except InsufficientMovementException as e:
                        messagebox.showwarning("Insufficient Movement", str(e))
                    except BattleTechException as e:
                        messagebox.showerror("Game Error", str(e))
                else:
                    self.log(f"Cannot reach ({q}, {r}) - out of movement range or blocked")
            elif self.selected_mech:
                selected_player_info = self.players[self.selected_mech.player_id - 1]
                if selected_player_info["is_ai"]:
                    self.log("You cannot move AI mechs")
        
        self.update_display()
    
    def update_display(self):
        """Update all display elements"""
        # Check if UI is initialized
        if not hasattr(self, 'canvas'):
            return
            
        # Mark all visible hexes as dirty to ensure complete redraw when needed
        if hasattr(self, 'selected_mech') and self.selected_mech:
            # Mark area around selected mech as dirty
            for dq in range(-2, 3):
                for dr in range(-2, 3):
                    self._mark_hex_dirty(self.selected_mech.hex_tile.q + dq, 
                                       self.selected_mech.hex_tile.r + dr)
        
        # Clear any previous movement range indicators
        self.canvas.delete("movement_range")
        
        self.draw_board()
        self.update_mech_info()
        self.update_attack_buttons()
        self.update_initiative_display()
    
    def update_mech_info(self):
        """Update mech information display"""
        # Check if UI exists yet
        if not hasattr(self, 'mech_info_frame'):
            return
            
        # Clear existing mech info
        for widget in self.mech_info_frame.winfo_children():
            widget.destroy()
        
        if self.selected_mech:
            mech = self.selected_mech
            info_text = f"{mech.stats.name} (Player {mech.player_id})\n"
            info_text += f"Speed: {mech.stats.speed}, Armor: {mech.stats.armor_hp}/{mech.stats.max_armor_hp}\n"
            info_text += f"Structure: {mech.stats.structure_hp}/{mech.stats.max_structure_hp}\n"
            info_text += f"Weapons: Laser {mech.stats.laser_attack}, Missile {mech.stats.missile_attack}\n"
            
            # Show current phase and movement info
            phase_name = str(mech.current_phase).split('.')[-1].title()
            info_text += f"Phase: {phase_name}\n"
            if mech.current_phase == MechPhase.MOVEMENT:
                remaining = mech.get_remaining_movement()
                info_text += f"Movement: {mech.movement_used}/{mech.stats.speed} used, {remaining} remaining"
            elif mech.current_phase == MechPhase.ATTACK:
                info_text += f"Movement: {mech.movement_used}/{mech.stats.speed} used (complete)"
            else:  # DONE
                info_text += "Turn complete"
            
            ttk.Label(self.mech_info_frame, text=info_text, font=("Arial", 9)).pack(anchor=tk.W)
            
            # Update instruction based on phase
            if mech.current_phase == MechPhase.MOVEMENT:
                if mech.can_still_move():
                    self.instruction_label.config(text="Green=Easy, Yellow=Moderate, Orange=Expensive movement. Click hex to move or End Movement")
                else:
                    self.instruction_label.config(text="No movement remaining - click End Movement to attack")
            elif mech.current_phase == MechPhase.ATTACK:
                self.instruction_label.config(text="Select target and attack, or click End Turn")
            else:  # DONE
                self.instruction_label.config(text="Turn complete - click End Turn")
        else:
            ttk.Label(self.mech_info_frame, text="No mech selected", font=("Arial", 9)).pack(anchor=tk.W)
            self.instruction_label.config(text="Select one of your mechs to begin")
        
        # Update target info
        for widget in self.target_info_frame.winfo_children():
            widget.destroy()
        
        if hasattr(self, 'target_mech') and self.target_mech:
            target = self.target_mech
            target_text = f"{target.stats.name} (Player {target.player_id})\n"
            target_text += f"Armor: {target.stats.armor_hp}/{target.stats.max_armor_hp}\n"
            target_text += f"Structure: {target.stats.structure_hp}/{target.stats.max_structure_hp}\n"
            
            if self.selected_mech:
                distance = self.selected_mech.hex_tile.distance_to(target.hex_tile)
                target_text += f"Range: {distance} hexes\n"
                
                # Check line of sight
                has_los, range_modifier = self.has_line_of_sight(self.selected_mech.hex_tile, target.hex_tile)
                los_text = "Clear" if has_los else "Blocked"
                target_text += f"Line of Sight: {los_text}\n"
                
                # Show weapon range and hit chance status
                target_text += f"Weapons:\n"
                
                # Laser weapon status
                laser_hit_chance = self.get_laser_hit_chance()
                if distance <= 8 and has_los:
                    target_text += f"  Laser: ✓ Range {distance}/8, Hit: {int(laser_hit_chance * 100)}%"
                elif distance <= 8:
                    target_text += f"  Laser: ✗ No LOS (Range {distance}/8)"
                else:
                    target_text += f"  Laser: ✗ Out of Range ({distance}/8)"
                    
                target_text += f"\n"
                
                # Missile weapon status
                missile_hit_chance = self.get_missile_hit_chance()
                if distance <= 12 and has_los:
                    target_text += f"  Missile: ✓ Range {distance}/12, Hit: {int(missile_hit_chance * 100)}%"
                elif distance <= 12:
                    target_text += f"  Missile: ✗ No LOS (Range {distance}/12)"
                else:
                    target_text += f"  Missile: ✗ Out of Range ({distance}/12)"
            
            ttk.Label(self.target_info_frame, text=target_text, font=("Arial", 9)).pack(anchor=tk.W)
        else:
            ttk.Label(self.target_info_frame, text="No target selected", font=("Arial", 9)).pack(anchor=tk.W)
    
    def can_laser_attack_target(self) -> bool:
        """Check if selected mech can laser attack the current target"""
        if not (self.selected_mech and hasattr(self, 'target_mech') and self.target_mech):
            return False
        
        # Check basic attack conditions
        if (self.selected_mech.has_fired or 
            not self.selected_mech.can_attack(self.target_mech) or
            self.selected_mech.current_phase != MechPhase.ATTACK):
            return False
        
        # Check laser range (8 hexes)
        distance = self.selected_mech.hex_tile.distance_to(self.target_mech.hex_tile)
        if distance > 8:
            return False
        
        # Check line of sight
        has_los, _ = self.has_line_of_sight(self.selected_mech.hex_tile, self.target_mech.hex_tile)
        return has_los
    
    def can_missile_attack_target(self) -> bool:
        """Check if selected mech can missile attack the current target"""
        if not (self.selected_mech and hasattr(self, 'target_mech') and self.target_mech):
            return False
        
        # Check basic attack conditions
        if (self.selected_mech.has_fired or 
            not self.selected_mech.can_attack(self.target_mech) or
            self.selected_mech.current_phase != MechPhase.ATTACK):
            return False
        
        # Check missile range (12 hexes)
        distance = self.selected_mech.hex_tile.distance_to(self.target_mech.hex_tile)
        if distance > 12:
            return False
        
        # Check line of sight
        has_los, _ = self.has_line_of_sight(self.selected_mech.hex_tile, self.target_mech.hex_tile)
        return has_los
    
    def get_laser_hit_chance(self) -> float:
        """Get hit chance for laser attack against current target"""
        if not (self.selected_mech and hasattr(self, 'target_mech') and self.target_mech):
            return 0.0
        return self.selected_mech.calculate_hit_chance(self.target_mech, "laser")
    
    def get_missile_hit_chance(self) -> float:
        """Get hit chance for missile attack against current target"""
        if not (self.selected_mech and hasattr(self, 'target_mech') and self.target_mech):
            return 0.0
        return self.selected_mech.calculate_hit_chance(self.target_mech, "missile")
    
    def update_attack_buttons(self):
        """Update attack button states"""
        # Check if UI exists yet
        if not hasattr(self, 'attack_laser_btn'):
            return
            
        can_end_movement = False
        
        # Check if it's the selected mech's turn for attack buttons
        is_active_mech = False
        if (hasattr(self, 'initiative_order') and 
            hasattr(self, 'current_mech_index') and 
            self.current_mech_index < len(self.initiative_order)):
            active_mech = self.initiative_order[self.current_mech_index]
            is_active_mech = (self.selected_mech == active_mech)
            can_end_movement = (active_mech.current_phase == MechPhase.MOVEMENT)
        
        # Check weapon-specific attack conditions
        can_laser_attack = is_active_mech and self.can_laser_attack_target()
        can_missile_attack = is_active_mech and self.can_missile_attack_target()
        
        # Update button states and text with hit chance information
        if can_laser_attack:
            laser_hit_chance = self.get_laser_hit_chance()
            self.attack_laser_btn.config(state=tk.NORMAL, text=f"🔫 Laser ({laser_hit_chance:.0%})")
        else:
            self.attack_laser_btn.config(state=tk.DISABLED, text="🔫 Laser Attack")
            
        if can_missile_attack:
            missile_hit_chance = self.get_missile_hit_chance()
            self.attack_missile_btn.config(state=tk.NORMAL, text=f"🚀 Missile ({missile_hit_chance:.0%})")
        else:
            self.attack_missile_btn.config(state=tk.DISABLED, text="🚀 Missile Attack")
            
        if can_end_movement:
            self.end_movement_btn.config(state=tk.NORMAL)
        else:
            self.end_movement_btn.config(state=tk.DISABLED)
    
    def laser_attack(self):
        """Perform laser attack"""
        if self.selected_mech and hasattr(self, 'target_mech') and self.target_mech:
            # Verify it's the selected mech's turn and they're in attack phase
            if (hasattr(self, 'initiative_order') and 
                hasattr(self, 'current_mech_index') and 
                self.current_mech_index < len(self.initiative_order)):
                active_mech = self.initiative_order[self.current_mech_index]
                if self.selected_mech != active_mech:
                    self.log(f"It's {active_mech.stats.name}'s turn, not {self.selected_mech.stats.name}'s turn!")
                    return
                if active_mech.current_phase != MechPhase.ATTACK:
                    self.log(f"{active_mech.stats.name} must finish movement before attacking!")
                    return
            
            result = self.selected_mech.attack(self.target_mech, "laser")
            self.log(f"{self.selected_mech.stats.name} laser attack: {result['message']}")
            
            # Start weapon animation
            self.start_weapon_animation("laser", self.selected_mech.hex_tile, self.target_mech.hex_tile)
            
            # Start explosion animation based on result
            if result['hit']:
                hit_type = "destroy" if self.target_mech.is_destroyed() else "hit"
                self.start_explosion_animation(self.target_mech.hex_tile, hit_type)
            else:
                self.start_explosion_animation(self.target_mech.hex_tile, "miss")
            
            if self.target_mech.is_destroyed():
                self.log(f"{self.target_mech.stats.name} is destroyed!")
                delattr(self, 'target_mech')
            
            self.check_victory()
            
            # End attack phase and complete turn after firing
            self.selected_mech.end_attack_phase()
            self.log(f"{self.selected_mech.stats.name} has completed their turn")
            self.end_turn()
    
    def missile_attack(self):
        """Perform missile attack"""
        if self.selected_mech and hasattr(self, 'target_mech') and self.target_mech:
            # Verify it's the selected mech's turn and they're in attack phase
            if (hasattr(self, 'initiative_order') and 
                hasattr(self, 'current_mech_index') and 
                self.current_mech_index < len(self.initiative_order)):
                active_mech = self.initiative_order[self.current_mech_index]
                if self.selected_mech != active_mech:
                    self.log(f"It's {active_mech.stats.name}'s turn, not {self.selected_mech.stats.name}'s turn!")
                    return
                if active_mech.current_phase != MechPhase.ATTACK:
                    self.log(f"{active_mech.stats.name} must finish movement before attacking!")
                    return
            
            result = self.selected_mech.attack(self.target_mech, "missile")
            self.log(f"{self.selected_mech.stats.name} missile attack: {result['message']}")
            
            # Start weapon animation
            self.start_weapon_animation("missile", self.selected_mech.hex_tile, self.target_mech.hex_tile)
            
            # Start explosion animation based on result
            if result['hit']:
                hit_type = "destroy" if self.target_mech.is_destroyed() else "hit"
                self.start_explosion_animation(self.target_mech.hex_tile, hit_type)
            else:
                self.start_explosion_animation(self.target_mech.hex_tile, "miss")
            
            if self.target_mech.is_destroyed():
                self.log(f"{self.target_mech.stats.name} is destroyed!")
                delattr(self, 'target_mech')
            
            self.check_victory()
            
            # End attack phase and complete turn after firing
            self.selected_mech.end_attack_phase()
            self.log(f"{self.selected_mech.stats.name} has completed their turn")
            self.end_turn()
    
    def end_movement_phase(self):
        """End movement phase for current mech and advance to attack phase"""
        if self.game_over:
            return
            
        current_mech = self.initiative_order[self.current_mech_index]
        if current_mech.current_phase == MechPhase.MOVEMENT:
            current_mech.end_movement_phase()
            self.update_attack_buttons()
            self.update_display()
    
    def end_turn(self):
        """End current mech's turn"""
        try:
            if self.game_over:
                return
                
            self.current_mech_index += 1
            
            # Clear selection and targeting when turn ends
            if hasattr(self, 'target_mech'):
                delattr(self, 'target_mech')
            
            # Skip destroyed mechs
            while (self.current_mech_index < len(self.initiative_order) and 
                   self.initiative_order[self.current_mech_index].is_destroyed()):
                self.current_mech_index += 1
            
            # Check if we've gone through all mechs or only destroyed mechs remain
            if (self.current_mech_index >= len(self.initiative_order) or
                all(m.is_destroyed() for m in self.initiative_order[self.current_mech_index:])):
                self.start_new_turn()
            else:
                self.activate_next_mech()
        except Exception as e:
            messagebox.showerror("Turn Error", f"Error ending turn: {str(e)}")
            print(f"Error in end_turn: {str(e)}")
    
    def start_new_turn(self):
        """Start a new turn"""
        if self.game_over:
            return
            
        # Clear AI cache for new turn
        self._clear_ai_cache()
        
        self.current_turn += 1
        self.turn_label.config(text=f"Turn {self.current_turn}")
        
        # Reset all living mechs
        for mech in self.mechs:
            if not mech.is_destroyed():
                mech.start_turn()
        
        # Recalculate initiative (include destroyed mechs at bottom)
        self.initiative_order = self.calculate_initiative_order()
        self.current_mech_index = 0
        
        # Clear selections
        self.selected_mech = None
        if hasattr(self, 'target_mech'):
            delattr(self, 'target_mech')
        
        # Check if any alive mechs remain
        alive_mechs = [m for m in self.mechs if not m.is_destroyed()]
        if not alive_mechs:
            self.log("All mechs destroyed!")
            self.game_over = True
            return
        
        self.log(f"=== TURN {self.current_turn} ===")
        self.activate_next_mech()
    
    def check_victory(self):
        """Check for victory conditions"""
        # Count players with living mechs
        players_alive = []
        for player_id in range(1, self.num_players + 1):
            if any(m.player_id == player_id and not m.is_destroyed() for m in self.mechs):
                players_alive.append(player_id)
        
        # Victory if only one player remains
        if len(players_alive) <= 1:
            # Clean up animations when game ends
            try:
                for animation in self.animations:
                    animation.cleanup(self.canvas)
                self.animations.clear()
            except Exception as e:
                print(f"Warning: Animation cleanup failed during game end: {e}")
                
            if len(players_alive) == 1:
                winner_id = players_alive[0]
                winner_name = self.players[winner_id - 1]["name"]
                self.log(f"{winner_name.upper()} WINS!")
                messagebox.showinfo("Game Over", f"{winner_name} Wins!")
            else:
                self.log("DRAW - ALL PLAYERS ELIMINATED!")
                messagebox.showinfo("Game Over", "Draw - All Players Eliminated!")
            self.game_over = True
    
    def show_readme_popup(self):
        """Show help popup with game instructions"""
        # Don't show help if root window doesn't exist yet
        if not self.root:
            return
            
        help_text = """
BATTLETECH HEX BATTLE - COMPLETE GUIDE

=== OBJECTIVE ===
Destroy all enemy mechs to achieve victory! In multi-player games, be the last player standing!

=== GAME SETUP ===
• Choose 2-4 players for epic battles
• Configure each player as Human or AI
• Customize player names (AI gets random callsigns)
• Players use different colored mechs: Neon Red, Neon Blue, Neon Purple, Neon Yellow
• Game starts with setup screen - configure before battle

=== CONTROLS ===
• Click & Drag: Pan the map view around the battlefield
• Click on your mechs: Select them (gold outline indicates selection)
• Click on empty hexes: Move selected mech (if in movement phase)
• Click on enemy mechs: Target them for attacks
• Attack Buttons: Fire laser or missile weapons at targeted enemy
• End Movement: Skip to attack phase if done moving
• End Turn: Complete current mech's activation
• Help: Show this help screen anytime

=== TERRAIN EFFECTS ===
• Clear (Light Green): Movement cost 1, no special effects
• Forest (Dark Green): Movement cost 2, provides 30% cover bonus
• Shallow Water (Light Blue): Movement cost 3, slows movement
• Deep Water (Dark Blue): Impassable terrain
• Mountains (Gray): Impassable, blocks line of sight completely

=== COMBAT SYSTEM ===
WEAPONS:
• Lasers: 8 hex range, accurate (85% base), consistent damage
• Missiles: 12 hex range, less accurate (70% base), variable damage

ACCURACY MODIFIERS:
• Range penalty: -5% per hex beyond optimal range (half max range)
• Cover bonus: -30% hit chance if target in forest
• Forest interference: -1 hex range per forest in line of sight
• Mountains: Block line of sight completely

DAMAGE SYSTEM:
• Armor absorbs damage first, then structure
• Mechs destroyed when structure reaches 0
• Lasers: Consistent damage with minimal variance
• Missiles: Highly variable (50% to 150% base damage)

=== TURN SEQUENCE ===
INITIATIVE ORDER:
• Faster mechs activate first each turn
• Initiative calculated by mech speed rating
• Order displayed in right panel with current mech highlighted

MECH PHASES:
1. MOVEMENT: Move up to speed rating in hexes
2. ATTACK: Fire one weapon at valid target
3. DONE: Mech activation complete

TURN FLOW:
• Each mech activates individually in initiative order
• Complete all mech activations to finish turn
• New turn begins with fresh movement and attack actions

=== MULTI-PLAYER STRATEGY ===
• In 3+ player games, temporary alliances may form naturally
• Target selection becomes crucial - who to attack first?
• Positioning to avoid being gang-up targets
• Monitor all players' mech health and positioning

=== AI BEHAVIOR ===
• Advanced tactical AI with positioning analysis
• Evaluates cover, range, and damage potential
• Chooses optimal targets and weapon types
• Uses terrain strategically for protection
• In multi-player games, AI chooses targets based on threat level

=== VICTORY CONDITIONS ===
• Eliminate all enemy mechs to win
• In multi-player: Last player with living mechs wins
• Game ends immediately when only one player remains
• Strategic positioning and smart targeting key to success

=== TIPS FOR SUCCESS ===
• Use forests for cover against enemy fire
• Keep faster mechs mobile to avoid concentrated fire
• Target damaged mechs to eliminate threats quickly
• Control range - engage at your weapon's optimal distance
• Use terrain to break enemy line of sight
• In multi-player: Consider when to engage vs when to let others fight

Good hunting, MechWarrior! The battlefield awaits your command.
        """
        
        # Create help window
        help_window = tk.Toplevel(self.root)
        help_window.title("BattleTech Hex Battle - Complete Guide")
        help_window.geometry("700x600")
        help_window.resizable(True, True)
        help_window.transient(self.root)
        help_window.grab_set()
        
        # Center the help window
        if self.root:
            help_window.geometry("+%d+%d" % (self.root.winfo_rootx() + 50, self.root.winfo_rooty() + 50))
        else:
            # Center on screen if no root window
            help_window.update_idletasks()
            x = (help_window.winfo_screenwidth() // 2) - (300)
            y = (help_window.winfo_screenheight() // 2) - (250)
            help_window.geometry(f"+{x}+{y}")
        
        # Add text widget with scrollbar
        text_frame = ttk.Frame(help_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text_widget = tk.Text(text_frame, wrap=tk.WORD, font=("Arial", 10))
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        text_widget.insert(tk.END, help_text)
        text_widget.config(state=tk.DISABLED)
        
        # Close button
        close_btn = ttk.Button(help_window, text="Close", command=help_window.destroy)
        close_btn.pack(pady=10)
    
    def highlight_enemies_in_range(self):
        """Highlight enemies in range (simplified version)"""
        # This is a simplified version - just highlights possible targets
        pass
    
    def highlight_movement_range(self):
        """Highlight movement range with pathfinding and cost display"""
        if (not self.selected_mech or 
            not self.selected_mech.can_still_move()):
            return
        
        # Calculate reachable hexes with remaining movement points
        remaining_movement = self.selected_mech.get_remaining_movement()
        reachable = self.calculate_reachable_hexes(self.selected_mech.hex_tile, remaining_movement)
        
        # Draw movement indicators for each reachable hex
        for (q, r), cost in reachable.items():
            x, y = self.hex_to_pixel(q, r)
            
            # Color code by movement cost relative to remaining movement
            if cost <= remaining_movement // 3:
                color = "lightgreen"  # Easy movement
                outline = "green"
            elif cost <= remaining_movement * 2 // 3:
                color = "yellow"      # Moderate movement
                outline = "orange"
            else:
                color = "orange"      # Expensive movement
                outline = "red"
            
            # Draw movement indicator circle
            radius = 6  # Reduced from 12 to 6
            self.canvas.create_oval(x - radius, y - radius, x + radius, y + radius,
                                  fill=color, outline=outline, width=1, tags="movement_range")
            
            # Draw cost number
            self.canvas.create_text(x, y, text=str(cost), 
                                  font=("Arial", 7, "bold"), fill="black", tags="movement_range")
    
    def run(self):
        """Start the game"""
        # This method is called after the game is fully initialized
        if not self.root:
            return
            
        self.log("BattleTech Hex Battle Started!")
        self.log("Click on your mechs to select them, then click on empty hexes to move.")
        self.log("Click on enemy mechs to target them, then use attack buttons.")
        self.update_display()
        
        # Ensure the window is visible and focused
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        
        # Start the main event loop
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            pass  # Clean exit on Ctrl+C
        except Exception as e:
            error_msg = f"Game error: {str(e)}"
            print(error_msg)
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    try:
        # Create game instance
        game = BattleTechGame()
        
        # Show setup screen and run setup loop
        game.show_game_setup()
        game.setup_window.mainloop()
        
    except Exception as e:
        error_msg = f"Failed to start BattleTech game: {str(e)}"
        print(error_msg)
        traceback.print_exc()
        input("Press Enter to exit...")