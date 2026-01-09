"""
pyMechAttack - Animation System Module
Contains all animation classes for visual effects
"""

import time
import math
from typing import Tuple

class Animation:
    """Base class for animations"""
    def __init__(self, animation_id: int, duration: float):
        self.id = animation_id
        self.duration = duration  # Duration in seconds
        self.start_time = time.time()
        self.progress = 0.0  # 0.0 to 1.0
        self.completed = False
        
    def update(self) -> bool:
        """Update animation progress. Returns True if still active."""
        current_time = time.time()
        elapsed = current_time - self.start_time
        self.progress = min(elapsed / self.duration, 1.0)
        self.completed = self.progress >= 1.0
        return not self.completed
        
    def cleanup(self, canvas):
        """Clean up animation resources"""
        pass

class MoveAnimation(Animation):
    """Animation for mech movement"""
    def __init__(self, animation_id: int, mech, start_pos: Tuple[int, int], end_pos: Tuple[int, int]):
        super().__init__(animation_id, 0.8)  # 0.8 second movement
        self.mech = mech
        self.start_x, self.start_y = start_pos
        self.end_x, self.end_y = end_pos
        self.current_x = self.start_x
        self.current_y = self.start_y
        
    def get_current_position(self) -> Tuple[int, int]:
        """Get current animated position"""
        # Smooth interpolation with easing
        t = self.ease_in_out(self.progress)
        self.current_x = self.start_x + (self.end_x - self.start_x) * t
        self.current_y = self.start_y + (self.end_y - self.start_y) * t
        return (int(self.current_x), int(self.current_y))
        
    def ease_in_out(self, t: float) -> float:
        """Smooth easing function"""
        return t * t * (3.0 - 2.0 * t)

class WeaponFireAnimation(Animation):
    """Animation for weapon firing effects"""
    def __init__(self, animation_id: int, weapon_type: str, start_pos: Tuple[int, int], end_pos: Tuple[int, int]):
        duration = 0.3 if weapon_type == "laser" else 0.6  # Missiles take longer
        super().__init__(animation_id, duration)
        self.weapon_type = weapon_type
        self.start_x, self.start_y = start_pos
        self.end_x, self.end_y = end_pos
        self.beam_objects = []
        self.particle_objects = []
        
    def cleanup(self, canvas):
        """Remove weapon effect objects"""
        for obj in self.beam_objects + self.particle_objects:
            try:
                canvas.delete(obj)
            except:
                pass

class ExplosionAnimation(Animation):
    """Animation for explosions and impacts"""
    def __init__(self, animation_id: int, pos: Tuple[int, int], hit_type: str = "hit"):
        super().__init__(animation_id, 0.5)  # 0.5 second explosion
        self.x, self.y = pos
        self.hit_type = hit_type  # "hit", "miss", "destroy"
        self.explosion_objects = []
        
    def cleanup(self, canvas):
        """Remove explosion objects"""
        for obj in self.explosion_objects:
            try:
                canvas.delete(obj)
            except:
                pass

class PulseAnimation(Animation):
    """Animation for pulsing highlights"""
    def __init__(self, animation_id: int, mech):
        super().__init__(animation_id, 999.0)  # Continuous until stopped
        self.mech = mech
        self.pulse_objects = []
        
    def get_pulse_alpha(self) -> float:
        """Get current pulse transparency (0.3 to 1.0)"""
        pulse_speed = 3.0  # Pulses per second
        return 0.65 + 0.35 * math.sin(time.time() * pulse_speed * 2 * math.pi)
        
    def cleanup(self, canvas):
        """Remove pulse objects"""
        for obj in self.pulse_objects:
            try:
                canvas.delete(obj)
            except:
                pass
