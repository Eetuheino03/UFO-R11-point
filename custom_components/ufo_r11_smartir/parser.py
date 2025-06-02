"""Point-codes file parser for UFO-R11 SmartIR integration."""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .ir_codes import IRCommand, IRCodeSet
from .const import (
    HVAC_MODE_OFF,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    HVAC_MODE_DRY,
    HVAC_MODE_FAN_ONLY,
    HVAC_MODE_AUTO,
    HVAC_MODE_SLEEP,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
    FAN_AUTO,
    SWING_OFF,
    SWING_VERTICAL,
    POINTCODES_MIN_TEMP,
    POINTCODES_MAX_TEMP,
)

_LOGGER = logging.getLogger(__name__)


class PointCodesParser:
    """Parser for Point-codes file format."""
    
    def __init__(self):
        """Initialize the parser."""
        self._command_mappings = self._build_command_mappings()
    
    def _build_command_mappings(self) -> Dict[str, Tuple[str, str]]:
        """Build mapping from Point-codes labels to category and key."""
        mappings = {}
        
        # Power commands
        mappings["ON"] = ("power", "on")
        mappings["OFF"] = ("power", "off")
        
        # Temperature commands (17-30°C)
        for temp in range(POINTCODES_MIN_TEMP, POINTCODES_MAX_TEMP + 1):
            mappings[f"{temp}c"] = ("temperature", str(temp))
        
        # Mode commands with pattern matching
        mode_patterns = {
            r"Mode\s+cool": ("mode", "cool"),
            r"Mode\s+dry": ("mode", "dry"),
            r"Mode\s+Heat": ("mode", "heat"),
            r"Mode\s+Fan": ("mode", "fan_only"),
            r"Mode\s+automatic.*": ("mode", "auto"),
            r"Mode\s+sleep.*": ("mode", "sleep"),
        }
        
        # Fan speed commands with pattern matching
        fan_patterns = {
            r"Fan\s+speed\s+low": ("fan_speed", "low"),
            r"Fan\s+speed\s+medium": ("fan_speed", "medium"),
            r"Fan\s+speed\s+high": ("fan_speed", "high"),
            r"Fan\s+speed\s+automatic": ("fan_speed", "auto"),
        }
        
        # Swing commands with pattern matching
        swing_patterns = {
            r"Swing\s+on": ("swing", "on"),
            r"swing\s+off": ("swing", "off"),
        }
        
        # Store patterns for later matching
        self._mode_patterns = mode_patterns
        self._fan_patterns = fan_patterns
        self._swing_patterns = swing_patterns
        
        return mappings
    
    def _match_pattern_command(self, label: str) -> Optional[Tuple[str, str]]:
        """Match label against regex patterns for complex commands."""
        # Try mode patterns
        for pattern, mapping in self._mode_patterns.items():
            if re.search(pattern, label, re.IGNORECASE):
                return mapping
        
        # Try fan patterns
        for pattern, mapping in self._fan_patterns.items():
            if re.search(pattern, label, re.IGNORECASE):
                return mapping
        
        # Try swing patterns
        for pattern, mapping in self._swing_patterns.items():
            if re.search(pattern, label, re.IGNORECASE):
                return mapping
        
        return None
    
    def _parse_line(self, line: str) -> Optional[Tuple[str, str, str]]:
        """Parse a single line from Point-codes file."""
        line = line.strip()
        
        # Skip empty lines
        if not line:
            return None
        
        # Parse format: [Command Label] - [Base64-encoded IR data]
        if " - " not in line:
            _LOGGER.warning("Invalid line format: %s", line)
            return None
        
        parts = line.split(" - ", 1)
        if len(parts) != 2:
            _LOGGER.warning("Invalid line format: %s", line)
            return None
        
        label = parts[0].strip()
        code = parts[1].strip()
        
        if not label or not code:
            _LOGGER.warning("Empty label or code in line: %s", line)
            return None
        
        return label, code, line
    
    def _map_command(self, label: str) -> Optional[Tuple[str, str]]:
        """Map Point-codes label to category and key."""
        # Try direct mapping first
        if label in self._command_mappings:
            return self._command_mappings[label]
        
        # Try pattern matching for complex commands
        pattern_match = self._match_pattern_command(label)
        if pattern_match:
            return pattern_match
        
        _LOGGER.warning("Unknown command label: %s", label)
        return None
    
    def parse_file(self, file_path: str | Path, device_id: str, device_name: str) -> Optional[IRCodeSet]:
        """Parse Point-codes file and create IRCodeSet."""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                _LOGGER.error("Point-codes file not found: %s", file_path)
                return None
            
            _LOGGER.info("Parsing Point-codes file: %s", file_path)
            
            # Create new code set
            code_set = IRCodeSet(
                device_id=device_id,
                device_name=device_name,
                device_type="air_conditioner",
                manufacturer="MOES",
                model="UFO-R11",
            )
            
            parsed_commands = 0
            skipped_commands = 0
            
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    parsed_line = self._parse_line(line)
                    if not parsed_line:
                        continue
                    
                    label, code, original_line = parsed_line
                    
                    # Map command to category and key
                    mapping = self._map_command(label)
                    if not mapping:
                        _LOGGER.debug("Skipping unmapped command on line %d: %s", line_num, label)
                        skipped_commands += 1
                        continue
                    
                    category, key = mapping
                    
                    # Create IR command
                    ir_command = IRCommand(
                        name=label,
                        code=code,
                        raw_data=original_line,
                    )
                    
                    # Add to code set
                    if code_set.add_command(category, key, ir_command):
                        parsed_commands += 1
                        _LOGGER.debug("Parsed command: %s -> %s.%s", label, category, key)
                    else:
                        _LOGGER.warning("Failed to add command: %s", label)
                        skipped_commands += 1
            
            _LOGGER.info(
                "Point-codes parsing complete. Parsed: %d, Skipped: %d, Total commands: %d",
                parsed_commands,
                skipped_commands,
                code_set.get_command_count()
            )
            
            # Validate the parsed code set
            validation = code_set.validate_commands()
            _LOGGER.info(
                "Validation results - Valid: %d, Invalid: %d, Missing: %d",
                len(validation["valid"]),
                len(validation["invalid"]),
                len(validation["missing"])
            )
            
            if validation["invalid"]:
                _LOGGER.warning("Invalid commands found: %s", validation["invalid"])
            
            if validation["missing"]:
                _LOGGER.warning("Missing essential commands: %s", validation["missing"])
            
            return code_set
            
        except Exception as e:
            _LOGGER.error("Failed to parse Point-codes file %s: %s", file_path, str(e))
            return None
    
    def parse_content(self, content: str, device_id: str, device_name: str) -> Optional[IRCodeSet]:
        """Parse Point-codes content from string and create IRCodeSet."""
        try:
            _LOGGER.info("Parsing Point-codes content for device %s", device_id)
            
            # Create new code set
            code_set = IRCodeSet(
                device_id=device_id,
                device_name=device_name,
                device_type="air_conditioner",
                manufacturer="MOES",
                model="UFO-R11",
            )
            
            parsed_commands = 0
            skipped_commands = 0
            
            for line_num, line in enumerate(content.splitlines(), 1):
                parsed_line = self._parse_line(line)
                if not parsed_line:
                    continue
                
                label, code, original_line = parsed_line
                
                # Map command to category and key
                mapping = self._map_command(label)
                if not mapping:
                    _LOGGER.debug("Skipping unmapped command on line %d: %s", line_num, label)
                    skipped_commands += 1
                    continue
                
                category, key = mapping
                
                # Create IR command
                ir_command = IRCommand(
                    name=label,
                    code=code,
                    raw_data=original_line,
                )
                
                # Add to code set
                if code_set.add_command(category, key, ir_command):
                    parsed_commands += 1
                    _LOGGER.debug("Parsed command: %s -> %s.%s", label, category, key)
                else:
                    _LOGGER.warning("Failed to add command: %s", label)
                    skipped_commands += 1
            
            _LOGGER.info(
                "Point-codes parsing complete. Parsed: %d, Skipped: %d, Total commands: %d",
                parsed_commands,
                skipped_commands,
                code_set.get_command_count()
            )
            
            return code_set
            
        except Exception as e:
            _LOGGER.error("Failed to parse Point-codes content: %s", str(e))
            return None
    
    def get_supported_commands(self) -> Dict[str, List[str]]:
        """Get list of supported commands by category."""
        commands = {
            "power": ["on", "off"],
            "temperature": [str(temp) for temp in range(POINTCODES_MIN_TEMP, POINTCODES_MAX_TEMP + 1)],
            "mode": ["cool", "dry", "heat", "fan_only", "auto", "sleep"],
            "fan_speed": ["low", "medium", "high", "auto"],
            "swing": ["on", "off"],
        }
        return commands
    
    def validate_point_codes_format(self, file_path: str | Path) -> Dict[str, any]:
        """Validate Point-codes file format without full parsing."""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                return {"valid": False, "error": "File not found"}
            
            total_lines = 0
            valid_lines = 0
            invalid_lines = []
            
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:  # Skip empty lines
                        continue
                    
                    total_lines += 1
                    
                    # Check format: [Command Label] - [Base64-encoded IR data]
                    if " - " in line:
                        parts = line.split(" - ", 1)
                        if len(parts) == 2 and parts[0].strip() and parts[1].strip():
                            valid_lines += 1
                        else:
                            invalid_lines.append(line_num)
                    else:
                        invalid_lines.append(line_num)
            
            return {
                "valid": len(invalid_lines) == 0,
                "total_lines": total_lines,
                "valid_lines": valid_lines,
                "invalid_lines": invalid_lines,
                "error": None if len(invalid_lines) == 0 else f"Invalid format on lines: {invalid_lines}",
            }
            
        except Exception as e:
            return {"valid": False, "error": str(e)}


def create_pointcodes_parser() -> PointCodesParser:
    """Create and return a Point-codes parser instance."""
    return PointCodesParser()