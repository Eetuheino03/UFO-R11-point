#!/usr/bin/env python3
"""Test script to validate frontend panel import fix."""

import sys
from pathlib import Path

# Add the custom_components directory to the path
sys.path.insert(0, str(Path(__file__).parent / "custom_components"))

def test_import_fix():
    """Test different import scenarios to validate the fix."""
    
    print("=== Testing Frontend Panel Import Fix ===\n")
    
    # Test 1: Import the frontend_panel module directly
    print("1. Testing direct module import...")
    try:
        from ufo_r11_smartir import frontend_panel
        print("✓ Successfully imported frontend_panel module")
        
        # Check available functions
        available_functions = [attr for attr in dir(frontend_panel) if callable(getattr(frontend_panel, attr)) and not attr.startswith('_')]
        print(f"   Available functions: {available_functions}")
        
    except ImportError as e:
        print(f"✗ Failed to import frontend_panel module: {e}")
        return False
    
    # Test 2: Try importing async_setup_frontend_panel (should fail)
    print("\n2. Testing async_setup_frontend_panel import (should fail)...")
    try:
        from ufo_r11_smartir.frontend_panel import async_setup_frontend_panel
        print("✗ Unexpected success - this import should fail!")
        return False
    except ImportError as e:
        print(f"✓ Expected failure: {e}")
    
    # Test 3: Try importing async_register_panel (should work)
    print("\n3. Testing async_register_panel import (should work)...")
    try:
        from ufo_r11_smartir.frontend_panel import async_register_panel
        print("✓ Successfully imported async_register_panel")
        print(f"   Function signature: {async_register_panel.__name__}")
        print(f"   Docstring: {async_register_panel.__doc__}")
    except ImportError as e:
        print(f"✗ Failed to import async_register_panel: {e}")
        return False
    
    # Test 4: Test the main module import (the fixed version)
    print("\n4. Testing main module import with fix...")
    try:
        # This should work now with our temporary fix
        from ufo_r11_smartir import __init__
        print("✓ Successfully imported main module")
    except ImportError as e:
        print(f"✗ Main module import still failing: {e}")
        return False
    
    print("\n=== All import tests passed! ===")
    return True

if __name__ == "__main__":
    success = test_import_fix()
    if success:
        print("\n✓ DIAGNOSIS CONFIRMED: async_register_panel works as replacement")
        print("RECOMMENDATION: Either rename async_register_panel to async_setup_frontend_panel")
        print("                OR create a wrapper function async_setup_frontend_panel")
    else:
        print("\n✗ Import issues remain - further investigation needed")
    
    sys.exit(0 if success else 1)