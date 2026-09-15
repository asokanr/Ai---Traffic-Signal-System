// ============================================================
// SCHEMATIC MINI-MAP CONFIGURATION
// ============================================================
const CONFIG = {
    roadWidth: 160, // Wider for realistic feel
    laneWidth: 80,
    stopOffset: 100,
    colors: {
        bg: '#020617', // Slate-950 (Deep Night)
        road: '#1e293b', // Slate-800 (Asphalt)
        sidewalk: '#0f172a', // Slate-900
        laneLine: '#475569', // Slate-600
        stopLine: '#f8fafc', // Slate-50 (Bright White)
        crosswalk: '#cbd5e1', // Slate-300
        vehicle: {
            car: '#3b82f6', // Blue
            bike: '#a855f7', // Purple
            truck: '#f59e0b', // Amber
            emergency: '#ef4444' // Red
        },
        signal: {
            red: '#ff4d4d',
            yellow: '#fbbf24',
            green: '#22c55e',
            inactive: '#1f2937',
            box: '#000000'
        }
    }
};

let sosRegions = []; // Store clickable SOS areas

let canvas, ctx;
let animationId;
let vehicles = []; // Visual vehicle objects

// Vehicle Class for Mini-Map
class MiniMapVehicle {
    constructor(direction, type) {
        this.direction = direction;
        this.type = type;
        this.initPosition();

        // Visual Props
        this.color = CONFIG.colors.vehicle[type] || CONFIG.colors.vehicle.car;

        // Size & Physics
        if (type === 'truck') {
            this.length = 26; this.width = 11;
            this.maxSpeed = 1.5 + Math.random();
            this.accel = 0.04;
        } else if (type === 'bike') {
            this.length = 14; this.width = 6;
            this.maxSpeed = 3.5 + Math.random();
            this.accel = 0.15;
        } else if (type === 'emergency') {
            this.length = 22; this.width = 10;
            this.maxSpeed = 4.5;
            this.accel = 0.2;
        } else { // Car
            this.length = 18; this.width = 9;
            this.maxSpeed = 2.5 + Math.random() * 1.5;
            this.accel = 0.08;
        }

        this.speed = this.maxSpeed * 0.5; // Start with some momentum
        this.crossed = false;
        this.gap = 20 + Math.random() * 15; // Safe distance
    }

    initPosition() {
        const cx = canvas.width / 2;
        const cy = canvas.height / 2;
        const spawnPadding = 80;
        const roadOffset = CONFIG.roadWidth / 4;

        // Initial positions (spawn far out)
        if (this.direction === 'N') {
            this.x = cx - roadOffset;
            this.y = -spawnPadding;
            this.dx = 0; this.dy = 1;
        } else if (this.direction === 'S') {
            this.x = cx + roadOffset;
            this.y = canvas.height + spawnPadding;
            this.dx = 0; this.dy = -1;
        } else if (this.direction === 'E') {
            this.x = canvas.width + spawnPadding;
            this.y = cy - roadOffset;
            this.dx = -1; this.dy = 0;
        } else if (this.direction === 'W') {
            this.x = -spawnPadding;
            this.y = cy + roadOffset;
            this.dx = 1; this.dy = 0;
        }
    }

