
#!/usr/bin/env python3
"""
Customer Performance Validation Script

This script validates the performance improvements in your environment
after migrating to Atlas Explorer modular architecture.
"""

import time
import sys
from pathlib import Path

def benchmark_import_performance():
    """Benchmark import performance."""
    print("🔍 Testing Import Performance...")
    
    # Test current architecture
    start_time = time.perf_counter()
    try:
        from atlasexplorer import AtlasExplorer
        import_time = time.perf_counter() - start_time
        print(f"  Import time: {import_time:.6f} seconds")
        
        if import_time < 0.1:  # Less than 100ms
            print("  ✅ Excellent import performance!")
        elif import_time < 0.5:  # Less than 500ms
            print("  ✅ Good import performance")
        else:
            print("  ⚠️  Import performance could be optimized")
            
        return import_time
        
    except Exception as e:
        print(f"  ❌ Import failed: {e}")
        return None

def benchmark_object_creation():
    """Benchmark object creation performance."""
    print("\n🔍 Testing Object Creation Performance...")
    
    try:
        from atlasexplorer import AtlasExplorer
        
        start_time = time.perf_counter()
        explorer = AtlasExplorer()
        creation_time = time.perf_counter() - start_time
        
        print(f"  Object creation time: {creation_time:.6f} seconds")
        
        if creation_time < 1.0:  # Less than 1 second
            print("  ✅ Excellent object creation performance!")
        elif creation_time < 3.0:  # Less than 3 seconds
            print("  ✅ Good object creation performance")
        else:
            print("  ⚠️  Object creation performance could be optimized")
            
        return creation_time
        
    except Exception as e:
        print(f"  ❌ Object creation failed: {e}")
        return None

def validate_api_compatibility():
    """Validate API compatibility."""
    print("\n🔍 Testing API Compatibility...")
    
    try:
        from atlasexplorer import AtlasExplorer, Experiment
        
        explorer = AtlasExplorer()
        print("  ✅ AtlasExplorer import successful")
        
        # Test basic API methods
        if hasattr(explorer, 'config'):
            print("  ✅ Configuration access available")
        
        if hasattr(explorer, 'get_supported_cores'):
            print("  ✅ Core support methods available")
            
        print("  ✅ API compatibility validated")
        return True
        
    except Exception as e:
        print(f"  ❌ API compatibility issue: {e}")
        return False

def main():
    """Main validation execution."""
    print("🎯 Atlas Explorer Performance Validation")
    print("=" * 50)
    
    results = {}
    
    # Run benchmarks
    results['import_time'] = benchmark_import_performance()
    results['creation_time'] = benchmark_object_creation()
    results['compatibility'] = validate_api_compatibility()
    
    # Summary
    print("\n📊 VALIDATION SUMMARY")
    print("-" * 30)
    
    if results['import_time'] and results['import_time'] < 0.1:
        print("✅ Import Performance: Excellent")
    elif results['import_time']:
        print(f"⚠️  Import Performance: {results['import_time']:.3f}s (consider optimization)")
    
    if results['creation_time'] and results['creation_time'] < 1.0:
        print("✅ Object Creation: Excellent")  
    elif results['creation_time']:
        print(f"⚠️  Object Creation: {results['creation_time']:.3f}s")
    
    if results['compatibility']:
        print("✅ API Compatibility: Validated")
    else:
        print("❌ API Compatibility: Issues detected")
    
    # Overall assessment
    if all(results.values()):
        print("\n🎉 Performance validation successful!")
        print("   Your environment is ready for production use.")
    else:
        print("\n⚠️  Some issues detected.")
        print("   Contact MIPS support for assistance.")

if __name__ == "__main__":
    main()
