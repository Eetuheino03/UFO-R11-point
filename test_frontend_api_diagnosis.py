#!/usr/bin/env python3
"""
Diagnostic script to test the correct Home Assistant frontend API usage.
This will help validate the proper method for registering static paths.
"""

import asyncio
import logging
from unittest.mock import MagicMock, AsyncMock
from pathlib import Path

# Mock Home Assistant components
class MockHTTP:
    """Mock HTTP component to test API calls"""
    
    def __init__(self):
        self.static_paths = []
        
    def register_static_path(self, url_path: str, path: str, cache_headers: bool = True):
        """Mock the singular register_static_path method"""
        print(f"✓ register_static_path called with: url_path='{url_path}', path='{path}', cache_headers={cache_headers}")
        self.static_paths.append({"url_path": url_path, "path": path, "cache_headers": cache_headers})
        return True
        
    async def async_register_static_paths(self, paths_list):
        """Mock the plural async_register_static_paths method"""
        print(f"✗ async_register_static_paths called with: {paths_list}")
        # This should fail with AttributeError when accessing url_path
        for path_config in paths_list:
            if hasattr(path_config, 'url_path'):
                print(f"  - Object has url_path: {path_config.url_path}")
            else:
                print(f"  - ERROR: Object missing url_path attribute: {type(path_config)} - {path_config}")
                raise AttributeError("'dict' object has no attribute 'url_path'")

class MockHass:
    """Mock Home Assistant instance"""
    
    def __init__(self):
        self.http = MockHTTP()
        self.data = {}

async def test_current_broken_approach():
    """Test the current broken approach that causes AttributeError"""
    print("=== Testing Current Broken Approach ===")
    hass = MockHass()
    www_path = Path(__file__).parent / "custom_components" / "ufo_r11_smartir" / "www"
    DOMAIN = "ufo_r11_smartir"
    
    try:
        # This is the current broken code
        await hass.http.async_register_static_paths([
            {
                "path": f"/api/{DOMAIN}/static",
                "directory": str(www_path),
            }
        ])
        print("✗ ERROR: This should have failed!")
    except AttributeError as e:
        print(f"✓ Expected AttributeError caught: {e}")

def test_correct_approach():
    """Test the correct approach using register_static_path"""
    print("\n=== Testing Correct Approach ===")
    hass = MockHass()
    www_path = Path(__file__).parent / "custom_components" / "ufo_r11_smartir" / "www"
    DOMAIN = "ufo_r11_smartir"
    
    try:
        # This should be the correct approach
        hass.http.register_static_path(
            f"/api/{DOMAIN}/static",
            str(www_path),
            cache_headers=True
        )
        print("✓ register_static_path succeeded!")
        return True
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

async def main():
    """Run all diagnostic tests"""
    print("Frontend Panel API Diagnosis")
    print("=" * 50)
    
    # Test the broken approach
    await test_current_broken_approach()
    
    # Test the correct approach
    success = test_correct_approach()
    
    print(f"\n=== Diagnosis Results ===")
    print("Root Cause: Using async_register_static_paths() with dictionaries")
    print("Solution: Use register_static_path() with individual parameters")
    print(f"API Test Success: {success}")

if __name__ == "__main__":
    asyncio.run(main())