    update() {
        const cx = canvas.width / 2;
        const cy = canvas.height / 2;
        const stopDist = CONFIG.stopOffset;

        // 1. Calculate Distance to Stop Line (Center)
        let distToCenter = 0;
        if (this.direction === 'N') distToCenter = cy - this.y;
        if (this.direction === 'S') distToCenter = this.y - cy;
        if (this.direction === 'E') distToCenter = this.x - cx;
        if (this.direction === 'W') distToCenter = cx - this.x;

        // 2. Identify Target Speed
        let targetSpeed = this.maxSpeed;

        // Signal Check
        const signal = window.signalData[this.direction];
        const state = signal ? signal.current_state : 'RED';
        const isEmergency = this.type === 'emergency' || (signal && signal.is_emergency_active);

        // If not crossed yet
        if (!this.crossed) {
            // Check Stop Line
            if (distToCenter > stopDist - 10 && distToCenter < stopDist + 150) {
                if (state === 'RED' && !isEmergency) {
                    const distToStop = distToCenter - stopDist;
                    if (distToStop < 40) targetSpeed = 0;
                    else targetSpeed = Math.min(this.maxSpeed, distToStop / 20);
                }
                else if (state === 'YELLOW' && !isEmergency) {
                    if (distToCenter > stopDist + 40) targetSpeed = 0;
                }
            }
            // Mark Crossed
            if (distToCenter <= stopDist - 20) this.crossed = true;
        }

        // 3. Collision / Gap Logic
        let vehicleAhead = null;
        let minDistAhead = Infinity;

        vehicles.forEach(other => {
            if (other.direction === this.direction && other !== this) {
                let d = 0;
                let isFront = false;

                if (this.direction === 'N') { if (other.y > this.y) { d = other.y - this.y; isFront = true; } }
                if (this.direction === 'S') { if (other.y < this.y) { d = this.y - other.y; isFront = true; } }
                if (this.direction === 'E') { if (other.x < this.x) { d = this.x - other.x; isFront = true; } }
                if (this.direction === 'W') { if (other.x > this.x) { d = other.x - this.x; isFront = true; } }

                if (isFront && d < minDistAhead) {
                    minDistAhead = d;
                    vehicleAhead = other;
                }
            }
        });

        if (vehicleAhead) {
            const requiredGap = (this.length / 2 + vehicleAhead.length / 2) + this.gap;
            if (minDistAhead < requiredGap + 20) {
                if (minDistAhead < requiredGap) targetSpeed = 0; // Brake
                else targetSpeed = Math.min(targetSpeed, vehicleAhead.speed);
            }
        }

        // 4. Apply Physics
        if (this.speed < targetSpeed) this.speed += this.accel;
        else if (this.speed > targetSpeed) this.speed -= this.accel * 2;
        if (this.speed < 0) this.speed = 0;

        // Move
        this.x += this.dx * this.speed;
        this.y += this.dy * this.speed;
    }

    draw() {
        ctx.save();
        ctx.translate(this.x, this.y);

        let rot = 0;
        if (this.direction === 'N') rot = Math.PI; // FLIP? N moves +y (down). If standard is right, +y is 90deg?
        // Standard geometric: 0 = Right, 90 = Down, 180 = Left, 270 = Up.
        if (this.direction === 'N') rot = Math.PI / 2;
        if (this.direction === 'S') rot = -Math.PI / 2;
        if (this.direction === 'E') rot = Math.PI;
        if (this.direction === 'W') rot = 0;

        ctx.rotate(rot);

        const len = this.length;
        const wid = this.width;

        // Headlights (Cone)
        const grad = ctx.createRadialGradient(len / 2 + 20, 0, 0, len / 2 + 60, 0, 50);
        grad.addColorStop(0, 'rgba(255, 255, 200, 0.4)');
        grad.addColorStop(1, 'rgba(255, 255, 200, 0)');
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.moveTo(len / 2, -wid / 2 + 1);
        ctx.lineTo(len / 2 + 80, -wid * 2);
        ctx.lineTo(len / 2 + 80, wid * 2);
        ctx.lineTo(len / 2, wid / 2 - 1);
        ctx.fill();

        // Body Shadow
        ctx.shadowColor = 'rgba(0,0,0,0.8)';
        ctx.shadowBlur = 10;

        // Body
        ctx.fillStyle = this.color;

        // Special Emergency Flash
        if (this.type === 'emergency') {
            const flash = Math.floor(Date.now() / 150) % 2 === 0;
            ctx.fillStyle = flash ? '#ef4444' : '#3b82f6'; // Red/Blue police style
            ctx.shadowColor = ctx.fillStyle;
            ctx.shadowBlur = 20;
        }

        if (ctx.roundRect) {
            ctx.beginPath();
            ctx.roundRect(-len / 2, -wid / 2, len, wid, 3);
            ctx.fill();
        } else {
            ctx.fillRect(-len / 2, -wid / 2, len, wid);
        }
        ctx.shadowBlur = 0;

        // Windshield (Black glass)
        ctx.fillStyle = '#000000';
        // Front
        ctx.fillRect(len / 6, -wid / 2 + 1, 3, wid - 2);
        // Rear
        ctx.fillRect(-len / 3, -wid / 2 + 1, 2, wid - 2);

        // Roof Lights (Emergency)
        if (this.type === 'emergency') {
            ctx.fillStyle = '#ffffff';
            ctx.fillRect(-2, -wid / 2 + 2, 4, wid - 4);
        }

        // Taillights
        ctx.fillStyle = '#ef4444'; // Red
        ctx.shadowColor = '#ef4444';
        ctx.shadowBlur = 5;
        ctx.beginPath();
        ctx.arc(-len / 2, -wid / 3, 1.5, 0, Math.PI * 2);
        ctx.arc(-len / 2, wid / 3, 1.5, 0, Math.PI * 2);
        ctx.fill();
        ctx.shadowBlur = 0;

        // Headlight Sources (White dots)
        ctx.fillStyle = '#ffffe0';
        ctx.beginPath();
        ctx.arc(len / 2, -wid / 3, 1, 0, Math.PI * 2);
        ctx.arc(len / 2, wid / 3, 1, 0, Math.PI * 2);
        ctx.fill();

        ctx.restore();
    }
}

