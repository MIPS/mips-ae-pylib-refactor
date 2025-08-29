#!/usr/bin/env python3
"""
Comprehensive unit tests for the Reports module.

Tests the SummaryReport class to achieve 90%+ coverage using proven patterns
from the successful experiment module enhancement.
"""

import json
import tempfile
import shutil
import unittest
import locale
from pathlib import Path
from unittest.mock import Mock, patch, mock_open, MagicMock

from atlasexplorer.analysis.reports import SummaryReport
from atlasexplorer.utils.exceptions import ExperimentError


class TestSummaryReport(unittest.TestCase):
    """Test cases for the SummaryReport class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create valid test report data
        self.valid_report_data = {
            "Statistics": {
                "Summary Performance Report": {
                    "Total Cycles Consumed": {"val": 253627},
                    "Total Instructions Retired": {"val": 196626},
                    "IPC": {"val": 0.775},
                    "L1 Instruction Cache Hit Rate": {"val": 99.96, "unit": "%"},
                    "L1 Data Cache Hit Rate": {"val": 99.86, "unit": "%"},
                    "Branch Mispredictions per 1K Instructions": {"val": 0.73},
                    "ordered_keys": ["should_be_removed"]
                }
            }
        }
        
        # Create multicore report data
        self.multicore_report_data = {
            "Statistics": {
                "Summary Performance Report": {
                    "Total Cycles Consumed": {"val": 257648},
                    "Total Instructions Retired (All Threads)": {"val": 393252},
                    "Thread 0 Instructions": {"val": 196626},
                    "Thread 1 Instructions": {"val": 196626}
                }
            }
        }
        
        # Create test JSON file
        self.test_report_path = Path(self.temp_dir) / "test_report.json"
        with open(self.test_report_path, 'w') as f:
            json.dump(self.valid_report_data, f)
        
        # Create multicore test file
        self.multicore_report_path = Path(self.temp_dir) / "multicore_report.json"
        with open(self.multicore_report_path, 'w') as f:
            json.dump(self.multicore_report_data, f)
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_summary_report_initialization_success(self):
        """Test successful SummaryReport initialization."""
        report = SummaryReport(self.test_report_path)
        
        self.assertEqual(report.json_file, self.test_report_path)
        self.assertEqual(report.totalcycles, 253627)
        self.assertEqual(report.totalinsts, 196626)
        self.assertIsInstance(report.summarydata, dict)
        
        # Verify ordered_keys was removed
        self.assertNotIn("ordered_keys", report.summarydata)
    
    def test_summary_report_initialization_multicore(self):
        """Test SummaryReport initialization with multicore data."""
        report = SummaryReport(self.multicore_report_path)
        
        self.assertEqual(report.totalcycles, 257648)
        self.assertEqual(report.totalinsts, 393252)  # Uses "All Threads" metric
    
    def test_summary_report_nonexistent_file(self):
        """Test SummaryReport initialization with non-existent file."""
        non_existent_path = Path(self.temp_dir) / "nonexistent.json"
        
        with self.assertRaises(ExperimentError) as context:
            SummaryReport(non_existent_path)
        
        self.assertIn("Summary report file does not exist", str(context.exception))
    
    def test_summary_report_invalid_json(self):
        """Test SummaryReport initialization with invalid JSON."""
        invalid_json_path = Path(self.temp_dir) / "invalid.json"
        with open(invalid_json_path, 'w') as f:
            f.write("{ invalid json content")
        
        with self.assertRaises(ExperimentError) as context:
            SummaryReport(invalid_json_path)
        
        self.assertIn("Invalid JSON in summary report", str(context.exception))
    
    def test_summary_report_missing_statistics_section(self):
        """Test SummaryReport initialization with missing Statistics section."""
        invalid_data = {"Other": "data"}
        invalid_path = Path(self.temp_dir) / "no_stats.json"
        with open(invalid_path, 'w') as f:
            json.dump(invalid_data, f)
        
        with self.assertRaises(ExperimentError) as context:
            SummaryReport(invalid_path)
        
        self.assertIn("Invalid summary report format", str(context.exception))
    
    def test_summary_report_missing_summary_performance_section(self):
        """Test SummaryReport initialization with missing Summary Performance Report section."""
        invalid_data = {"Statistics": {"Other": "data"}}
        invalid_path = Path(self.temp_dir) / "no_summary.json"
        with open(invalid_path, 'w') as f:
            json.dump(invalid_data, f)
        
        with self.assertRaises(ExperimentError) as context:
            SummaryReport(invalid_path)
        
        self.assertIn("Invalid summary report format", str(context.exception))
    
    def test_summary_report_missing_total_cycles(self):
        """Test SummaryReport initialization with missing Total Cycles metric."""
        invalid_data = {
            "Statistics": {
                "Summary Performance Report": {
                    "Total Instructions Retired": {"val": 196626}
                }
            }
        }
        invalid_path = Path(self.temp_dir) / "no_cycles.json"
        with open(invalid_path, 'w') as f:
            json.dump(invalid_data, f)
        
        with self.assertRaises(ExperimentError) as context:
            SummaryReport(invalid_path)
        
        self.assertIn("Summary report missing 'Total Cycles Consumed' metric", str(context.exception))
    
    def test_summary_report_missing_instructions(self):
        """Test SummaryReport initialization with missing instruction metrics."""
        invalid_data = {
            "Statistics": {
                "Summary Performance Report": {
                    "Total Cycles Consumed": {"val": 253627}
                }
            }
        }
        invalid_path = Path(self.temp_dir) / "no_instructions.json"
        with open(invalid_path, 'w') as f:
            json.dump(invalid_data, f)
        
        with self.assertRaises(ExperimentError) as context:
            SummaryReport(invalid_path)
        
        self.assertIn("Summary report missing instruction count metrics", str(context.exception))
    
    def test_summary_report_general_loading_error(self):
        """Test SummaryReport initialization with general loading error."""
        with patch('builtins.open', side_effect=IOError("Permission denied")):
            with self.assertRaises(ExperimentError) as context:
                SummaryReport(self.test_report_path)
            
            self.assertIn("Error loading summary report", str(context.exception))
    
    def test_get_total_cycles(self):
        """Test get_total_cycles method."""
        report = SummaryReport(self.test_report_path)
        cycles = report.get_total_cycles()
        
        self.assertEqual(cycles, 253627)
        self.assertIsInstance(cycles, int)
    
    def test_get_total_instructions(self):
        """Test get_total_instructions method."""
        report = SummaryReport(self.test_report_path)
        instructions = report.get_total_instructions()
        
        self.assertEqual(instructions, 196626)
        self.assertIsInstance(instructions, int)
    
    def test_get_ipc(self):
        """Test get_ipc method."""
        report = SummaryReport(self.test_report_path)
        ipc = report.get_ipc()
        
        expected_ipc = 196626 / 253627
        self.assertAlmostEqual(ipc, expected_ipc, places=6)
    
    def test_get_ipc_zero_cycles(self):
        """Test get_ipc method with zero cycles."""
        # Create report with zero cycles
        zero_cycles_data = {
            "Statistics": {
                "Summary Performance Report": {
                    "Total Cycles Consumed": {"val": 0},
                    "Total Instructions Retired": {"val": 100}
                }
            }
        }
        zero_cycles_path = Path(self.temp_dir) / "zero_cycles.json"
        with open(zero_cycles_path, 'w') as f:
            json.dump(zero_cycles_data, f)
        
        report = SummaryReport(zero_cycles_path)
        ipc = report.get_ipc()
        
        self.assertEqual(ipc, 0.0)


class TestSummaryReportMetricAccess(unittest.TestCase):
    """Test metric access and filtering functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create comprehensive test report data
        self.comprehensive_report_data = {
            "Statistics": {
                "Summary Performance Report": {
                    "Total Cycles Consumed": {"val": 253627},
                    "Total Instructions Retired": {"val": 196626},
                    "L1 Instruction Cache Hit Rate": {"val": 99.96, "unit": "%"},
                    "L1 Data Cache Hit Rate": {"val": 99.86, "unit": "%"},
                    "L2 Cache Hit Rate": {"val": 98.5, "unit": "%"},
                    "Branch Prediction Accuracy": {"val": 99.27, "unit": "%"},
                    "Branch Mispredictions per 1K Instructions": {"val": 0.73},
                    "ALU Utilization": {"val": 45.2, "unit": "%"},
                    "FPU Utilization": {"val": 12.8, "unit": "%"},
                    "Memory Bandwidth": {"val": 1024, "unit": "MB/s"}
                }
            }
        }
        
        self.test_report_path = Path(self.temp_dir) / "comprehensive_report.json"
        with open(self.test_report_path, 'w') as f:
            json.dump(self.comprehensive_report_data, f)
        
        self.report = SummaryReport(self.test_report_path)
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_get_metric_keys_all(self):
        """Test getting all metric keys."""
        keys = self.report.get_metric_keys()
        
        expected_keys = [
            "Total Cycles Consumed",
            "Total Instructions Retired", 
            "L1 Instruction Cache Hit Rate",
            "L1 Data Cache Hit Rate",
            "L2 Cache Hit Rate",
            "Branch Prediction Accuracy",
            "Branch Mispredictions per 1K Instructions",
            "ALU Utilization",
            "FPU Utilization",
            "Memory Bandwidth"
        ]
        
        self.assertEqual(set(keys), set(expected_keys))
    
    def test_get_metric_keys_regex_filter(self):
        """Test getting metric keys with regex filter."""
        # Test cache-related metrics
        cache_keys = self.report.get_metric_keys(r".*[Cc]ache.*")
        expected_cache_keys = [
            "L1 Instruction Cache Hit Rate",
            "L1 Data Cache Hit Rate", 
            "L2 Cache Hit Rate"
        ]
        self.assertEqual(set(cache_keys), set(expected_cache_keys))
        
        # Test branch-related metrics
        branch_keys = self.report.get_metric_keys(r".*[Bb]ranch.*")
        expected_branch_keys = [
            "Branch Prediction Accuracy",
            "Branch Mispredictions per 1K Instructions"
        ]
        self.assertEqual(set(branch_keys), set(expected_branch_keys))
    
    def test_get_metric_keys_invalid_regex(self):
        """Test getting metric keys with invalid regex."""
        with patch('builtins.print') as mock_print:
            keys = self.report.get_metric_keys(r"[invalid regex")
            
            # Should return all keys when regex is invalid
            self.assertEqual(len(keys), 10)
            mock_print.assert_called_with("Invalid regex pattern: [invalid regex")
    
    def test_get_metric_value_success(self):
        """Test successful metric value retrieval."""
        cycles = self.report.get_metric_value("Total Cycles Consumed")
        self.assertEqual(cycles, 253627)
        
        hit_rate = self.report.get_metric_value("L1 Instruction Cache Hit Rate")
        self.assertEqual(hit_rate, 99.96)
    
    def test_get_metric_value_missing_key(self):
        """Test metric value retrieval with missing key."""
        with self.assertRaises(ExperimentError) as context:
            self.report.get_metric_value("Nonexistent Metric")
        
        self.assertIn("Metric key 'Nonexistent Metric' not found", str(context.exception))
    
    def test_get_metric_info_success(self):
        """Test successful metric info retrieval."""
        cache_info = self.report.get_metric_info("L1 Instruction Cache Hit Rate")
        
        expected_info = {"val": 99.96, "unit": "%"}
        self.assertEqual(cache_info, expected_info)
    
    def test_get_metric_info_missing_key(self):
        """Test metric info retrieval with missing key."""
        with self.assertRaises(ExperimentError) as context:
            self.report.get_metric_info("Nonexistent Metric")
        
        self.assertIn("Metric key 'Nonexistent Metric' not found", str(context.exception))


