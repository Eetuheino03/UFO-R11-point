# UFO-R11 SmartIR Integration

A Home Assistant custom integration for controlling IR devices through MOES UFO-R11 Zigbee IR blasters with native climate entities and Point-codes dataset support.

## Overview

The UFO-R11 SmartIR integration provides seamless control of IR-based devices (primarily air conditioners) through UFO-R11 Zigbee IR blasters. It creates native Home Assistant climate entities while maintaining compatibility with the SmartIR ecosystem.

### Key Features

- **Native Climate Entities**: Full Home Assistant climate entity support with intuitive controls
- **Web Frontend Interface**: Modern web-based management panel accessible from Home Assistant sidebar
- **Point-codes Dataset**: Pre-configured with 55 IR commands for immediate air conditioner control
- **Zigbee2MQTT Integration**: Seamless communication through your existing Z2M setup
- **IR Code Learning**: Interactive learning interface for custom remote controls with real-time feedback
- **SmartIR Export**: Export configurations to SmartIR format for advanced users
- **Multi-device Support**: Configure multiple UFO-R11 devices for different rooms
- **Template System**: Extensible device templates for various manufacturers

## 🎛️ Web Frontend Interface

The UFO-R11 SmartIR integration includes a comprehensive web-based management interface accessible directly from your Home Assistant sidebar. This modern, responsive interface provides intuitive device management and IR code learning capabilities.

### ✨ Interface Features

- **Device Dashboard**: Real-time status monitoring for all UFO-R11 devices
- **Learning Wizard**: Step-by-step guided IR code learning with visual feedback
- **Command Testing**: Test learned IR commands directly from the interface
- **Export Tools**: Generate SmartIR configurations with one-click export
- **Import Utilities**: Import existing Point-codes and configuration files
- **Responsive Design**: Optimized for desktop, tablet, and mobile devices
- **Real-time Updates**: WebSocket-powered live status updates during learning sessions

### 📱 Quick Start Guide

1. **Access the Interface**: After installation, find "UFO-R11 SmartIR" in your Home Assistant sidebar
2. **Device Overview**: View all configured devices and their current status
3. **Learn IR Codes**:
   - Navigate to the "Learn Codes" tab
   - Select your device and command category
   - Follow the step-by-step learning wizard
   - Test and save learned codes
4. **Export Configurations**: Use the "Export & Import" tab to generate SmartIR files

### 🎯 Learning Interface

The learning interface provides an intuitive step-by-step process:

**Step 1: Command Setup**
- Select command category (Power, Temperature, Mode, Fan, Swing, Timer, Custom)
- Choose from preset command names or enter custom names
- Configure learning timeout (10-60 seconds)

**Step 2: IR Learning**
- Real-time learning status with progress indicators
- Visual feedback for signal detection
- Automatic timeout handling with retry options

**Step 3: Verification**
- Test learned commands before saving
- Preview IR code data
- Add to device command library

### 📊 Supported Command Categories

| Category | Examples | Description |
|----------|----------|-------------|
| **Power** | on, off, toggle | Device power control |
| **Temperature** | temp_16, temp_24, temp_30 | Temperature settings (16-30°C) |
| **Mode** | auto, cool, heat, dry, fan | HVAC operation modes |
| **Fan Speed** | auto, low, medium, high, turbo | Fan speed control |
| **Swing** | off, vertical, horizontal, both | Air direction control |
| **Timer** | timer_1h, timer_2h, timer_off | Timer functions |
| **Custom** | sleep, eco, turbo | Device-specific functions |

## Requirements

- Home Assistant 2023.1 or newer
- MQTT integration configured and running
- Zigbee2MQTT with UFO-R11 device paired
- MOES UFO-R11 Zigbee IR Blaster

## Installation

### Via HACS (Recommended)

1. Open HACS in your Home Assistant
2. Go to "Integrations"
3. Click the three dots menu and select "Custom repositories"
4. Add this repository URL: `https://github.com/UFO-R11/ufo-r11-smartir`
5. Select "Integration" as the category
6. Click "Add"
7. Search for "UFO-R11 SmartIR" and install
8. Restart Home Assistant

### Manual Installation

1. Download the latest release from GitHub
2. Extract the files to `custom_components/ufo_r11_smartir/` in your config directory
3. Restart Home Assistant

## Configuration

### Step 1: Add Integration

1. Go to Settings → Devices & Services
2. Click "Add Integration"
3. Search for "UFO-R11 SmartIR"
4. Follow the setup wizard

### Step 2: Device Setup

The setup wizard will guide you through:

1. **Device Discovery**: Enter your UFO-R11 device ID and MQTT topic
2. **Device Type**: Select Air Conditioner (recommended), TV, or Custom
3. **Code Source**: Choose Point-codes for immediate AC support
4. **Device Testing**: Verify commands work with your device

