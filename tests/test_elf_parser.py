#!/usr/bin/env python3
"""
Comprehensive unit tests for the ELF Parser module.

Tests the ELFAnalyzer class to achieve 90%+ coverage using proven patterns
from the successful experiment module enhancement.
"""

import os
import tempfile
import shutil
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open, MagicMock

from atlasexplorer.analysis.elf_parser import ELFAnalyzer
from atlasexplorer.utils.exceptions import ELFValidationError


class TestELFAnalyzer(unittest.TestCase):
    """Test cases for the ELFAnalyzer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.analyzer = ELFAnalyzer(verbose=True)
        self.analyzer_quiet = ELFAnalyzer(verbose=False)
        
        # Create test ELF file path
        self.test_elf_path = os.path.join(self.temp_dir, "test.elf")
        with open(self.test_elf_path, 'wb') as f:
            f.write(b'\x7fELF')  # Basic ELF magic number
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_analyzer_initialization(self):
        """Test ELFAnalyzer initialization."""
        # Test verbose initialization
        analyzer_verbose = ELFAnalyzer(verbose=True)
        self.assertTrue(analyzer_verbose.verbose)
        
        # Test quiet initialization
        analyzer_quiet = ELFAnalyzer(verbose=False)
        self.assertFalse(analyzer_quiet.verbose)
        
        # Test default initialization
        analyzer_default = ELFAnalyzer()
        self.assertTrue(analyzer_default.verbose)  # Default is True
    
    def test_snapshot_source_files_nonexistent_path(self):
        """Test snapshot_source_files with non-existent path."""
        non_existent_path = "/path/that/does/not/exist.elf"
        
        # Test with verbose output
        with patch('builtins.print') as mock_print:
            result = self.analyzer.snapshot_source_files(non_existent_path)
            self.assertEqual(result, set())
            mock_print.assert_called_with(f"ELF path does not exist: {non_existent_path}")
        
        # Test with quiet mode
        result = self.analyzer_quiet.snapshot_source_files(non_existent_path)
        self.assertEqual(result, set())
    
    def test_snapshot_source_files_empty_path(self):
        """Test snapshot_source_files with empty/None path."""
        # Test empty string
        result = self.analyzer.snapshot_source_files("")
        self.assertEqual(result, set())
        
        # Test None path - this will cause TypeError in Path() but we test it anyway
        with self.assertRaises(TypeError):
            self.analyzer.snapshot_source_files(None)
    
    @patch('elftools.elf.elffile.ELFFile')
    def test_snapshot_source_files_no_dwarf_info(self, mock_elf_file):
        """Test snapshot_source_files with ELF file containing no DWARF info."""
        # Mock ELF file without DWARF info
        mock_elffile_instance = Mock()
        mock_elffile_instance.has_dwarf_info.return_value = False
        mock_elf_file.return_value = mock_elffile_instance
        
        with patch('builtins.open', mock_open(read_data=b'\x7fELF')):
            with patch('builtins.print') as mock_print:
                result = self.analyzer.snapshot_source_files(self.test_elf_path)
                self.assertEqual(result, set())
                mock_print.assert_called_with(f"ELF file has no DWARF debug information: {self.test_elf_path}")
    
    def test_snapshot_source_files_import_error(self):
        """Test snapshot_source_files when elftools is not available."""
        # Patch the import inside the method
        with patch('builtins.__import__', side_effect=ImportError("No module named 'elftools'")):
            with patch('builtins.open', mock_open(read_data=b'\x7fELF')):
                with self.assertRaises(ELFValidationError) as context:
                    self.analyzer.snapshot_source_files(self.test_elf_path)
                
                self.assertIn("elftools library not available", str(context.exception))
    
    @patch('elftools.elf.elffile.ELFFile')
    def test_snapshot_source_files_general_exception(self, mock_elf_file):
        """Test snapshot_source_files with general exception during processing."""
        mock_elf_file.side_effect = RuntimeError("Unexpected error")
        
        with patch('builtins.open', mock_open(read_data=b'\x7fELF')):
            with patch('builtins.print') as mock_print:
                result = self.analyzer.snapshot_source_files(self.test_elf_path)
                self.assertEqual(result, set())
                mock_print.assert_called_with(f"Warning: Error reading ELF file {self.test_elf_path}: Unexpected error")
    
    @patch('elftools.elf.elffile.ELFFile')
    def test_snapshot_source_files_successful_extraction(self, mock_elf_file):
        """Test successful source file extraction with DWARF info."""
        # Setup mock ELF file with DWARF info
        mock_elffile_instance = Mock()
        mock_elffile_instance.has_dwarf_info.return_value = True
        
        # Mock DWARF info and compilation units
        mock_dwarf_info = Mock()
        mock_cu = Mock()
        mock_dwarf_info.iter_CUs.return_value = [mock_cu]
        mock_elffile_instance.get_dwarf_info.return_value = mock_dwarf_info
        
        mock_elf_file.return_value = mock_elffile_instance
        
        # Create temporary source files to satisfy Path.exists() checks
        source1_path = os.path.join(self.temp_dir, "source1.c")
        source2_path = os.path.join(self.temp_dir, "source2.c")
        with open(source1_path, 'w') as f:
            f.write("// test source")
        with open(source2_path, 'w') as f:
            f.write("// test source")
        
        test_sources_real = {source1_path, source2_path}
        
        with patch.object(self.analyzer, '_extract_sources_from_cu', return_value=test_sources_real):
            with patch('builtins.open', mock_open(read_data=b'\x7fELF')):
                with patch('builtins.print') as mock_print:
                    result = self.analyzer.snapshot_source_files(self.test_elf_path)
                    
                    self.assertEqual(result, test_sources_real)
                    # Verify verbose output was called
                    mock_print.assert_any_call("Embedded source files in ELF:")


class TestELFAnalyzerSourceExtraction(unittest.TestCase):
    """Test source file extraction from compilation units."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.analyzer = ELFAnalyzer(verbose=True)
        self.analyzer_quiet = ELFAnalyzer(verbose=False)
        self.test_elf_path = Path("/test/path.elf")
    
    def test_extract_sources_from_cu_basic(self):
        """Test basic source extraction from compilation unit."""
        # Mock compilation unit
        mock_cu = Mock()
        
        # Mock top DIE with compilation directory
        mock_top_die = Mock()
        mock_top_die.attributes = {"DW_AT_comp_dir": Mock(value="/home/user/project")}
        mock_cu.get_top_DIE.return_value = mock_top_die
        
        # Mock DWARF info and line program
        mock_dwarf_info = Mock()
        mock_cu.dwarfinfo = mock_dwarf_info
        
        mock_lineprog = Mock()
        mock_lineprog.__getitem__ = Mock(side_effect=lambda key: {
            "file_entry": [
                Mock(name="main.c", dir_index=0),
                Mock(name="utils.c", dir_index=1)
            ]
        }[key])
        
        mock_dwarf_info.line_program_for_CU.return_value = mock_lineprog
        
        # Mock _resolve_file_path to return resolved paths
        with patch.object(self.analyzer, '_resolve_file_path') as mock_resolve:
            mock_resolve.side_effect = ["/home/user/project/main.c", "/home/user/project/lib/utils.c"]
            
            result = self.analyzer._extract_sources_from_cu(mock_cu, self.test_elf_path)
            
            self.assertEqual(result, {"/home/user/project/main.c", "/home/user/project/lib/utils.c"})
            self.assertEqual(mock_resolve.call_count, 2)
    
    def test_extract_sources_from_cu_no_comp_dir(self):
        """Test source extraction when compilation unit has no directory."""
        mock_cu = Mock()
        
        # Mock top DIE without compilation directory
        mock_top_die = Mock()
        mock_top_die.attributes = {}
        mock_cu.get_top_DIE.return_value = mock_top_die
        
        # Mock DWARF info and line program
        mock_dwarf_info = Mock()
        mock_cu.dwarfinfo = mock_dwarf_info
        
        mock_lineprog = Mock()
        mock_lineprog.__getitem__ = Mock(side_effect=lambda key: {
            "file_entry": [Mock(name="main.c", dir_index=0)]
        }[key])
        
        mock_dwarf_info.line_program_for_CU.return_value = mock_lineprog
        
        with patch.object(self.analyzer, '_resolve_file_path') as mock_resolve:
            mock_resolve.return_value = "main.c"
            
            result = self.analyzer._extract_sources_from_cu(mock_cu, self.test_elf_path)
            
            self.assertEqual(result, {"main.c"})
    
    def test_extract_sources_from_cu_bytes_comp_dir(self):
        """Test source extraction with bytes-encoded compilation directory."""
        mock_cu = Mock()
        
        # Mock top DIE with bytes compilation directory
        mock_top_die = Mock()
        mock_top_die.attributes = {"DW_AT_comp_dir": Mock(value=b"/home/user/project")}
        mock_cu.get_top_DIE.return_value = mock_top_die
        
        # Mock DWARF info and line program
        mock_dwarf_info = Mock()
        mock_cu.dwarfinfo = mock_dwarf_info
        
        mock_lineprog = Mock()
        mock_file_entry = Mock(name="main.c", dir_index=0)
        mock_lineprog.__getitem__ = Mock(side_effect=lambda key: {
            "file_entry": [mock_file_entry]
        }[key])
        
        mock_dwarf_info.line_program_for_CU.return_value = mock_lineprog
        
        with patch.object(self.analyzer, '_resolve_file_path') as mock_resolve:
            mock_resolve.return_value = "/home/user/project/main.c"
            
            result = self.analyzer._extract_sources_from_cu(mock_cu, self.test_elf_path)
            
            self.assertEqual(result, {"/home/user/project/main.c"})
            # Verify resolve was called with decoded string
            mock_resolve.assert_called_with(
                mock_file_entry, 
                mock_lineprog, 
                "/home/user/project"
            )
    
    def test_extract_sources_from_cu_no_line_program(self):
        """Test source extraction when no line program is available."""
        mock_cu = Mock()
        
        mock_top_die = Mock()
        mock_top_die.attributes = {"DW_AT_comp_dir": Mock(value="/home/user")}
        mock_cu.get_top_DIE.return_value = mock_top_die
        
        # Mock DWARF info with no line program
        mock_dwarf_info = Mock()
        mock_cu.dwarfinfo = mock_dwarf_info
        mock_dwarf_info.line_program_for_CU.return_value = None
        
        result = self.analyzer._extract_sources_from_cu(mock_cu, self.test_elf_path)
        
        self.assertEqual(result, set())
    
    def test_extract_sources_from_cu_file_entry_exception(self):
        """Test source extraction with exception during file entry processing."""
        mock_cu = Mock()
        
        mock_top_die = Mock()
        mock_top_die.attributes = {"DW_AT_comp_dir": Mock(value="/home/user")}
        mock_cu.get_top_DIE.return_value = mock_top_die
        
        # Mock DWARF info and line program
        mock_dwarf_info = Mock()
        mock_cu.dwarfinfo = mock_dwarf_info
        
        mock_lineprog = Mock()
        mock_lineprog.__getitem__ = Mock(side_effect=lambda key: {
            "file_entry": [
                Mock(name="good.c", dir_index=0),
                Mock(name="bad.c", dir_index=0)
            ]
        }[key])
        
        mock_dwarf_info.line_program_for_CU.return_value = mock_lineprog
        
        # Mock _resolve_file_path to succeed for first file, fail for second
        with patch.object(self.analyzer, '_resolve_file_path') as mock_resolve:
            mock_resolve.side_effect = ["/home/user/good.c", RuntimeError("Processing error")]
            
            with patch('builtins.print') as mock_print:
                result = self.analyzer._extract_sources_from_cu(mock_cu, self.test_elf_path)
                
                self.assertEqual(result, {"/home/user/good.c"})
                mock_print.assert_called_with(f"Warning: Error processing file entry in ELF {self.test_elf_path}: Processing error")
    
    def test_extract_sources_from_cu_general_exception(self):
        """Test source extraction with general exception."""
        mock_cu = Mock()
        mock_cu.get_top_DIE.side_effect = RuntimeError("DWARF processing error")
        
        with patch('builtins.print') as mock_print:
            result = self.analyzer._extract_sources_from_cu(mock_cu, self.test_elf_path)
            
            self.assertEqual(result, set())
            mock_print.assert_called_with(f"Warning: Error processing compilation unit in ELF {self.test_elf_path}: DWARF processing error")


