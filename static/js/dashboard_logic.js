// ============================================================
// GLOBAL VARIABLES
// ============================================================

window.vehicleExtra = {
    N: { crossed: 0, lastCrossed: 0, passed_breakdown: { bike: 0, car: 0, truck: 0, emergency: 0 } },
    S: { crossed: 0, lastCrossed: 0, passed_breakdown: { bike: 0, car: 0, truck: 0, emergency: 0 } },
    E: { crossed: 0, lastCrossed: 0, passed_breakdown: { bike: 0, car: 0, truck: 0, emergency: 0 } },
    W: { crossed: 0, lastCrossed: 0, passed_breakdown: { bike: 0, car: 0, truck: 0, emergency: 0 } }
};

window.vehicleQueues = {
    N: { two_wheeler: 0, four_wheeler: 0, heavy_vehicle: 0, emergency_vehicle: 0 },
    S: { two_wheeler: 0, four_wheeler: 0, heavy_vehicle: 0, emergency_vehicle: 0 },
    E: { two_wheeler: 0, four_wheeler: 0, heavy_vehicle: 0, emergency_vehicle: 0 },
    W: { two_wheeler: 0, four_wheeler: 0, heavy_vehicle: 0, emergency_vehicle: 0 }
};

window.simulationActive = false;
window.updateInterval = 1000;
window.signalData = {};
window.simulationIntervalId = null;

// ============================================================
// API FUNCTIONS
// ============================================================

async function fetchSignals() {
    try {
        const response = await fetch('/api/signals/all_signals/');
        return await response.json();
    } catch (error) {
        console.error('❌ Failed to fetch signals');
        return [];
    }
}

async function updateVehicleCount(direction, vehicleCounts) {
    const signal = signalData[direction];
    if (!signal) return;

    try {
        const response = await fetch(
            `/api/signals/${signal.id}/update_count/`,
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify(vehicleCounts)
            }
        );

        const data = await response.json();
        signalData[direction] = data;
        updateAllControls([data]);
        return data;
    } catch {
        console.error('❌ Vehicle update failed');
    }
}

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
}

// ============================================================
// UI FUNCTIONS
// ============================================================

function createSignalControl(signal) {
    const directions = { N: 'NORTH', S: 'SOUTH', E: 'EAST', W: 'WEST' };
    const icons = { N: 'fa-arrow-up', S: 'fa-arrow-down', E: 'fa-arrow-right', W: 'fa-arrow-left' };
    const state = signal.current_state;
    const isEmergency = signal.is_emergency_active;

    // Status Styling
    let activeClass = '';
    if (isEmergency) activeClass = 'emergency-mode';
    else if (state === 'GREEN') activeClass = 'active-green';
    else if (state === 'RED') activeClass = 'active-red';
    else if (state === 'YELLOW') activeClass = 'active-yellow';

    const stateColor = isEmergency ? '#ef4444' :
        (state === 'GREEN' ? 'var(--neon-green)' :
            (state === 'RED' ? 'var(--neon-red)' : 'var(--neon-yellow)'));

    return `
    <div class="control-card ${activeClass}" id="control-${signal.direction}">
        <!-- HEADER -->
        <div class="card-header">
            <div class="header-left">
                <div class="status-dot" style="background:${stateColor}"></div>
                <div class="direction-title">
                    <i class="fa-solid ${icons[signal.direction]} direction-icon"></i> 
                    ${directions[signal.direction]}
                </div>
            </div>
            <span class="status-text signal-badge ${state}" style="color:${stateColor}">${state}</span>
        </div>

        <!-- STATS ROW -->
        <div class="card-stats-row">
            <div class="stats-group">
                <span class="stats-label"><i class="fa-solid fa-car-side"></i> Queue</span>
                <span class="stats-value highlight-score" id="count-${signal.direction}">${signal.vehicle_count}</span>
            </div>
             <div class="stats-group">
                <span class="stats-label"><i class="fa-solid fa-stopwatch"></i> Timer</span>
                <span class="stats-value timer-display" id="time-${signal.direction}" style="color:${stateColor}">--</span>
            </div>
        </div>

        <!-- VEHICLE CONTROLS -->
        <div class="vehicle-controls">
            <button onclick="addVehicle('${signal.direction}', 'bike')" class="btn-add-vehicle" title="Add Bike">
                <i class="fa-solid fa-motorcycle"></i> 
                <span>BIKE</span>
            </button>
            <button onclick="addVehicle('${signal.direction}', 'car')" class="btn-add-vehicle" title="Add Car">
                <i class="fa-solid fa-car"></i>
                <span>CAR</span>
            </button>
             <button onclick="addVehicle('${signal.direction}', 'truck')" class="btn-add-vehicle" title="Add Truck">
                <i class="fa-solid fa-truck"></i>
                <span>TRUCK</span>
            </button>
        </div>

        <!-- FOOTER ACTIONS -->
        <div class="action-buttons">
            <button onclick="triggerEmergency('${signal.direction}')" id="sos-btn-${signal.direction}" class="btn-action btn-sos ${isEmergency ? 'active' : ''}">
                ${isEmergency ? '<i class="fa-solid fa-spinner fa-spin"></i> ACTIVE' : '<i class="fa-solid fa-truck-medical"></i> SOS'}
            </button>
            <button onclick="showDirectionDetails('${signal.direction}')" class="btn-action btn-details">
                <i class="fa-solid fa-circle-info"></i> DETAILS
            </button>
        </div>
    </div>
    `;
}

