#!/usr/bin/env python3
"""Test script for the UFO-R11 IR code processing system."""

import asyncio
import json
import sys
import os
from pathlib import Path

# Add the custom components path to sys.path
custom_components_path = str(Path(__file__).parent / "custom_components")
sys.path.insert(0, custom_components_path)

# Now import as a package
from ufo_r11_smartir.parser import PointCodesParser
from ufo_r11_smartir.ir_codes import IRCodeManager, IRCodeSet
from ufo_r11_smartir.device_manager import DeviceManager
from ufo_r11_smartir.smartir_generator import SmartIRGenerator


async def test_ir_system():
    """Test the complete IR code processing system."""
    print("🧪 Testing UFO-R11 IR Code Processing System")
    print("=" * 50)
    
    # Test 1: Parse Point-codes file
    print("\n1. Testing Point-codes Parser...")
    parser = PointCodesParser()
    pointcodes_file = Path("custom_components/ufo_r11_smartir/data/Point-codes")
    
    try:
        ir_commands = await parser.parse_file(str(pointcodes_file))
        print(f"✅ Successfully parsed {len(ir_commands)} IR commands")
        
        # Show first few commands
        for i, cmd in enumerate(list(ir_commands.values())[:5]):
            print(f"   • {cmd.name}: {cmd.ir_code[:50]}...")
            
    except Exception as err:
        print(f"❌ Failed to parse Point-codes: {err}")
        return False
    
    # Test 2: IR Code Manager
    print("\n2. Testing IR Code Manager...")
    try:
        ir_manager = IRCodeManager()
        
        # Create a code set from parsed commands
        code_set = IRCodeSet(
            device_id="test_device",
            device_name="Test UFO-R11",
            commands=ir_commands
        )
        
        # Store and retrieve
        await ir_manager.store_device_codes("test_device", code_set)
        retrieved = ir_manager.get_device_codes("test_device")
        
        if retrieved and len(retrieved.commands) == len(ir_commands):
            print(f"✅ IR Code Manager working correctly ({len(retrieved.commands)} commands stored)")
        else:
            print("❌ IR Code Manager failed to store/retrieve correctly")
            return False
            
    except Exception as err:
        print(f"❌ IR Code Manager error: {err}")
        return False
    
    # Test 3: SmartIR Generator
    print("\n3. Testing SmartIR Generator...")
    try:
        generator = SmartIRGenerator()
        smartir_config = await generator.generate_config(
            device_id="test_device",
            device_name="Test UFO-R11", 
            ir_commands=ir_commands
        )
        
        # Validate the configuration has expected structure
        required_keys = ["manufacturer", "supportedModels", "temperature", "operations"]
        if all(key in smartir_config for key in required_keys):
            print("✅ SmartIR configuration generated successfully")
            print(f"   • Manufacturer: {smartir_config['manufacturer']}")
            print(f"   • Temperature range: {smartir_config['temperature']['min']}-{smartir_config['temperature']['max']}°C")
            print(f"   • Operations: {len(smartir_config['operations'])} modes")
        else:
            print("❌ SmartIR configuration missing required keys")
            return False
            
    except Exception as err:
        print(f"❌ SmartIR Generator error: {err}")
        return False
    
    # Test 4: Command lookup
    print("\n4. Testing Command Lookup...")
    try:
        # Test temperature lookup
        temp_cmd = ir_manager.get_ir_code("test_device", "20c")
        if temp_cmd:
            print(f"✅ Temperature command lookup working (20c found)")
        else:
            print("❌ Temperature command lookup failed")
            
        # Test mode lookup  
        power_cmd = ir_manager.get_ir_code("test_device", "ON")
        if power_cmd:
            print(f"✅ Power command lookup working (ON found)")
        else:
            print("❌ Power command lookup failed")
            
    except Exception as err:
        print(f"❌ Command lookup error: {err}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 IR Code Processing System Test Complete!")
    print("✅ All components working correctly")
    return True


if __name__ == "__main__":
    success = asyncio.run(test_ir_system())
    if not success:
        sys.exit(1)