class TestELFAnalyzerFilePathResolution(unittest.TestCase):
    """Test file path resolution logic."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.analyzer = ELFAnalyzer(verbose=False)
    
    def test_resolve_file_path_simple_filename(self):
        """Test resolving simple filename with compilation directory."""
        mock_file_entry = Mock()
        mock_file_entry.name = "main.c"
        mock_file_entry.dir_index = 0
        
        mock_lineprog = Mock()
        comp_dir = "/home/user/project"
        
        result = self.analyzer._resolve_file_path(mock_file_entry, mock_lineprog, comp_dir)
        
        self.assertEqual(result, "/home/user/project/main.c")
    
    def test_resolve_file_path_bytes_filename(self):
        """Test resolving bytes-encoded filename."""
        mock_file_entry = Mock()
        mock_file_entry.name = b"main.c"
        mock_file_entry.dir_index = 0
        
        mock_lineprog = Mock()
        comp_dir = "/home/user/project"
        
        result = self.analyzer._resolve_file_path(mock_file_entry, mock_lineprog, comp_dir)
        
        self.assertEqual(result, "/home/user/project/main.c")
    
    def test_resolve_file_path_with_include_directory(self):
        """Test resolving filename with include directory."""
        mock_file_entry = Mock()
        mock_file_entry.name = "header.h"
        mock_file_entry.dir_index = 1
        
        mock_lineprog = {"include_directory": [".", "include", "lib"]}
        comp_dir = "/home/user/project"
        
        result = self.analyzer._resolve_file_path(mock_file_entry, mock_lineprog, comp_dir)
        
        # Should build path with include directories up to dir_index
        expected = "/home/user/project/./include/header.h"
        self.assertEqual(result, expected)
    
    def test_resolve_file_path_bytes_include_directory(self):
        """Test resolving with bytes-encoded include directory."""
        mock_file_entry = Mock()
        mock_file_entry.name = "header.h"
        mock_file_entry.dir_index = 1
        
        mock_lineprog = {"include_directory": [b".", b"include"]}
        comp_dir = "/home/user/project"
        
        result = self.analyzer._resolve_file_path(mock_file_entry, mock_lineprog, comp_dir)
        
        expected = "/home/user/project/./include/header.h"
        self.assertEqual(result, expected)
    
    def test_resolve_file_path_absolute_directory(self):
        """Test resolving with absolute include directory."""
        mock_file_entry = Mock()
        mock_file_entry.name = "system.h"
        mock_file_entry.dir_index = 1
        
        mock_lineprog = {"include_directory": [".", "/usr/include"]}
        comp_dir = "/home/user/project"
        
        result = self.analyzer._resolve_file_path(mock_file_entry, mock_lineprog, comp_dir)
        
        # When directory is absolute, it should be used directly
        expected = "/usr/include/system.h"
        self.assertEqual(result, expected)
    
    def test_resolve_file_path_no_include_directory(self):
        """Test resolving when no include directory is available."""
        mock_file_entry = Mock()
        mock_file_entry.name = "main.c"
        mock_file_entry.dir_index = 1
        
        mock_lineprog = {}  # No include_directory key
        comp_dir = "/home/user/project"
        
        result = self.analyzer._resolve_file_path(mock_file_entry, mock_lineprog, comp_dir)
        
        self.assertEqual(result, "/home/user/project/main.c")
    
    def test_resolve_file_path_dir_index_out_of_range(self):
        """Test resolving with directory index out of range."""
        mock_file_entry = Mock()
        mock_file_entry.name = "main.c"
        mock_file_entry.dir_index = 5  # Out of range
        
        mock_lineprog = {"include_directory": [".", "include"]}
        comp_dir = "/home/user/project"
        
        result = self.analyzer._resolve_file_path(mock_file_entry, mock_lineprog, comp_dir)
        
        # Should fall back to comp_dir only
        self.assertEqual(result, "/home/user/project/main.c")
    
    def test_resolve_file_path_no_comp_dir(self):
        """Test resolving without compilation directory."""
        mock_file_entry = Mock()
        mock_file_entry.name = "main.c"
        mock_file_entry.dir_index = 0
        
        mock_lineprog = Mock()
        comp_dir = ""
        
        result = self.analyzer._resolve_file_path(mock_file_entry, mock_lineprog, comp_dir)
        
        self.assertEqual(result, "main.c")
    
    def test_resolve_file_path_exception_handling(self):
        """Test file path resolution with exception."""
        mock_file_entry = Mock()
        mock_file_entry.name = Mock(side_effect=RuntimeError("Access error"))
        
        mock_lineprog = Mock()
        comp_dir = "/home/user"
        
        result = self.analyzer._resolve_file_path(mock_file_entry, mock_lineprog, comp_dir)
        
        self.assertIsNone(result)


class TestELFAnalyzerValidation(unittest.TestCase):
    """Test ELF file validation functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.analyzer = ELFAnalyzer(verbose=False)
        
        # Create test ELF file
        self.test_elf_path = os.path.join(self.temp_dir, "test.elf")
        with open(self.test_elf_path, 'wb') as f:
            f.write(b'\x7fELF')
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_validate_elf_file_nonexistent(self):
        """Test validation of non-existent file."""
        non_existent_path = "/path/that/does/not/exist.elf"
        
        with self.assertRaises(ELFValidationError) as context:
            self.analyzer.validate_elf_file(non_existent_path)
        
        self.assertIn("ELF file does not exist", str(context.exception))
        self.assertIn(non_existent_path, str(context.exception))
    
    def test_validate_elf_file_import_error(self):
        """Test validation when elftools is not available."""
        # Patch the import inside the method
        with patch('builtins.__import__', side_effect=ImportError("No module named 'elftools'")):
            with patch('builtins.open', mock_open(read_data=b'\x7fELF')):
                with self.assertRaises(ELFValidationError) as context:
                    self.analyzer.validate_elf_file(self.test_elf_path)
                
                self.assertIn("elftools library not available", str(context.exception))
    
    @patch('elftools.elf.elffile.ELFFile')
    def test_validate_elf_file_invalid_header(self, mock_elf_file):
        """Test validation of ELF file with invalid header."""
        mock_elffile_instance = Mock()
        mock_elffile_instance.header = None
        mock_elf_file.return_value = mock_elffile_instance
        
        with patch('builtins.open', mock_open(read_data=b'\x7fELF')):
            with self.assertRaises(ELFValidationError) as context:
                self.analyzer.validate_elf_file(self.test_elf_path)
            
            self.assertIn("Invalid ELF header", str(context.exception))
    
    @patch('elftools.elf.elffile.ELFFile')
    def test_validate_elf_file_parsing_error(self, mock_elf_file):
        """Test validation with ELF parsing error."""
        mock_elf_file.side_effect = ValueError("Invalid ELF format")
        
        with patch('builtins.open', mock_open(read_data=b'\x7fELF')):
            with self.assertRaises(ELFValidationError) as context:
                self.analyzer.validate_elf_file(self.test_elf_path)
            
            self.assertIn("Invalid ELF file", str(context.exception))
            self.assertIn("Invalid ELF format", str(context.exception))
    
    @patch('elftools.elf.elffile.ELFFile')
    def test_validate_elf_file_success(self, mock_elf_file):
        """Test successful ELF file validation."""
        mock_elffile_instance = Mock()
        mock_elffile_instance.header = {"valid": "header"}
        mock_elf_file.return_value = mock_elffile_instance
        
        with patch('builtins.open', mock_open(read_data=b'\x7fELF')):
            result = self.analyzer.validate_elf_file(self.test_elf_path)
            
            self.assertTrue(result)
    
    def test_validate_elf_file_path_handling(self):
        """Test validation with different path types."""
        # Test with string path
        with patch('elftools.elf.elffile.ELFFile') as mock_elf_file:
            mock_elffile_instance = Mock()
            mock_elffile_instance.header = {"valid": "header"}
            mock_elf_file.return_value = mock_elffile_instance
            
            with patch('builtins.open', mock_open(read_data=b'\x7fELF')):
                result = self.analyzer.validate_elf_file(str(self.test_elf_path))
                self.assertTrue(result)
        
        # Test with Path object
        with patch('elftools.elf.elffile.ELFFile') as mock_elf_file:
            mock_elffile_instance = Mock()
            mock_elffile_instance.header = {"valid": "header"}
            mock_elf_file.return_value = mock_elffile_instance
            
            with patch('builtins.open', mock_open(read_data=b'\x7fELF')):
                result = self.analyzer.validate_elf_file(Path(self.test_elf_path))
                self.assertTrue(result)


