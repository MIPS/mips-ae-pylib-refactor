"""Command-line interface for Atlas Explorer.

This module provides secure CLI commands to replace the unsafe eval() usage
in the original implementation.
"""

import argparse
import sys
from typing import Dict, Callable, Any

from ..core.config import AtlasConfig
from ..utils.exceptions import AtlasExplorerError, ConfigurationError


# Legacy compatibility functions for functional parity
def configure(args):
    """Legacy configure function for API compatibility.
    
    This function provides backward compatibility with the legacy monolithic
    module's configure function.
    """
    cli = AtlasExplorerCLI()
    cli.configure_command(args)


def subcmd_configure(subparsers):
    """Legacy subcmd_configure function for API compatibility.
    
    This function provides backward compatibility with the legacy monolithic
    module's subcmd_configure function.
    """
    parser = subparsers.add_parser(
        "configure",
        help="Configure Atlas Explorer Cloud Access",
    )
    parser.set_defaults(handler_function="configure")


class AtlasExplorerCLI:
    """Secure command-line interface for Atlas Explorer.
    
    This class replaces the unsafe eval() usage with a secure dispatch
    mechanism for handling CLI commands.
    """
    
    def __init__(self):
        """Initialize the CLI with available commands."""
        self.commands: Dict[str, Callable[[Any], None]] = {
            "configure": self.configure_command
        }
    
    def run(self, args: argparse.Namespace) -> None:
        """Execute a command based on parsed arguments.
        
        This method replaces the unsafe eval(args.handler_function + "(args)")
        pattern with a secure dispatch mechanism.
        
        Args:
            args: Parsed command-line arguments
        """
        handler_name = getattr(args, 'handler_function', None)
        
        if not handler_name:
            print("Error: No command specified")
            sys.exit(1)
        
        if handler_name not in self.commands:
            print(f"Error: Unknown command '{handler_name}'")
            sys.exit(1)
        
        try:
            self.commands[handler_name](args)
        except AtlasExplorerError as e:
            print(f"Error: {e}")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\\nOperation cancelled by user")
            sys.exit(0)
        except Exception as e:
            print(f"Unexpected error: {e}")
            sys.exit(1)
    
    def configure_command(self, args: argparse.Namespace) -> None:
        """Handle the configure command.
        
        Args:
            args: Parsed command-line arguments
        """
        from .interactive import InteractiveConfig
        
        try:
            interactive = InteractiveConfig()
            interactive.run_configuration()
        except Exception as e:
            raise ConfigurationError(f"Configuration failed: {e}")
    
    @staticmethod
    def create_parser() -> argparse.ArgumentParser:
        """Create the main argument parser.
        
        Returns:
            Configured argument parser
        """
        parser = argparse.ArgumentParser(
            prog="atlasexplorer",
            description="Atlas Explorer Utility - Secure Performance Analysis",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  atlasexplorer configure              Configure API credentials
  atlasexplorer configure --help       Show configuration options
            """)
        
        subparsers = parser.add_subparsers(
            title="Commands",
            description="Available Atlas Explorer commands",
            help="Use 'command --help' for command-specific help",
            dest="command",
            required=True
        )
        
        # Configure command
        configure_parser = subparsers.add_parser(
            "configure",
            help="Configure Atlas Explorer Cloud Access",
            description="Interactive configuration of API credentials and settings"
        )
        configure_parser.set_defaults(handler_function="configure")
        
        return parser
    
    @staticmethod
    def main() -> None:
        """Main entry point for the CLI."""
        parser = AtlasExplorerCLI.create_parser()
        args = parser.parse_args()
        
        cli = AtlasExplorerCLI()
        cli.run(args)