function spawnVisuals() {
    if (!window.simulationActive) return;
    if (Math.random() > 0.05) return; // Spawn rate

    if (typeof vehicleQueues === 'undefined') return;

    ['N', 'S', 'E', 'W'].forEach(dir => {
        const qData = vehicleQueues[dir];
        if (!qData) return;

        // Total pending
        const totalPending = qData.two_wheeler + qData.four_wheeler + qData.heavy_vehicle + qData.emergency_vehicle;

        // Count displayed
        const visualCount = vehicles.filter(v => v.direction === dir && !v.crossed).length;

        if (visualCount < totalPending) {
            // Safety check
            let safe = true;
            vehicles.forEach(v => {
                if (v.direction === dir && !v.crossed) {
                    if (dir === 'N' && v.y < 70) safe = false;
                    if (dir === 'S' && v.y > canvas.height - 70) safe = false;
                    if (dir === 'E' && v.x > canvas.width - 70) safe = false;
                    if (dir === 'W' && v.x < 70) safe = false;
                }
            });

            if (safe) {
                let type = 'car';
                if (qData.emergency_vehicle > visualCount && Math.random() < 0.5) type = 'emergency';
                else if (qData.heavy_vehicle > 0 && Math.random() < 0.2) type = 'truck';
                else if (qData.two_wheeler > 0 && Math.random() < 0.3) type = 'bike';

                vehicles.push(new MiniMapVehicle(dir, type));
            }
        }
    });
}

function drawGrid() {
    // Subtle background texture
    ctx.strokeStyle = '#0f172a'; // Very subtle slate
    ctx.lineWidth = 1;
    const step = 40;
    ctx.beginPath();
    for (let x = 0; x < canvas.width; x += step) { ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); }
    for (let y = 0; y < canvas.height; y += step) { ctx.moveTo(0, y); ctx.lineTo(canvas.width, y); }
    ctx.stroke();
}

