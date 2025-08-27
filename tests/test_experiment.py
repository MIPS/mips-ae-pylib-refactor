#!/usr/bin/env python3
"""
Unit tests for the modular Experiment class.

Tests the new Experiment class extracted in Phase 1.2 to ensure
it maintains functionality while providing better architecture.
"""

import unittest
import tempfile
import os
import json
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

from atlasexplorer.core.experiment import Experiment
from atlasexplorer.core.client import AtlasExplorer
from atlasexplorer.utils.exceptions import (
    ExperimentError,
    ELFValidationError,
    ConfigurationError
)


class TestExperiment(unittest.TestCase):
    """Test cases for the Experiment class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.mock_atlas = Mock(spec=AtlasExplorer)
        
        # Set up config mock
        self.mock_config = Mock()
        self.mock_config.apikey = "test-api-key"
        self.mock_atlas.config = self.mock_config
        
        # Set up mock methods
        self.mock_atlas._getCloudCaps = Mock()
        self.mock_atlas.getVersionList = Mock(return_value=["0.0.97"])
        self.mock_atlas.getCoreInfo = Mock(return_value={"name": "I8500", "num_threads": 1})
        self.mock_atlas.getSignedUrls = Mock()
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_experiment_initialization(self):
        """Test experiment initialization."""
        experiment = Experiment(self.temp_dir, self.mock_atlas, verbose=False)
        
        self.assertEqual(experiment.expdir, os.path.abspath(self.temp_dir))
        self.assertEqual(experiment.atlas, self.mock_atlas)
        self.assertFalse(experiment.verbose)
        self.assertEqual(experiment.workloads, [])
        self.assertIsNone(experiment.core)
    
    def test_experiment_directory_creation(self):
        """Test that experiment directory is created if it doesn't exist."""
        non_existent_dir = os.path.join(self.temp_dir, "new_experiment")
        self.assertFalse(os.path.exists(non_existent_dir))
        
        experiment = Experiment(non_existent_dir, self.mock_atlas, verbose=False)
        
        self.assertTrue(os.path.exists(non_existent_dir))
        self.assertEqual(experiment.expdir, os.path.abspath(non_existent_dir))
    
    def test_load_existing_config(self):
        """Test loading existing experiment configuration."""
        config_data = {
            "name": "test_experiment",
            "core": "I8500",
            "uuid": "test-uuid"
        }
        
        config_path = os.path.join(self.temp_dir, "config.json")
        with open(config_path, 'w') as f:
            json.dump(config_data, f)
        
        experiment = Experiment(self.temp_dir, self.mock_atlas, verbose=False)
        
        self.assertEqual(experiment.config, config_data)
    
    def test_get_root(self):
        """Test getRoot method."""
        experiment = Experiment(self.temp_dir, self.mock_atlas, verbose=False)
        self.assertEqual(experiment.getRoot(), os.path.abspath(self.temp_dir))
    
    def test_set_core(self):
        """Test setCore method."""
        experiment = Experiment(self.temp_dir, self.mock_atlas, verbose=False)
        
        experiment.setCore("I8500")
        self.assertEqual(experiment.core, "I8500")
        
        # Test with whitespace
        experiment.setCore("  P8500  ")
        self.assertEqual(experiment.core, "P8500")
    
    def test_set_core_invalid(self):
        """Test setCore with invalid input."""
        experiment = Experiment(self.temp_dir, self.mock_atlas, verbose=False)
        
        with self.assertRaises(ExperimentError):
            experiment.setCore("")
        
        with self.assertRaises(ExperimentError):
            experiment.setCore(None)
    
    @patch('atlasexplorer.core.experiment.Path')
    def test_add_workload_valid_elf(self, mock_path):
        """Test adding a valid ELF workload."""
        experiment = Experiment(self.temp_dir, self.mock_atlas, verbose=False)
        
        # Mock path operations
        mock_elf_path = Mock()
        mock_elf_path.exists.return_value = True
        mock_path.return_value = mock_elf_path
        
        # Mock ELF validation
        experiment.elf_analyzer.validate_elf_file = Mock()
        
        test_elf = "/path/to/test.elf"
        experiment.addWorkload(test_elf)
        
        self.assertIn(str(mock_elf_path), experiment.workloads)
        experiment.elf_analyzer.validate_elf_file.assert_called_once()
    
    @patch('atlasexplorer.core.experiment.Path')
    def test_add_workload_nonexistent_file(self, mock_path):
        """Test adding a non-existent workload file."""
        experiment = Experiment(self.temp_dir, self.mock_atlas, verbose=False)
        
        mock_elf_path = Mock()
        mock_elf_path.exists.return_value = False
        mock_path.return_value = mock_elf_path
        
        with self.assertRaises(ELFValidationError):
            experiment.addWorkload("/nonexistent/file.elf")
    
    def test_run_without_workloads(self):
        """Test running experiment without workloads."""
        experiment = Experiment(self.temp_dir, self.mock_atlas, verbose=False)
        experiment.setCore("I8500")
        
        with self.assertRaises(ExperimentError) as context:
            experiment.run()
        
        self.assertIn("No workloads", str(context.exception))
    
    def test_run_without_core(self):
        """Test running experiment without setting core."""
        experiment = Experiment(self.temp_dir, self.mock_atlas, verbose=False)
        experiment.workloads = ["/path/to/test.elf"]
        
        with self.assertRaises(ExperimentError) as context:
            experiment.run()
        
        self.assertIn("No core set", str(context.exception))
    
    @patch('atlasexplorer.core.experiment.datetime')
    def test_experiment_name_generation(self, mock_datetime):
        """Test automatic experiment name generation."""
        experiment = Experiment(self.temp_dir, self.mock_atlas, verbose=False)
        experiment.setCore("I8500")
        experiment.workloads = ["/path/to/test.elf"]
        
        # Mock datetime
        mock_now = Mock()
        mock_now.strftime.return_value = "250827_123456"
        mock_datetime.now.return_value = mock_now
        
        # Mock other dependencies to prevent actual execution
        with patch.object(experiment, '_execute_experiment') as mock_execute:
            experiment.run()
            
            self.assertEqual(experiment.expname, "I8500_250827_123456")
            self.assertEqual(experiment.experiment_timestamp, "250827_123456")
            mock_execute.assert_called_once()
    
    def test_get_experiment(self):
        """Test getExperiment method."""
        experiment = Experiment(self.temp_dir, self.mock_atlas, verbose=False)
        
        # Create a subdirectory for the sub-experiment
        sub_exp_dir = os.path.join(self.temp_dir, "sub_experiment")
        os.makedirs(sub_exp_dir)
        
        sub_experiment = experiment.getExperiment(sub_exp_dir)
        
        self.assertIsInstance(sub_experiment, Experiment)
        self.assertEqual(sub_experiment.expdir, os.path.abspath(sub_exp_dir))
        self.assertEqual(sub_experiment.atlas, self.mock_atlas)
    
    def test_get_experiment_nonexistent(self):
        """Test getExperiment with non-existent directory."""
        experiment = Experiment(self.temp_dir, self.mock_atlas, verbose=False)
        
        with self.assertRaises(ExperimentError):
            experiment.getExperiment("/nonexistent/directory")
    
    def test_get_summary_no_summary(self):
        """Test getSummary when no summary is available."""
        experiment = Experiment(self.temp_dir, self.mock_atlas, verbose=False)
        
        result = experiment.getSummary()
        self.assertIsNone(result)
    
    def test_get_summary_with_summary(self):
        """Test getSummary when summary is available."""
        experiment = Experiment(self.temp_dir, self.mock_atlas, verbose=False)
        
        mock_summary = Mock()
        experiment.summary = mock_summary
        
        result = experiment.getSummary()
        self.assertEqual(result, mock_summary)


