"""ELF file analysis and source code extraction.

This module provides functionality to analyze ELF files, extract DWARF debug
information, and identify source files used in compilation.
"""

import os
from pathlib import Path
from typing import Set, Union, Optional

from ..utils.exceptions import ELFValidationError


class ELFAnalyzer:
    """Analyzes ELF files and extracts debug information.
    
    This class provides functionality to:
    - Validate ELF file format
    - Extract DWARF debug information
    - Identify source files used in compilation
    - Parse compilation units and line programs
    """
    
    def __init__(self, verbose: bool = True):
        """Initialize the ELF analyzer.
        
        Args:
            verbose: Enable verbose logging
        """
        self.verbose = verbose
    
    def snapshot_source_files(self, elf_path: Union[str, Path]) -> Set[str]:
        """Extract source file paths from ELF debug information.
        
        This method analyzes DWARF debug information in the ELF file to identify
        all source files that were used during compilation.
        
        Args:
            elf_path: Path to ELF file to analyze
            
        Returns:
            Set of absolute paths to source files that exist on the filesystem
            
        Raises:
            ELFValidationError: If ELF file is invalid or cannot be processed
        """
        elf_path = Path(elf_path)
        
        if not elf_path or not elf_path.exists():
            if self.verbose:
                print(f"ELF path does not exist: {elf_path}")
            return set()
        
        source_files: Set[str] = set()
        
        try:
            from elftools.elf.elffile import ELFFile
            
            with open(elf_path, "rb") as f:
                elffile = ELFFile(f)
                
                if not elffile.has_dwarf_info():
                    if self.verbose:
                        print(f"ELF file has no DWARF debug information: {elf_path}")
                    return set()
                
                dwarfinfo = elffile.get_dwarf_info()
                
                for compilation_unit in dwarfinfo.iter_CUs():
                    source_files.update(self._extract_sources_from_cu(compilation_unit, elf_path))
                    
        except ImportError:
            raise ELFValidationError("elftools library not available for ELF analysis")
        except Exception as e:
            if self.verbose:
                print(f"Warning: Error reading ELF file {elf_path}: {e}")
            return set()
        
        # Filter for existing files only
        existing_source_files = set()
        if self.verbose:
            print("Embedded source files in ELF:")
            
        for src in sorted(source_files):
            if Path(src).exists():
                existing_source_files.add(src)
                if self.verbose:
                    print(f"  {src}")
        
        return existing_source_files
    
    def _extract_sources_from_cu(self, compilation_unit, elf_path: Path) -> Set[str]:
        """Extract source files from a single compilation unit.
        
        Args:
            compilation_unit: DWARF compilation unit
            elf_path: Path to ELF file (for error reporting)
            
        Returns:
            Set of source file paths from this compilation unit
        """
        source_files: Set[str] = set()
        
        try:
            # Get compilation directory from the compilation unit
            comp_dir = ""
            top_die = compilation_unit.get_top_DIE()
            if "DW_AT_comp_dir" in top_die.attributes:
                comp_dir = top_die.attributes["DW_AT_comp_dir"].value
                if isinstance(comp_dir, bytes):
                    comp_dir = comp_dir.decode("utf-8")
            
            # Get line program for this compilation unit
            dwarfinfo = compilation_unit.dwarfinfo
            lineprog = dwarfinfo.line_program_for_CU(compilation_unit)
            if lineprog is None:
                return source_files
            
            # Extract file entries from line program
            for file_entry in lineprog["file_entry"]:
                try:
                    full_path = self._resolve_file_path(file_entry, lineprog, comp_dir)
                    if full_path:
                        source_files.add(full_path)
                except Exception as e:
                    if self.verbose:
                        print(f"Warning: Error processing file entry in ELF {elf_path}: {e}")
                    continue
                    
        except Exception as e:
            if self.verbose:
                print(f"Warning: Error processing compilation unit in ELF {elf_path}: {e}")
        
        return source_files
    
    def _resolve_file_path(self, file_entry, lineprog, comp_dir: str) -> Optional[str]:
        """Resolve the full path for a file entry.
        
        Args:
            file_entry: DWARF file entry
            lineprog: DWARF line program
            comp_dir: Compilation directory
            
        Returns:
            Resolved absolute file path, or None if resolution fails
        """
        try:
            # Get filename
            filename = file_entry.name
            if isinstance(filename, bytes):
                filename = filename.decode("utf-8")
            
            # Get directory index and resolve directory
            dir_index = getattr(file_entry, "dir_index", 0)
            directory = ""
            
            if dir_index > 0 and "include_directory" in lineprog:
                include_dirs = lineprog["include_directory"]
                if dir_index <= len(include_dirs):
                    # Build directory by appending include_directory entries up to dir_index
                    directory_parts = []
                    try:
                        for i in range(dir_index + 1):
                            if i < len(include_dirs):
                                dir_part = include_dirs[i]
                                if isinstance(dir_part, bytes):
                                    dir_part = dir_part.decode("utf-8")
                                directory_parts.append(dir_part)
                        directory = os.path.join(*directory_parts) if directory_parts else ""
                    except (IndexError, ValueError):
                        directory = ""
                    
                    if isinstance(directory, bytes):
                        directory = directory.decode("utf-8")
            
            # Build full path
            if directory:
                if os.path.isabs(directory):
                    full_path = os.path.join(directory, filename)
                elif comp_dir:
                    full_path = os.path.join(comp_dir, directory, filename)
                else:
                    full_path = os.path.join(directory, filename)
            elif comp_dir:
                full_path = os.path.join(comp_dir, filename)
            else:
                full_path = filename
            
            return full_path
            
        except Exception:
            return None
    
    def validate_elf_file(self, elf_path: Union[str, Path]) -> bool:
        """Validate that a file is a proper ELF file.
        
        Args:
            elf_path: Path to file to validate
            
        Returns:
            True if file is a valid ELF file
            
        Raises:
            ELFValidationError: If file is not a valid ELF file
        """
        elf_path = Path(elf_path)
        
        if not elf_path.exists():
            raise ELFValidationError(f"ELF file does not exist: {elf_path}", str(elf_path))
        
        try:
            from elftools.elf.elffile import ELFFile
            
            with open(elf_path, "rb") as f:
                # Try to parse as ELF file
                elffile = ELFFile(f)
                
                # Basic validation
                if not elffile.header:
                    raise ELFValidationError(f"Invalid ELF header: {elf_path}", str(elf_path))
                
                return True
                
        except ImportError:
            raise ELFValidationError("elftools library not available for ELF validation")
        except Exception as e:
            raise ELFValidationError(f"Invalid ELF file {elf_path}: {e}", str(elf_path))
