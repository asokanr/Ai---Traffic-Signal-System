/**
 * Multi-Junction Control Module
 * Handles junction selection, signal status display,
 * manual override, and remote timing configuration.
 */

let currentJunctionId = null;
let junctionSignals = [];

async function initMultiJunctionView() {
    await loadJunctions();
    await loadJunctionOverviewCards();
}

async function loadJunctions() {
    try {
        const res = await fetch('/api/junctions/');
        const data = await res.json();
        const junctions = data.results || data;

        const selector = document.getElementById('junctionSelector');
        if (!selector) return;

        // Keep the default option
        selector.innerHTML = '<option value="">-- Select Junction --</option>';

        junctions.forEach(jn => {
            const opt = document.createElement('option');
            opt.value = jn.id;
            opt.textContent = `${jn.name} (${jn.code})`;
            selector.appendChild(opt);
        });
    } catch (err) {
        console.error('Junctions load error:', err);
    }
}

async function loadJunctionOverviewCards() {
    try {
        const res = await fetch('/api/junctions/');
        const data = await res.json();
        const junctions = data.results || data;

        const grid = document.getElementById('junctionOverviewGrid');
        if (!grid) return;

        grid.innerHTML = '';

        for (const jn of junctions) {
            // Get junction status
            let statusData = null;
            try {
                const statusRes = await fetch(`/api/junctions/${jn.id}/status/`);
                statusData = await statusRes.json();
            } catch (e) {
                statusData = { total_vehicles: 0, avg_density: 0, emergency_active: false };
            }

            const isEmergency = statusData.emergency_active;
            const cardClass = isEmergency ? 'junction-card junction-card-emergency' : 'junction-card';

            const card = document.createElement('div');
            card.className = cardClass;
            card.onclick = () => {
                document.getElementById('junctionSelector').value = jn.id;
                loadJunctionStatus();
            };

            card.innerHTML = `
                <div class="junction-card-header">
                    <h4>${jn.name}</h4>
                    <span class="junction-code">${jn.code}</span>
                </div>
                <div class="junction-card-stats">
                    <div class="jc-stat">
                        <span class="jc-stat-value">${statusData.total_vehicles || 0}</span>
                        <span class="jc-stat-label">Vehicles</span>
                    </div>
                    <div class="jc-stat">
                        <span class="jc-stat-value">${statusData.avg_density || 0}</span>
                        <span class="jc-stat-label">Density</span>
                    </div>
                    <div class="jc-stat">
                        <span class="jc-stat-value">${jn.signal_count || 0}</span>
                        <span class="jc-stat-label">Signals</span>
                    </div>
                </div>
                ${isEmergency ? '<div class="junction-emergency-tag">🚨 EMERGENCY</div>' : ''}
            `;

            grid.appendChild(card);
        }

        if (junctions.length === 0) {
            grid.innerHTML = '<p style="color:var(--text-secondary); padding:20px;">No junctions configured. Add junctions via Admin panel.</p>';
        }
    } catch (err) {
        console.error('Junction overview error:', err);
    }
}

async function loadJunctionStatus() {
    const selector = document.getElementById('junctionSelector');
    const jnId = selector.value;

    if (!jnId) {
        document.getElementById('selectedJunctionDetail').style.display = 'none';
        return;
    }

    currentJunctionId = jnId;

    try {
        const res = await fetch(`/api/junctions/${jnId}/status/`);
        const data = await res.json();

        document.getElementById('selectedJunctionDetail').style.display = 'block';
        document.getElementById('selectedJunctionTitle').innerHTML =
            `<i class="fa-solid fa-traffic-light"></i> ${data.junction.name} — Signals`;

        junctionSignals = data.signals || [];
        renderJunctionSignals(junctionSignals);
        populateSignalSelectors(junctionSignals);

    } catch (err) {
        console.error('Junction status error:', err);
    }
}

