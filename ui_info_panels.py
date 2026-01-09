"""
pyMechAttack - Info Panels Module
Manages the mech information and target information display panels
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional
from entities import Mech
from models import MechPhase


class InfoPanelManager:
    """Manages the information display panels for selected mechs and targets"""
    
    def __init__(self, mech_info_frame: ttk.Frame, target_info_frame: ttk.Frame, 
                 instruction_label: ttk.Label):
        """
        Initialize the info panel manager
        
        Args:
            mech_info_frame: Frame for selected mech info
            target_info_frame: Frame for target mech info
            instruction_label: Label for instructions
        """
        self.mech_info_frame = mech_info_frame
        self.target_info_frame = target_info_frame
        self.instruction_label = instruction_label
    
    def update_mech_info(self, mech: Optional[Mech]):
        """
        Update the selected mech information display
        
        Args:
            mech: The selected mech, or None if no mech is selected
        """
        # Clear existing mech info
        for widget in self.mech_info_frame.winfo_children():
            widget.destroy()
        
        if mech:
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
            self._update_instruction_for_phase(mech.current_phase, mech.can_still_move())
        else:
            ttk.Label(self.mech_info_frame, text="No mech selected", font=("Arial", 9)).pack(anchor=tk.W)
            self.instruction_label.config(text="Select one of your mechs to begin")
    
    def _update_instruction_for_phase(self, phase: MechPhase, can_move: bool):
        """Update instruction label based on current phase"""
        if phase == MechPhase.MOVEMENT:
            if can_move:
                self.instruction_label.config(
                    text="Green=Easy, Yellow=Moderate, Orange=Expensive movement. Click hex to move or End Movement"
                )
            else:
                self.instruction_label.config(text="No movement remaining - click End Movement to attack")
        elif phase == MechPhase.ATTACK:
            self.instruction_label.config(text="Select target and attack, or click End Turn")
        else:  # DONE
            self.instruction_label.config(text="Turn complete - click End Turn")
    
    def update_target_info(self, target: Optional[Mech], selected_mech: Optional[Mech],
                          has_los_func, laser_hit_chance: float = 0.0, missile_hit_chance: float = 0.0):
        """
        Update the target information display
        
        Args:
            target: The target mech, or None if no target selected
            selected_mech: The currently selected mech
            has_los_func: Function to check line of sight (takes two hex tiles, returns (bool, int))
            laser_hit_chance: Hit chance for laser weapon (0.0 to 1.0)
            missile_hit_chance: Hit chance for missile weapon (0.0 to 1.0)
        """
        # Clear existing target info
        for widget in self.target_info_frame.winfo_children():
            widget.destroy()
        
        if target:
            target_text = f"{target.stats.name} (Player {target.player_id})\n"
            target_text += f"Armor: {target.stats.armor_hp}/{target.stats.max_armor_hp}\n"
            target_text += f"Structure: {target.stats.structure_hp}/{target.stats.max_structure_hp}\n"
            
            if selected_mech:
                distance = selected_mech.hex_tile.distance_to(target.hex_tile)
                target_text += f"Range: {distance} hexes\n"
                
                # Check line of sight
                has_los, range_modifier = has_los_func(selected_mech.hex_tile, target.hex_tile)
                los_text = "Clear" if has_los else "Blocked"
                target_text += f"Line of Sight: {los_text}\n"
                
                # Show weapon range and hit chance status
                target_text += "Weapons:\n"
                
                # Laser weapon status
                if distance <= 8 and has_los:
                    target_text += f"  Laser: ✓ Range {distance}/8, Hit: {int(laser_hit_chance * 100)}%"
                elif distance <= 8:
                    target_text += f"  Laser: ✗ No LOS (Range {distance}/8)"
                else:
                    target_text += f"  Laser: ✗ Out of Range ({distance}/8)"
                    
                target_text += "\n"
                
                # Missile weapon status
                if distance <= 12 and has_los:
                    target_text += f"  Missile: ✓ Range {distance}/12, Hit: {int(missile_hit_chance * 100)}%"
                elif distance <= 12:
                    target_text += f"  Missile: ✗ No LOS (Range {distance}/12)"
                else:
                    target_text += f"  Missile: ✗ Out of Range ({distance}/12)"
            
            ttk.Label(self.target_info_frame, text=target_text, font=("Arial", 9)).pack(anchor=tk.W)
        else:
            ttk.Label(self.target_info_frame, text="No target selected", font=("Arial", 9)).pack(anchor=tk.W)
    
    def set_instruction(self, text: str):
        """Set the instruction label text"""
        self.instruction_label.config(text=text)
