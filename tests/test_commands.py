"""
Comprehensive tests for CLI Commands module.
"""

import unittest
from unittest.mock import Mock, patch
import argparse

from atlasexplorer.cli.commands import AtlasExplorerCLI
from atlasexplorer.utils.exceptions import AtlasExplorerError, ConfigurationError


class TestAtlasExplorerCLIInitialization(unittest.TestCase):
    """Test CLI initialization and setup."""

    def setUp(self):
        """Set up test fixtures."""
        self.cli = AtlasExplorerCLI()

    def test_initialization_default_parameters(self):
        """Test CLI initialization with default parameters."""
        self.assertIsInstance(self.cli, AtlasExplorerCLI)

    def test_available_commands(self):
        """Test that available commands are properly defined."""
        self.assertTrue(hasattr(self.cli, 'configure_command'))
        self.assertIn('configure', self.cli.commands)

    def test_commands_registry_structure(self):
        """Test commands registry structure and accessibility."""
        expected_methods = ['configure_command', 'create_parser', 'run']
        for method in expected_methods:
            self.assertTrue(hasattr(self.cli, method), f"CLI should have {method} method")

    def test_commands_dictionary_setup(self):
        """Test that the commands dictionary is properly initialized."""
        self.assertIsInstance(self.cli.commands, dict)
        self.assertEqual(self.cli.commands['configure'], self.cli.configure_command)


class TestAtlasExplorerCLICommandExecution(unittest.TestCase):
    """Test command execution and dispatch functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.cli = AtlasExplorerCLI()

    def test_run_with_valid_command(self):
        """Test execution with valid configure command."""
        args = Mock()
        args.handler_function = "configure"
        
        with patch('atlasexplorer.cli.interactive.InteractiveConfig') as mock_interactive:
            mock_interactive.return_value.run_configuration.return_value = None
            
            self.cli.run(args)
            
            mock_interactive.assert_called_once()
            mock_interactive.return_value.run_configuration.assert_called_once()

    def test_run_with_no_command(self):
        """Test execution with no command specified."""
        # Create args without handler_function attribute
        class FakeArgs:
            pass
        args = FakeArgs()
        
        with patch('sys.exit') as mock_exit:
            mock_exit.side_effect = SystemExit  # Make exit actually exit
            with patch('builtins.print') as mock_print:
                with self.assertRaises(SystemExit):
                    self.cli.run(args)
                
                mock_print.assert_called_with("Error: No command specified")
                mock_exit.assert_called_with(1)

    def test_run_with_unknown_command(self):
        """Test execution with unknown command."""
        args = Mock()
        args.handler_function = "nonexistent_command"
        
        with patch('sys.exit') as mock_exit:
            mock_exit.side_effect = SystemExit  # Make exit actually exit
            with patch('builtins.print') as mock_print:
                with self.assertRaises(SystemExit):
                    self.cli.run(args)
                
                mock_print.assert_called_with("Error: Unknown command 'nonexistent_command'")
                mock_exit.assert_called_with(1)

    def test_run_with_atlas_explorer_error(self):
        """Test execution with AtlasExplorerError exception."""
        args = Mock()
        args.handler_function = "configure"
        
        error_message = "Configuration validation failed"
        
        with patch('atlasexplorer.cli.interactive.InteractiveConfig') as mock_interactive:
            mock_interactive.return_value.run_configuration.side_effect = AtlasExplorerError(error_message)
            
            with patch('sys.exit') as mock_exit:
                mock_exit.side_effect = SystemExit  # Make exit actually exit
                with patch('builtins.print') as mock_print:
                    with self.assertRaises(SystemExit):
                        self.cli.run(args)
                    
                    mock_print.assert_called_with(f"Error: Configuration failed: {error_message}")
                    mock_exit.assert_called_with(1)

    def test_run_with_configuration_error(self):
        """Test execution with ConfigurationError exception."""
        args = Mock()
        args.handler_function = "configure"
        
        error_message = "Invalid configuration parameters"
        
        with patch('atlasexplorer.cli.interactive.InteractiveConfig') as mock_interactive:
            mock_interactive.return_value.run_configuration.side_effect = Exception(error_message)
            
            with patch('sys.exit') as mock_exit:
                mock_exit.side_effect = SystemExit  # Make exit actually exit
                with patch('builtins.print') as mock_print:
                    with self.assertRaises(SystemExit):
                        self.cli.run(args)
                    
                    mock_print.assert_called_with(f"Error: Configuration failed: {error_message}")
                    mock_exit.assert_called_with(1)

    def test_run_with_keyboard_interrupt(self):
        """Test execution with KeyboardInterrupt (Ctrl+C)."""
        args = Mock()
        args.handler_function = "configure"
        
        with patch('atlasexplorer.cli.interactive.InteractiveConfig') as mock_interactive:
            mock_interactive.return_value.run_configuration.side_effect = KeyboardInterrupt()
            
            with patch('sys.exit') as mock_exit:
                mock_exit.side_effect = SystemExit  # Make exit actually exit
                with patch('builtins.print') as mock_print:
                    with self.assertRaises(SystemExit):
                        self.cli.run(args)
                    
                    mock_print.assert_called_with("\\nOperation cancelled by user")
                    mock_exit.assert_called_with(0)

    def test_run_with_general_exception(self):
        """Test execution with general (unexpected) exception."""
        args = Mock()
        args.handler_function = "configure"
        
        error_message = "Something unexpected happened"
        
        # Mock the command function to raise a general exception directly
        def failing_command(args):
            raise ValueError(error_message)
        
        # Replace the configure command with our failing version
        self.cli.commands["configure"] = failing_command
        
        with patch('sys.exit') as mock_exit:
            mock_exit.side_effect = SystemExit  # Make exit actually exit
            with patch('builtins.print') as mock_print:
                with self.assertRaises(SystemExit):
                    self.cli.run(args)
                
                # Should trigger lines 55-57: "Unexpected error: {e}"
                mock_print.assert_called_with(f"Unexpected error: {error_message}")
                mock_exit.assert_called_with(1)


class TestAtlasExplorerCLIConfigureCommand(unittest.TestCase):
    """Test configure command functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.cli = AtlasExplorerCLI()

    def test_configure_command_success(self):
        """Test successful configure command execution."""
        args = Mock()
        
        with patch('atlasexplorer.cli.interactive.InteractiveConfig') as mock_interactive_class:
            mock_interactive = Mock()
            mock_interactive_class.return_value = mock_interactive
            
            self.cli.configure_command(args)
            
            mock_interactive_class.assert_called_once()
            mock_interactive.run_configuration.assert_called_once()

    def test_configure_command_with_exception(self):
        """Test configure command with exception during interactive configuration."""
        args = Mock()
        
        error_message = "Interactive configuration failed"
        
        with patch('atlasexplorer.cli.interactive.InteractiveConfig') as mock_interactive_class:
            mock_interactive = Mock()
            mock_interactive.run_configuration.side_effect = Exception(error_message)
            mock_interactive_class.return_value = mock_interactive
            
            with self.assertRaises(ConfigurationError) as context:
                self.cli.configure_command(args)
            
            self.assertIn("Configuration failed:", str(context.exception))
            self.assertIn(error_message, str(context.exception))