### Device Configuration Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| Device ID | UFO-R11 device identifier from Zigbee2MQTT | `0x00158d00012345ab` |
| Device Name | Friendly name for the device | `Living Room AC` |
| MQTT Topic | Base MQTT topic for the device | `zigbee2mqtt/UFO-R11-Device` |

## Usage

### Climate Entity Control

Once configured, your UFO-R11 device appears as a standard Home Assistant climate entity with full functionality:

- **Temperature Control**: Set target temperature (17-30°C with Point-codes)
- **HVAC Modes**: Off, Cool, Heat, Dry, Fan Only, Auto, Sleep
- **Fan Speeds**: Low, Medium, High, Auto
- **Swing Control**: Off, Vertical
- **Power Control**: Turn device on/off

### Custom Services

The integration provides several custom services for advanced functionality:

#### Learn IR Code
```yaml
service: ufo_r11_smartir.learn_ir_code
data:
  device_id: "0x00158d00012345ab"
  command_name: "power_toggle"
  timeout: 30
```

#### Export SmartIR Configuration
```yaml
service: ufo_r11_smartir.export_smartir
data:
  device_id: "0x00158d00012345ab"
  output_path: "/config/smartir_export/my_ac.json"
```

#### Test IR Command
```yaml
service: ufo_r11_smartir.test_command
data:
  device_id: "0x00158d00012345ab"
  ir_code: "CUMRQxElAnUGJQJAAUAHQAPAAeATC8..."
```

### Web Interface Usage

The UFO-R11 SmartIR web interface provides a user-friendly alternative to services and automations for device management and IR code learning.

#### Accessing the Interface

1. After installation and setup, look for "UFO-R11 SmartIR" in your Home Assistant sidebar
2. Click to open the web interface
3. The interface will load with tabs for different functions:
   - **Devices**: Overview of all UFO-R11 devices
   - **Learn Codes**: Interactive IR code learning
   - **Test Commands**: Test learned IR codes
   - **Export & Import**: Configuration management

#### Device Management

The Devices tab shows:
- Device status (online/offline)
- Number of learned commands
- Device configuration details
- Quick access to device-specific actions

#### Learning New Commands

1. **Navigate to Learn Codes tab**
2. **Select your device** from the dropdown
3. **Choose command category**:
   - Power (on, off, toggle)
   - Temperature (16°C to 30°C)
   - Mode (auto, cool, heat, dry, fan)
   - Fan Speed (auto, low, medium, high, turbo)
   - Swing (off, vertical, horizontal, both)
   - Timer (1h, 2h, 4h, 8h, off)
   - Custom (any custom command)
4. **Enter command name** or select from presets
5. **Click "Start Learning"**
6. **Point your remote** at the UFO-R11 device
7. **Press the desired button** within the timeout period
8. **Test the learned code** to verify it works
9. **Save the command** to your device

#### Testing Commands

Use the Test Commands tab to:
- Test any learned IR command
- Send custom IR codes for troubleshooting
- Verify device responses
- Debug IR code issues

#### Export & Import

- **Export SmartIR**: Generate SmartIR-compatible configuration files
- **Import Point-codes**: Load existing IR code databases
- **Backup/Restore**: Save and restore device configurations

### Automation Examples

#### Temperature-based Automation
```yaml
automation:
  - alias: "Auto AC Control"
    trigger:
      - platform: numeric_state
        entity_id: sensor.living_room_temperature
        above: 25
    action:
      - service: climate.set_temperature
        target:
          entity_id: climate.living_room_ac
        data:
          temperature: 22
          hvac_mode: cool
```

#### Scene Integration
```yaml
scene:
  - name: "Movie Night"
    entities:
      climate.living_room_ac:
        hvac_mode: cool
        temperature: 20
        fan_mode: low
```

## Point-codes Dataset

The integration includes a comprehensive dataset of 55 pre-configured IR commands optimized for air conditioner control:

- **Temperature Range**: 17°C to 30°C
- **Complete Mode Set**: All standard HVAC modes
- **Fan Control**: Multiple speed settings
- **Special Functions**: Sleep mode, swing control
- **Power Management**: On/off commands

This eliminates the need for manual IR code learning for most air conditioner models.

## Device Templates

### Air Conditioner Template
- Temperature range: 17-30°C
- HVAC modes: Cool, Heat, Dry, Fan, Auto, Sleep
- Fan speeds: Low, Medium, High, Auto
- Swing modes: Off, Vertical

### Custom Templates
Create custom device templates for specific manufacturers or device types by following the template structure in the integration documentation.

## Troubleshooting

### Common Issues

**Device Not Found**
- Verify UFO-R11 is paired with Zigbee2MQTT
- Check device ID matches exactly (case-sensitive)
- Ensure MQTT integration is working

