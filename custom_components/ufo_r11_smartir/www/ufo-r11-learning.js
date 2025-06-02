/**
 * UFO-R11 SmartIR Learning Interface
 * 
 * Specialized module for interactive IR code learning with step-by-step wizard
 * and real-time feedback during learning sessions.
 */

class UFOLearningInterface {
    constructor(apiClient) {
        this.apiClient = apiClient;
        this.currentSession = null;
        this.websocket = null;
        this.currentStep = 1;
        this.maxSteps = 3;
        this.learningTimeout = null;
        
        // Command categories and presets
        this.commandCategories = {
            power: {
                name: 'Power Control',
                icon: '⚡',
                presets: ['power_on', 'power_off', 'power_toggle']
            },
            temperature: {
                name: 'Temperature',
                icon: '🌡️',
                presets: this.generateTempPresets()
            },
            mode: {
                name: 'HVAC Mode',
                icon: '🔄',
                presets: ['mode_auto', 'mode_cool', 'mode_heat', 'mode_dry', 'mode_fan']
            },
            fan: {
                name: 'Fan Speed',
                icon: '💨',
                presets: ['fan_auto', 'fan_low', 'fan_medium', 'fan_high', 'fan_turbo']
            },
            swing: {
                name: 'Swing Control',
                icon: '↔️',
                presets: ['swing_off', 'swing_vertical', 'swing_horizontal', 'swing_both']
            },
            timer: {
                name: 'Timer',
                icon: '⏰',
                presets: ['timer_1h', 'timer_2h', 'timer_4h', 'timer_8h', 'timer_off']
            },
            custom: {
                name: 'Custom Commands',
                icon: '⚙️',
                presets: ['sleep', 'eco', 'turbo', 'display', 'health', 'clean']
            }
        };
    }

    generateTempPresets() {
        const temps = [];
        for (let i = 16; i <= 30; i++) {
            temps.push(`temp_${i}`);
        }
        return temps;
    }

    renderLearningInterface() {
        return `
            <div class="learning-container">
                <div class="learning-header">
                    <h2>IR Code Learning Wizard</h2>
                    <div class="progress-bar">
                        <div class="progress-steps">
                            ${this.renderProgressSteps()}
                        </div>
                        <div class="progress-line">
                            <div class="progress-fill" style="width: ${((this.currentStep - 1) / (this.maxSteps - 1)) * 100}%"></div>
                        </div>
                    </div>
                </div>

                <div class="learning-content">
                    ${this.renderCurrentStep()}
                </div>

                <div class="learning-actions">
                    ${this.renderStepActions()}
                </div>
            </div>
        `;
    }

    renderProgressSteps() {
        const steps = [
            { number: 1, title: 'Setup', icon: '⚙️' },
            { number: 2, title: 'Learn', icon: '📡' },
            { number: 3, title: 'Verify', icon: '✅' }
        ];

        return steps.map(step => `
            <div class="progress-step ${step.number <= this.currentStep ? 'active' : ''} ${step.number < this.currentStep ? 'completed' : ''}">
                <div class="step-icon">${step.icon}</div>
                <div class="step-title">${step.title}</div>
                <div class="step-number">${step.number}</div>
            </div>
        `).join('');
    }

    renderCurrentStep() {
        switch (this.currentStep) {
            case 1:
                return this.renderSetupStep();
            case 2:
                return this.renderLearningStep();
            case 3:
                return this.renderVerificationStep();
            default:
                return this.renderCompleteStep();
        }
    }

