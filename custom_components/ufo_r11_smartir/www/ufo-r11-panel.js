/**
 * UFO-R11 SmartIR Frontend Panel
 * Main JavaScript application for device management and IR code learning
 */

class UFOSmartIRPanel {
    constructor() {
        this.hass = null;
        this.devices = [];
        this.currentDevice = null;
        this.learningSession = null;
        this.websocket = null;
        this.notifications = [];
        
        this.init();
    }

    async init() {
        await this.loadDevices();
        this.setupWebSocket();
        this.render();
        this.bindEvents();
        
        // Refresh devices every 30 seconds
        setInterval(() => this.loadDevices(), 30000);
    }

    async loadDevices() {
        try {
            const response = await fetch('/api/ufo_r11_smartir/devices', {
                headers: {
                    'Authorization': `Bearer ${this.hass?.auth?.access_token || ''}`,
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                this.devices = data.devices || [];
                this.updateDevicesDisplay();
            } else {
                this.showNotification('Failed to load devices', 'error');
            }
        } catch (error) {
            console.error('Error loading devices:', error);
            this.showNotification('Failed to load devices: ' + error.message, 'error');
        }
    }

    setupWebSocket() {
        if (this.hass?.connection) {
            this.hass.connection.subscribeMessage(
                (message) => this.handleWebSocketMessage(message),
                { type: 'ufo_r11_smartir/subscribe' }
            );
        }
    }

    handleWebSocketMessage(message) {
        if (message.type === 'device_update') {
            this.handleDeviceUpdate(message.data);
        } else if (message.type === 'learning_update') {
            this.handleLearningUpdate(message.data);
        }
    }

    handleDeviceUpdate(data) {
        const deviceIndex = this.devices.findIndex(d => d.device_id === data.device_id);
        if (deviceIndex >= 0) {
            this.devices[deviceIndex] = { ...this.devices[deviceIndex], ...data };
            this.updateDevicesDisplay();
        }
    }

    handleLearningUpdate(data) {
        if (this.learningSession && this.learningSession.device_id === data.device_id) {
            this.learningSession = { ...this.learningSession, ...data };
            this.updateLearningDisplay();
        }
    }

    render() {
        const container = document.createElement('div');
        container.className = 'ufo-r11-panel';
        container.innerHTML = `
            <div class="ufo-r11-header">
                <div class="ufo-r11-logo">
                    <ha-icon icon="mdi:remote"></ha-icon>
                </div>
                <div>
                    <h1 class="ufo-r11-title">UFO-R11 SmartIR</h1>
                    <p class="ufo-r11-subtitle">Device Management & IR Code Learning</p>
                </div>
            </div>

            <div id="ufo-notifications"></div>

            <div class="ufo-tabs">
                <ul class="ufo-tab-list">
                    <li><button class="ufo-tab active" data-tab="devices">Devices</button></li>
                    <li><button class="ufo-tab" data-tab="learning">Learn Codes</button></li>
                    <li><button class="ufo-tab" data-tab="testing">Test Commands</button></li>
                    <li><button class="ufo-tab" data-tab="export">Export & Import</button></li>
                </ul>
            </div>

            <div id="devices-tab" class="ufo-tab-content active">
                <div class="ufo-card">
                    <div class="ufo-card-header">
                        <h2 class="ufo-card-title">
                            <ha-icon icon="mdi:devices"></ha-icon>
                            Managed Devices
                        </h2>
                        <div class="ufo-card-actions">
                            <button class="ufo-button ufo-button-primary" id="refresh-devices">
                                <ha-icon icon="mdi:refresh"></ha-icon>
                                Refresh
                            </button>
                        </div>
                    </div>
                    <div class="ufo-card-content">
                        <div id="devices-container">
                            <div class="ufo-loading">
                                <div class="ufo-spinner"></div>
                                <p>Loading devices...</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div id="learning-tab" class="ufo-tab-content">
                <div class="ufo-card">
                    <div class="ufo-card-header">
                        <h2 class="ufo-card-title">
                            <ha-icon icon="mdi:school"></ha-icon>
                            IR Code Learning
                        </h2>
                    </div>
                    <div class="ufo-card-content">
                        <div id="learning-container"></div>
                    </div>
                </div>
            </div>

            <div id="testing-tab" class="ufo-tab-content">
                <div class="ufo-card">
                    <div class="ufo-card-header">
                        <h2 class="ufo-card-title">
                            <ha-icon icon="mdi:test-tube"></ha-icon>
                            Command Testing
                        </h2>
                    </div>
                    <div class="ufo-card-content">
                        <div id="testing-container"></div>
                    </div>
                </div>
            </div>

            <div id="export-tab" class="ufo-tab-content">
                <div class="ufo-card">
                    <div class="ufo-card-header">
                        <h2 class="ufo-card-title">
                            <ha-icon icon="mdi:export"></ha-icon>
                            Export & Import
                        </h2>
                    </div>
                    <div class="ufo-card-content">
                        <div id="export-container"></div>
                    </div>
                </div>
            </div>
        `;

        // Clear and append to panel root
        const panelRoot = document.querySelector('ufo-r11-smartir') || document.body;
        panelRoot.innerHTML = '';
        panelRoot.appendChild(container);

        this.initializeTabContent();
    }

    initializeTabContent() {
        this.initializeLearningTab();
        this.initializeTestingTab();
        this.initializeExportTab();
    }

    initializeLearningTab() {
        const container = document.getElementById('learning-container');
        container.innerHTML = `
            <div class="ufo-form-group">
                <label class="ufo-form-label">Select Device</label>
                <select class="ufo-form-select" id="learning-device-select">
                    <option value="">Choose a device...</option>
                </select>
            </div>

            <div id="learning-wizard" class="ufo-learning-wizard" style="display: none;">
                <div class="ufo-learning-steps">
                    <div class="ufo-learning-step active" data-step="1">
                        <div class="ufo-learning-step-number">1</div>
                        <div class="ufo-learning-step-label">Select Command</div>
                    </div>
                    <div class="ufo-learning-step" data-step="2">
                        <div class="ufo-learning-step-number">2</div>
                        <div class="ufo-learning-step-label">Learn IR Code</div>
                    </div>
                    <div class="ufo-learning-step" data-step="3">
                        <div class="ufo-learning-step-number">3</div>
                        <div class="ufo-learning-step-label">Verify & Save</div>
                    </div>
                </div>

                <div id="learning-step-1" class="ufo-learning-content">
                    <h3>Select Command to Learn</h3>
                    <div class="ufo-form-group">
                        <label class="ufo-form-label">Command Category</label>
                        <select class="ufo-form-select" id="command-category">
                            <option value="power">Power Control</option>
                            <option value="temperature">Temperature</option>
                            <option value="mode">Mode Control</option>
                            <option value="fan">Fan Speed</option>
                            <option value="swing">Swing Control</option>
                            <option value="timer">Timer</option>
                            <option value="custom">Custom Command</option>
                        </select>
                    </div>
                    <div class="ufo-form-group">
                        <label class="ufo-form-label">Command Name</label>
                        <input type="text" class="ufo-form-input" id="command-name" 
                               placeholder="e.g., power_on, temp_24, mode_cool">
                    </div>
                    <button class="ufo-button ufo-button-primary" id="start-learning">
                        Start Learning
                    </button>
                </div>

                <div id="learning-step-2" class="ufo-learning-content" style="display: none;">
                    <h3>Point Remote at UFO-R11 Device</h3>
                    <p class="ufo-learning-instruction">
                        Point your remote control at the UFO-R11 device and press the button 
                        you want to learn within the next 30 seconds.
                    </p>
                    <div class="ufo-learning-status waiting">
                        <div class="ufo-spinner"></div>
                        <span>Waiting for IR signal...</span>
                    </div>
                    <div class="ufo-progress">
                        <div class="ufo-progress-bar" id="learning-progress"></div>
                    </div>
                    <button class="ufo-button ufo-button-secondary" id="cancel-learning">
                        Cancel Learning
                    </button>
                </div>

                <div id="learning-step-3" class="ufo-learning-content" style="display: none;">
                    <h3>Learning Complete</h3>
                    <div class="ufo-learning-status success">
                        <ha-icon icon="mdi:check-circle"></ha-icon>
                        <span>IR code learned successfully!</span>
                    </div>
                    <div class="ufo-form-group">
                        <label class="ufo-form-label">Learned IR Code</label>
                        <textarea class="ufo-form-input ufo-form-textarea" id="learned-code" readonly></textarea>
                    </div>
                    <div class="ufo-form-group">
                        <button class="ufo-button ufo-button-success" id="save-learned-code">
                            Save Code
                        </button>
                        <button class="ufo-button ufo-button-secondary" id="test-learned-code">
                            Test Code
                        </button>
                        <button class="ufo-button ufo-button-secondary" id="retry-learning">
                            Learn Again
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    initializeTestingTab() {
        const container = document.getElementById('testing-container');
        container.innerHTML = `
            <div class="ufo-form-group">
                <label class="ufo-form-label">Select Device</label>
                <select class="ufo-form-select" id="testing-device-select">
                    <option value="">Choose a device...</option>
                </select>
            </div>

            <div id="testing-interface" style="display: none;">
                <div class="ufo-form-group">
                    <label class="ufo-form-label">Test Method</label>
                    <div class="ufo-tabs">
                        <ul class="ufo-tab-list">
                            <li><button class="ufo-tab active" data-tab="test-commands">Available Commands</button></li>
                            <li><button class="ufo-tab" data-tab="test-manual">Manual IR Code</button></li>
                        </ul>
                    </div>
                </div>

                <div id="test-commands-tab" class="ufo-tab-content active">
                    <div id="commands-list"></div>
                </div>

                <div id="test-manual-tab" class="ufo-tab-content">
                    <div class="ufo-form-group">
                        <label class="ufo-form-label">IR Code</label>
                        <textarea class="ufo-form-input ufo-form-textarea" id="manual-ir-code" 
                                  placeholder="Enter IR code in hex format (e.g., 02DC002D00AD...)"></textarea>
                    </div>
                    <button class="ufo-button ufo-button-primary" id="test-manual-code">
                        Send IR Code
                    </button>
                </div>
            </div>
        `;
    }

    initializeExportTab() {
        const container = document.getElementById('export-container');
        container.innerHTML = `
            <div class="ufo-form-group">
                <label class="ufo-form-label">Select Device</label>
                <select class="ufo-form-select" id="export-device-select">
                    <option value="">Choose a device...</option>
                </select>
            </div>

            <div id="export-interface" style="display: none;">
                <div class="ufo-tabs">
                    <ul class="ufo-tab-list">
                        <li><button class="ufo-tab active" data-tab="export-smartir">Export SmartIR</button></li>
                        <li><button class="ufo-tab" data-tab="import-codes">Import Codes</button></li>
                        <li><button class="ufo-tab" data-tab="backup-device">Backup Device</button></li>
                    </ul>
                </div>

                <div id="export-smartir-tab" class="ufo-tab-content active">
                    <p>Export device configuration as SmartIR JSON file for use with the SmartIR integration.</p>
                    <div class="ufo-form-group">
                        <label class="ufo-form-label">Output Path (optional)</label>
                        <input type="text" class="ufo-form-input" id="export-path" 
                               placeholder="Leave empty for default location">
                    </div>
                    <button class="ufo-button ufo-button-primary" id="export-smartir-btn">
                        <ha-icon icon="mdi:download"></ha-icon>
                        Export SmartIR Config
                    </button>
                </div>

                <div id="import-codes-tab" class="ufo-tab-content">
                    <p>Import IR codes from Point-codes file or custom JSON format.</p>
                    <div class="ufo-form-group">
                        <label class="ufo-form-label">File Path</label>
                        <input type="text" class="ufo-form-input" id="import-file-path" 
                               placeholder="/config/custom_components/ufo_r11_smartir/data/Point-codes">
                    </div>
                    <div class="ufo-form-group">
                        <label class="ufo-form-label">File Format</label>
                        <select class="ufo-form-select" id="import-format">
                            <option value="pointcodes">Point-codes Format</option>
                            <option value="json">JSON Format</option>
                        </select>
                    </div>
                    <button class="ufo-button ufo-button-primary" id="import-codes-btn">
                        <ha-icon icon="mdi:upload"></ha-icon>
                        Import Codes
                    </button>
                </div>

                <div id="backup-device-tab" class="ufo-tab-content">
                    <p>Create a backup of all learned IR codes for this device.</p>
                    <button class="ufo-button ufo-button-primary" id="backup-device-btn">
                        <ha-icon icon="mdi:content-save"></ha-icon>
                        Create Backup
                    </button>
                </div>
            </div>
        `;
    }

    bindEvents() {
        // Tab switching
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('ufo-tab')) {
                this.switchTab(e.target.dataset.tab);
            }
        });

        // Refresh devices
        document.getElementById('refresh-devices')?.addEventListener('click', () => {
            this.loadDevices();
        });

        // Learning events
        this.bindLearningEvents();
        this.bindTestingEvents();
        this.bindExportEvents();
    }

    bindLearningEvents() {
        const deviceSelect = document.getElementById('learning-device-select');
        deviceSelect?.addEventListener('change', (e) => {
            const wizard = document.getElementById('learning-wizard');
            if (e.target.value) {
                wizard.style.display = 'block';
                this.resetLearningWizard();
            } else {
                wizard.style.display = 'none';
            }
        });

        document.getElementById('start-learning')?.addEventListener('click', () => {
            this.startLearning();
        });

        document.getElementById('cancel-learning')?.addEventListener('click', () => {
            this.cancelLearning();
        });

        document.getElementById('save-learned-code')?.addEventListener('click', () => {
            this.saveLearningResults();
        });

        document.getElementById('test-learned-code')?.addEventListener('click', () => {
            this.testLearnedCode();
        });

        document.getElementById('retry-learning')?.addEventListener('click', () => {
            this.resetLearningWizard();
        });
    }

    bindTestingEvents() {
        const deviceSelect = document.getElementById('testing-device-select');
        deviceSelect?.addEventListener('change', (e) => {
            const interfaceEl = document.getElementById('testing-interface');
            if (e.target.value) {
                interfaceEl.style.display = 'block';
                this.loadDeviceCommands(e.target.value);
            } else {
                interfaceEl.style.display = 'none';
            }
        });

        document.getElementById('test-manual-code')?.addEventListener('click', () => {
            this.testManualCode();
        });
    }

    bindExportEvents() {
        const deviceSelect = document.getElementById('export-device-select');
        deviceSelect?.addEventListener('change', (e) => {
            const interfaceEl = document.getElementById('export-interface');
            interfaceEl.style.display = e.target.value ? 'block' : 'none';
        });

        document.getElementById('export-smartir-btn')?.addEventListener('click', () => {
            this.exportSmartIR();
        });

        document.getElementById('import-codes-btn')?.addEventListener('click', () => {
            this.importCodes();
        });

        document.getElementById('backup-device-btn')?.addEventListener('click', () => {
            this.backupDevice();
        });
    }

    switchTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.ufo-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.tab === tabName);
        });

        // Update tab content
        document.querySelectorAll('.ufo-tab-content').forEach(content => {
            content.classList.toggle('active', content.id === `${tabName}-tab`);
        });

        // Load tab-specific data
        if (tabName === 'devices') {
            this.loadDevices();
        } else if (tabName === 'learning' || tabName === 'testing' || tabName === 'export') {
            this.updateDeviceSelects();
        }
    }

    updateDevicesDisplay() {
        const container = document.getElementById('devices-container');
        
        if (this.devices.length === 0) {
            container.innerHTML = `
                <div class="ufo-text-center">
                    <ha-icon icon="mdi:devices" style="font-size: 48px; color: var(--ufo-text-secondary); margin-bottom: 16px;"></ha-icon>
                    <h3>No Devices Found</h3>
                    <p>Add UFO-R11 devices through the Home Assistant integrations page.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = `
            <div class="ufo-devices-grid">
                ${this.devices.map(device => this.renderDeviceCard(device)).join('')}
            </div>
        `;

        // Bind device-specific events
        this.bindDeviceEvents();
    }

    renderDeviceCard(device) {
        const statusClass = device.available ? 'online' : '';
        const commandCount = device.command_count || 0;
        const lastSeen = device.last_seen ? new Date(device.last_seen).toLocaleString() : 'Never';

        return `
            <div class="ufo-card ufo-device-card" data-device-id="${device.device_id}">
                <div class="ufo-device-status ${statusClass}"></div>
                <div class="ufo-card-content">
                    <div class="ufo-device-info">
                        <h3 class="ufo-device-name">${device.device_name}</h3>
                        <p class="ufo-device-id">${device.device_id}</p>
                    </div>
                    
                    <div class="ufo-device-stats">
                        <div class="ufo-stat">
                            <p class="ufo-stat-value">${commandCount}</p>
                            <p class="ufo-stat-label">Commands</p>
                        </div>
                        <div class="ufo-stat">
                            <p class="ufo-stat-value">${device.available ? 'Online' : 'Offline'}</p>
                            <p class="ufo-stat-label">Status</p>
                        </div>
                    </div>
                    
                    <div class="ufo-form-group ufo-mb-0">
                        <button class="ufo-button ufo-button-primary ufo-button-small" 
                                onclick="ufoPanel.openDeviceDetails('${device.device_id}')">
                            <ha-icon icon="mdi:information"></ha-icon>
                            Details
                        </button>
                        <button class="ufo-button ufo-button-secondary ufo-button-small" 
                                onclick="ufoPanel.quickTest('${device.device_id}')">
                            <ha-icon icon="mdi:play"></ha-icon>
                            Test
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    bindDeviceEvents() {
        // Device card clicks are handled through onclick attributes in renderDeviceCard
    }

    updateDeviceSelects() {
        const selects = [
            'learning-device-select',
            'testing-device-select', 
            'export-device-select'
        ];
        
        selects.forEach(selectId => {
            const select = document.getElementById(selectId);
            if (select) {
                const currentValue = select.value;
                select.innerHTML = '<option value="">Choose a device...</option>';
                
                this.devices.forEach(device => {
                    const option = document.createElement('option');
                    option.value = device.device_id;
                    option.textContent = `${device.device_name} (${device.device_id})`;
                    select.appendChild(option);
                });
                
                // Restore previous selection if still valid
                if (currentValue && this.devices.find(d => d.device_id === currentValue)) {
                    select.value = currentValue;
                }
            }
        });
    }

    async openDeviceDetails(deviceId) {
        try {
            const response = await fetch(`/api/ufo_r11_smartir/device/${deviceId}`, {
                headers: {
                    'Authorization': `Bearer ${this.hass?.auth?.access_token || ''}`,
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                const device = await response.json();
                this.showDeviceModal(device);
            } else {
                this.showNotification('Failed to load device details', 'error');
            }
        } catch (error) {
            this.showNotification('Error loading device details: ' + error.message, 'error');
        }
    }

    showDeviceModal(device) {
        const modal = document.createElement('div');
        modal.className = 'ufo-modal-overlay';
        modal.innerHTML = `
            <div class="ufo-modal">
                <div class="ufo-modal-header">
                    <h2 class="ufo-modal-title">${device.device_name}</h2>
                    <button class="ufo-modal-close">&times;</button>
                </div>
                <div class="ufo-modal-content">
                    <div class="ufo-form-group">
                        <label class="ufo-form-label">Device ID</label>
                        <input type="text" class="ufo-form-input" value="${device.device_id}" readonly>
                    </div>
                    <div class="ufo-form-group">
                        <label class="ufo-form-label">MQTT Topic</label>
                        <input type="text" class="ufo-form-input" value="${device.mqtt_topic}" readonly>
                    </div>
                    <div class="ufo-form-group">
                        <label class="ufo-form-label">Status</label>
                        <input type="text" class="ufo-form-input" value="${device.available ? 'Online' : 'Offline'}" readonly>
                    </div>
                    <div class="ufo-form-group">
                        <label class="ufo-form-label">Available Commands</label>
                        <div class="ufo-commands-list">
                            ${this.renderCommandsList(device.commands || {})}
                        </div>
                    </div>
                </div>
                <div class="ufo-modal-footer">
                    <button class="ufo-button ufo-button-secondary close-modal">Close</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Bind close events
        modal.querySelector('.ufo-modal-close').addEventListener('click', () => {
            document.body.removeChild(modal);
        });
        modal.querySelector('.close-modal').addEventListener('click', () => {
            document.body.removeChild(modal);
        });
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                document.body.removeChild(modal);
            }
        });
    }

    renderCommandsList(commands) {
        let html = '';
        Object.entries(commands).forEach(([category, categoryCommands]) => {
            if (typeof categoryCommands === 'object') {
                Object.entries(categoryCommands).forEach(([key, command]) => {
                    html += `
                        <div class="ufo-command-item">
                            <div class="ufo-command-info">
                                <p class="ufo-command-name">${category}.${key}</p>
                                <p class="ufo-command-code">${command.code || 'N/A'}</p>
                            </div>
                            <div class="ufo-command-actions">
                                <button class="ufo-button ufo-button-small ufo-button-primary" 
                                        onclick="ufoPanel.testCommand('${this.currentDevice || ''}', '${command.code}')">
                                    Test
                                </button>
                            </div>
                        </div>
                    `;
                });
            }
        });
        return html || '<p>No commands available</p>';
    }

    async quickTest(deviceId) {
        // TODO: Implement quick test functionality
        this.showNotification('Quick test functionality coming soon', 'info');
    }

    // Learning methods
    resetLearningWizard() {
        // Reset all steps
        document.querySelectorAll('.ufo-learning-step').forEach((step, index) => {
            step.classList.toggle('active', index === 0);
            step.classList.remove('completed');
        });

        // Show first step
        document.getElementById('learning-step-1').style.display = 'block';
        document.getElementById('learning-step-2').style.display = 'none';
        document.getElementById('learning-step-3').style.display = 'none';

        // Reset form
        document.getElementById('command-name').value = '';
        document.getElementById('command-category').value = 'power';
    }

    async startLearning() {
        const deviceId = document.getElementById('learning-device-select').value;
        const commandName = document.getElementById('command-name').value;
        
        if (!deviceId || !commandName) {
            this.showNotification('Please select a device and enter a command name', 'error');
            return;
        }

        try {
            const response = await fetch('/api/ufo_r11_smartir/learn', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.hass?.auth?.access_token || ''}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    device_id: deviceId,
                    command_name: commandName,
                    timeout: 30
                })
            });

            if (response.ok) {
                this.showLearningStep(2);
                this.startLearningProgress();
                this.showNotification('Learning session started', 'success');
            } else {
                const error = await response.json();
                this.showNotification('Failed to start learning: ' + error.error, 'error');
            }
        } catch (error) {
            this.showNotification('Error starting learning: ' + error.message, 'error');
        }
    }

    showLearningStep(stepNumber) {
        // Update step indicators
        document.querySelectorAll('.ufo-learning-step').forEach((step, index) => {
            const stepNum = index + 1;
            step.classList.toggle('active', stepNum === stepNumber);
            step.classList.toggle('completed', stepNum < stepNumber);
        });

        // Show corresponding content
        for (let i = 1; i <= 3; i++) {
            const content = document.getElementById(`learning-step-${i}`);
            content.style.display = i === stepNumber ? 'block' : 'none';
        }
    }

    startLearningProgress() {
        const progressBar = document.getElementById('learning-progress');
        let progress = 0;
        
        const interval = setInterval(() => {
            progress += 100 / 30; // 30 second timeout
            progressBar.style.width = Math.min(progress, 100) + '%';
            
            if (progress >= 100) {
                clearInterval(interval);
                this.learningTimeout();
            }
        }, 1000);

        this.learningProgressInterval = interval;
    }

    cancelLearning() {
        if (this.learningProgressInterval) {
            clearInterval(this.learningProgressInterval);
        }
        this.resetLearningWizard();
        this.showNotification('Learning cancelled', 'info');
    }

    learningTimeout() {
        this.showNotification('Learning timeout - no IR signal received', 'error');
        this.resetLearningWizard();
    }

    async testLearnedCode() {
        const deviceId = document.getElementById('learning-device-select').value;
        const irCode = document.getElementById('learned-code').value;
        
        await this.testCommand(deviceId, irCode);
    }

    saveLearningResults() {
        this.showNotification('IR code saved successfully', 'success');
        this.resetLearningWizard();
        this.loadDevices(); // Refresh device list
    }

    // Testing methods
    async loadDeviceCommands(deviceId) {
        try {
            const response = await fetch(`/api/ufo_r11_smartir/device/${deviceId}`, {
                headers: {
                    'Authorization': `Bearer ${this.hass?.auth?.access_token || ''}`,
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                const device = await response.json();
                const commandsList = document.getElementById('commands-list');
                commandsList.innerHTML = this.renderCommandsList(device.commands || {});
                this.currentDevice = deviceId;
            }
        } catch (error) {
            this.showNotification('Error loading device commands: ' + error.message, 'error');
        }
    }

    async testCommand(deviceId, irCode) {
        try {
            const response = await fetch('/api/ufo_r11_smartir/test', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.hass?.auth?.access_token || ''}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    device_id: deviceId,
                    ir_code: irCode
                })
            });

            if (response.ok) {
                this.showNotification('IR command sent successfully', 'success');
            } else {
                const error = await response.json();
                this.showNotification('Failed to send command: ' + error.error, 'error');
            }
        } catch (error) {
            this.showNotification('Error sending command: ' + error.message, 'error');
        }
    }

    async testManualCode() {
        const deviceId = document.getElementById('testing-device-select').value;
        const irCode = document.getElementById('manual-ir-code').value;
        
        if (!deviceId || !irCode) {
            this.showNotification('Please select a device and enter an IR code', 'error');
            return;
        }

        await this.testCommand(deviceId, irCode);
    }

    // Export/Import methods
    async exportSmartIR() {
        const deviceId = document.getElementById('export-device-select').value;
        const outputPath = document.getElementById('export-path').value;
        
        if (!deviceId) {
            this.showNotification('Please select a device', 'error');
            return;
        }

        try {
            const response = await fetch('/api/ufo_r11_smartir/export', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.hass?.auth?.access_token || ''}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    device_id: deviceId,
                    output_path: outputPath || undefined
                })
            });

            if (response.ok) {
                this.showNotification('SmartIR configuration exported successfully', 'success');
            } else {
                const error = await response.json();
                this.showNotification('Export failed: ' + error.error, 'error');
            }
        } catch (error) {
            this.showNotification('Export error: ' + error.message, 'error');
        }
    }

    async importCodes() {
        const deviceId = document.getElementById('export-device-select').value;
        const filePath = document.getElementById('import-file-path').value;
        
        if (!deviceId || !filePath) {
            this.showNotification('Please select a device and enter a file path', 'error');
            return;
        }

        try {
            const response = await fetch('/api/ufo_r11_smartir/import', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.hass?.auth?.access_token || ''}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    device_id: deviceId,
                    file_path: filePath
                })
            });

            if (response.ok) {
                this.showNotification('IR codes imported successfully', 'success');
                this.loadDevices(); // Refresh device list
            } else {
                const error = await response.json();
                this.showNotification('Import failed: ' + error.error, 'error');
            }
        } catch (error) {
            this.showNotification('Import error: ' + error.message, 'error');
        }
    }

    async backupDevice() {
        const deviceId = document.getElementById('export-device-select').value;
        
        if (!deviceId) {
            this.showNotification('Please select a device', 'error');
            return;
        }

        // Use export functionality with timestamp in filename
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const outputPath = `/config/backups/ufo-r11-${deviceId}-${timestamp}.json`;
        
        document.getElementById('export-path').value = outputPath;
        await this.exportSmartIR();
    }

    // Utility methods
    showNotification(message, type = 'info') {
        const container = document.getElementById('ufo-notifications');
        if (!container) {
            console.warn('Notifications container not found, logging message:', message);
            return;
        }
        
        const notification = document.createElement('div');
        notification.className = `ufo-notification ${type}`;
        
        const icon = {
            'success': 'mdi:check-circle',
            'error': 'mdi:alert-circle',
            'warning': 'mdi:alert',
            'info': 'mdi:information'
        }[type] || 'mdi:information';
        
        notification.innerHTML = `
            <ha-icon icon="${icon}"></ha-icon>
            <span>${message}</span>
            <button class="ufo-button ufo-button-small" onclick="this.parentElement.remove()">
                <ha-icon icon="mdi:close"></ha-icon>
            </button>
        `;
        
        container.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentElement) {
                notification.parentElement.removeChild(notification);
            }
        }, 5000);
    }
}

// Initialize the panel when the DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.ufoPanel = new UFOSmartIRPanel();
});

// Export for Home Assistant panel integration
if (typeof customElements !== 'undefined') {
    class UFOSmartIRElement extends HTMLElement {
        connectedCallback() {
            this.innerHTML = '<div>Loading UFO-R11 SmartIR Panel...</div>';
            
            // Initialize panel after a short delay to ensure proper loading
            setTimeout(() => {
                if (!window.ufoPanel) {
                    window.ufoPanel = new UFOSmartIRPanel();
                }
            }, 100);
        }
        
        setConfig(config) {
            // Panel configuration if needed
        }
        
        set hass(hass) {
            if (window.ufoPanel) {
                window.ufoPanel.hass = hass;
            }
        }
    }
    
    customElements.define('ufo-r11-smartir', UFOSmartIRElement);
}