class TestSummaryReportPrinting(unittest.TestCase):
    """Test metric printing and formatting functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test report with various data types
        self.test_report_data = {
            "Statistics": {
                "Summary Performance Report": {
                    "Total Cycles Consumed": {"val": 253627},
                    "Total Instructions Retired": {"val": 196626},
                    "IPC Ratio": {"val": 0.775123},
                    "Cache Hit Rate": {"val": 99.96, "unit": "%"},
                    "Status": {"val": "completed"}
                }
            }
        }
        
        self.test_report_path = Path(self.temp_dir) / "test_report.json"
        with open(self.test_report_path, 'w') as f:
            json.dump(self.test_report_data, f)
        
        self.report = SummaryReport(self.test_report_path)
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('builtins.print')
    def test_print_metrics_all(self, mock_print):
        """Test printing all metrics."""
        self.report.print_metrics()
        
        # Verify header was printed
        mock_print.assert_any_call("\\nSummary Report Metrics (5 metrics):")
        mock_print.assert_any_call("=" * 50)
        
        # Verify some metrics were printed (format may vary by locale)
        printed_calls = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(any("Total Cycles Consumed" in call for call in printed_calls))
        self.assertTrue(any("IPC Ratio" in call for call in printed_calls))
    
    @patch('builtins.print')
    def test_print_metrics_regex_filter(self, mock_print):
        """Test printing metrics with regex filter."""
        self.report.print_metrics(r".*[Cc]ache.*")
        
        # Should only print cache-related metrics
        printed_calls = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(any("Cache Hit Rate" in call for call in printed_calls))
        self.assertFalse(any("Total Cycles" in call for call in printed_calls))
    
    @patch('locale.setlocale')
    @patch('builtins.print')
    def test_print_metrics_locale_error(self, mock_print, mock_setlocale):
        """Test printing metrics when locale setting fails."""
        mock_setlocale.side_effect = locale.Error("Locale not available")
        
        self.report.print_metrics()
        
        # Should still print metrics even if locale setting fails
        printed_calls = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(any("Total Cycles Consumed" in call for call in printed_calls))
    
    @patch('builtins.print')
    def test_print_metrics_value_formatting(self, mock_print):
        """Test metric value formatting for different types."""
        # Create report with error-prone metric
        with patch.object(self.report, 'get_metric_value', side_effect=Exception("Test error")):
            self.report.print_metrics()
            
            # Should print error message for problematic metric
            printed_calls = [str(call) for call in mock_print.call_args_list]
            self.assertTrue(any("<error: Test error>" in call for call in printed_calls))
    
    @patch('locale.format_string')
    @patch('builtins.print')
    def test_print_metrics_locale_formatting_error(self, mock_print, mock_format):
        """Test printing metrics when locale formatting fails."""
        mock_format.side_effect = ValueError("Formatting error")
        
        self.report.print_metrics()
        
        # Should fall back to simple string formatting
        printed_calls = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(len(printed_calls) > 0)


class TestSummaryReportExport(unittest.TestCase):
    """Test metric export functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
        self.test_report_data = {
            "Statistics": {
                "Summary Performance Report": {
                    "Total Cycles Consumed": {"val": 253627, "unit": "cycles"},
                    "Total Instructions Retired": {"val": 196626, "unit": "instructions"},
                    "L1 Cache Hit Rate": {"val": 99.96, "unit": "%"}
                }
            }
        }
        
        self.test_report_path = Path(self.temp_dir) / "test_report.json"
        with open(self.test_report_path, 'w') as f:
            json.dump(self.test_report_data, f)
        
        self.report = SummaryReport(self.test_report_path)
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_export_metrics_all(self):
        """Test exporting all metrics."""
        output_path = Path(self.temp_dir) / "exported_metrics.json"
        
        self.report.export_metrics(output_path)
        
        # Verify file was created
        self.assertTrue(output_path.exists())
        
        # Verify content
        with open(output_path) as f:
            exported_data = json.load(f)
        
        self.assertEqual(exported_data["source_report"], str(self.test_report_path))
        self.assertEqual(exported_data["total_cycles"], 253627)
        self.assertEqual(exported_data["total_instructions"], 196626)
        self.assertAlmostEqual(exported_data["ipc"], 196626 / 253627, places=6)
        self.assertIn("metrics", exported_data)
        self.assertEqual(len(exported_data["metrics"]), 3)
    
    def test_export_metrics_regex_filter(self):
        """Test exporting metrics with regex filter."""
        output_path = Path(self.temp_dir) / "cache_metrics.json"
        
        self.report.export_metrics(output_path, r".*[Cc]ache.*")
        
        with open(output_path) as f:
            exported_data = json.load(f)
        
        # Should only export cache-related metrics
        self.assertEqual(len(exported_data["metrics"]), 1)
        self.assertIn("L1 Cache Hit Rate", exported_data["metrics"])
    
    def test_export_metrics_directory_creation(self):
        """Test exporting metrics with automatic directory creation."""
        output_path = Path(self.temp_dir) / "subdir" / "nested" / "metrics.json"
        
        self.report.export_metrics(output_path)
        
        # Verify directory was created and file exists
        self.assertTrue(output_path.exists())
        self.assertTrue(output_path.parent.exists())
    
    def test_export_metrics_with_errors(self):
        """Test exporting metrics when some metrics have errors."""
        # Mock get_metric_info to raise error for specific metric
        original_method = self.report.get_metric_info
        
        def mock_get_metric_info(key):
            if key == "Total Cycles Consumed":
                raise Exception("Test error")
            return original_method(key)
        
        with patch.object(self.report, 'get_metric_info', side_effect=mock_get_metric_info):
            output_path = Path(self.temp_dir) / "error_metrics.json"
            self.report.export_metrics(output_path)
            
            with open(output_path) as f:
                exported_data = json.load(f)
            
            # Should include error information
            self.assertEqual(exported_data["metrics"]["Total Cycles Consumed"]["error"], "Test error")


