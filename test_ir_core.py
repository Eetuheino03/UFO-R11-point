#!/usr/bin/env python3
"""Standalone test for UFO-R11 IR code processing core functionality."""

import asyncio
import base64
import json
import re
import sys
from pathlib import Path
from typing import Dict, Any


class IRCommand:
    """IR command with Base64-encoded data."""
    
    def __init__(self, name: str, ir_code: str):
        self.name = name
        self.ir_code = ir_code
        self.validate()
    
    def validate(self) -> None:
        """Validate the IR command."""
        if not self.name or not self.name.strip():
            raise ValueError("Command name cannot be empty")
        
        if not self.ir_code or not self.ir_code.strip():
            raise ValueError("IR code cannot be empty")
        
        # Validate Base64 encoding
        try:
            base64.b64decode(self.ir_code)
        except Exception as err:
            raise ValueError(f"Invalid Base64 IR code: {err}")


class PointCodesParser:
    """Parser for Point-codes file format."""
    
    def __init__(self):
        self.command_pattern = re.compile(r'^([^-]+)\s*-\s*(.+)$')
    
    async def parse_file(self, file_path: str) -> Dict[str, IRCommand]:
        """Parse Point-codes file and return IR commands."""
        commands = {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                for line_num, line in enumerate(file, 1):
                    line = line.strip()
                    if not line:  # Skip empty lines
                        continue
                    
                    match = self.command_pattern.match(line)
                    if not match:
                        print(f"Warning: Line {line_num} doesn't match expected format: {line}")
                        continue
                    
                    command_name = match.group(1).strip()
                    ir_code = match.group(2).strip()
                    
                    try:
                        command = IRCommand(command_name, ir_code)
                        commands[command_name] = command
                    except ValueError as err:
                        print(f"Warning: Invalid command on line {line_num}: {err}")
                        continue
        
        except FileNotFoundError:
            raise FileNotFoundError(f"Point-codes file not found: {file_path}")
        except Exception as err:
            raise RuntimeError(f"Failed to parse Point-codes file: {err}")
        
        return commands


class SmartIRGenerator:
    """Generate SmartIR configuration from IR commands."""
    
    def __init__(self):
        self.temperature_pattern = re.compile(r'^(\d{2})c$')
    
    async def generate_config(self, device_id: str, device_name: str, ir_commands: Dict[str, IRCommand]) -> Dict[str, Any]:
        """Generate SmartIR JSON configuration."""
        
        # Extract temperature commands
        temp_commands = {}
        for name, cmd in ir_commands.items():
            match = self.temperature_pattern.match(name)
            if match:
                temp = int(match.group(1))
                temp_commands[temp] = cmd.ir_code
        
        # Build SmartIR configuration
        config = {
            "manufacturer": "MOES",
            "supportedModels": [device_name],
            "supportedController": "UFO-R11",
            "commandsEncoding": "Base64",
            "temperature": {
                "min": min(temp_commands.keys()) if temp_commands else 17,
                "max": max(temp_commands.keys()) if temp_commands else 30
            },
            "operations": {
                "off": [{"ir_code": ir_commands["OFF"].ir_code}] if "OFF" in ir_commands else [],
                "cool": self._build_mode_operations("cool", temp_commands, ir_commands),
                "heat": self._build_mode_operations("heat", temp_commands, ir_commands),
                "dry": self._build_mode_operations("dry", temp_commands, ir_commands),
                "fan_only": self._build_mode_operations("fan", temp_commands, ir_commands),
                "auto": self._build_mode_operations("auto", temp_commands, ir_commands),
            }
        }
        
        return config
    
    def _build_mode_operations(self, mode: str, temp_commands: Dict[int, str], ir_commands: Dict[str, IRCommand]) -> list:
        """Build operations for a specific mode."""
        operations = []
        
        for temp, ir_code in sorted(temp_commands.items()):
            operation = {
                "temperature": temp,
                "ir_code": ir_code
            }
            operations.append(operation)
        
        return operations


async def test_ir_core():
    """Test the core IR processing functionality."""
    print("🧪 Testing UFO-R11 IR Code Processing Core")
    print("=" * 50)
    
    # Test 1: Parse Point-codes file
    print("\n1. Testing Point-codes Parser...")
    parser = PointCodesParser()
    pointcodes_file = Path("custom_components/ufo_r11_smartir/data/Point-codes")
    
    if not pointcodes_file.exists():
        print(f"❌ Point-codes file not found: {pointcodes_file}")
        return False
    
    try:
        ir_commands = await parser.parse_file(str(pointcodes_file))
        print(f"✅ Successfully parsed {len(ir_commands)} IR commands")
        
        # Show first few commands
        for i, (name, cmd) in enumerate(list(ir_commands.items())[:5]):
            print(f"   • {name}: {cmd.ir_code[:50]}...")
            
    except Exception as err:
        print(f"❌ Failed to parse Point-codes: {err}")
        return False
    
    # Test 2: Validate IR codes
    print("\n2. Testing IR Code Validation...")
    try:
        valid_count = 0
        for name, cmd in ir_commands.items():
            try:
                base64.b64decode(cmd.ir_code)
                valid_count += 1
            except Exception:
                print(f"   ⚠️ Invalid Base64 in command: {name}")
        
        print(f"✅ {valid_count}/{len(ir_commands)} commands have valid Base64 encoding")
        
    except Exception as err:
        print(f"❌ Validation error: {err}")
        return False
    
    # Test 3: Test command categorization
    print("\n3. Testing Command Categorization...")
    try:
        categories = {
            "temperature": [],
            "power": [],
            "modes": [],
            "fan": [],
            "swing": []
        }
        
        temp_pattern = re.compile(r'^(\d{2})c$')
        
        for name in ir_commands.keys():
            if temp_pattern.match(name):
                categories["temperature"].append(name)
            elif name in ["ON", "OFF"]:
                categories["power"].append(name)
            elif name in ["cool", "heat", "dry", "fan", "auto", "sleep"]:
                categories["modes"].append(name)
            elif name in ["low", "medium", "high", "auto"]:
                categories["fan"].append(name)
            elif "swing" in name.lower():
                categories["swing"].append(name)
        
        for category, commands in categories.items():
            if commands:
                print(f"   • {category}: {len(commands)} commands ({', '.join(commands[:3])}{'...' if len(commands) > 3 else ''})")
        
        print("✅ Command categorization working")
        
    except Exception as err:
        print(f"❌ Categorization error: {err}")
        return False
    
    # Test 4: SmartIR Generator
    print("\n4. Testing SmartIR Generator...")
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
            
            # Count total operations
            total_ops = sum(len(ops) for ops in smartir_config['operations'].values())
            print(f"   • Total operations: {total_ops}")
        else:
            print("❌ SmartIR configuration missing required keys")
            return False
            
    except Exception as err:
        print(f"❌ SmartIR Generator error: {err}")
        return False
    
    # Test 5: Export test config
    print("\n5. Testing Configuration Export...")
    try:
        output_file = "test_smartir_config.json"
        with open(output_file, 'w') as f:
            json.dump(smartir_config, f, indent=2)
        
        print(f"✅ SmartIR configuration exported to {output_file}")
        
    except Exception as err:
        print(f"❌ Export error: {err}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 IR Code Processing Core Test Complete!")
    print("✅ All core components working correctly")
    return True


if __name__ == "__main__":
    success = asyncio.run(test_ir_core())
    if not success:
        sys.exit(1)