    renderSetupStep() {
        return `
            <div class="step-content">
                <div class="step-header">
                    <h3>Step 1: Command Setup</h3>
                    <p>Configure the IR command you want to learn</p>
                </div>

                <div class="form-group">
                    <label for="learning-device-select">Select Device:</label>
                    <select id="learning-device-select" class="form-control">
                        <option value="">Choose a device...</option>
                    </select>
                </div>

                <div class="form-group">
                    <label for="command-category">Command Category:</label>
                    <div class="category-grid">
                        ${Object.entries(this.commandCategories).map(([key, category]) => `
                            <div class="category-card" data-category="${key}">
                                <div class="category-icon">${category.icon}</div>
                                <div class="category-name">${category.name}</div>
                            </div>
                        `).join('')}
                    </div>
                </div>

                <div class="form-group" id="command-name-group" style="display: none;">
                    <label for="command-name">Command Name:</label>
                    <div class="command-input-container">
                        <select id="command-preset" class="form-control">
                            <option value="">Select preset or enter custom...</option>
                        </select>
                        <input type="text" id="command-name" class="form-control" placeholder="Enter custom command name">
                    </div>
                </div>

                <div class="form-group">
                    <label for="learning-timeout">Learning Timeout:</label>
                    <div class="timeout-slider">
                        <input type="range" id="learning-timeout" min="10" max="60" value="30" class="slider">
                        <div class="timeout-display">
                            <span id="timeout-value">30</span> seconds
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    renderLearningStep() {
        const session = this.currentSession || {};
        return `
            <div class="step-content">
                <div class="step-header">
                    <h3>Step 2: Learn IR Code</h3>
                    <p>Point your remote at the UFO-R11 device and press the button</p>
                </div>

                <div class="learning-session">
                    <div class="session-info">
                        <div class="session-detail">
                            <strong>Device:</strong> ${session.deviceName || 'Unknown'}
                        </div>
                        <div class="session-detail">
                            <strong>Command:</strong> ${session.commandName || 'Unknown'}
                        </div>
                        <div class="session-detail">
                            <strong>Category:</strong> ${session.category || 'Unknown'}
                        </div>
                    </div>

                    <div class="learning-visual">
                        <div class="device-illustration">
                            <div class="ufo-device">
                                <div class="device-body"></div>
                                <div class="device-receiver ${this.currentSession?.status === 'learning' ? 'receiving' : ''}"></div>
                                <div class="device-indicator ${this.getIndicatorClass()}"></div>
                            </div>
                            <div class="remote-illustration">
                                <div class="remote-body">
                                    <div class="remote-button ${this.currentSession?.status === 'learning' ? 'pulse' : ''}"></div>
                                </div>
                                <div class="signal-waves ${this.currentSession?.status === 'learning' ? 'active' : ''}">
                                    <div class="wave wave1"></div>
                                    <div class="wave wave2"></div>
                                    <div class="wave wave3"></div>
                                </div>
                            </div>
                        </div>

                        <div class="learning-status">
                            <div class="status-message">
                                ${this.getLearningStatusMessage()}
                            </div>
                            <div class="countdown-timer" id="learning-countdown" style="display: none;">
                                <div class="countdown-circle">
                                    <div class="countdown-number">30</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="learning-controls">
                        <button id="start-learning-btn" class="btn btn-primary btn-large">
                            <span class="btn-icon">📡</span>
                            Start Learning
                        </button>
                        <button id="stop-learning-btn" class="btn btn-secondary" style="display: none;">
                            <span class="btn-icon">⏹️</span>
                            Stop Learning
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    renderVerificationStep() {
        const session = this.currentSession || {};
        return `
            <div class="step-content">
                <div class="step-header">
                    <h3>Step 3: Verify & Save</h3>
                    <p>Test the learned code and save it to your device</p>
                </div>

                <div class="verification-section">
                    <div class="learned-code-info">
                        <div class="code-summary">
                            <h4>Learned IR Code</h4>
                            <div class="code-details">
                                <div class="detail-item">
                                    <strong>Command:</strong> ${session.commandName || 'N/A'}
                                </div>
                                <div class="detail-item">
                                    <strong>Protocol:</strong> ${session.protocol || 'Unknown'}
                                </div>
                                <div class="detail-item">
                                    <strong>Length:</strong> ${session.codeLength || 'Unknown'} bits
                                </div>
                                <div class="detail-item">
                                    <strong>Frequency:</strong> ${session.frequency || 'Unknown'} Hz
                                </div>
                            </div>
                            <div class="raw-code">
                                <label>Raw Code:</label>
                                <textarea readonly class="code-display">${session.rawCode || 'No code data available'}</textarea>
                            </div>
                        </div>
                    </div>

                    <div class="verification-controls">
                        <div class="test-section">
                            <h4>Test Command</h4>
                            <p>Test the learned code to ensure it works correctly</p>
                            <button id="test-code-btn" class="btn btn-secondary">
                                <span class="btn-icon">🧪</span>
                                Test Code
                            </button>
                            <div id="test-result" class="test-result" style="display: none;"></div>
                        </div>

                        <div class="save-section">
                            <h4>Save Command</h4>
                            <p>Add this command to your device's library</p>
                            <div class="save-options">
                                <label>
                                    <input type="checkbox" id="save-to-smartir" checked>
                                    Include in SmartIR export
                                </label>
                            </div>
                            <button id="save-code-btn" class="btn btn-success btn-large">
                                <span class="btn-icon">💾</span>
                                Save Command
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    renderCompleteStep() {
        const session = this.currentSession || {};
        return `
            <div class="step-content">
                <div class="completion-message">
                    <div class="success-icon">✅</div>
                    <h3>Learning Complete!</h3>
                    <p>Successfully learned and saved IR command: <strong>${session.commandName}</strong></p>
                    
                    <div class="completion-actions">
                        <button id="learn-another-btn" class="btn btn-primary">
                            <span class="btn-icon">➕</span>
                            Learn Another Command
                        </button>
                        <button id="view-device-btn" class="btn btn-secondary">
                            <span class="btn-icon">📱</span>
                            View Device Commands
                        </button>
                        <button id="export-smartir-btn" class="btn btn-success">
                            <span class="btn-icon">📤</span>
                            Export to SmartIR
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    renderStepActions() {
        const actions = [];

        // Previous button (except on first step)
        if (this.currentStep > 1 && this.currentStep < 4) {
            actions.push(`
                <button id="prev-step-btn" class="btn btn-secondary">
                    <span class="btn-icon">⬅️</span>
                    Previous
                </button>
            `);
        }

        // Next/Continue button
        if (this.currentStep === 1) {
            actions.push(`
                <button id="next-step-btn" class="btn btn-primary" disabled>
                    <span class="btn-icon">➡️</span>
                    Start Learning
                </button>
            `);
        } else if (this.currentStep === 2) {
            actions.push(`
                <button id="next-step-btn" class="btn btn-primary" disabled>
                    <span class="btn-icon">➡️</span>
                    Continue to Verification
                </button>
            `);
        }

        // Cancel button
        actions.push(`
            <button id="cancel-learning-btn" class="btn btn-outline">
                <span class="btn-icon">❌</span>
                Cancel
            </button>
        `);

        return `<div class="step-actions">${actions.join('')}</div>`;
    }

    getIndicatorClass() {
        if (!this.currentSession) return '';
        
        switch (this.currentSession.status) {
            case 'learning': return 'status-learning';
            case 'success': return 'status-success';
            case 'error': return 'status-error';
            case 'timeout': return 'status-timeout';
            default: return '';
        }
    }

    getLearningStatusMessage() {
        if (!this.currentSession) {
            return 'Ready to start learning. Click "Start Learning" to begin.';
        }

        switch (this.currentSession.status) {
            case 'learning':
                return 'Listening for IR signal... Point remote at device and press button.';
            case 'success':
                return '✅ IR code received successfully!';
            case 'error':
                return '❌ Learning failed. Please try again.';
            case 'timeout':
                return '⏰ Learning timeout. No signal received.';
            default:
                return 'Ready to learn IR code.';
        }
    }

    initializeEventListeners() {
        // Device selection
        const deviceSelect = document.getElementById('learning-device-select');
        if (deviceSelect) {
            deviceSelect.addEventListener('change', (e) => {
                this.onDeviceSelected(e.target.value);
            });
        }

        // Category selection
        document.querySelectorAll('.category-card').forEach(card => {
            card.addEventListener('click', (e) => {
                this.onCategorySelected(card.dataset.category);
            });
        });

        // Command preset selection
        const presetSelect = document.getElementById('command-preset');
        if (presetSelect) {
            presetSelect.addEventListener('change', (e) => {
                this.onPresetSelected(e.target.value);
            });
        }

        // Custom command name input
        const commandInput = document.getElementById('command-name');
        if (commandInput) {
            commandInput.addEventListener('input', (e) => {
                this.onCommandNameChanged(e.target.value);
            });
        }

        // Timeout slider
        const timeoutSlider = document.getElementById('learning-timeout');
        if (timeoutSlider) {
            timeoutSlider.addEventListener('input', (e) => {
                document.getElementById('timeout-value').textContent = e.target.value;
            });
        }

        // Learning controls
        const startBtn = document.getElementById('start-learning-btn');
        if (startBtn) {
            startBtn.addEventListener('click', () => this.startLearning());
        }

        const stopBtn = document.getElementById('stop-learning-btn');
        if (stopBtn) {
            stopBtn.addEventListener('click', () => this.stopLearning());
        }

        // Verification controls
        const testBtn = document.getElementById('test-code-btn');
        if (testBtn) {
            testBtn.addEventListener('click', () => this.testLearnedCode());
        }

        const saveBtn = document.getElementById('save-code-btn');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.saveLearnedCode());
        }

        // Navigation buttons
        const nextBtn = document.getElementById('next-step-btn');
        if (nextBtn) {
            nextBtn.addEventListener('click', () => this.nextStep());
        }

        const prevBtn = document.getElementById('prev-step-btn');
        if (prevBtn) {
            prevBtn.addEventListener('click', () => this.previousStep());
        }

        const cancelBtn = document.getElementById('cancel-learning-btn');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => this.cancelLearning());
        }

        // Completion actions
        const learnAnotherBtn = document.getElementById('learn-another-btn');
        if (learnAnotherBtn) {
            learnAnotherBtn.addEventListener('click', () => this.startNewLearning());
        }

        const viewDeviceBtn = document.getElementById('view-device-btn');
        if (viewDeviceBtn) {
            viewDeviceBtn.addEventListener('click', () => this.viewDeviceCommands());
        }

        const exportBtn = document.getElementById('export-smartir-btn');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => this.exportToSmartIR());
        }
    }

    async loadDevices() {
        try {
            const devices = await this.apiClient.getDevices();
            const deviceSelect = document.getElementById('learning-device-select');
            
            if (deviceSelect) {
                deviceSelect.innerHTML = '<option value="">Choose a device...</option>';
                devices.forEach(device => {
                    const option = document.createElement('option');
                    option.value = device.device_id;
                    option.textContent = `${device.name} (${device.device_id})`;
                    deviceSelect.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Failed to load devices:', error);
            this.showNotification('Failed to load devices', 'error');
        }
    }

    onDeviceSelected(deviceId) {
        if (deviceId) {
            this.currentSession = { ...this.currentSession, deviceId };
            this.updateStepValidation();
        }
    }

    onCategorySelected(category) {
        // Clear previous selection
        document.querySelectorAll('.category-card').forEach(card => {
            card.classList.remove('selected');
        });

        // Select current category
        const selectedCard = document.querySelector(`[data-category="${category}"]`);
        if (selectedCard) {
            selectedCard.classList.add('selected');
        }

        // Update session and show command input
        this.currentSession = { ...this.currentSession, category };
        this.updateCommandPresets(category);
        
        const commandGroup = document.getElementById('command-name-group');
        if (commandGroup) {
            commandGroup.style.display = 'block';
        }

        this.updateStepValidation();
    }

    updateCommandPresets(category) {
        const presetSelect = document.getElementById('command-preset');
        const categoryData = this.commandCategories[category];
        
        if (presetSelect && categoryData) {
            presetSelect.innerHTML = '<option value="">Select preset or enter custom...</option>';
            categoryData.presets.forEach(preset => {
                const option = document.createElement('option');
                option.value = preset;
                option.textContent = preset.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                presetSelect.appendChild(option);
            });
        }
    }

    onPresetSelected(preset) {
        const commandInput = document.getElementById('command-name');
        if (commandInput) {
            commandInput.value = preset;
            this.onCommandNameChanged(preset);
        }
    }

    onCommandNameChanged(commandName) {
        this.currentSession = { ...this.currentSession, commandName };
        this.updateStepValidation();
    }

    updateStepValidation() {
        const nextBtn = document.getElementById('next-step-btn');
        if (!nextBtn) return;

        const isValid = this.validateCurrentStep();
        nextBtn.disabled = !isValid;
    }

    validateCurrentStep() {
        switch (this.currentStep) {
            case 1:
                return this.currentSession?.deviceId && 
                       this.currentSession?.category && 
                       this.currentSession?.commandName;
            case 2:
                return this.currentSession?.status === 'success';
            case 3:
                return true;
            default:
                return false;
        }
    }

    async startLearning() {
        if (!this.currentSession?.deviceId || !this.currentSession?.commandName) {
            this.showNotification('Please complete the setup first', 'error');
            return;
        }

        try {
            const timeout = parseInt(document.getElementById('learning-timeout')?.value || '30');
            
            // Update UI
            const startBtn = document.getElementById('start-learning-btn');
            const stopBtn = document.getElementById('stop-learning-btn');
            const countdown = document.getElementById('learning-countdown');
            
            if (startBtn) startBtn.style.display = 'none';
            if (stopBtn) stopBtn.style.display = 'inline-block';
            if (countdown) countdown.style.display = 'block';

            // Start countdown
            this.startCountdown(timeout);

            // Initialize WebSocket for real-time updates
            this.connectWebSocket();

            // Start learning session
            const response = await this.apiClient.startLearning({
                device_id: this.currentSession.deviceId,
                command_name: this.currentSession.commandName,
                timeout: timeout
            });

            this.currentSession = {
                ...this.currentSession,
                sessionId: response.session_id,
                status: 'learning'
            };

            this.updateLearningDisplay();

        } catch (error) {
            console.error('Failed to start learning:', error);
            this.showNotification('Failed to start learning session', 'error');
            this.resetLearningUI();
        }
    }

    async stopLearning() {
        if (this.learningTimeout) {
            clearInterval(this.learningTimeout);
            this.learningTimeout = null;
        }

        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }

        this.currentSession = { ...this.currentSession, status: 'cancelled' };
        this.resetLearningUI();
        this.updateLearningDisplay();
    }

    startCountdown(seconds) {
        const countdownEl = document.querySelector('.countdown-number');
        let remaining = seconds;

        if (countdownEl) {
            countdownEl.textContent = remaining;
        }

        this.learningTimeout = setInterval(() => {
            remaining--;
            if (countdownEl) {
                countdownEl.textContent = remaining;
            }

            if (remaining <= 0) {
                clearInterval(this.learningTimeout);
                this.learningTimeout = null;
                this.onLearningTimeout();
            }
        }, 1000);
    }

    connectWebSocket() {
        if (!this.currentSession?.deviceId) return;

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/api/ufo_r11_smartir/ws/${this.currentSession.deviceId}`;

        this.websocket = new WebSocket(wsUrl);

        this.websocket.onopen = () => {
            console.log('WebSocket connected for learning updates');
        };

        this.websocket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleWebSocketMessage(data);
            } catch (error) {
                console.error('Failed to parse WebSocket message:', error);
            }
        };

        this.websocket.onclose = () => {
            console.log('WebSocket disconnected');
        };

        this.websocket.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }

    handleWebSocketMessage(data) {
        if (data.type === 'learning_update') {
            this.currentSession = {
                ...this.currentSession,
                status: data.status,
                rawCode: data.ir_code,
                protocol: data.protocol,
                codeLength: data.code_length,
                frequency: data.frequency
            };

            this.updateLearningDisplay();

            if (data.status === 'success') {
                this.onLearningSuccess();
            } else if (data.status === 'error') {
                this.onLearningError(data.error);
            }
        }
    }

    onLearningSuccess() {
        if (this.learningTimeout) {
            clearInterval(this.learningTimeout);
            this.learningTimeout = null;
        }

        this.resetLearningUI();
        this.showNotification('IR code learned successfully!', 'success');
        
        // Enable next step
        this.updateStepValidation();
    }

    onLearningError(error) {
        if (this.learningTimeout) {
            clearInterval(this.learningTimeout);
            this.learningTimeout = null;
        }

        this.resetLearningUI();
        this.showNotification(`Learning failed: ${error}`, 'error');
    }

    onLearningTimeout() {
        this.currentSession = { ...this.currentSession, status: 'timeout' };
        this.resetLearningUI();
        this.updateLearningDisplay();
        this.showNotification('Learning timeout - no signal received', 'warning');
    }

    resetLearningUI() {
        const startBtn = document.getElementById('start-learning-btn');
        const stopBtn = document.getElementById('stop-learning-btn');
        const countdown = document.getElementById('learning-countdown');
        
        if (startBtn) startBtn.style.display = 'inline-block';
        if (stopBtn) stopBtn.style.display = 'none';
        if (countdown) countdown.style.display = 'none';
    }

    updateLearningDisplay() {
        const statusEl = document.querySelector('.status-message');
        if (statusEl) {
            statusEl.textContent = this.getLearningStatusMessage();
        }

        const indicatorEl = document.querySelector('.device-indicator');
        if (indicatorEl) {
            indicatorEl.className = `device-indicator ${this.getIndicatorClass()}`;
        }

        const receiverEl = document.querySelector('.device-receiver');
        if (receiverEl) {
            receiverEl.classList.toggle('receiving', this.currentSession?.status === 'learning');
        }

        const wavesEl = document.querySelector('.signal-waves');
        if (wavesEl) {
            wavesEl.classList.toggle('active', this.currentSession?.status === 'learning');
        }
    }

    async testLearnedCode() {
        if (!this.currentSession?.rawCode || !this.currentSession?.deviceId) {
            this.showNotification('No code to test', 'error');
            return;
        }

        try {
            const testBtn = document.getElementById('test-code-btn');
            const resultEl = document.getElementById('test-result');
            
            if (testBtn) testBtn.disabled = true;
            if (resultEl) {
                resultEl.style.display = 'block';
                resultEl.textContent = 'Testing...';
                resultEl.className = 'test-result testing';
            }

            await this.apiClient.testCommand({
                device_id: this.currentSession.deviceId,
                ir_code: this.currentSession.rawCode
            });

            if (resultEl) {
                resultEl.textContent = 'Test successful! ✅';
                resultEl.className = 'test-result success';
            }

            this.showNotification('Test command sent successfully', 'success');

        } catch (error) {
            console.error('Test failed:', error);
            
            const resultEl = document.getElementById('test-result');
            if (resultEl) {
                resultEl.textContent = 'Test failed ❌';
                resultEl.className = 'test-result error';
            }
            
            this.showNotification('Test command failed', 'error');
        } finally {
            const testBtn = document.getElementById('test-code-btn');
            if (testBtn) testBtn.disabled = false;
        }
    }

    async saveLearnedCode() {
        if (!this.currentSession?.rawCode || !this.currentSession?.deviceId || !this.currentSession?.commandName) {
            this.showNotification('Missing required data to save', 'error');
            return;
        }

        try {
            const saveBtn = document.getElementById('save-code-btn');
            if (saveBtn) saveBtn.disabled = true;

            await this.apiClient.saveCommand({
                device_id: this.currentSession.deviceId,
                command_name: this.currentSession.commandName,
                ir_code: this.currentSession.rawCode,
                category: this.currentSession.category,
                include_in_smartir: document.getElementById('save-to-smartir')?.checked || false
            });

            this.showNotification('Command saved successfully!', 'success');
            this.nextStep(); // Move to completion step

        } catch (error) {
            console.error('Save failed:', error);
            this.showNotification('Failed to save command', 'error');
        } finally {
            const saveBtn = document.getElementById('save-code-btn');
            if (saveBtn) saveBtn.disabled = false;
        }
    }

    nextStep() {
        if (this.currentStep < this.maxSteps) {
            this.currentStep++;
        } else {
            this.currentStep = 4; // Completion step
        }
        this.updateDisplay();
    }

    previousStep() {
        if (this.currentStep > 1) {
            this.currentStep--;
            this.updateDisplay();
        }
    }

    updateDisplay() {
        const container = document.querySelector('.learning-container');
        if (container) {
            container.innerHTML = this.renderLearningInterface();
            this.initializeEventListeners();
            
            // Restore state for current step
            if (this.currentStep === 1) {
                this.loadDevices();
            } else if (this.currentStep === 2) {
                this.updateLearningDisplay();
            }
        }
    }

    startNewLearning() {
        this.currentStep = 1;
        this.currentSession = null;
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
        if (this.learningTimeout) {
            clearInterval(this.learningTimeout);
            this.learningTimeout = null;
        }
        this.updateDisplay();
    }

    viewDeviceCommands() {
        // Navigate back to devices tab
        const devicesTab = document.querySelector('[data-tab="devices"]');
        if (devicesTab) {
            devicesTab.click();
        }
    }

    async exportToSmartIR() {
        if (!this.currentSession?.deviceId) {
            this.showNotification('No device selected for export', 'error');
            return;
        }

        try {
            await this.apiClient.exportSmartIR({
                device_id: this.currentSession.deviceId
            });
            
            this.showNotification('SmartIR configuration exported successfully', 'success');
        } catch (error) {
            console.error('Export failed:', error);
            this.showNotification('Failed to export SmartIR configuration', 'error');
        }
    }

    cancelLearning() {
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
        
        if (this.learningTimeout) {
            clearInterval(this.learningTimeout);
            this.learningTimeout = null;
        }

        // Navigate back to devices tab
        const devicesTab = document.querySelector('[data-tab="devices"]');
        if (devicesTab) {
            devicesTab.click();
        }
    }

    showNotification(message, type = 'info') {
        // Use parent panel's notification system
        if (window.ufoPanel && window.ufoPanel.showNotification) {
            window.ufoPanel.showNotification(message, type);
        } else {
            // Fallback
            console.log(`${type.toUpperCase()}: ${message}`);
        }
    }
}

// Export for use by main panel
window.UFOLearningInterface = UFOLearningInterface;