function updateAllControls(signals) {
    const panel = document.getElementById('signalControls');
    if (!panel) return;

    signals.forEach(s => {
        signalData[s.direction] = s;
        const cardId = `control-${s.direction}`;
        let card = document.getElementById(cardId);

        if (!card) {
            panel.innerHTML += createSignalControl(s);
        } else {
            // Update Existing Card
            const isEmergency = s.is_emergency_active;
            const state = s.current_state;

            // 1. Text & Classes
            card.classList.remove('active-green', 'active-red', 'active-yellow', 'emergency-mode');
            if (isEmergency) card.classList.add('emergency-mode');
            else if (state === 'GREEN') card.classList.add('active-green');
            else if (state === 'RED') card.classList.add('active-red');
            else if (state === 'YELLOW') card.classList.add('active-yellow');

            const stateColor = isEmergency ? '#ef4444' :
                (state === 'GREEN' ? 'var(--neon-green)' :
                    (state === 'RED' ? 'var(--neon-red)' : 'var(--neon-yellow)'));

            // 2. Metrics
            const countEl = document.getElementById(`count-${s.direction}`);
            if (countEl) countEl.innerText = s.vehicle_count;

            const badge = card.querySelector('.signal-badge');
            if (badge) {
                badge.className = `signal-badge ${state}`;
                badge.innerText = state;
            }

            // 3. Timer
            const timeEl = document.getElementById(`time-${s.direction}`);
            if (timeEl) {
                if (isEmergency) {
                    timeEl.innerText = 'SOS';
                    timeEl.style.color = '#ef4444';
                } else if (s.current_state === 'RED') {
                    timeEl.innerText = 'WAIT';
                    timeEl.style.color = 'var(--neon-red)';
                } else if (s.state_start_time) {
                    const now = new Date();
                    const start = new Date(s.state_start_time);
                    const elapsed = (now - start) / 1000;
                    const duration = s.current_state === 'GREEN' ? s.green_time : (s.yellow_time || 3);
                    const remaining = Math.max(0, Math.ceil(duration - elapsed));
                    const mins = Math.floor(remaining / 60);
                    const secs = remaining % 60;
                    timeEl.innerText = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
                    timeEl.style.color = stateColor;
                } else {
                    timeEl.innerText = '--:--';
                }
            }

            // 4. SOS Button
            const sosBtn = document.getElementById(`sos-btn-${s.direction}`);
            if (sosBtn) {
                if (isEmergency) {
                    sosBtn.classList.add('active');
                    sosBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> ACTIVE';
                } else {
                    sosBtn.classList.remove('active');
                    sosBtn.innerHTML = '<i class="fa-solid fa-truck-medical"></i> SOS';
                }
            }
        }
    });

    updateSOSVisuals();
    updateTimersLocally();
}

