"""
BattleTech Game - Animation Rendering System Module
Handles visual effects rendering for animations including movement, weapon fire,
explosions, and selection highlights
"""

from animations import MoveAnimation, WeaponFireAnimation, ExplosionAnimation, PulseAnimation


class AnimationRenderer:
    """Handles rendering of animation visual effects on canvas"""
    
    def __init__(self, canvas, hex_to_pixel_func):
        """
        Initialize animation renderer
        
        Args:
            canvas: Tkinter canvas to draw on
            hex_to_pixel_func: Function to convert hex coordinates to pixel coordinates
        """
        self.canvas = canvas
        self.hex_to_pixel = hex_to_pixel_func
    
    def update_animation_effects(self, animations, selected_mech=None):
        """Update visual effects for active animations"""
        for animation in animations:
            if isinstance(animation, MoveAnimation):
                self.update_move_animation(animation, selected_mech)
            elif isinstance(animation, WeaponFireAnimation):
                self.update_weapon_animation(animation)
            elif isinstance(animation, ExplosionAnimation):
                self.update_explosion_animation(animation)
            elif isinstance(animation, PulseAnimation):
                self.update_pulse_animation(animation, selected_mech)
    
    def update_move_animation(self, animation: MoveAnimation, selected_mech=None):
        """Update movement animation visual effects"""
        if animation.mech and not animation.mech.is_destroyed():
            # Remove old mech visual
            self.canvas.delete(f"mech_{id(animation.mech)}")
            
            # Draw mech at animated position
            x, y = animation.get_current_position()
            self.draw_mech_at_position(animation.mech, x, y, f"mech_{id(animation.mech)}", selected_mech)
    
    def update_weapon_animation(self, animation: WeaponFireAnimation):
        """Update weapon fire animation effects"""
        # Clear previous frame
        for obj in animation.beam_objects + animation.particle_objects:
            self.canvas.delete(obj)
        animation.beam_objects.clear()
        animation.particle_objects.clear()
        
        if animation.weapon_type == "laser":
            self.draw_laser_beam(animation)
        else:  # missile
            self.draw_missile_trail(animation)
    
    def update_explosion_animation(self, animation: ExplosionAnimation):
        """Update explosion animation effects"""
        # Clear previous frame
        for obj in animation.explosion_objects:
            self.canvas.delete(obj)
        animation.explosion_objects.clear()
        
        # Draw explosion rings
        self.draw_explosion_rings(animation)
    
    def update_pulse_animation(self, animation: PulseAnimation, selected_mech):
        """Update pulsing selection highlight"""
        if animation.mech == selected_mech:
            # Clear previous pulse
            for obj in animation.pulse_objects:
                self.canvas.delete(obj)
            animation.pulse_objects.clear()
            
            # Draw new pulse
            self.draw_pulse_highlight(animation)
        else:
            # Mech no longer selected, end animation
            animation.completed = True
    
    def draw_laser_beam(self, animation: WeaponFireAnimation):
        """Draw laser beam effect"""
        alpha = 1.0 - animation.progress
        width = int(3 * alpha + 1)
        
        # Main beam
        beam = self.canvas.create_line(
            animation.start_x, animation.start_y,
            animation.end_x, animation.end_y,
            fill="red", width=width, tags="weapon_effect"
        )
        animation.beam_objects.append(beam)
        
        # Glow effect
        if alpha > 0.5:
            glow = self.canvas.create_line(
                animation.start_x, animation.start_y,
                animation.end_x, animation.end_y,
                fill="orange", width=width + 2, tags="weapon_effect"
            )
            animation.beam_objects.append(glow)
    
    def draw_missile_trail(self, animation: WeaponFireAnimation):
        """Draw missile trail effect"""
        # Calculate missile position along path
        missile_x = animation.start_x + (animation.end_x - animation.start_x) * animation.progress
        missile_y = animation.start_y + (animation.end_y - animation.start_y) * animation.progress
        
        # Draw missile
        missile = self.canvas.create_oval(
            missile_x - 2, missile_y - 2, missile_x + 2, missile_y + 2,
            fill="yellow", outline="orange", tags="weapon_effect"
        )
        animation.particle_objects.append(missile)
        
        # Draw smoke trail
        for i in range(5):
            trail_progress = max(0, animation.progress - i * 0.1)
            if trail_progress > 0:
                trail_x = animation.start_x + (animation.end_x - animation.start_x) * trail_progress
                trail_y = animation.start_y + (animation.end_y - animation.start_y) * trail_progress
                alpha = 0.5 - i * 0.1
                
                trail = self.canvas.create_oval(
                    trail_x - 1, trail_y - 1, trail_x + 1, trail_y + 1,
                    fill="gray", outline="", tags="weapon_effect"
                )
                animation.particle_objects.append(trail)
    
    def draw_explosion_rings(self, animation: ExplosionAnimation):
        """Draw explosion ring effects"""
        x, y = animation.x, animation.y
        
        # Multiple expanding rings
        for i in range(3):
            ring_progress = max(0, animation.progress - i * 0.2)
            if ring_progress > 0:
                radius = int(20 * ring_progress)
                alpha = 1.0 - ring_progress
                
                # Color based on hit type
                if animation.hit_type == "destroy":
                    color = "red"
                elif animation.hit_type == "hit":
                    color = "orange"
                else:  # miss
                    color = "yellow"
                
                ring = self.canvas.create_oval(
                    x - radius, y - radius, x + radius, y + radius,
                    outline=color, width=2, fill="", tags="explosion_effect"
                )
                animation.explosion_objects.append(ring)
    
    def draw_pulse_highlight(self, animation: PulseAnimation):
        """Draw pulsing selection highlight"""
        if not animation.mech:
            return
            
        x, y = self.hex_to_pixel(animation.mech.hex_tile.q, animation.mech.hex_tile.r)
        alpha = animation.get_pulse_alpha()
        
        # Calculate highlight intensity
        intensity = int(255 * alpha)
        color = f"#{intensity:02x}{intensity:02x}00"  # Yellow pulse
        
        # Draw pulsing ring around mech
        radius = 20
        pulse_ring = self.canvas.create_oval(
            x - radius, y - radius, x + radius, y + radius,
            outline=color, width=3, fill="", tags="pulse_effect"
        )
        animation.pulse_objects.append(pulse_ring)
    
    def draw_mech_at_position(self, mech, x: int, y: int, tag: str, selected_mech=None):
        """Draw a mech at a specific position (for animations)"""
        radius = 15
        outline_color = "gold" if mech == selected_mech else "black"
        outline_width = 3 if mech == selected_mech else 2
        
        if mech.is_destroyed():
            fill_color = "gray"
        else:
            fill_color = mech.color
        
        # Draw circle
        self.canvas.create_oval(x - radius, y - radius, x + radius, y + radius,
                               fill=fill_color, outline=outline_color, width=outline_width, tags=tag)
        
        # Draw mech icon
        if mech.is_destroyed():
            self.canvas.create_text(x, y, text="✗", font=("Arial", 16, "bold"), fill="white", tags=tag)
        else:
            self.draw_mech_icon_at_position(x, y, fill_color, tag)
    
    def draw_mech_icon_at_position(self, x: int, y: int, fill_color: str, tag: str):
        """Draw mech icon at specific position"""
        icon_color = "white" if fill_color != "white" else "black"
        
        # Main body
        body_width, body_height = 8, 10
        self.canvas.create_rectangle(
            x - body_width//2, y - body_height//2,
            x + body_width//2, y + body_height//2,
            fill=icon_color, outline="", tags=tag
        )
        
        # Head
        head_radius = 3
        self.canvas.create_oval(
            x - head_radius, y - body_height//2 - head_radius,
            x + head_radius, y - body_height//2 + head_radius,
            fill=icon_color, outline="", tags=tag
        )
        
        # Arms and legs (simplified for animation)
        arm_width, arm_height = 3, 6
        leg_width, leg_height = 3, 4
        
        # Left arm, right arm, left leg, right leg
        positions = [
            (x - body_width//2 - arm_width, y - arm_height//2, x - body_width//2, y + arm_height//2),
            (x + body_width//2, y - arm_height//2, x + body_width//2 + arm_width, y + arm_height//2),
            (x - leg_width - 1, y + body_height//2, x - 1, y + body_height//2 + leg_height),
            (x + 1, y + body_height//2, x + leg_width + 1, y + body_height//2 + leg_height)
        ]
        
        for x1, y1, x2, y2 in positions:
            self.canvas.create_rectangle(x1, y1, x2, y2, fill=icon_color, outline="", tags=tag)