class TestExperimentWorkflow(unittest.TestCase):
    """Integration tests for experiment workflow."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.mock_atlas = Mock(spec=AtlasExplorer)
        
        # Set up config mock  
        self.mock_config = Mock()
        self.mock_config.apikey = "test-api-key"
        self.mock_atlas.config = self.mock_config
        
        # Configure mock methods
        self.mock_atlas._getCloudCaps = Mock()
        self.mock_atlas.getVersionList = Mock(return_value=["0.0.97"])
        self.mock_atlas.getCoreInfo = Mock(return_value={
            "name": "I8500",
            "num_threads": 1,
            "arch": "riscv64"
        })
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('atlasexplorer.core.experiment.uuid')
    @patch('atlasexplorer.core.experiment.datetime')
    def test_create_experiment_config(self, mock_datetime, mock_uuid):
        """Test experiment configuration creation."""
        experiment = Experiment(self.temp_dir, self.mock_atlas, verbose=False)
        experiment.setCore("I8500")
        experiment.workloads = ["/path/to/test.elf"]
        
        # Mock datetime and UUID
        mock_now = Mock()
        mock_now.strftime.return_value = "250827_123456"
        mock_datetime.now.return_value = mock_now
        mock_uuid.uuid4.return_value = "mock-uuid-1234"
        
        # Set up experiment state
        experiment.experiment_timestamp = "250827_123456"
        experiment.expname = "test_experiment"
        
        # Test config creation (private method, so we test the behavior indirectly)
        with patch.object(experiment, '_execute_cloud_experiment') as mock_cloud_execute, \
             patch.object(experiment, '_download_and_unpack_results') as mock_download, \
             patch.object(experiment, '_create_experiment_package') as mock_package, \
             patch('atlasexplorer.core.experiment.os.mkdir') as mock_mkdir, \
             patch('builtins.open', mock_open()) as mock_file:
            
            mock_package.return_value = "/path/to/mock/package.tar.gz"
            
            experiment.run(expname="test_experiment")
            
            # Verify atlas methods were called
            self.mock_atlas._getCloudCaps.assert_called_once_with("0.0.97")
            self.mock_atlas.getVersionList.assert_called_once()
            self.mock_atlas.getCoreInfo.assert_called_once_with("I8500")


if __name__ == '__main__':
    unittest.main()