function drawSchematicRoads() {
    const w = canvas.width;
    const h = canvas.height;
    const cx = w / 2;
    const cy = h / 2;
    const rw = CONFIG.roadWidth;
    const off = CONFIG.stopOffset;

    ctx.clearRect(0, 0, w, h);

    // 1. Sidewalks (Fill corners)
    ctx.fillStyle = CONFIG.colors.sidewalk;
    // Corners are actually the background technically, but let's make them distinct
    // The road is a cross shape, so corners are the 4 quadrants minus the road
    // We can just clearRect or fillRect the whole bg, then draw roads on top.

    // Background Grid
    ctx.fillStyle = CONFIG.colors.bg;
    ctx.fillRect(0, 0, w, h);
    drawGrid();


    // 2. Roads (Asphalt)
    ctx.fillStyle = CONFIG.colors.road;
    // We want a subtle grain or just simple flat color for now.
    ctx.shadowColor = '#000';
    ctx.shadowBlur = 10;

    // Draw perpendicular roads
    ctx.fillRect(cx - rw / 2, 0, rw, h); // Vertical
    ctx.fillRect(0, cy - rw / 2, w, rw); // Horizontal
    ctx.shadowBlur = 0;

    // Intersection Box (Slightly lighter or darker?)
    ctx.fillStyle = '#1e293b'; // Same for smooth look
    ctx.fillRect(cx - rw / 2, cy - rw / 2, rw, rw);

    // 3. Markings
    ctx.strokeStyle = CONFIG.colors.laneLine;
    ctx.lineWidth = 2;

    // Center divider (Yellow or white?) White is modern.
    ctx.setLineDash([20, 20]); // Dashed
    ctx.beginPath();
    // Vertical
    ctx.moveTo(cx, 0); ctx.lineTo(cx, cy - off - 20); // Stop before crosswalk
    ctx.moveTo(cx, cy + off + 20); ctx.lineTo(cx, h);
    // Horizontal
    ctx.moveTo(0, cy); ctx.lineTo(cx - off - 20, cy);
    ctx.moveTo(cx + off + 20, cy); ctx.lineTo(w, cy);
    ctx.stroke();

    // Shoulder lines (Solid)
    ctx.setLineDash([]);
    ctx.strokeStyle = '#334155'; // Darker
    ctx.beginPath();
    // Vertical Shoulders
    ctx.moveTo(cx - rw / 2 + 5, 0); ctx.lineTo(cx - rw / 2 + 5, h);
    ctx.moveTo(cx + rw / 2 - 5, 0); ctx.lineTo(cx + rw / 2 - 5, h);
    // Horizontal Shoulders
    ctx.moveTo(0, cy - rw / 2 + 5); ctx.lineTo(w, cy - rw / 2 + 5);
    ctx.moveTo(0, cy + rw / 2 - 5); ctx.lineTo(w, cy + rw / 2 - 5);
    ctx.stroke();

    // 4. Crosswalks (Zebra)
    ctx.fillStyle = CONFIG.colors.crosswalk;
    const stripeW = 10;
    const stripeH = rw - 20; // Full road width minus shoulders
    const cwPos = off + 10; // Position from center

    // Function to draw zebra
    const drawZebra = (x, y, w, h, vertical) => {
        const count = 6;
        const gap = w / count;
        for (let i = 0; i < count; i++) {
            if (vertical) ctx.fillRect(x + i * gap + 2, y, gap - 4, h);
            else ctx.fillRect(x, y + i * gap + 2, w, gap - 4);
        }
    };

    // North (Top) - Horizontal Stripes
    // Pos: cy - cwPos - 20 (thickness 20)
    // Actually zebra stripes span across the road width?
    // Standard: Stripes are parallel to road flow.
    // N road: Flow is vertical. Stripes are vertical bars.
    // Rect: [cx - rw/2 + 10, cy - off - 20, rw - 20, 20]
    drawZebra(cx - rw / 2 + 10, cy - off - 15, rw - 20, 15, true);

    // South
    drawZebra(cx - rw / 2 + 10, cy + off, rw - 20, 15, true);

    // West (Left) - Horizontal bars
    drawZebra(cx - off - 15, cy - rw / 2 + 10, 15, rw - 20, false);

    // East
    drawZebra(cx + off, cy - rw / 2 + 10, 15, rw - 20, false);


    // 5. Stop Lines (Thick Glowing Bar)
    ctx.strokeStyle = CONFIG.colors.stopLine;
    ctx.lineWidth = 4;
    ctx.shadowColor = '#fff';
    ctx.shadowBlur = 10;
    ctx.setLineDash([]);

    // N Stop (Line before crosswalk)
    ctx.beginPath();
    ctx.moveTo(cx, cy - off); ctx.lineTo(cx - rw / 2 + 10, cy - off); // Only right lane (incoming)?? No, full width usually
    // Actually for traffic light, stop line is for incoming traffic.
    // N incoming is Left side (if driving right) or Right side (if driving left).
    // Let's assume driving LEFT (India/UK) or RIGHT (US)?
    // Code says: "N... moveTo(cx - rw/2, cy - off)... lineTo(cx, cy - off)"
    // That covers the LEFT half of the vertical road (if looking from top).
    // If N is moving DOWN, it stays on the LEFT side (if US/Right-hand traffic)? No, Right hand traffic drives on Right.
    // If driving on Right: N(down) uses Left part of screen? No, Right part of screen.
    // Let's stick to the previous logic which assumes N is Top-Left quadrant?
    // Original code: "ctx.moveTo(cx - rw / 2, cy - off); ctx.lineTo(cx, cy - off);" -> Left half.
    // That implies incoming traffic from North is on the Left side. That's Left-Hand Traffic (UK/India).
    // Okay, maintain Left-Hand Traffic visual.

    // N (Top Left)
    ctx.beginPath(); ctx.moveTo(cx - rw / 2 + 5, cy - off - 20); ctx.lineTo(cx - 5, cy - off - 20); ctx.stroke();

    // S (Bottom Right)
    ctx.beginPath(); ctx.moveTo(cx + 5, cy + off + 20); ctx.lineTo(cx + rw / 2 - 5, cy + off + 20); ctx.stroke();

    // E (Right Top) -> Incoming from East moves Left. Top half.
    ctx.beginPath(); ctx.moveTo(cx + off + 20, cy - rw / 2 + 5); ctx.lineTo(cx + off + 20, cy - 5); ctx.stroke();

    // W (Left Bottom) -> Incoming from West moves Right. Bottom half.
    ctx.beginPath(); ctx.moveTo(cx - off - 20, cy + 5); ctx.lineTo(cx - off - 20, cy + rw / 2 - 5); ctx.stroke();

    ctx.shadowBlur = 0;
}

