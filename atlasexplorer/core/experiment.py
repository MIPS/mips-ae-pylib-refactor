#!/usr/bin/env python3
"""
Experiment class for Atlas Explorer - Phase 1.2 Extraction

This module contains the Experiment class extracted from the monolithic atlasexplorer.py
with modern Python patterns, type safety, and dependency injection.
"""

import os
import sys
import json
import time
import uuid
import tarfile
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Union, TYPE_CHECKING

import requests

from ..utils.exceptions import (
    AtlasExplorerError,
    ELFValidationError,
    ExperimentError,
    EncryptionError,
    NetworkError
)
from ..security.encryption import SecureEncryption
from ..analysis.elf_parser import ELFAnalyzer
from ..analysis.reports import SummaryReport
from ..network.api_client import AtlasAPIClient
from ..core.constants import AtlasConstants

if TYPE_CHECKING:
    from .client import AtlasExplorer


class Experiment:
    """
    Manages Atlas Explorer experiment lifecycle including workload management,
    cloud execution, and result processing.
    
    This class handles:
    - Experiment configuration and directory management
    - Workload file validation and packaging
    - Cloud experiment execution with status monitoring
    - Result downloading and unpacking
    - Source file analysis from ELF binaries
    """
    
    def __init__(self, expdir: Union[str, Path], atlas: 'AtlasExplorer', verbose: bool = True):
        """
        Initialize experiment with directory and Atlas Explorer instance.
        
        Args:
            expdir: Directory path for experiment results
            atlas: AtlasExplorer instance for cloud communication
            verbose: Enable verbose logging output
            
        Raises:
            ExperimentError: If experiment directory cannot be created
        """
        self.verbose = verbose
        self.atlas = atlas
        
        # Setup experiment directory
        self.expdir = os.path.abspath(str(expdir))
        if not os.path.exists(self.expdir):
            try:
                os.mkdir(self.expdir)
            except OSError as e:
                raise ExperimentError(f"Cannot create experiment directory {self.expdir}: {e}")
        
        # Initialize experiment state
        self.config: Optional[Dict[str, Any]] = None
        self.summary: Optional[SummaryReport] = None
        self.instcounts: Optional[Any] = None
        self.insttrace: Optional[Any] = None
        self.workloads: List[str] = []
        self.core: Optional[str] = None
        self.expname: Optional[str] = None
        self.experiment_timestamp: Optional[str] = None
        self.unpack: bool = True
        
        # Initialize analysis components
        self.encryption = SecureEncryption()
        self.elf_analyzer = ELFAnalyzer()
        
        # Load existing experiment configuration if available
        self._load_config()
    
    def _load_config(self) -> None:
        """Load experiment configuration from config.json if it exists."""
        config_path = os.path.join(self.expdir, "config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    self.config = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                if self.verbose:
                    print(f"Warning: Could not load config from {config_path}: {e}")
    
    def getRoot(self) -> str:
        """
        Get the root directory of the experiment.
        
        Returns:
            Absolute path to experiment directory
        """
        return self.expdir
    
    def getSummary(self) -> Optional[SummaryReport]:
        """
        Get the summary report of the experiment.
        
        Returns:
            SummaryReport instance if available, None otherwise
        """
        if self.summary:
            return self.summary
        else:
            if self.verbose:
                print("No summary report found for this experiment.")
            return None
    
    def addWorkload(self, workload: Union[str, Path]) -> None:
        """
        Add a workload ELF file to the experiment.
        
        Args:
            workload: Path to ELF file
            
        Raises:
            ELFValidationError: If ELF file doesn't exist or is invalid
        """
        workload_path = Path(workload)
        
        # Validate ELF file exists
        if not workload_path.exists():
            raise ELFValidationError(f"ELF file does not exist: {workload_path}", workload_path)
        
        # Validate it's actually an ELF file
        try:
            self.elf_analyzer.validate_elf_file(workload_path)
        except Exception as e:
            raise ELFValidationError(f"Invalid ELF file {workload_path}: {e}", workload_path)
        
        self.workloads.append(str(workload_path))
        if self.verbose:
            print(f"Added workload: {workload_path}")
    
    def setCore(self, core: str) -> None:
        """
        Set the processor core for the experiment.
        
        Args:
            core: Core identifier (e.g., 'I8500', 'P8500')
            
        Raises:
            ExperimentError: If core is invalid
        """
        if not isinstance(core, str) or not core.strip():
            raise ExperimentError("Core must be a non-empty string")
        
        self.core = core.strip()
        if self.verbose:
            print(f"Core set to: {self.core}")
    
    def run(self, expname: Optional[str] = None, unpack: bool = True) -> None:
        """
        Execute the experiment on the cloud platform.
        
        Args:
            expname: Name for the experiment (auto-generated if None)
            unpack: Whether to unpack results after completion
            
        Raises:
            ExperimentError: If experiment execution fails
            NetworkError: If cloud communication fails
        """
        if not self.workloads:
            raise ExperimentError("No workloads added to experiment")
        
        if not self.core:
            raise ExperimentError("No core set for experiment")
        
        # Generate experiment metadata
        now = datetime.now()
        self.experiment_timestamp = now.strftime("%y%m%d_%H%M%S")
        
        if expname is None:
            expname = f"{self.core}_{self.experiment_timestamp}"
        
        self.expname = expname
        self.unpack = unpack
        
        if self.verbose:
            print(f"Creating experiment: {expname}")
        
        try:
            self._execute_experiment(now)
        except Exception as e:
            raise ExperimentError(f"Experiment execution failed: {e}")
    
    def _execute_experiment(self, timestamp: datetime) -> None:
        """Execute the full experiment workflow."""
        # Create experiment directory
        expdir = os.path.join(self.expdir, self.expname)
        os.mkdir(expdir)
        self.expdir = expdir
        
        # Generate experiment configuration
        config = self._create_experiment_config(timestamp)
        
        # Save configuration
        config_path = os.path.join(expdir, "config.json")
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        
        # Create and encrypt experiment package
        package_path = self._create_experiment_package(expdir, config)
        
        # Upload and execute on cloud
        self._execute_cloud_experiment(package_path, config)
        
        # Download and process results
        if self.unpack:
            self._download_and_unpack_results(config)
    
    def _create_experiment_config(self, timestamp: datetime) -> Dict[str, Any]:
        """Create experiment configuration dictionary."""
        expuuid = f"{self.experiment_timestamp}_{uuid.uuid4()}"
        
        if self.verbose:
            print(f"Experiment UUID: {expuuid}")
        
        # Get cloud capabilities and core info
        self.atlas._getCloudCaps(AtlasConstants.API_VERSION)
        versions = self.atlas.getVersionList()
        if self.verbose:
            print(f"Available versions: {', '.join(versions)}")
        
        arch_info = self.atlas.getCoreInfo(self.core)
        
        # Create workload objects
        workload_objs = [{"elf": wl, "zstf": ""} for wl in self.workloads]
        
        # Generate OTP for encryption
        otp = "".join([chr(x) for x in os.urandom(32)])
        
        config = {
            "date": timestamp.strftime("%y%m%d_%H%M%S"),
            "name": self.expname,
            "core": self.core,
            "workload": workload_objs,
            "uuid": expuuid,
            "toolsVersion": "latest",
            "timeout": 300,
            "pluginVersion": AtlasConstants.API_VERSION,
            "compiler": "",
            "compilerFlags": "",
            "numRegions": 0,
            "reports": [],
            "heartbeat": "104723",
            "iss": "esesc",
            "apikey": self.atlas.config.apikey,
            "geolocation": {},
            "otp": otp,
            "version": "1.0.0",
            "arch": arch_info,
            "clientType": "python",
        }
        
        # Add reports configuration
        self._add_reports_to_config(config, workload_objs)
        
        return config
    
    def _add_reports_to_config(self, config: Dict[str, Any], workload_objs: List[Dict[str, str]]) -> None:
        """Add report configurations to experiment config."""
        # Summary report
        summary_report = self._create_report_config("summary", "", config, "", "")
        config["reports"].append(summary_report)
        
        # Individual workload reports
        for wl_obj in workload_objs:
            elf_name = os.path.basename(wl_obj["elf"])
            zstf_name = wl_obj["zstf"] or f"{elf_name}.zstf"
            
            # Remove .elf extension for base name
            elf_base = elf_name[:-4] if elf_name.lower().endswith(".elf") else elf_name
            
            # Instruction counts report
            inst_count_report = self._create_report_config(
                "inst_counts",
                f"{elf_base}_Instruction_Counts",
                config,
                elf_name,
                zstf_name
            )
            config["reports"].append(inst_count_report)
            
            # Instruction trace report
            inst_trace_report = self._create_report_config(
                "inst_trace",
                f"{elf_base}_Instruction_Trace",
                config,
                elf_name,
                zstf_name
            )
            config["reports"].append(inst_trace_report)
    
    def _create_report_config(self, report_type: str, report_name: str, 
                            exp_config: Dict[str, Any], elf_name: str, 
                            zstf_name: str) -> Dict[str, Any]:
        """Create configuration for a specific report."""
        if self.verbose:
            print(f"Creating report: {report_type}")
        
        report_uuid = f"{self.experiment_timestamp}_{uuid.uuid4()}"
        
        return {
            "startDate": self.experiment_timestamp,
            "reportUUID": report_uuid,
            "expUUID": exp_config["uuid"],
            "core": exp_config["core"],
            "elfFileName": elf_name,
            "zstfFileName": zstf_name,
            "reportName": report_name,
            "reportType": report_type,
            "userParameters": [],
            "startInst": 1,
            "endInst": -1,
            "resolution": 1,
            "toolsVersion": "latest",
            "timeout": 300,
            "pluginVersion": AtlasConstants.API_VERSION,
            "isROIReport": False,
            "region": 0,
        }
    
    def _create_experiment_package(self, expdir: str, config: Dict[str, Any]) -> str:
        """Create and encrypt experiment package."""
        package_path = os.path.join(expdir, "workload.exp")
        
        # Create tar.gz package
        with tarfile.open(package_path, "w:gz") as tar:
            # Add config file
            tar.add(os.path.join(expdir, "config.json"), arcname="config.json")
            
            # Add workload files
            for wl in self.workloads:
                if os.path.exists(wl):
                    tar.add(wl, arcname=os.path.basename(wl))
                else:
                    raise ExperimentError(f"Workload file does not exist: {wl}")
        
        return package_path
    
    def _execute_cloud_experiment(self, package_path: str, config: Dict[str, Any]) -> None:
        """Execute experiment on cloud platform."""
        # Get signed URLs from cloud
        resp = self.atlas.getSignedUrls(config["uuid"], self.expname, self.core)
        resp_data = resp.json()
        
        package_url = resp_data["exppackageurl"]
        public_key = resp_data["publicKey"]
        status_url = resp_data["statusget"]
        
        # Encrypt package
        self.encryption.hybrid_encrypt_file(public_key, Path(package_path))
        
        # Upload package
        self._upload_package(package_url, package_path)
        
        # Monitor experiment status
        self._monitor_experiment_status(status_url, config)
    
    def _upload_package(self, url: str, package_path: str) -> None:
        """Upload experiment package to cloud."""
        if self.verbose:
            print("Uploading experiment package")
        
        headers = {
            "Content-Type": "application/octet-stream",
            "Content-Length": str(os.path.getsize(package_path)),
        }
        
        try:
            with open(package_path, "rb") as data:
                resp = requests.put(url, data=data, headers=headers)
                resp.raise_for_status()
        except Exception as e:
            raise NetworkError(f"Failed to upload experiment package: {e}")
    
    def _monitor_experiment_status(self, status_url: str, config: Dict[str, Any]) -> None:
        """Monitor experiment execution status."""
        count = 0
        max_retries = 10
        
        while count < max_retries:
            count += 1
            time.sleep(2)
            
            try:
                response = requests.get(status_url)
                response.raise_for_status()
                status = response.json()
                
                if status["code"] == 100:
                    if self.verbose:
                        print("Experiment is being generated...")
                elif status["code"] == 200:
                    if self.verbose:
                        print("Experiment is ready, downloading now")
                    
                    # Download results
                    result = status["metadata"]["result"]
                    result_url = result["url"]
                    
                    if result["type"] == "stream":
                        self._download_result_file(result_url, f"{self.expname}.tar.gz")
                    break
                elif status["code"] == 404:
                    raise ExperimentError("Experiment not found on server")
                elif status["code"] == 500:
                    raise ExperimentError("Server error during experiment generation")
                    
            except requests.RequestException as e:
                raise NetworkError(f"Failed to check experiment status: {e}")
        
        if count >= max_retries:
            raise ExperimentError("Experiment status monitoring timed out")
    
    def _download_result_file(self, url: str, filename: str) -> None:
        """Download result file from cloud."""
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            file_path = os.path.join(self.expdir, filename)
            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024):
                    f.write(chunk)
                    
        except requests.RequestException as e:
            raise NetworkError(f"Failed to download result file: {e}")
    
    def _download_and_unpack_results(self, config: Dict[str, Any]) -> None:
        """Download and unpack experiment results."""
        if self.verbose:
            print("Preparing download")
        
        result_file = os.path.join(self.expdir, f"{self.expname}.tar.gz")
        
        if os.path.exists(result_file):
            # Decrypt with OTP
            if self.verbose:
                print("Decrypting package")
            
            try:
                self.encryption.decrypt_file_with_password(result_file, config["otp"])
            except Exception as e:
                raise EncryptionError(f"Failed to decrypt result package: {e}")
            
            # Unpack
            if self.verbose:
                print("Unpacking package")
            
            try:
                with tarfile.open(result_file, "r:gz") as tar:
                    tar.extractall(self.expdir, filter='tar')
            except Exception as e:
                raise ExperimentError(f"Failed to unpack results: {e}")
            
            # Clean up invalid summary files
            self._clean_summaries("summary")
            
            # Load summary report
            summary_path = os.path.join(
                self.expdir, self.expname, "reports", "summary", "summary.json"
            )
            if os.path.exists(summary_path):
                self.summary = SummaryReport(summary_path)
            
            # Clean up temporary files
            workload_tar = os.path.join(self.expdir, "workload.exp")
            if os.path.exists(workload_tar):
                os.remove(workload_tar)
            
            # Analyze source files from ELF binaries
            for wl_config in config["workload"]:
                elf_path = wl_config.get("elf")
                if elf_path and os.path.exists(elf_path):
                    self.elf_analyzer.snapshot_source_files(Path(elf_path), verbose=self.verbose)
        else:
            raise ExperimentError(f"Result package not found: {result_file}")
    
    def _clean_summaries(self, report_type: str) -> None:
        """Clean up invalid summary reports."""
        if not hasattr(self, "expdir"):
            if self.verbose:
                print("No experiment directory set")
            return
        
        summary_dir = os.path.join(self.expdir, "reports", report_type)
        if not os.path.exists(summary_dir):
            if self.verbose:
                print(f"No report directory found: {report_type}")
            return
        
        for filename in os.listdir(summary_dir):
            if "_roi_" in filename and filename.endswith(".json"):
                filepath = os.path.join(summary_dir, filename)
                try:
                    summary_report = SummaryReport(filepath)
                    if summary_report.totalcycles == 0 and summary_report.totalinsts == 0:
                        if self.verbose:
                            print(f"Deleting invalid ROI report: {filepath}")
                        os.remove(filepath)
                except Exception as e:
                    if self.verbose:
                        print(f"Error processing summary file {filepath}: {e}")
    
    def getExperiment(self, expdir: Union[str, Path], atlas: Optional['AtlasExplorer'] = None, 
                     verbose: bool = True) -> 'Experiment':
        """
        Create an Experiment object for an existing experiment directory.
        
        Args:
            expdir: Path to experiment directory
            atlas: AtlasExplorer instance (uses self.atlas if None)
            verbose: Enable verbose output
            
        Returns:
            New Experiment instance
            
        Raises:
            ExperimentError: If experiment directory doesn't exist
        """
        if not os.path.exists(expdir):
            raise ExperimentError(f"Experiment directory does not exist: {expdir}")
        
        # Use self.atlas if not provided
        if atlas is None:
            atlas = self.atlas
        
        return Experiment(expdir, atlas, verbose=verbose)
    
    def snapshotSource(self, elf_path: Union[str, Path]) -> set:
        """
        Extract source file paths from ELF DWARF debug information.
        
        Args:
            elf_path: Path to ELF file
            
        Returns:
            Set of source file paths found in ELF
            
        Note:
            This method is deprecated. Use ELFAnalyzer.snapshot_source_files() instead.
        """
        import warnings
        warnings.warn(
            "snapshotSource is deprecated. Use ELFAnalyzer.snapshot_source_files() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        return self.elf_analyzer.snapshot_source_files(Path(elf_path), verbose=self.verbose)