function renderJunctionSignals(signals) {
    const grid = document.getElementById('junctionSignalsGrid');
    if (!grid) return;

    grid.innerHTML = '';

    const dirNames = { 'N': 'North', 'S': 'South', 'E': 'East', 'W': 'West' };
    const stateColors = { 'RED': '#ef4444', 'YELLOW': '#eab308', 'GREEN': '#22c55e' };

    signals.forEach(sig => {
        const card = document.createElement('div');
        card.className = 'junction-signal-card';

        const stateColor = stateColors[sig.current_state] || '#888';
        const isCongested = sig.density_percentage > 70;

        card.innerHTML = `
            <div class="jsc-header" style="border-left: 4px solid ${stateColor};">
                <h4>${dirNames[sig.direction] || sig.direction}</h4>
                <div class="jsc-state" style="color:${stateColor};">${sig.current_state}</div>
            </div>
            <div class="jsc-body">
                <div class="jsc-metric">
                    <span class="jsc-metric-label">Vehicles</span>
                    <span class="jsc-metric-value">${sig.vehicle_count}</span>
                </div>
                <div class="jsc-metric">
                    <span class="jsc-metric-label">Density</span>
                    <div class="density-bar-container">
                        <div class="density-bar" style="width:${sig.density_percentage || 0}%; background:${stateColor};"></div>
                    </div>
                    <span class="jsc-metric-value">${sig.density_percentage || 0}%</span>
                </div>
                <div class="jsc-metric">
                    <span class="jsc-metric-label">Timer</span>
                    <span class="jsc-metric-value">${sig.remaining_time || 0}s</span>
                </div>
                <div class="jsc-metric">
                    <span class="jsc-metric-label">Mode</span>
                    <span class="jsc-metric-value mode-${sig.mode}">${sig.mode}</span>
                </div>
            </div>
            ${isCongested ? '<div class="congestion-warning">⚠️ CONGESTED</div>' : ''}
        `;

        grid.appendChild(card);
    });
}

function populateSignalSelectors(signals) {
    const dirNames = { 'N': 'North', 'S': 'South', 'E': 'East', 'W': 'West' };
    const overrideSelect = document.getElementById('overrideSignalSelect');
    const timingSelect = document.getElementById('timingSignalSelect');

    [overrideSelect, timingSelect].forEach(sel => {
        if (!sel) return;
        sel.innerHTML = '';
        signals.forEach(sig => {
            const opt = document.createElement('option');
            opt.value = sig.id;
            opt.textContent = `${dirNames[sig.direction] || sig.direction} (${sig.current_state})`;
            sel.appendChild(opt);
        });
    });
}

// Modal controls
function showOverrideModal() {
    document.getElementById('overrideModal').style.display = 'flex';
}
function closeOverrideModal() {
    document.getElementById('overrideModal').style.display = 'none';
}
function showTimingModal() {
    document.getElementById('timingModal').style.display = 'flex';
}
function closeTimingModal() {
    document.getElementById('timingModal').style.display = 'none';
}

async function applyOverride() {
    const signalId = document.getElementById('overrideSignalSelect').value;
    const newState = document.getElementById('overrideStateSelect').value;

    if (!signalId) {
        showNotification('Error', 'Please select a signal.', 'warning');
        return;
    }

    try {
        const res = await fetch(`/api/signals/${signalId}/manual_override/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken(),
            },
            body: JSON.stringify({ state: newState }),
        });

        const data = await res.json();

        if (res.ok) {
            showNotification('Override Applied', `Signal changed to ${newState}`, 'success');
            closeOverrideModal();
            loadJunctionStatus();
        } else {
            showNotification('Override Failed', data.error || 'Access denied', 'danger');
        }
    } catch (err) {
        showNotification('Error', 'Failed to apply override', 'danger');
    }
}

async function applyTimingConfig() {
    const signalId = document.getElementById('timingSignalSelect').value;
    const green = document.getElementById('timingGreen').value;
    const yellow = document.getElementById('timingYellow').value;
    const red = document.getElementById('timingRed').value;

    if (!signalId) {
        showNotification('Error', 'Please select a signal.', 'warning');
        return;
    }

    try {
        const res = await fetch(`/api/signals/${signalId}/configure_timing/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken(),
            },
            body: JSON.stringify({ green_time: green, yellow_time: yellow, red_time: red }),
        });

        const data = await res.json();

        if (res.ok) {
            showNotification('Timing Updated', `Configuration applied successfully`, 'success');
            closeTimingModal();
            loadJunctionStatus();
        } else {
            showNotification('Config Failed', data.error || 'Access denied', 'danger');
        }
    } catch (err) {
        showNotification('Error', 'Failed to apply timing config', 'danger');
    }
}