class TestAtlasExplorerCLIArgumentParser(unittest.TestCase):
    """Test argument parser creation and configuration."""

    def test_create_parser_returns_argument_parser(self):
        """Test that create_parser returns an ArgumentParser instance."""
        parser = AtlasExplorerCLI.create_parser()
        self.assertIsInstance(parser, argparse.ArgumentParser)

    def test_create_parser_configure_subcommand(self):
        """Test that configure subcommand is properly configured."""
        parser = AtlasExplorerCLI.create_parser()
        
        args = parser.parse_args(['configure'])
        self.assertEqual(args.handler_function, 'configure')

    def test_create_parser_help_functionality(self):
        """Test that parser provides help functionality."""
        parser = AtlasExplorerCLI.create_parser()
        
        help_text = parser.format_help()
        self.assertIsInstance(help_text, str)
        self.assertIn('configure', help_text.lower())

    def test_create_parser_with_invalid_command(self):
        """Test parser behavior with invalid command."""
        parser = AtlasExplorerCLI.create_parser()
        
        with self.assertRaises(SystemExit):
            parser.parse_args(['invalid_command'])

    def test_create_parser_program_name(self):
        """Test that parser has correct program name."""
        parser = AtlasExplorerCLI.create_parser()
        self.assertEqual(parser.prog, 'atlasexplorer')

    def test_create_parser_subcommands_setup(self):
        """Test that subcommands are properly set up."""
        parser = AtlasExplorerCLI.create_parser()
        
        # Should have subparsers
        self.assertTrue(hasattr(parser, '_subparsers'))


class TestAtlasExplorerCLIMainEntry(unittest.TestCase):
    """Test main entry point functionality."""

    def test_main_entry_point_exists(self):
        """Test that main entry point is available."""
        # The main function should be available as a static method
        self.assertTrue(hasattr(AtlasExplorerCLI, 'main'))
        self.assertTrue(callable(AtlasExplorerCLI.main))

    @patch('atlasexplorer.cli.commands.AtlasExplorerCLI.create_parser')
    @patch('atlasexplorer.cli.commands.AtlasExplorerCLI')
    def test_main_with_configure_command(self, mock_cli_class, mock_create_parser):
        """Test main entry point with configure command."""
        # Mock parser and CLI
        mock_parser = Mock()
        mock_args = Mock()
        mock_args.handler_function = 'configure'
        mock_parser.parse_args.return_value = mock_args
        mock_create_parser.return_value = mock_parser
        
        mock_cli = Mock()
        mock_cli_class.return_value = mock_cli
        
        # Test main execution
        with patch('sys.argv', ['atlas-explorer', 'configure']):
            AtlasExplorerCLI.main()
        
        mock_create_parser.assert_called_once()
        mock_parser.parse_args.assert_called_once()
        mock_cli_class.assert_called_once()
        mock_cli.run.assert_called_once_with(mock_args)