function drawSchematicSignals() {
    const cx = canvas.width / 2;
    const cy = canvas.height / 2;
    const rw = CONFIG.roadWidth;
    const off = CONFIG.stopOffset + 20; // Align with new stop lines

    sosRegions = [];

    const boxW = 16; const boxH = 40; // Slightly bigger

    ['N', 'S', 'E', 'W'].forEach(dir => {
        const s = window.signalData ? window.signalData[dir] : null;
        const state = s ? s.current_state : 'RED';
        const isEmergency = s && s.is_emergency_active;

        ctx.save();
        let x, y, rot;

        // Position signals naturally near stop lines
        if (dir === 'N') { x = cx - rw / 2 - 30; y = cy - off; rot = 0; }
        else if (dir === 'S') { x = cx + rw / 2 + 30; y = cy + off; rot = Math.PI; }
        else if (dir === 'E') { x = cx + off; y = cy - rw / 2 - 30; rot = Math.PI / 2; }
        else if (dir === 'W') { x = cx - off; y = cy + rw / 2 + 30; rot = -Math.PI / 2; }

        ctx.translate(x, y);
        ctx.rotate(rot);

        // Pole
        ctx.fillStyle = '#64748b'; // Slate pole
        ctx.fillRect(-2, -5, 4, 30); // Vertical stand

        ctx.strokeStyle = '#64748b';
        ctx.lineWidth = 4;
        ctx.beginPath();
        ctx.moveTo(0, 0); ctx.lineTo(20, 0); // Arm sticking out
        ctx.stroke();

        // Signal Box
        ctx.fillStyle = '#0f172a';
        ctx.shadowColor = '#000';
        ctx.shadowBlur = 5;
        // Position at end of arm
        ctx.translate(20, 0);
        ctx.fillRect(-boxW / 2, -boxH / 2, boxW, boxH);

        // Border
        ctx.strokeStyle = state === 'GREEN' ? '#22c55e' : (state === 'RED' ? '#ef4444' : '#fbbf24');
        ctx.lineWidth = 1;
        ctx.strokeRect(-boxW / 2, -boxH / 2, boxW, boxH);

        ctx.shadowBlur = 0;

        // Lights
        const colors = [CONFIG.colors.signal.red, CONFIG.colors.signal.yellow, CONFIG.colors.signal.green];
        const activeIdx = state === 'RED' ? 0 : (state === 'YELLOW' ? 1 : 2);

        [0, 1, 2].forEach((i) => {
            const ly = -boxH / 2 + 7 + i * 13;
            ctx.beginPath();
            ctx.arc(0, ly, 4, 0, Math.PI * 2);
            if (i === activeIdx) {
                ctx.fillStyle = colors[i];
                ctx.shadowColor = colors[i];
                ctx.shadowBlur = 20;
            } else {
                ctx.fillStyle = '#334155';
                ctx.shadowBlur = 0;
            }
            if (isEmergency && i === 2 && (Date.now() % 400 < 200)) {
                // Blink green
                ctx.shadowBlur = 40;
                ctx.fillStyle = '#fff';
            }
            ctx.fill();
        });

        ctx.restore();
    });
}

function animate() {
    drawSchematicRoads();
    drawSchematicSignals();
    spawnVisuals();

    vehicles.forEach((v, i) => {
        v.update();
        v.draw();
        // Cull
        if (v.x < -100 || v.x > canvas.width + 100 || v.y < -100 || v.y > canvas.height + 100) {
            vehicles.splice(i, 1);
        }
    });

    animationId = requestAnimationFrame(animate);
}

// Init
window.addEventListener('load', () => {
    canvas = document.getElementById('intersectionCanvas');
    if (canvas) {
        ctx = canvas.getContext('2d');

        const resizeCanvas = () => {
            const parent = canvas.parentElement;
            if (parent) {
                canvas.width = parent.clientWidth;
                canvas.height = parent.clientHeight;
            }
        };

        window.addEventListener('resize', resizeCanvas);
        resizeCanvas();
        animate();
    }
});