// ============================================================
// DASHBOARD STATS MENU
// ============================================================
async function updateDashboardMenu() {
    try {
        // Fetch global stats
        const globalRes = await fetch('/api/signals/global_stats/');

        if (globalRes.ok) {
            const gData = await globalRes.json();
            // Total Vehicles Crossed
            const crossed = document.getElementById('dashCrossed');
            if (crossed) crossed.innerText = gData.total_crossed || 0;

            // Efficiency — calculate from total crossed vs total vehicles
            const effEl = document.getElementById('dashEfficiency');
            if (effEl) {
                const totalV = gData.total_vehicles || 0;
                const totalC = gData.total_crossed || 0;
                const eff = totalV > 0 ? Math.min(100, Math.round((totalC / (totalV + totalC)) * 100)) : 0;
                effEl.innerText = eff + '%';
            }
        }

        // Active Green
        const activeGreenEl = document.getElementById('dashActiveGreen');
        if (activeGreenEl) {
            const greenSignal = Object.values(signalData).find(s => s.current_state === 'GREEN');
            if (greenSignal) {
                activeGreenEl.innerText = greenSignal.direction === 'N' ? 'NORTH' : (greenSignal.direction === 'S' ? 'SOUTH' : (greenSignal.direction === 'E' ? 'EAST' : 'WEST'));
                activeGreenEl.style.color = 'var(--neon-green)';
            } else {
                activeGreenEl.innerText = 'WAIT';
                activeGreenEl.style.color = 'var(--neon-yellow)';
            }
        }

        // Total Vehicles (Live Queue)
        const totalLiveEl = document.getElementById('dashTotalVehicles');
        if (totalLiveEl) {
            const total = Object.values(signalData).reduce((sum, s) => sum + (s.vehicle_count || 0), 0);
            totalLiveEl.innerText = total;
        }

        // Active Countdown Timer
        const dashTimerEl = document.getElementById('dashTimer');
        if (dashTimerEl) {
            const activeSig = Object.values(signalData).find(s => s.current_state === 'GREEN' || s.current_state === 'YELLOW');
            if (activeSig && activeSig.state_start_time) {
                const now = new Date();
                const start = new Date(activeSig.state_start_time);
                const elapsed = (now - start) / 1000;
                const dur = activeSig.current_state === 'GREEN' ? activeSig.green_time : (activeSig.yellow_time || 5);
                const remaining = Math.max(0, Math.ceil(dur - elapsed));
                dashTimerEl.innerText = remaining + 's';
                dashTimerEl.style.color = activeSig.current_state === 'GREEN' ? 'var(--neon-green)' : 'var(--neon-yellow)';
            } else {
                dashTimerEl.innerText = '--';
            }
        }

    } catch (e) {
        console.warn("Stats update failed", e);
    }
}


// ============================================================
// SIMULATION LOOP
// ============================================================