**Commands Not Working**
- Test MQTT communication manually
- Verify IR codes are correct for your device
- Check device positioning and IR signal path
- Try learning new codes for your specific remote

**Integration Not Loading**
- Check Home Assistant logs for errors
- Verify all dependencies are installed
- Restart Home Assistant after installation

**Web Interface Issues**
- **Panel not visible**: Restart Home Assistant after installation and clear browser cache
- **Loading errors**: Check browser console for JavaScript errors and ensure stable internet connection
- **Learning timeouts**: Verify UFO-R11 device is online and MQTT communication is working
- **API errors**: Check Home Assistant logs for authentication or permission issues
- **Mobile display issues**: Clear browser cache and ensure responsive mode is enabled

**WebSocket Connection Issues**
- Check Home Assistant WebSocket connectivity
- Verify authentication tokens are valid
- Restart Home Assistant if WebSocket errors persist
- Check browser developer tools for connection errors

### Debug Logging

Enable debug logging for troubleshooting:

```yaml
logger:
  default: warning
  logs:
    custom_components.ufo_r11_smartir: debug
```

### MQTT Testing

Test MQTT communication directly:

```bash
# Subscribe to device status
mosquitto_sub -h YOUR_MQTT_HOST -t "zigbee2mqtt/UFO-R11-Device"

# Send test command
mosquitto_pub -h YOUR_MQTT_HOST -t "zigbee2mqtt/UFO-R11-Device/set" -m '{"ir_code_to_send": "YOUR_IR_CODE"}'
```

## Advanced Configuration

### Options Configuration

Configure advanced options through the integration's options flow:

- **Update Interval**: How often to check device status (10-300 seconds)
- **Enable Learning**: Allow IR code learning functionality
- **Auto Export**: Automatically export learned codes to SmartIR format

### Multiple Devices

Configure multiple UFO-R11 devices by running the integration setup for each device with unique device IDs and names.

## Development

### Contributing

Contributions are welcome! Please read the contributing guidelines and submit pull requests for any improvements.

### Architecture

The integration follows Home Assistant best practices:

- **Config Flow**: Standard HA configuration flow
- **Coordinator Pattern**: Efficient data updates
- **Entity Platform**: Native climate entity implementation
- **Service Layer**: Custom services for advanced functionality
- **Web Frontend**: Modern web interface with real-time updates
- **API Layer**: RESTful API with WebSocket support

### Code Structure

```
custom_components/ufo_r11_smartir/
├── __init__.py              # Integration setup and coordinator
├── manifest.json           # HACS manifest
├── config_flow.py          # Configuration flow
├── climate.py              # Climate platform
├── const.py                # Constants and configuration
├── services.yaml           # Service definitions
├── strings.json            # Localization strings
├── translations/           # Multi-language support
├── api.py                  # REST API endpoints and WebSocket handlers
├── frontend_panel.py       # Home Assistant panel registration
├── device_manager.py       # Device management and coordination
├── smartir_generator.py    # SmartIR configuration generator
├── www/                    # Web frontend files
│   ├── index.html          # Main HTML entry point
│   ├── ufo-r11-panel.js    # Main application JavaScript
│   ├── ufo-r11-learning.js # Learning interface module
│   └── ufo-r11-styles.css  # Responsive CSS styling
└── README.md              # This file
```

### Web Frontend Architecture

The web interface follows a modular JavaScript architecture:

- **index.html**: Entry point with loading states and error handling
- **ufo-r11-panel.js**: Main application class with device management and tabbed interface
- **ufo-r11-learning.js**: Specialized learning interface with step-by-step wizard
- **ufo-r11-styles.css**: Responsive CSS framework with dark mode support

### API Endpoints

The integration provides comprehensive REST API endpoints:

- `GET /api/ufo_r11_smartir/devices` - List all configured devices
- `GET /api/ufo_r11_smartir/device/{device_id}` - Get device details and commands
- `POST /api/ufo_r11_smartir/learn` - Start IR learning session
- `POST /api/ufo_r11_smartir/test` - Test IR command
- `POST /api/ufo_r11_smartir/export` - Export SmartIR configuration
- `POST /api/ufo_r11_smartir/import` - Import IR codes from file
- `WebSocket /api/ufo_r11_smartir/ws/{device_id}` - Real-time learning updates

## Support

- **Documentation**: [GitHub Wiki](https://github.com/UFO-R11/ufo-r11-smartir/wiki)
- **Issues**: [GitHub Issues](https://github.com/UFO-R11/ufo-r11-smartir/issues)
- **Discussions**: [GitHub Discussions](https://github.com/UFO-R11/ufo-r11-smartir/discussions)
- **Community**: [Home Assistant Community Forum](https://community.home-assistant.io)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- SmartIR project for inspiration and compatibility
- Home Assistant community for support and feedback
- MOES for the UFO-R11 hardware
- Point-codes dataset contributors