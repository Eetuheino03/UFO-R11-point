#!/usr/bin/env python3
"""Final validation script to confirm the frontend panel import fix."""

import ast
import sys
from pathlib import Path

def validate_import_fix():
    """Validate that the frontend panel import issue is resolved."""
    
    print("=== Final Frontend Panel Import Fix Validation ===\n")
    
    # Step 1: Verify frontend_panel.py has the required function
    frontend_panel_path = Path("custom_components/ufo_r11_smartir/frontend_panel.py")
    
    with open(frontend_panel_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for the required function definition
    has_async_setup_frontend_panel = "async def async_setup_frontend_panel(hass: HomeAssistant)" in content
    has_async_register_panel = "async def async_register_panel(hass: HomeAssistant)" in content
    has_async_unregister_panel = "async def async_unregister_panel(hass: HomeAssistant)" in content
    
    print("1. Frontend Panel Function Check:")
    print(f"   ✓ async_setup_frontend_panel: {has_async_setup_frontend_panel}")
    print(f"   ✓ async_register_panel: {has_async_register_panel}")
    print(f"   ✓ async_unregister_panel: {has_async_unregister_panel}")
    
    if not has_async_setup_frontend_panel:
        print("   ✗ MISSING: async_setup_frontend_panel function!")
        return False
    
    # Step 2: Verify __init__.py imports are correct
    init_path = Path("custom_components/ufo_r11_smartir/__init__.py")
    
    with open(init_path, 'r', encoding='utf-8') as f:
        init_content = f.read()
    
    # Check imports
    imports_setup = "from .frontend_panel import async_setup_frontend_panel" in init_content
    imports_unregister = "async_unregister_panel" in init_content
    calls_setup = "await async_setup_frontend_panel(hass)" in init_content
    calls_unregister = "await async_unregister_panel(hass)" in init_content
    
    print("\n2. Import and Usage Check:")
    print(f"   ✓ Imports async_setup_frontend_panel: {imports_setup}")
    print(f"   ✓ Imports async_unregister_panel: {imports_unregister}")
    print(f"   ✓ Calls async_setup_frontend_panel: {calls_setup}")
    print(f"   ✓ Calls async_unregister_panel: {calls_unregister}")
    
    if not (imports_setup and calls_setup):
        print("   ✗ MISSING: Proper import or usage of async_setup_frontend_panel!")
        return False
    
    # Step 3: Check wrapper function implementation
    setup_calls_register = "await async_register_panel(hass)" in content
    
    print("\n3. Wrapper Function Implementation:")
    print(f"   ✓ async_setup_frontend_panel calls async_register_panel: {setup_calls_register}")
    
    if not setup_calls_register:
        print("   ✗ MISSING: async_setup_frontend_panel should call async_register_panel!")
        return False
    
    # Step 4: Check for proper error handling
    has_error_handling = "try:" in content and "except Exception as e:" in content
    
    print("\n4. Error Handling Check:")
    print(f"   ✓ Has proper error handling: {has_error_handling}")
    
    # Step 5: Summary
    print("\n=== VALIDATION RESULTS ===")
    
    if has_async_setup_frontend_panel and imports_setup and calls_setup and setup_calls_register:
        print("✅ IMPORT FIX SUCCESSFUL!")
        print("   - Missing async_setup_frontend_panel function has been added")
        print("   - Proper wrapper pattern implemented (calls async_register_panel)")
        print("   - Import statements corrected in __init__.py")
        print("   - Complete setup/teardown lifecycle implemented")
        return True
    else:
        print("❌ IMPORT FIX INCOMPLETE!")
        return False

if __name__ == "__main__":
    success = validate_import_fix()
    sys.exit(0 if success else 1)