async function simulateTraffic() {
    while (simulationActive) {
        // 1. Queue Logic (Same as before)
        for (const dir in signalData) {
            const signal = signalData[dir];
            const queue = vehicleQueues[dir];

            // Arrivals
            if (Math.random() > 0.3) {
                const rand = Math.random();
                if (rand < 0.6) queue.two_wheeler++;
                else if (rand < 0.9) queue.four_wheeler++;
                else queue.heavy_vehicle++;
            }

            // Departures
            if (signal.current_state === 'GREEN') {
                let flowCapacity = 2; // Vehicles per sec
                while (flowCapacity > 0) {
                    if (queue.emergency_vehicle > 0) {
                        queue.emergency_vehicle--;
                        vehicleExtra[dir].crossed++;
                        vehicleExtra[dir].passed_breakdown.emergency++;
                        flowCapacity--;
                    } else if (queue.heavy_vehicle > 0) {
                        queue.heavy_vehicle--;
                        vehicleExtra[dir].crossed++;
                        vehicleExtra[dir].passed_breakdown.truck++;
                        flowCapacity--;
                    } else if (queue.four_wheeler > 0) {
                        queue.four_wheeler--;
                        vehicleExtra[dir].crossed++;
                        vehicleExtra[dir].passed_breakdown.car++;
                        flowCapacity--;
                    } else if (queue.two_wheeler > 0) {
                        queue.two_wheeler--;
                        vehicleExtra[dir].crossed++;
                        vehicleExtra[dir].passed_breakdown.bike++;
                        flowCapacity--;
                    } else {
                        break;
                    }
                }
            }

            // Update Backend
            const currentCrossed = vehicleExtra[dir].crossed;
            const deltaPassed = currentCrossed - (vehicleExtra[dir].lastCrossed || 0);
            vehicleExtra[dir].lastCrossed = currentCrossed;

            const passed = vehicleExtra[dir].passed_breakdown;
            const payload = {
                two_wheeler: queue.two_wheeler,
                four_wheeler: queue.four_wheeler,
                heavy_vehicle: queue.heavy_vehicle,
                emergency_vehicle: queue.emergency_vehicle,
                vehicles_passed: deltaPassed,
                passed_two_wheeler: passed.bike,
                passed_four_wheeler: passed.car,
                passed_heavy_vehicle: passed.truck,
                passed_emergency_vehicle: passed.emergency
            };

            await updateVehicleCount(dir, payload);
            vehicleExtra[dir].passed_breakdown = { bike: 0, car: 0, truck: 0, emergency: 0 };
        }

        // 2. Cycle & Global Stats
        await cycleSignals();
        updateDashboardMenu();

        // 3. Tick
        await new Promise(r => setTimeout(r, updateInterval));
    }
}

async function cycleSignals() {
    try {
        const response = await fetch('/api/signals/cycle/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') }
        });
        const data = await response.json();
        if (data && data.signals) updateAllControls(data.signals);
    } catch (e) {
        console.error("Cycle failed", e);
    }
}


function startSimulation() {
    if (simulationActive) return;
    simulationActive = true;
    simulateTraffic(); // Starts the backend loop

    // UI Feedback
    const startBtn = document.querySelector('button[onclick="startSimulation()"]');
    const stopBtn = document.querySelector('button[onclick="stopSimulation()"]');
    if (startBtn) startBtn.style.opacity = '0.5';
    if (stopBtn) stopBtn.style.opacity = '1';
}

function stopSimulation() {
    if (!simulationActive) return;
    simulationActive = false;

    // UI Feedback
    const startBtn = document.querySelector('button[onclick="startSimulation()"]');
    const stopBtn = document.querySelector('button[onclick="stopSimulation()"]');
    if (startBtn) startBtn.style.opacity = '1';
    if (stopBtn) stopBtn.style.opacity = '0.5';

    // Force Final Stats Update
    updateDashboardMenu();

    // If on Stats page, refresh it
    const statsView = document.getElementById('view-stats');
    if (statsView && statsView.style.display === 'block') {
        // Identify current active tab direction
        const activeTab = document.querySelector('#view-stats .dir-tab.active');
        if (activeTab) {
            const dir = activeTab.innerText.charAt(0); // "N", "S" etc
            loadStats(dir, activeTab);
        }
    }
}

// ============================================================
// NAVIGATION & STATS PAGE
// ============================================================

// ============================================================
// NAVIGATION & STATS PAGE
// ============================================================

