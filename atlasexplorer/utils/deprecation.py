"""
Deprecation warning system for Atlas Explorer legacy components.

This module provides graceful deprecation warnings when customers use
legacy monolithic classes while guiding them to superior modular alternatives.
"""

import warnings
import functools


class AtlasDeprecationWarning(UserWarning):
    """Custom warning class for Atlas Explorer deprecations."""
    pass


def deprecated_class(reason, replacement=None, version="3.0.0"):
    """
    Decorator to mark classes as deprecated with helpful migration guidance.
    
    Args:
        reason: Explanation of why the class is deprecated
        replacement: Name of the modular replacement class
        version: Version when the class will be removed
    """
    def decorator(cls):
        original_init = cls.__init__
        
        @functools.wraps(original_init)
        def wrapper(self, *args, **kwargs):
            warning_msg = f"{cls.__name__} is deprecated. {reason}"
            if replacement:
                warning_msg += f" Use {replacement} instead."
            warning_msg += f" Will be removed in version {version}."
            
            warnings.warn(
                warning_msg, 
                AtlasDeprecationWarning, 
                stacklevel=2
            )
            return original_init(self, *args, **kwargs)
        
        cls.__init__ = wrapper
        return cls
    return decorator


def deprecated_function(reason, replacement=None, version="3.0.0"):
    """
    Decorator to mark functions as deprecated with helpful migration guidance.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            warning_msg = f"{func.__name__}() is deprecated. {reason}"
            if replacement:
                warning_msg += f" Use {replacement} instead."
            warning_msg += f" Will be removed in version {version}."
            
            warnings.warn(
                warning_msg,
                AtlasDeprecationWarning,
                stacklevel=2
            )
            return func(*args, **kwargs)
        return wrapper
    return decorator


def configure_deprecation_warnings():
    """
    Configure how deprecation warnings are displayed to users.
    """
    # Ensure our deprecation warnings are always shown
    warnings.filterwarnings("always", category=AtlasDeprecationWarning)
    
    # Create a custom warning format for better user experience
    def custom_warning_handler(message, category, filename, lineno, file=None, line=None):
        if category == AtlasDeprecationWarning:
            print(f"\n⚠️  DEPRECATION WARNING: {message}")
            print("💡 For migration help, see: https://docs.atlasexplorer.com/migration")
            print("🚀 Benefits of modular architecture: better performance, security, and maintainability\n")
        else:
            # Use default handling for other warnings
            warnings.showwarning(message, category, filename, lineno, file, line)
    
    warnings.showwarning = custom_warning_handler


# Configure warnings when module is imported
configure_deprecation_warnings()