class TestELFAnalyzerIntegration(unittest.TestCase):
    """Integration tests using real ELF files from resources."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.analyzer = ELFAnalyzer(verbose=False)
        self.resources_dir = Path(__file__).parent.parent / "resources"
        
        # Check if we have real ELF files for testing
        self.mandelbrot_elf = self.resources_dir / "mandelbrot_rv64_O0.elf"
        self.has_real_elf = self.mandelbrot_elf.exists()
    
    @unittest.skipIf(not Path(__file__).parent.parent.joinpath("resources/mandelbrot_rv64_O0.elf").exists(), 
                     "Real ELF file not available for integration testing")
    def test_validate_real_elf_file(self):
        """Test validation of real ELF file."""
        result = self.analyzer.validate_elf_file(self.mandelbrot_elf)
        self.assertTrue(result)
    
    @unittest.skipIf(not Path(__file__).parent.parent.joinpath("resources/mandelbrot_rv64_O0.elf").exists(), 
                     "Real ELF file not available for integration testing")
    def test_snapshot_real_elf_file(self):
        """Test source file extraction from real ELF file."""
        # This may return empty set if no DWARF info, but should not crash
        result = self.analyzer.snapshot_source_files(self.mandelbrot_elf)
        self.assertIsInstance(result, set)


if __name__ == '__main__':
    unittest.main()