window.switchMainView = function (viewName) {
    // 1. Sidebar Active State
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    const links = document.querySelectorAll('.nav-item');
    for (let l of links) {
        if (l.getAttribute('onclick')?.includes(viewName)) l.classList.add('active');
    }

    // 2. Stop all view-specific intervals
    if (typeof stopEmergencyRefresh === 'function') stopEmergencyRefresh();
    if (typeof stopHeatmapRefresh === 'function') stopHeatmapRefresh();

    // 3. All view IDs
    const viewIds = ['view-dashboard', 'view-emergency', 'view-multijunction',
        'view-heatmap', 'view-stats', 'view-environment', 'view-history', 'view-admin', 'view-ai-analysis'];
    viewIds.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.classList.add('hidden');
            el.style.display = 'none';
        }
    });

    // 4. Show selected view and init
    const target = document.getElementById('view-' + viewName);
    if (!target) return;

    target.classList.remove('hidden');
    if (viewName === 'dashboard') {
        target.style.display = 'flex';
        setTimeout(() => window.dispatchEvent(new Event('resize')), 100);
    } else {
        target.style.display = 'block';
    }

    // 5. Initialize view-specific logic
    try {
        switch (viewName) {
            case 'emergency':
                if (typeof initEmergencyView === 'function') initEmergencyView();
                break;
            case 'multijunction':
                if (typeof initMultiJunctionView === 'function') initMultiJunctionView();
                break;
            case 'heatmap':
                if (typeof initHeatmapView === 'function') initHeatmapView();
                break;
            case 'stats':
                if (typeof loadStats === 'function') {
                    const activeTab = document.querySelector('#view-stats .dir-tab.active');
                    loadStats('N', activeTab);
                }
                if (typeof initAnalyticsView === 'function') initAnalyticsView();
                break;
            case 'history':
                if (typeof loadHistory === 'function') loadHistory();
                break;
            case 'admin':
                if (typeof initAdminView === 'function') initAdminView();
                break;
            case 'environment':
                if (typeof initEnvironmentView === 'function') initEnvironmentView();
                break;
            case 'ai-analysis':
                if (typeof initAiAnalysis === 'function') initAiAnalysis();
                break;
        }
    } catch (err) {
        console.error(`[View Switch Error in ${viewName}]`, err);
    }
};

// SOS Dimming Helper
window.updateSOSVisuals = function () {
    // Check if any signal is in SOS mode
    const isAnySOS = Object.values(window.signalData).some(s => s.is_emergency_active);

    // Toggle dimmed class on cards
    Object.values(window.signalData).forEach(s => {
        const card = document.getElementById(`control-${s.direction}`);
        if (card) {
            if (isAnySOS && !s.is_emergency_active) {
                card.classList.add('dimmed');
            } else {
                card.classList.remove('dimmed');
            }
        }
    });
}


let volChart = null;
let compChart = null;

