#!/usr/bin/env python3
"""Simple validation script for frontend panel import structure."""

import ast
import sys
from pathlib import Path

def validate_frontend_panel_structure():
    """Validate the frontend panel module structure."""
    
    print("=== Frontend Panel Import Structure Validation ===\n")
    
    # Read and parse the frontend_panel.py file
    frontend_panel_path = Path("custom_components/ufo_r11_smartir/frontend_panel.py")
    if not frontend_panel_path.exists():
        print(f"✗ Frontend panel file not found: {frontend_panel_path}")
        return False
    
    with open(frontend_panel_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        print(f"✗ Syntax error in frontend_panel.py: {e}")
        return False
    
    # Find all function definitions
    functions = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            functions.append(node.name)
    
    print(f"Functions found in frontend_panel.py: {functions}")
    
    # Check for the expected functions
    has_async_register_panel = "async_register_panel" in functions
    has_async_setup_frontend_panel = "async_setup_frontend_panel" in functions
    
    print(f"✓ Has async_register_panel: {has_async_register_panel}")
    print(f"✓ Has async_setup_frontend_panel: {has_async_setup_frontend_panel}")
    
    # Read and check __init__.py imports
    init_path = Path("custom_components/ufo_r11_smartir/__init__.py")
    if not init_path.exists():
        print(f"✗ Init file not found: {init_path}")
        return False
    
    with open(init_path, 'r', encoding='utf-8') as f:
        init_content = f.read()
    
    # Check what's being imported
    imports_async_setup_frontend_panel = "from .frontend_panel import async_setup_frontend_panel" in init_content
    imports_async_register_panel = "from .frontend_panel import async_register_panel" in init_content
    calls_async_setup_frontend_panel = "await async_setup_frontend_panel(hass)" in init_content
    calls_async_register_panel = "await async_register_panel(hass)" in init_content
    
    print(f"\nImport analysis in __init__.py:")
    print(f"✓ Imports async_setup_frontend_panel: {imports_async_setup_frontend_panel}")
    print(f"✓ Imports async_register_panel: {imports_async_register_panel}")
    print(f"✓ Calls async_setup_frontend_panel: {calls_async_setup_frontend_panel}")
    print(f"✓ Calls async_register_panel: {calls_async_register_panel}")
    
    # Diagnosis
    print(f"\n=== DIAGNOSIS ===")
    if has_async_setup_frontend_panel:
        print("✓ No import error - async_setup_frontend_panel exists")
        return True
    elif has_async_register_panel and imports_async_register_panel:
        print("✓ Temporary fix applied - using async_register_panel")
        print("RECOMMENDATION: Add async_setup_frontend_panel wrapper function")
        return True
    else:
        print("✗ Import mismatch detected")
        print(f"   - Function exists: async_register_panel = {has_async_register_panel}")
        print(f"   - Function exists: async_setup_frontend_panel = {has_async_setup_frontend_panel}")
        print(f"   - Import attempts: async_setup_frontend_panel = {imports_async_setup_frontend_panel}")
        return False

if __name__ == "__main__":
    success = validate_frontend_panel_structure()
    sys.exit(0 if success else 1)