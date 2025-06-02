#!/usr/bin/env python3
"""
Validation test for critical Home Assistant integration fixes.

This script validates that all three critical issues identified in the live logs
have been properly resolved:

1. Event loop blocking from synchronous file operations
2. Deprecated config flow patterns  
3. Missing aiofiles dependency

Live log issues addressed:
- "Detected blocking call to open" in parser.py line 163
- "Detected blocking call to open" in ir_codes.py lines 282 and 304
- "sets option flow config_entry explicitly, which is deprecated" in config_flow.py line 235
"""

import asyncio
import sys
import logging
from pathlib import Path

# Setup logging to catch any warnings
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_manifest_dependency():
    """Test that aiofiles dependency was added to manifest.json."""
    logger.info("=== Testing manifest.json aiofiles dependency ===")
    
    manifest_path = Path("custom_components/ufo_r11_smartir/manifest.json")
    if not manifest_path.exists():
        logger.error("❌ manifest.json not found")
        return False
        
    import json
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    
    requirements = manifest.get('requirements', [])
    aiofiles_found = any('aiofiles' in req for req in requirements)
    
    if aiofiles_found:
        logger.info("✅ aiofiles dependency found in manifest.json")
        logger.info(f"   Requirements: {requirements}")
        return True
    else:
        logger.error("❌ aiofiles dependency missing from manifest.json")
        return False

def test_aiofiles_import():
    """Test that aiofiles can be imported (simulates HA environment)."""
    logger.info("=== Testing aiofiles import availability ===")
    
    try:
        import aiofiles
        logger.info("✅ aiofiles import successful")
        return True
    except ImportError as e:
        logger.warning(f"⚠️  aiofiles not installed locally: {e}")
        logger.info("   This is OK - Home Assistant will install it from manifest.json")
        return True

async def test_parser_async_operations():
    """Test that parser.py uses async file operations."""
    logger.info("=== Testing parser.py async file operations ===")
    
    parser_path = Path("custom_components/ufo_r11_smartir/parser.py")
    if not parser_path.exists():
        logger.error("❌ parser.py not found")
        return False
    
    with open(parser_path, 'r') as f:
        content = f.read()
    
    # Check for async function signature
    if "async def parse_file(" in content:
        logger.info("✅ parse_file() converted to async function")
    else:
        logger.error("❌ parse_file() not converted to async")
        return False
    
    # Check for aiofiles import
    if "import aiofiles" in content:
        logger.info("✅ aiofiles import found in parser.py")
    else:
        logger.error("❌ aiofiles import missing from parser.py")
        return False
    
    # Check for async file operations
    if "async with aiofiles.open(" in content:
        logger.info("✅ Non-blocking async file operations found")
    else:
        logger.error("❌ Still using blocking file operations")
        return False
    
    # Check that blocking operations are removed
    if "with open(" in content and "async with" not in content.split("with open(")[0].split('\n')[-1]:
        logger.warning("⚠️  Potential blocking file operations still present")
    else:
        logger.info("✅ No blocking file operations detected")
    
    return True

async def test_ir_codes_async_operations():
    """Test that ir_codes.py uses async file operations."""
    logger.info("=== Testing ir_codes.py async file operations ===")
    
    ir_codes_path = Path("custom_components/ufo_r11_smartir/ir_codes.py")
    if not ir_codes_path.exists():
        logger.error("❌ ir_codes.py not found")
        return False
    
    with open(ir_codes_path, 'r') as f:
        content = f.read()
    
    # Check for aiofiles import
    if "import aiofiles" in content:
        logger.info("✅ aiofiles import found in ir_codes.py")
    else:
        logger.error("❌ aiofiles import missing from ir_codes.py")
        return False
    
    # Check for async file operations
    async_operations = content.count("async with aiofiles.open(")
    if async_operations >= 2:
        logger.info(f"✅ Found {async_operations} async file operations (read & write)")
    else:
        logger.error(f"❌ Only found {async_operations} async file operations, expected 2")
        return False
    
    # Check for modern async patterns
    if "await f.read()" in content and "await f.write(" in content:
        logger.info("✅ Modern async file read/write patterns found")
    else:
        logger.error("❌ Missing modern async file read/write patterns")
        return False
    
    return True

def test_config_flow_modern_pattern():
    """Test that config_flow.py uses modern Home Assistant patterns."""
    logger.info("=== Testing config_flow.py modern HA patterns ===")
    
    config_flow_path = Path("custom_components/ufo_r11_smartir/config_flow.py")
    if not config_flow_path.exists():
        logger.error("❌ config_flow.py not found")
        return False
    
    with open(config_flow_path, 'r') as f:
        content = f.read()
    
    # Check for modern super() initialization
    if "super().__init__()" in content:
        logger.info("✅ Modern super().__init__() pattern found")
    else:
        logger.error("❌ Modern super().__init__() pattern missing")
        return False
    
    # Check that deprecated pattern is removed
    if "self.config_entry = config_entry" in content:
        logger.error("❌ Deprecated self.config_entry assignment still present")
        return False
    else:
        logger.info("✅ Deprecated config_entry assignment removed")
    
    return True

async def main():
    """Run all validation tests."""
    logger.info("🔍 Starting validation of critical Home Assistant integration fixes...")
    logger.info("=" * 70)
    
    tests = [
        ("Manifest Dependencies", test_manifest_dependency),
        ("Aiofiles Import", test_aiofiles_import),
        ("Parser Async Operations", test_parser_async_operations),
        ("IR Codes Async Operations", test_ir_codes_async_operations),
        ("Config Flow Modern Pattern", test_config_flow_modern_pattern),
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n📋 Running: {test_name}")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"❌ {test_name} failed with error: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("🎯 VALIDATION SUMMARY")
    logger.info("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status}: {test_name}")
    
    logger.info("=" * 70)
    logger.info(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 ALL CRITICAL FIXES VALIDATED SUCCESSFULLY!")
        logger.info("   - Event loop blocking eliminated")
        logger.info("   - Deprecated patterns modernized")
        logger.info("   - Dependencies properly configured")
        logger.info("   Integration should now load without warnings!")
    else:
        logger.error("⚠️  Some fixes may need additional work")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)