function getCSRFToken() {
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'csrftoken') return value;
    }
    return '';
}

// ============================================================
// ADD NEW JUNCTION
// ============================================================

function showAddJunctionModal() {
    // Reset form
    document.getElementById('newJunctionName').value = '';
    document.getElementById('newJunctionCode').value = '';
    document.getElementById('newJunctionLat').value = '0.0';
    document.getElementById('newJunctionLng').value = '0.0';
    document.getElementById('newJunctionCreateSignals').checked = true;
    document.getElementById('addJunctionModal').style.display = 'flex';
}

function closeAddJunctionModal() {
    document.getElementById('addJunctionModal').style.display = 'none';
}

async function createJunction() {
    const name = document.getElementById('newJunctionName').value.trim();
    const code = document.getElementById('newJunctionCode').value.trim();
    const latitude = parseFloat(document.getElementById('newJunctionLat').value) || 0.0;
    const longitude = parseFloat(document.getElementById('newJunctionLng').value) || 0.0;
    const createSignals = document.getElementById('newJunctionCreateSignals').checked;

    // Validation
    if (!name) {
        showNotification('Validation Error', 'Junction name is required.', 'warning');
        return;
    }
    if (!code) {
        showNotification('Validation Error', 'Junction code is required.', 'warning');
        return;
    }

    const btn = document.getElementById('createJunctionBtn');
    const origHTML = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Creating...';
    btn.disabled = true;

    try {
        // 1. Create the junction
        const res = await fetch('/api/junctions/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken(),
            },
            body: JSON.stringify({
                name: name,
                code: code,
                latitude: latitude,
                longitude: longitude,
                is_active: true,
            }),
        });

        const data = await res.json();

        if (!res.ok) {
            // Parse error messages
            let errorMsg = 'Failed to create junction.';
            if (typeof data === 'object') {
                const errors = [];
                for (const key in data) {
                    const fieldErrors = Array.isArray(data[key]) ? data[key].join(', ') : data[key];
                    errors.push(`${key}: ${fieldErrors}`);
                }
                if (errors.length > 0) errorMsg = errors.join(' | ');
            }
            showNotification('Creation Failed', errorMsg, 'danger');
            return;
        }

        const junctionId = data.id;

        // 2. Auto-create 4 directional signals if checked
        if (createSignals && junctionId) {
            const directions = ['N', 'S', 'E', 'W'];
            for (const dir of directions) {
                try {
                    await fetch('/api/signals/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCSRFToken(),
                        },
                        body: JSON.stringify({
                            junction: junctionId,
                            direction: dir,
                            current_state: 'RED',
                            green_time: 30,
                            yellow_time: 5,
                            red_time: 10,
                        }),
                    });
                } catch (sigErr) {
                    console.warn(`Failed to create signal ${dir}:`, sigErr);
                }
            }
        }

        showNotification('Junction Created', `"${name}" has been created successfully!`, 'success');
        closeAddJunctionModal();

        // 3. Refresh the multi-junction view
        await loadJunctions();
        await loadJunctionOverviewCards();

        // 4. Auto-select the new junction
        const selector = document.getElementById('junctionSelector');
        if (selector && junctionId) {
            selector.value = junctionId;
            loadJunctionStatus();
        }

    } catch (err) {
        console.error('Create junction error:', err);
        showNotification('Error', 'An unexpected error occurred.', 'danger');
    } finally {
        btn.innerHTML = origHTML;
        btn.disabled = false;
    }
}

// Close modals when clicking on the dark backdrop or pressing Escape
document.addEventListener('DOMContentLoaded', () => {
    ['overrideModal', 'timingModal', 'addJunctionModal'].forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('click', (e) => {
                if (e.target === el) {
                    el.classList.add('hidden');
                    el.style.display = 'none';
                }
            });
        }
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            ['overrideModal', 'timingModal', 'addJunctionModal'].forEach(id => {
                const el = document.getElementById(id);
                if (el) {
                    el.classList.add('hidden');
                    el.style.display = 'none';
                }
            });
        }
    });
});
