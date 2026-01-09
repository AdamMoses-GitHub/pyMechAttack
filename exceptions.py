"""
pyMechAttack - Custom Exceptions Module
Contains all game-specific exception classes
"""

# Custom Exceptions
class BattleTechException(Exception):
    """Base exception for BattleTech game"""
    pass

class InvalidMoveException(BattleTechException):
    """Raised when a move is not valid"""
    pass

class InvalidTargetException(BattleTechException):
    """Raised when target is invalid"""
    pass

class OutOfRangeException(BattleTechException):
    """Raised when target is out of weapon range"""
    pass

class NoLineOfSightException(BattleTechException):
    """Raised when LOS is blocked"""
    pass

class InvalidPhaseException(BattleTechException):
    """Raised when action attempted in wrong phase"""
    pass

class MechDestroyedException(BattleTechException):
    """Raised when action attempted on destroyed mech"""
    pass

class InvalidWeaponException(BattleTechException):
    """Raised when weapon type is invalid"""
    pass

class InsufficientMovementException(BattleTechException):
    """Raised when insufficient movement points"""
    pass

class ConfigurationException(BattleTechException):
    """Raised when configuration is invalid"""
    pass