class TestSummaryReportSpecializedMetrics(unittest.TestCase):
    """Test specialized metric extraction functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create comprehensive test report
        self.comprehensive_report_data = {
            "Statistics": {
                "Summary Performance Report": {
                    "Total Cycles Consumed": {"val": 253627},
                    "Total Instructions Retired": {"val": 196626},
                    
                    # Cache metrics
                    "L1 Instruction Cache Hit Rate": {"val": 99.96, "unit": "%"},
                    "L1 Data Cache Hit Rate": {"val": 99.86, "unit": "%"},
                    "L2 Cache Hit Rate": {"val": 98.5, "unit": "%"},
                    "L1 Cache Miss Rate": {"val": 0.14, "unit": "%"},
                    "L2 Cache Miss Count": {"val": 1024},
                    
                    # Branch metrics  
                    "Branch Prediction Accuracy": {"val": 99.27, "unit": "%"},
                    "Branch Mispredictions": {"val": 147},
                    "Branch Mispredictions per 1K Instructions": {"val": 0.73},
                    
                    # Other metrics
                    "ALU Utilization": {"val": 45.2, "unit": "%"},
                    "Memory Bandwidth": {"val": 2048, "unit": "MB/s"}
                }
            }
        }
        
        self.test_report_path = Path(self.temp_dir) / "comprehensive_report.json"
        with open(self.test_report_path, 'w') as f:
            json.dump(self.comprehensive_report_data, f)
        
        self.report = SummaryReport(self.test_report_path)
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_get_cache_metrics(self):
        """Test extraction of cache-related metrics."""
        cache_metrics = self.report.get_cache_metrics()
        
        expected_cache_keys = {
            "L1 Instruction Cache Hit Rate",
            "L1 Data Cache Hit Rate",
            "L2 Cache Hit Rate", 
            "L1 Cache Miss Rate",
            "L2 Cache Miss Count"
        }
        
        self.assertEqual(set(cache_metrics.keys()), expected_cache_keys)
        self.assertEqual(cache_metrics["L1 Instruction Cache Hit Rate"], 99.96)
        self.assertEqual(cache_metrics["L2 Cache Miss Count"], 1024)
    
    def test_get_cache_metrics_with_errors(self):
        """Test cache metrics extraction with some metrics having errors."""
        # Mock get_metric_value to raise error for specific metrics
        original_method = self.report.get_metric_value
        
        def mock_get_metric_value(key):
            if "L2" in key:
                raise Exception("L2 cache error")
            return original_method(key)
        
        with patch.object(self.report, 'get_metric_value', side_effect=mock_get_metric_value):
            cache_metrics = self.report.get_cache_metrics()
            
            # Should include L1 metrics but skip L2 metrics with errors
            self.assertIn("L1 Instruction Cache Hit Rate", cache_metrics)
            self.assertIn("L1 Data Cache Hit Rate", cache_metrics)
            self.assertNotIn("L2 Cache Hit Rate", cache_metrics)
    
    def test_get_branch_metrics(self):
        """Test extraction of branch prediction metrics."""
        branch_metrics = self.report.get_branch_metrics()
        
        expected_branch_keys = {
            "Branch Prediction Accuracy",
            "Branch Mispredictions",
            "Branch Mispredictions per 1K Instructions"
        }
        
        self.assertEqual(set(branch_metrics.keys()), expected_branch_keys)
        self.assertEqual(branch_metrics["Branch Prediction Accuracy"], 99.27)
        self.assertEqual(branch_metrics["Branch Mispredictions"], 147)
    
    def test_get_branch_metrics_with_errors(self):
        """Test branch metrics extraction with some metrics having errors."""
        original_method = self.report.get_metric_value
        
        def mock_get_metric_value(key):
            if "Mispredictions" in key:
                raise Exception("Branch error")
            return original_method(key)
        
        with patch.object(self.report, 'get_metric_value', side_effect=mock_get_metric_value):
            branch_metrics = self.report.get_branch_metrics()
            
            # Should include accuracy but skip misprediction metrics with errors
            self.assertIn("Branch Prediction Accuracy", branch_metrics)
            self.assertNotIn("Branch Mispredictions", branch_metrics)
    
    def test_specialized_metrics_empty_report(self):
        """Test specialized metrics extraction with empty report."""
        # Create minimal report without specialized metrics
        minimal_data = {
            "Statistics": {
                "Summary Performance Report": {
                    "Total Cycles Consumed": {"val": 1000},
                    "Total Instructions Retired": {"val": 800}
                }
            }
        }
        
        minimal_path = Path(self.temp_dir) / "minimal_report.json"
        with open(minimal_path, 'w') as f:
            json.dump(minimal_data, f)
        
        minimal_report = SummaryReport(minimal_path)
        
        cache_metrics = minimal_report.get_cache_metrics()
        branch_metrics = minimal_report.get_branch_metrics()
        
        self.assertEqual(cache_metrics, {})
        self.assertEqual(branch_metrics, {})


class TestSummaryReportPathHandling(unittest.TestCase):
    """Test path handling and string/Path compatibility."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
        self.test_report_data = {
            "Statistics": {
                "Summary Performance Report": {
                    "Total Cycles Consumed": {"val": 1000},
                    "Total Instructions Retired": {"val": 800}
                }
            }
        }
        
        self.test_report_path = Path(self.temp_dir) / "test_report.json"
        with open(self.test_report_path, 'w') as f:
            json.dump(self.test_report_data, f)
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initialization_with_string_path(self):
        """Test SummaryReport initialization with string path."""
        report = SummaryReport(str(self.test_report_path))
        
        self.assertEqual(report.json_file, self.test_report_path)
        self.assertEqual(report.totalcycles, 1000)
    
    def test_initialization_with_path_object(self):
        """Test SummaryReport initialization with Path object."""
        report = SummaryReport(self.test_report_path)
        
        self.assertEqual(report.json_file, self.test_report_path)
        self.assertEqual(report.totalcycles, 1000)
    
    def test_export_with_string_path(self):
        """Test export_metrics with string output path."""
        report = SummaryReport(self.test_report_path)
        output_path = str(Path(self.temp_dir) / "exported.json")
        
        report.export_metrics(output_path)
        
        self.assertTrue(Path(output_path).exists())
    
    def test_export_with_path_object(self):
        """Test export_metrics with Path object output path."""
        report = SummaryReport(self.test_report_path)
        output_path = Path(self.temp_dir) / "exported.json"
        
        report.export_metrics(output_path)
        
        self.assertTrue(output_path.exists())


if __name__ == '__main__':
    unittest.main()