window.loadStats = async function (direction, tabEl) {
    if (tabEl) {
        document.querySelectorAll('#view-stats .dir-tab').forEach(t => t.classList.remove('active'));
        tabEl.classList.add('active');
    }

    try {
        // Fetch Summary
        const sumRes = await fetch(`/api/analytics/direction/${direction}/summary/`);
        const summary = await sumRes.json();

        // Fetch Charts
        const chartRes = await fetch(`/api/analytics/direction/${direction}/charts/`);
        const charts = await chartRes.json();

        // Fetch Insights
        const insRes = await fetch(`/api/analytics/direction/${direction}/insights/`);
        const insights = await insRes.json();

        // Update Direction Summary Cards
        const totalPassed = document.getElementById('statsTotalPassed');
        if (totalPassed) totalPassed.innerText = summary.total_vehicles_today || 0;

        const emCount = document.getElementById('statsEmergencyCount');
        if (emCount) emCount.innerText = summary.emergency_events || 0;

        const avgWait = document.getElementById('statsAvgWait');
        if (avgWait) avgWait.innerText = (summary.average_wait_time || 0) + 's';

        // Peak Hour
        const peakHour = document.getElementById('peakHourValue');
        if (peakHour) peakHour.innerText = insights.peak_hour || '--:--';

        const peakVol = document.getElementById('peakVolumeValue');
        if (peakVol) peakVol.innerText = (insights.peak_volume || 0) + ' Vehicles';

        // Traffic Volume Chart (Line)
        const ctxVol = document.getElementById('trafficVolumeChart')?.getContext('2d');
        if (ctxVol) {
            if (volChart) volChart.destroy();

            volChart = new Chart(ctxVol, {
                type: 'line',
                data: {
                    labels: charts.labels || [],
                    datasets: [{
                        label: 'Traffic Volume',
                        data: charts.vehicles || [],
                        borderColor: '#22c55e',
                        backgroundColor: 'rgba(34, 197, 94, 0.1)',
                        fill: true,
                        tension: 0.4
                    }, {
                        label: 'Density',
                        data: charts.density || [],
                        borderColor: '#3b82f6',
                        backgroundColor: 'rgba(59, 130, 246, 0.05)',
                        fill: true,
                        tension: 0.4,
                        yAxisID: 'y1',
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#888' } },
                        x: { grid: { display: false }, ticks: { color: '#888' } },
                        y1: { position: 'right', grid: { display: false }, ticks: { color: '#888' } }
                    },
                    plugins: { legend: { labels: { color: '#aaa' } } }
                }
            });
        }

        // Composition Chart (Doughnut)
        const bd = summary.vehicle_breakdown || {};
        const ctxComp = document.getElementById('compositionChart')?.getContext('2d');
        if (ctxComp) {
            if (compChart) compChart.destroy();

            compChart = new Chart(ctxComp, {
                type: 'doughnut',
                data: {
                    labels: ['Two Wheeler', 'Four Wheeler', 'Heavy Vehicle', 'Emergency'],
                    datasets: [{
                        data: [bd.two_wheeler || 0, bd.four_wheeler || 0, bd.heavy_vehicle || 0, bd.emergency_vehicle || 0],
                        backgroundColor: ['#a78bfa', '#60a5fa', '#fbbf24', '#ef4444'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { position: 'right', labels: { color: '#aaa' } } }
                }
            });
        }

    } catch (e) {
        console.error("Stats Load Error", e);
    }
}

// ============================================================
// HELPERS
// ============================================================
function addVehicle(direction, type) {
    const map = { 'bike': 'two_wheeler', 'car': 'four_wheeler', 'truck': 'heavy_vehicle' };
    const key = map[type];
    if (vehicleQueues[direction]) vehicleQueues[direction][key]++;
}

async function triggerEmergency(direction) {
    const signal = signalData[direction];
    if (!signal) return;
    const newState = !signal.is_emergency_active;
    const dirNames = { 'N': 'NORTH', 'S': 'SOUTH', 'E': 'EAST', 'W': 'WEST' };
    const dirName = dirNames[direction] || direction;

    if (newState) {
        if (vehicleQueues[direction]) {
            vehicleQueues[direction].emergency_vehicle = Math.max(1, (vehicleQueues[direction].emergency_vehicle || 0) + 1);
        }
        if (typeof vehicles !== 'undefined' && typeof MiniMapVehicle === 'function') {
            vehicles.push(new MiniMapVehicle(direction, 'emergency'));
        }
        if (typeof showNotification === 'function') {
            showNotification('EMERGENCY ACTIVE', `Priority corridor opened for ${dirName}!`, 'danger');
        }
    } else {
        if (vehicleQueues[direction]) {
            vehicleQueues[direction].emergency_vehicle = 0;
        }
        if (typeof showNotification === 'function') {
            showNotification('EMERGENCY RESOLVED', `Normal traffic flow resumed for ${dirName}.`, 'success');
        }
    }

    try {
        const response = await fetch(`/api/signals/${signal.id}/toggle_sos/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
            body: JSON.stringify({ active: newState })
        });
        const data = await response.json();
        if (data && data.signals) {
            updateAllControls(data.signals);
        }
        updateDashboardMenu();
    } catch (e) {
        console.error("SOS toggle error", e);
    }
}

let isCycleLocked = false;

window.updateTimersLocally = function () {
    const now = Date.now();
    let activeSignal = null;
    const dirNames = { 'N': 'NORTH', 'S': 'SOUTH', 'E': 'EAST', 'W': 'WEST' };

    Object.values(window.signalData || {}).forEach(s => {
        const timeEl = document.getElementById(`time-${s.direction}`);
        const isEmergency = s.is_emergency_active;
        const state = s.current_state;

        if (state === 'GREEN' || state === 'YELLOW') {
            activeSignal = s;
        }

        if (timeEl) {
            if (isEmergency) {
                timeEl.innerText = 'SOS';
                timeEl.style.color = '#ef4444';
            } else if (state === 'RED') {
                timeEl.innerText = 'WAIT';
                timeEl.style.color = 'var(--neon-red)';
            } else if (s.state_start_time) {
                const start = new Date(s.state_start_time).getTime();
                const elapsed = Math.max(0, (now - start) / 1000);
                const duration = state === 'GREEN' ? (s.green_time || 30) : (s.yellow_time || 3);
                const remaining = Math.max(0, Math.ceil(duration - elapsed));
                const mins = Math.floor(remaining / 60);
                const secs = remaining % 60;
                timeEl.innerText = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
                timeEl.style.color = state === 'GREEN' ? 'var(--neon-green)' : 'var(--neon-yellow)';
            } else {
                timeEl.innerText = '--:--';
            }
        }
    });

    // Update Dashboard Stats Bottom/Top Active Displays
    const activeGreenEl = document.getElementById('dashActiveGreen');
    const dashTimerEl = document.getElementById('dashTimer');

    if (activeSignal) {
        if (activeGreenEl) {
            activeGreenEl.innerText = dirNames[activeSignal.direction] || activeSignal.direction;
            activeGreenEl.style.color = activeSignal.current_state === 'GREEN' ? 'var(--neon-green)' : 'var(--neon-yellow)';
        }

        if (dashTimerEl && activeSignal.state_start_time) {
            const start = new Date(activeSignal.state_start_time).getTime();
            const elapsed = Math.max(0, (now - start) / 1000);
            const duration = activeSignal.current_state === 'GREEN' ? (activeSignal.green_time || 30) : (activeSignal.yellow_time || 3);
            const remaining = Math.max(0, Math.ceil(duration - elapsed));
            const mins = Math.floor(remaining / 60);
            const secs = remaining % 60;
            dashTimerEl.innerText = `00:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
            dashTimerEl.style.color = activeSignal.current_state === 'GREEN' ? 'var(--neon-green)' : 'var(--neon-yellow)';

            // Auto-advance cycle when timer hits 0
            if (remaining <= 0 && !isCycleLocked && !activeSignal.is_emergency_active) {
                isCycleLocked = true;
                cycleSignals().finally(() => {
                    setTimeout(() => { isCycleLocked = false; }, 1000);
                });
            }
        }
    } else {
        if (activeGreenEl) {
            activeGreenEl.innerText = 'WAIT';
            activeGreenEl.style.color = 'var(--neon-yellow)';
        }
        if (dashTimerEl) {
            dashTimerEl.innerText = '00:00:00';
        }
    }
};

// Init
document.addEventListener('DOMContentLoaded', () => {
    fetchSignals().then(data => {
        if (data) updateAllControls(data);
    });

    // Continuous 1-second countdown loop
    setInterval(updateTimersLocally, 1000);
});

async function resetStats() {
    if (!confirm("Are you sure you want to reset all traffic stats? This cannot be undone.")) return;

    try {
        const response = await fetch('/api/signals/reset_stats/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            }
        });

        if (response.ok) {
            // Reset UI counters locally
            const crossed = document.getElementById('dashCrossed');
            if (crossed) crossed.innerText = '0';

            const eff = document.getElementById('dashEfficiency');
            if (eff) eff.innerText = '--';

            const total = document.getElementById('dashTotalVehicles');
            if (total) total.innerText = '0';

            // Reset simulation data
            if (typeof vehicleExtra !== 'undefined') {
                Object.keys(vehicleExtra).forEach(dir => {
                    vehicleExtra[dir].crossed = 0;
                    vehicleExtra[dir].lastCrossed = 0;
                    vehicleExtra[dir].passed_breakdown = { bike: 0, car: 0, truck: 0, emergency: 0 };
                });
            }

            alert("Traffic stats reset successfully.");
            updateDashboardMenu(); // Fetch fresh 0 values
        } else {
            alert("Failed to reset stats.");
        }
    } catch (e) {
        console.error("Reset failed", e);
        alert("Error resetting stats.");
    }
}

// ============================================================
// DETAILS MODAL LOGIC
// ============================================================

let detailsChartInstance = null;

window.showDirectionDetails = async function (direction) {
    const modal = document.getElementById('detailsModal');
    if (!modal) { console.error('Details modal not found in HTML'); return; }

    const title = document.getElementById('modalTitle');
    const directions = { N: 'NORTH', S: 'SOUTH', E: 'EAST', W: 'WEST' };

    // Show modal immediately with loading state
    title.innerText = `${directions[direction] || direction} — Loading...`;
    modal.style.display = 'flex';

    try {
        // Fetch Summary + Charts in parallel
        const [summaryRes, chartRes] = await Promise.all([
            fetch(`/api/analytics/direction/${direction}/summary/?format=json`),
            fetch(`/api/analytics/direction/${direction}/charts/?format=json`)
        ]);

        const summary = await summaryRes.json();
        const chartData = await chartRes.json();

        // ── Populate Title ──
        title.innerText = `${directions[direction] || direction} — Direction Details`;

        // ── Populate Summary Stats ──
        const totalEl = document.getElementById('modalTotalVehicles');
        if (totalEl) totalEl.innerText = summary.current_vehicles ?? summary.total_vehicles_today ?? 0;

        const densityEl = document.getElementById('modalPeakDensity');
        if (densityEl) densityEl.innerText = (summary.max_density_score ?? 0).toFixed(1);

        const greenEl = document.getElementById('modalGreenTime');
        if (greenEl) greenEl.innerText = (summary.total_green_time ?? 0) + 's';

        const emergEl = document.getElementById('modalEmergencyCount');
        if (emergEl) emergEl.innerText = summary.emergency_events ?? 0;

        const waitEl = document.getElementById('modalAvgWait');
        if (waitEl) waitEl.innerText = (summary.average_wait_time ?? 0) + 's';

        // ── Populate Vehicle Breakdown ──
        const list = document.getElementById('modalBreakdownList');
        if (list) {
            const bd = summary.vehicle_breakdown || {};
            list.innerHTML = `
                <li><span><i class="fa-solid fa-motorcycle"></i> Two Wheelers</span> <strong>${bd.two_wheeler ?? 0}</strong></li>
                <li><span><i class="fa-solid fa-car"></i> Four Wheelers</span> <strong>${bd.four_wheeler ?? 0}</strong></li>
                <li><span><i class="fa-solid fa-truck"></i> Heavy Vehicles</span> <strong>${bd.heavy_vehicle ?? 0}</strong></li>
                <li><span><i class="fa-solid fa-truck-medical" style="color:var(--neon-red)"></i> Emergency</span> <strong>${bd.emergency_vehicle ?? 0}</strong></li>
            `;
        }

        // ── Render Traffic Flow Chart ──
        const labels = chartData.flow_labels || chartData.labels || [];
        const data = chartData.flow_data || chartData.vehicles || [];
        renderDetailsChart(labels, data);

    } catch (e) {
        console.error('Details fetch error:', e);
        title.innerText = 'Error Loading Data';
    }
};

function renderDetailsChart(labels, data) {
    const canvas = document.getElementById('detailsChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    if (detailsChartInstance) detailsChartInstance.destroy();

    const gradient = ctx.createLinearGradient(0, 0, 0, 300);
    gradient.addColorStop(0, 'rgba(34, 211, 238, 0.4)');
    gradient.addColorStop(1, 'rgba(34, 211, 238, 0.0)');

    detailsChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Traffic Flow',
                data: data,
                borderColor: '#22d3ee',
                backgroundColor: gradient,
                borderWidth: 2.5,
                pointBackgroundColor: '#ffffff',
                pointBorderColor: '#22d3ee',
                pointHoverBackgroundColor: '#22d3ee',
                pointHoverBorderColor: '#ffffff',
                pointRadius: 4,
                pointHoverRadius: 6,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(255,255,255,0.05)', borderDash: [5, 5] },
                    ticks: { color: '#94a3b8', font: { family: 'Inter' } }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#94a3b8', font: { family: 'Inter' } }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.95)',
                    titleColor: '#fff',
                    bodyColor: '#cbd5e1',
                    borderColor: 'rgba(34, 211, 238, 0.3)',
                    borderWidth: 1,
                    padding: 10,
                    displayColors: false,
                    callbacks: {
                        label: function (context) {
                            return context.parsed.y + ' Vehicle(s)';
                        }
                    }
                }
            }
        }
    });
}

window.closeDetailsModal = function () {
    const modal = document.getElementById('detailsModal');
    if (modal) modal.style.display = 'none';
};
