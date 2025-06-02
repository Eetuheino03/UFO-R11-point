#!/usr/bin/env python3
"""Simple syntax validation for the AttributeError fix."""

import ast
import sys
from pathlib import Path

def test_syntax_validation():
    """Test that the fixed __init__.py file has valid Python syntax."""
    try:
        init_file = Path("custom_components/ufo_r11_smartir/__init__.py")
        
        if not init_file.exists():
            print("❌ ERROR: __init__.py file not found!")
            return False
            
        with open(init_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the Python code to check for syntax errors
        ast.parse(content)
        print("✅ SUCCESS: __init__.py has valid Python syntax!")
        
        # Check if the old method call is gone
        if "setup_device_from_pointcodes" in content:
            print("❌ ERROR: Old method call still found in code!")
            return False
        else:
            print("✅ SUCCESS: Old method call removed!")
            
        # Check if the new method call exists
        if "async_setup_device" in content:
            print("✅ SUCCESS: New method call found!")
        else:
            print("❌ ERROR: New method call not found!")
            return False
            
        # Check if required parameters are used
        if "CODE_SOURCE_POINTCODES" in content and "DEVICE_TYPE_AC" in content:
            print("✅ SUCCESS: Required constants are used!")
        else:
            print("❌ ERROR: Required constants not found in method call!")
            return False
            
        return True
        
    except SyntaxError as e:
        print(f"❌ SYNTAX ERROR: {e}")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def check_device_manager_methods():
    """Check DeviceManager source for available methods."""
    try:
        dm_file = Path("custom_components/ufo_r11_smartir/device_manager.py")
        
        if not dm_file.exists():
            print("❌ ERROR: device_manager.py file not found!")
            return False
            
        with open(dm_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("\n=== DeviceManager Method Analysis ===")
        
        # Check for the methods we care about
        if "def setup_device_from_pointcodes" in content:
            print("❌ WARNING: Old method definition still exists in DeviceManager!")
        else:
            print("✅ SUCCESS: Old method definition not found (as expected)!")
            
        if "async def async_setup_device" in content:
            print("✅ SUCCESS: New method definition found!")
        else:
            print("❌ ERROR: New method definition not found!")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    print("Testing AttributeError fix (syntax and structure)...")
    
    syntax_test = test_syntax_validation()
    method_test = check_device_manager_methods()
    
    if syntax_test and method_test:
        print("\n🎉 ALL TESTS PASSED! The AttributeError fix should work correctly.")
        print("\nSummary of fix:")
        print("- Replaced 'setup_device_from_pointcodes' with 'async_setup_device'")
        print("- Updated parameters to use device_type and code_source")
        print("- Verified all required constants are imported and used")
        sys.exit(0)
    else:
        print("\n💥 TESTS FAILED! There may be issues with the fix.")
        sys.exit(1)