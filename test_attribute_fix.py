#!/usr/bin/env python3
"""Test script to validate the AttributeError fix."""

import sys
import os

# Add the custom_components directory to the path
sys.path.insert(0, os.path.join(os.getcwd(), 'custom_components', 'ufo_r11_smartir'))

def test_device_manager_methods():
    """Test that DeviceManager has the correct methods."""
    try:
        from device_manager import DeviceManager
        
        # Check if the old method exists (should NOT exist)
        has_old_method = hasattr(DeviceManager, 'setup_device_from_pointcodes')
        
        # Check if the new method exists (should exist)
        has_new_method = hasattr(DeviceManager, 'async_setup_device')
        
        print("=== DeviceManager Method Check ===")
        print(f"Has old method 'setup_device_from_pointcodes': {has_old_method}")
        print(f"Has new method 'async_setup_device': {has_new_method}")
        
        if has_old_method:
            print("❌ ERROR: Old method still exists!")
            return False
            
        if not has_new_method:
            print("❌ ERROR: New method doesn't exist!")
            return False
            
        print("✅ SUCCESS: Method validation passed!")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: Failed to import DeviceManager: {e}")
        return False

def test_constants_availability():
    """Test that required constants are available."""
    try:
        from const import CODE_SOURCE_POINTCODES, DEVICE_TYPE_AC
        
        print("\n=== Constants Check ===")
        print(f"CODE_SOURCE_POINTCODES: {CODE_SOURCE_POINTCODES}")
        print(f"DEVICE_TYPE_AC: {DEVICE_TYPE_AC}")
        print("✅ SUCCESS: Constants imported successfully!")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: Failed to import constants: {e}")
        return False

if __name__ == "__main__":
    print("Testing AttributeError fix...")
    
    method_test = test_device_manager_methods()
    constants_test = test_constants_availability()
    
    if method_test and constants_test:
        print("\n🎉 ALL TESTS PASSED! The AttributeError should be fixed.")
        sys.exit(0)
    else:
        print("\n💥 TESTS FAILED! The fix may not work.")
        sys.exit(1)