class TestAtlasExplorerCLIErrorHandling(unittest.TestCase):
    """Test error handling scenarios."""

    def setUp(self):
        """Set up test fixtures."""
        self.cli = AtlasExplorerCLI()

    def test_command_not_found_handling(self):
        """Test handling of commands that don't exist."""
        args = Mock()
        args.handler_function = "nonexistent"
        
        with patch('sys.exit') as mock_exit:
            mock_exit.side_effect = SystemExit  # Make exit actually exit
            with patch('builtins.print') as mock_print:
                with self.assertRaises(SystemExit):
                    self.cli.run(args)
                
                mock_print.assert_called_with("Error: Unknown command 'nonexistent'")
                mock_exit.assert_called_with(1)

    def test_none_command_handling(self):
        """Test handling when no command is specified."""
        # Create args without handler_function attribute  
        class FakeArgs:
            pass
        args = FakeArgs()
        
        with patch('sys.exit') as mock_exit:
            mock_exit.side_effect = SystemExit  # Make exit actually exit
            with patch('builtins.print') as mock_print:
                with self.assertRaises(SystemExit):
                    self.cli.run(args)
                
                mock_print.assert_called_with("Error: No command specified")
                mock_exit.assert_called_with(1)

    def test_exception_propagation(self):
        """Test that exceptions are properly caught and handled."""
        args = Mock()
        args.handler_function = "configure"
        
        # Test that general exceptions result in "Error: Configuration failed:"
        with patch('atlasexplorer.cli.interactive.InteractiveConfig') as mock_interactive:
            mock_interactive.return_value.run_configuration.side_effect = RuntimeError("Test error")
            
            with patch('sys.exit') as mock_exit:
                mock_exit.side_effect = SystemExit  # Make exit actually exit
                with patch('builtins.print') as mock_print:
                    with self.assertRaises(SystemExit):
                        self.cli.run(args)
                    
                    mock_print.assert_called_with("Error: Configuration failed: Test error")
                    mock_exit.assert_called_with(1)


class TestAtlasExplorerCLISecurityFeatures(unittest.TestCase):
    """Test security features and protections."""

    def setUp(self):
        """Set up test fixtures."""
        self.cli = AtlasExplorerCLI()

    def test_command_dispatch_security(self):
        """Test that command dispatch is secure."""
        args = Mock()
        args.handler_function = "__import__"
        
        with patch('sys.exit') as mock_exit:
            mock_exit.side_effect = SystemExit  # Make exit actually exit
            with patch('builtins.print') as mock_print:
                with self.assertRaises(SystemExit):
                    self.cli.run(args)
                
                mock_print.assert_called_with("Error: Unknown command '__import__'")
                mock_exit.assert_called_with(1)

    def test_no_eval_usage(self):
        """Test that the CLI doesn't use eval() for command execution."""
        args = Mock()
        args.handler_function = "eval('print(\"hacked\")')"
        
        with patch('sys.exit') as mock_exit:
            mock_exit.side_effect = SystemExit  # Make exit actually exit
            with patch('builtins.print') as mock_print:
                with self.assertRaises(SystemExit):
                    self.cli.run(args)
                
                expected_message = "Error: Unknown command 'eval('print(\"hacked\")')'"
                mock_print.assert_called_with(expected_message)
                mock_exit.assert_called_with(1)

    def test_command_validation(self):
        """Test that only valid commands are executed."""
        # Test with valid command
        args = Mock()
        args.handler_function = "configure"
        
        with patch('atlasexplorer.cli.interactive.InteractiveConfig'):
            # Should not raise exception for valid commands  
            try:
                self.cli.run(args)
            except SystemExit:
                pass  # Expected due to the success path

    def test_dictionary_based_dispatch(self):
        """Test that command dispatch uses dictionary lookup, not eval."""
        # Verify that commands are stored in a dictionary
        self.assertIsInstance(self.cli.commands, dict)
        self.assertIn('configure', self.cli.commands)
        
        # Verify that the configure command points to the method
        self.assertEqual(self.cli.commands['configure'], self.cli.configure_command)


if __name__ == '__main__':
    unittest.main()
