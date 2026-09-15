/* ============================================================
   SMART TRAFFIC AI – AUTH PAGE INTERACTIVE EFFECTS + LOGIC
   ============================================================ */

(function () {
    'use strict';

    /* ============================
       CSRF TOKEN HELPER
    ============================ */
    function getCSRFToken() {
        const el = document.querySelector('[name=csrfmiddlewaretoken]');
        if (el) return el.value;
        const cookie = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='));
        return cookie ? cookie.split('=')[1] : '';
    }

    /* ============================
       TOAST NOTIFICATION SYSTEM
    ============================ */
    function showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;
        const icons = { success: 'fa-circle-check', error: 'fa-circle-exclamation', info: 'fa-circle-info' };
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `<i class="fa-solid ${icons[type] || icons.info}"></i><span>${message}</span>`;
        container.appendChild(toast);
        setTimeout(() => {
            toast.classList.add('fade-out');
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    /* ============================
       INLINE FIELD ERROR HELPERS
    ============================ */
    function showFieldError(fieldName, message) {
        const group = document.getElementById(`${fieldName}-group`);
        const errorEl = document.getElementById(`${fieldName}-error`);
        if (group) {
            group.classList.add('has-error');
        }
        if (errorEl) {
            const span = errorEl.querySelector('span');
            if (span) span.textContent = message;
            errorEl.classList.add('visible');
        }
    }

    function clearFieldError(fieldName) {
        const group = document.getElementById(`${fieldName}-group`);
        const errorEl = document.getElementById(`${fieldName}-error`);
        if (group) group.classList.remove('has-error');
        if (errorEl) errorEl.classList.remove('visible');
    }

    function clearAllFieldErrors() {
        document.querySelectorAll('.input-group.has-error').forEach(g => g.classList.remove('has-error'));
        document.querySelectorAll('.field-error-msg.visible').forEach(e => e.classList.remove('visible'));
    }

    /* ============================
       PARTICLE + CIRCUIT CANVAS
    ============================ */
    const canvas = document.getElementById('particles-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    function resize() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    }
    resize();
    window.addEventListener('resize', resize);

    const PARTICLE_COUNT = 60;
    const particles = [];

    class Particle {
        constructor() { this.reset(); }
        reset() {
            this.x = Math.random() * canvas.width;
            this.y = Math.random() * canvas.height;
            this.size = Math.random() * 2 + 0.5;
            this.speedX = (Math.random() - 0.5) * 0.4;
            this.speedY = (Math.random() - 0.5) * 0.4;
            this.opacity = Math.random() * 0.5 + 0.1;
            this.color = Math.random() > 0.5 ? '99,102,241' : '34,211,238';
        }
        update() {
            this.x += this.speedX;
            this.y += this.speedY;
            if (this.x < 0 || this.x > canvas.width || this.y < 0 || this.y > canvas.height) this.reset();
        }
        draw() {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(${this.color},${this.opacity})`;
            ctx.fill();
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.size * 3, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(${this.color},${this.opacity * 0.15})`;
            ctx.fill();
        }
    }

    for (let i = 0; i < PARTICLE_COUNT; i++) particles.push(new Particle());

    const CIRCUIT_COUNT = 8;
    const circuits = [];

    class CircuitLine {
        constructor() { this.reset(); }
        reset() {
            this.segments = [];
            let x = Math.random() * canvas.width;
            let y = Math.random() * canvas.height;
            const segCount = Math.floor(Math.random() * 4) + 3;
            for (let i = 0; i < segCount; i++) {
                const nx = x + (Math.random() > 0.5 ? 1 : -1) * (Math.random() * 120 + 40);
                const ny = y + (Math.random() > 0.5 ? 1 : -1) * (Math.random() * 120 + 40);
                this.segments.push({ x1: x, y1: y, x2: nx, y2: ny });
                if (Math.random() > 0.5) x = nx; else y = ny;
                x = nx; y = ny;
            }
            this.progress = 0;
            this.speed = 0.003 + Math.random() * 0.004;
            this.opacity = 0.08 + Math.random() * 0.08;
        }
        update() {
            this.progress += this.speed;
            if (this.progress > 2) this.reset();
        }
        draw() {
            const totalSegs = this.segments.length;
            const drawProgress = Math.min(this.progress, 1);
            const segsToShow = Math.floor(drawProgress * totalSegs);
            ctx.strokeStyle = `rgba(99,102,241,${this.opacity})`;
            ctx.lineWidth = 0.8;
            ctx.beginPath();
            for (let i = 0; i <= segsToShow && i < totalSegs; i++) {
                const s = this.segments[i];
                if (i === 0) ctx.moveTo(s.x1, s.y1);
                if (i < segsToShow) {
                    ctx.lineTo(s.x2, s.y2);
                } else {
                    const frac = (drawProgress * totalSegs) - i;
                    ctx.lineTo(s.x1 + (s.x2 - s.x1) * frac, s.y1 + (s.y2 - s.y1) * frac);
                }
                if (i < segsToShow) {
                    ctx.stroke();
                    ctx.beginPath();
                    ctx.arc(s.x2, s.y2, 2, 0, Math.PI * 2);
                    ctx.fillStyle = `rgba(34,211,238,${this.opacity * 2})`;
                    ctx.fill();
                    ctx.beginPath();
                    ctx.moveTo(s.x2, s.y2);
                }
            }
            ctx.stroke();
        }
    }

    for (let i = 0; i < CIRCUIT_COUNT; i++) circuits.push(new CircuitLine());

    function animateCanvas() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        particles.forEach(p => { p.update(); p.draw(); });
        circuits.forEach(c => { c.update(); c.draw(); });
        requestAnimationFrame(animateCanvas);
    }
    animateCanvas();

    /* ============================
       DIGITAL RAIN
    ============================ */
    const rainContainer = document.querySelector('.digital-rain');
    if (rainContainer) {
        const chars = '01アイウエオカキクケコサシスセソ';
        for (let i = 0; i < 20; i++) {
            const col = document.createElement('div');
            col.className = 'rain-column';
            col.style.left = Math.random() * 100 + '%';
            col.style.animationDuration = (8 + Math.random() * 12) + 's';
            col.style.animationDelay = (-Math.random() * 15) + 's';
            let text = '';
            for (let j = 0; j < 30; j++) text += chars[Math.floor(Math.random() * chars.length)] + '\n';
            col.textContent = text;
            rainContainer.appendChild(col);
        }
    }

    /* ============================
       PARALLAX MOUSE
    ============================ */
    const loginWrapper = document.querySelector('.login-wrapper');
    const gridOverlay = document.querySelector('.city-grid-overlay');
    const radialGlow = document.querySelector('.radial-glow');

    document.addEventListener('mousemove', (e) => {
        const cx = window.innerWidth / 2;
        const cy = window.innerHeight / 2;
        const dx = (e.clientX - cx) / cx;
        const dy = (e.clientY - cy) / cy;
        if (loginWrapper) loginWrapper.style.transform = `translate(${dx * 6}px, ${dy * 6}px)`;
        if (gridOverlay) gridOverlay.style.transform = `translate(${dx * -12}px, ${dy * -12}px)`;
        if (radialGlow) radialGlow.style.transform = `translate(calc(-50% + ${dx * 20}px), calc(-50% + ${dy * 20}px))`;
    });

    /* ============================
       TRAFFIC SIGNAL CYCLING
    ============================ */
    const lights = document.querySelectorAll('.signal-light');
    const sequence = ['red', 'yellow', 'green'];
    let currentLight = 0;

    function cycleLights() {
        lights.forEach(l => l.classList.remove('active'));
        const el = document.querySelector(`.signal-light.${sequence[currentLight]}`);
        if (el) el.classList.add('active');
        currentLight = (currentLight + 1) % sequence.length;
    }
    cycleLights();
    setInterval(cycleLights, 2000);

    /* ============================
       DIGITAL CLOCK
    ============================ */
    const clockTime = document.getElementById('clock-time');
    const clockDate = document.getElementById('clock-date');

    function updateClock() {
        const now = new Date();
        if (clockTime) clockTime.textContent = now.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
        if (clockDate) clockDate.textContent = now.toLocaleDateString('en-US', { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' }).toUpperCase();
    }
    updateClock();
    setInterval(updateClock, 1000);

    /* ============================
       CONGESTION UPDATES
    ============================ */
    const congestionEl = document.getElementById('congestion-value');
    const levels = ['Low', 'Moderate', 'High'];
    const colors = { 'Low': '#4ade80', 'Moderate': '#facc15', 'High': '#f43f5e' };

    function updateCongestion() {
        if (!congestionEl) return;
        const level = levels[Math.floor(Math.random() * levels.length)];
        congestionEl.textContent = level;
        congestionEl.style.color = colors[level];
    }
    updateCongestion();
    setInterval(updateCongestion, 8000);

    /* ============================
       DARK / LIGHT MODE TOGGLE
    ============================ */
    const toggleSwitch = document.querySelector('.toggle-switch');
    if (toggleSwitch) {
        toggleSwitch.addEventListener('click', () => {
            const html = document.documentElement;
            const current = html.getAttribute('data-theme');
            html.setAttribute('data-theme', current === 'light' ? 'dark' : 'light');
        });
    }

    /* ============================
       PASSWORD VISIBILITY TOGGLE
    ============================ */
    document.querySelectorAll('.password-toggle').forEach(toggle => {
        toggle.addEventListener('click', () => {
            const input = toggle.parentElement.querySelector('input');
            if (!input) return;
            const isPassword = input.type === 'password';
            input.type = isPassword ? 'text' : 'password';
            toggle.classList.toggle('fa-eye');
            toggle.classList.toggle('fa-eye-slash');
        });
    });

    /* ============================
       ERROR STATE ON CARD
    ============================ */
    const hasErrors = document.querySelector('.login-messages .error-msg');
    if (hasErrors) {
        const card = document.querySelector('.login-card');
        if (card) {
            card.classList.add('error-state');
            setTimeout(() => card.classList.remove('error-state'), 1500);
        }
    }

    /* ============================
       BUTTON RIPPLE EFFECT
    ============================ */
    document.querySelectorAll('.btn-enter').forEach(btn => {
        btn.addEventListener('click', function (e) {
            const rect = this.getBoundingClientRect();
            const ripple = document.createElement('span');
            ripple.className = 'ripple';
            const size = Math.max(rect.width, rect.height);
            ripple.style.width = ripple.style.height = size + 'px';
            ripple.style.left = (e.clientX - rect.left - size / 2) + 'px';
            ripple.style.top = (e.clientY - rect.top - size / 2) + 'px';
            this.appendChild(ripple);
            setTimeout(() => ripple.remove(), 600);
        });
    });

    /* ============================================================
       AUTH TAB SYSTEM
    ============================================================ */
    const tabBtns = document.querySelectorAll('.tab-btn');
    const panels = document.querySelectorAll('.auth-panel');
    const gotoRegister = document.getElementById('goto-register');
    const gotoLogin = document.getElementById('goto-login');

    function switchTab(tabName) {
        tabBtns.forEach(b => b.classList.toggle('active', b.dataset.tab === tabName));
        panels.forEach(p => {
            p.classList.remove('active');
            if (p.id === `panel-${tabName}`) p.classList.add('active');
        });
    }

    tabBtns.forEach(btn => btn.addEventListener('click', () => switchTab(btn.dataset.tab)));
    if (gotoRegister) gotoRegister.addEventListener('click', (e) => { e.preventDefault(); switchTab('register'); });
    if (gotoLogin) gotoLogin.addEventListener('click', (e) => { e.preventDefault(); switchTab('login'); });

    // Check URL for ?tab=register
    if (window.location.search.includes('tab=register')) switchTab('register');

    /* ============================================================
       LOGIN FORM – SCANNING EFFECT
    ============================================================ */
    const loginForm = document.getElementById('login-form');
    const btnLogin = document.getElementById('btn-login');
    if (loginForm && btnLogin) {
        loginForm.addEventListener('submit', function () {
            btnLogin.classList.add('loading');
            const scanOverlay = document.querySelector('.scan-overlay');
            if (scanOverlay) {
                scanOverlay.classList.add('active');
                setTimeout(() => scanOverlay.classList.remove('active'), 1600);
            }
        });
    }

    /* ============================================================
       REGISTER – MULTI-STEP NAVIGATION
    ============================================================ */
    const regSteps = document.querySelectorAll('.reg-step');
    const formSteps = document.querySelectorAll('.form-step');

    function goToStep(stepNum) {
        formSteps.forEach(s => s.classList.remove('active'));
        const target = document.getElementById(`step-${stepNum}`);
        if (target) target.classList.add('active');

        regSteps.forEach(s => {
            const sn = parseInt(s.dataset.step);
            s.classList.remove('active', 'completed');
            if (sn < stepNum) s.classList.add('completed');
            if (sn === stepNum) s.classList.add('active');
        });
    }

    // Step navigation buttons
    const btnStep2 = document.getElementById('btn-step-2');
    const btnStep3 = document.getElementById('btn-step-3');
    const btnBack1 = document.getElementById('btn-back-1');
    const btnBack2 = document.getElementById('btn-back-2');

    if (btnStep2) btnStep2.addEventListener('click', () => {
        // Validate step 1 fields
        const fullname = document.getElementById('reg-fullname');
        const username = document.getElementById('reg-username');
        const email = document.getElementById('reg-email');
        const mobile = document.getElementById('reg-mobile');

        if (!fullname.value.trim()) { showToast('Please enter your full name', 'error'); fullname.focus(); return; }
        if (!username.value.trim() || username.value.length < 3) { showToast('Username must be at least 3 characters', 'error'); showFieldError('username', 'Username must be at least 3 characters'); username.focus(); return; }
        if (usernameStatus === 'taken') { showToast('Username is already taken', 'error'); showFieldError('username', 'Username is already taken'); username.focus(); return; }
        if (!email.value.trim() || !validateEmail(email.value)) { showToast('Please enter a valid email', 'error'); showFieldError('email', 'Please enter a valid email address'); email.focus(); return; }
        if (emailStatus === 'taken') { showToast('This email is already taken', 'error'); showFieldError('email', 'This email is already taken'); email.focus(); return; }
        if (!mobile.value.trim() || mobile.value.length < 10) { showToast('Please enter a valid mobile number', 'error'); mobile.focus(); return; }

        // Update verification summary
        updateVerificationSummary();
        goToStep(2);
    });

    if (btnStep3) btnStep3.addEventListener('click', () => {
        if (!emailVerified) { showToast('Please verify your email before continuing', 'error'); return; }
        goToStep(3);
    });

    if (btnBack1) btnBack1.addEventListener('click', () => goToStep(1));
    if (btnBack2) btnBack2.addEventListener('click', () => goToStep(2));

    /* ============================================================
       USERNAME AVAILABILITY CHECK
    ============================================================ */
    const regUsername = document.getElementById('reg-username');
    const usernameStatusEl = document.getElementById('username-status');
    let usernameStatus = '';
    let usernameTimer = null;

    if (regUsername) {
        regUsername.addEventListener('input', () => {
            clearFieldError('username');
            clearTimeout(usernameTimer);
            const val = regUsername.value.trim();
            if (val.length < 3) {
                usernameStatusEl.textContent = '';
                usernameStatusEl.className = 'field-status';
                usernameStatus = '';
                return;
            }
            usernameStatusEl.textContent = '...';
            usernameStatusEl.className = 'field-status checking';
            usernameTimer = setTimeout(() => {
                fetch(`/accounts/api/check-username/?username=${encodeURIComponent(val)}`)
                    .then(r => r.json())
                    .then(data => {
                        if (data.available) {
                            usernameStatusEl.innerHTML = '<i class="fa-solid fa-check"></i>';
                            usernameStatusEl.className = 'field-status available';
                            usernameStatus = 'available';
                            clearFieldError('username');
                        } else {
                            usernameStatusEl.innerHTML = '<i class="fa-solid fa-xmark"></i> Taken';
                            usernameStatusEl.className = 'field-status taken';
                            usernameStatus = 'taken';
                            showFieldError('username', 'Username is already taken');
                        }
                    })
                    .catch(() => {
                        usernameStatusEl.textContent = '';
                        usernameStatus = '';
                    });
            }, 500);
        });
    }

    /* ============================================================
       EMAIL VALIDATION
    ============================ */
    function validateEmail(email) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    }

    const regEmail = document.getElementById('reg-email');
    const btnVerifyEmail = document.getElementById('btn-verify-email');
    const emailStatusEl = document.getElementById('email-status');
    let emailStatus = ''; // '', 'available', 'taken'
    let emailTimer = null;

    if (regEmail) {
        regEmail.addEventListener('input', () => {
            clearFieldError('email');
            clearTimeout(emailTimer);
            const val = regEmail.value.trim();

            // Enable/disable verify button
            if (btnVerifyEmail) {
                btnVerifyEmail.disabled = !validateEmail(val);
            }

            if (!validateEmail(val)) {
                if (emailStatusEl) {
                    emailStatusEl.textContent = '';
                    emailStatusEl.className = 'field-status';
                }
                emailStatus = '';
                return;
            }

            if (emailStatusEl) {
                emailStatusEl.textContent = '...';
                emailStatusEl.className = 'field-status checking';
            }

            emailTimer = setTimeout(() => {
                fetch(`/accounts/api/check-email/?email=${encodeURIComponent(val)}`)
                    .then(r => r.json())
                    .then(data => {
                        if (data.available) {
                            if (emailStatusEl) {
                                emailStatusEl.innerHTML = '<i class="fa-solid fa-check"></i>';
                                emailStatusEl.className = 'field-status available';
                            }
                            emailStatus = 'available';
                            clearFieldError('email');
                        } else {
                            if (emailStatusEl) {
                                emailStatusEl.innerHTML = '<i class="fa-solid fa-xmark"></i> Taken';
                                emailStatusEl.className = 'field-status taken';
                            }
                            emailStatus = 'taken';
                            showFieldError('email', 'This email is already taken');
                        }
                    })
                    .catch(() => {
                        if (emailStatusEl) {
                            emailStatusEl.textContent = '';
                        }
                        emailStatus = '';
                    });
            }, 500);
        });
    }

    /* ============================================================
       MOBILE VALIDATION
    ============================ */
    const regMobile = document.getElementById('reg-mobile');
    const btnVerifyMobile = document.getElementById('btn-verify-mobile');

    if (regMobile && btnVerifyMobile) {
        regMobile.addEventListener('input', () => {
            regMobile.value = regMobile.value.replace(/\D/g, '').slice(0, 10);
            btnVerifyMobile.disabled = regMobile.value.length < 10;
        });
    }

       /* ============================
       OTP MODAL & DEMO SYSTEM
    ============================ */
    const otpOverlay = document.getElementById('otp-overlay');
    const otpModal = document.getElementById('otp-modal');
    const otpClose = document.getElementById('otp-close');
    const otpBoxes = document.querySelectorAll('.otp-box');
    const otpTitle = document.getElementById('otp-title');
    const otpSubtitle = document.getElementById('otp-subtitle');
    const otpIcon = otpModal ? otpModal.querySelector('.otp-icon i') : null;
    const otpTimerText = document.getElementById('otp-timer-text');
    const otpCountdown = document.getElementById('otp-countdown');
    const otpResendBtn = document.getElementById('otp-resend');
    const btnOtpVerify = document.getElementById('btn-otp-verify');
    const btnOtpVerifyText = document.getElementById('btn-otp-verify-text');
    const demoOtpDisplay = document.getElementById('demo-otp-display');
    const demoTargetLabel = document.getElementById('demo-target-label');
    const btnDemoAutofill = document.getElementById('btn-demo-autofill');
    const otpInputLabel = document.getElementById('otp-input-label');
    const otpFeedbackMsg = document.getElementById('otp-feedback-msg');
    const demoEmailInlineCard = document.getElementById('demo-email-inline-card');
    const demoMobileInlineCard = document.getElementById('demo-mobile-inline-card');

    let otpTimerInterval = null;
    let currentOtpType = ''; // 'email' or 'mobile'
    let emailVerified = false;
    let mobileVerified = false;
    const activeDemoOtp = { email: '', mobile: '' };

    function showFeedbackMsg(type, msg) {
        if (!otpFeedbackMsg) return;
        otpFeedbackMsg.className = `otp-feedback-msg ${type}`;
        otpFeedbackMsg.textContent = msg;
        otpFeedbackMsg.classList.remove('hidden');
    }

    function hideFeedbackMsg() {
        if (otpFeedbackMsg) {
            otpFeedbackMsg.classList.add('hidden');
            otpFeedbackMsg.textContent = '';
        }
    }

    function fillDemoOtp(code) {
        if (!code || code.length !== 6) return;
        code.split('').forEach((ch, idx) => {
            if (otpBoxes[idx]) {
                otpBoxes[idx].value = ch;
                otpBoxes[idx].classList.add('filled');
            }
        });
        checkOtpComplete();
        hideFeedbackMsg();
        if (otpBoxes.length > 0) otpBoxes[otpBoxes.length - 1].focus();
    }

    if (btnDemoAutofill) {
        btnDemoAutofill.addEventListener('click', () => {
            fillDemoOtp(activeDemoOtp[currentOtpType]);
        });
    }

    if (demoOtpDisplay) {
        demoOtpDisplay.addEventListener('click', () => {
            fillDemoOtp(activeDemoOtp[currentOtpType]);
        });
    }

    function openOtpModal(type) {
        currentOtpType = type;
        hideFeedbackMsg();
        otpBoxes.forEach(b => { b.value = ''; b.classList.remove('filled'); b.classList.remove('shake-error'); });
        btnOtpVerify.disabled = true;

        if (type === 'email') {
            if (otpTitle) otpTitle.textContent = 'Email Verification';
            if (otpSubtitle) otpSubtitle.textContent = `Enter the 6-digit code for ${regEmail.value.trim()}`;
            if (otpIcon) otpIcon.className = 'fa-solid fa-envelope-circle-check';
            if (demoTargetLabel) demoTargetLabel.textContent = 'Your Email OTP:';
            const emailLabelText = document.getElementById('otp-input-label-text');
            if (emailLabelText) emailLabelText.textContent = 'Enter Email OTP:';
            else if (otpInputLabel) otpInputLabel.textContent = 'Enter Email OTP:';
            if (btnOtpVerifyText) btnOtpVerifyText.textContent = 'Verify Email';
            if (demoOtpDisplay) demoOtpDisplay.textContent = activeDemoOtp.email || '------';
        } else {
            const countryCode = document.getElementById('country-code') ? document.getElementById('country-code').value : '+91';
            if (otpTitle) otpTitle.textContent = 'Mobile Verification';
            if (otpSubtitle) otpSubtitle.textContent = `Enter the 6-digit code for ${countryCode}${regMobile.value.trim()}`;
            if (otpIcon) otpIcon.className = 'fa-solid fa-mobile-screen-button';
            if (demoTargetLabel) demoTargetLabel.textContent = 'Your Mobile OTP:';
            const mobileLabelText = document.getElementById('otp-input-label-text');
            if (mobileLabelText) mobileLabelText.textContent = 'Enter Mobile OTP:';
            else if (otpInputLabel) otpInputLabel.textContent = 'Enter Mobile OTP:';
            if (btnOtpVerifyText) btnOtpVerifyText.textContent = 'Verify Mobile';
            if (demoOtpDisplay) demoOtpDisplay.textContent = activeDemoOtp.mobile || '------';
        }

        otpOverlay.classList.remove('hidden');
        if (otpBoxes.length > 0) otpBoxes[0].focus();
        startOtpTimer();
    }

    function closeOtpModal() {
        otpOverlay.classList.add('hidden');
        hideFeedbackMsg();
        clearInterval(otpTimerInterval);
    }

    if (otpClose) otpClose.addEventListener('click', closeOtpModal);
    if (otpOverlay) otpOverlay.addEventListener('click', (e) => { if (e.target === otpOverlay) closeOtpModal(); });

    // OTP Box navigation
    otpBoxes.forEach((box, index) => {
        box.addEventListener('input', (e) => {
            hideFeedbackMsg();
            const val = e.target.value.replace(/\D/g, '');
            e.target.value = val.slice(0, 1);
            e.target.classList.toggle('filled', val.length > 0);
            if (val && index < otpBoxes.length - 1) otpBoxes[index + 1].focus();
            checkOtpComplete();
        });

        box.addEventListener('keydown', (e) => {
            if (e.key === 'Backspace' && !box.value && index > 0) otpBoxes[index - 1].focus();
            if (e.key === 'ArrowLeft' && index > 0) otpBoxes[index - 1].focus();
            if (e.key === 'ArrowRight' && index < otpBoxes.length - 1) otpBoxes[index + 1].focus();
        });

        box.addEventListener('paste', (e) => {
            e.preventDefault();
            hideFeedbackMsg();
            const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
            pasted.split('').forEach((ch, i) => {
                if (i < otpBoxes.length) {
                    otpBoxes[i].value = ch;
                    otpBoxes[i].classList.add('filled');
                }
            });
            checkOtpComplete();
            otpBoxes[Math.min(pasted.length, otpBoxes.length - 1)].focus();
        });
    });

    function getOtpValue() {
        return Array.from(otpBoxes).map(b => b.value).join('');
    }

    function checkOtpComplete() {
        btnOtpVerify.disabled = getOtpValue().length !== 6;
    }

    // OTP Timer (60s countdown for resend button)
    function startOtpTimer() {
        let seconds = 60;
        otpResendBtn.classList.add('hidden');
        otpTimerText.classList.remove('hidden');
        otpCountdown.textContent = seconds;

        clearInterval(otpTimerInterval);
        otpTimerInterval = setInterval(() => {
            seconds--;
            otpCountdown.textContent = seconds;
            if (seconds <= 0) {
                clearInterval(otpTimerInterval);
                otpTimerText.classList.add('hidden');
                otpResendBtn.classList.remove('hidden');
            }
        }, 1000);
    }

    /* ============================
       SEND EMAIL OTP (DEMO FLOW)
    ============================ */
    if (btnVerifyEmail) {
        btnVerifyEmail.addEventListener('click', () => {
            if (emailVerified) return;
            const emailVal = regEmail.value.trim();
            if (!emailVal) {
                showToast('Please enter an email address first', 'error');
                regEmail.focus();
                return;
            }

            btnVerifyEmail.disabled = true;
            btnVerifyEmail.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Generating...';

            fetch('/accounts/api/send-email-otp/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
                body: JSON.stringify({ email: emailVal })
            })
                .then(r => r.json())
                .then(data => {
                    btnVerifyEmail.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Verify Email';
                    btnVerifyEmail.disabled = false;

                    if (data.success && data.otp) {
                        activeDemoOtp.email = String(data.otp);
                        showToast(`Email OTP generated: ${data.otp}`, 'info');
                        openOtpModal('email');
                    } else {
                        showToast(data.error || 'Failed to generate OTP', 'error');
                    }
                })
                .catch(() => {
                    showToast('Network error. Please try again.', 'error');
                    btnVerifyEmail.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Verify Email';
                    btnVerifyEmail.disabled = false;
                });
        });
    }

    /* ============================
       SEND MOBILE OTP (DEMO FLOW)
    ============================ */
    if (btnVerifyMobile) {
        btnVerifyMobile.addEventListener('click', () => {
            if (mobileVerified) return;
            const mobileVal = regMobile.value.trim();
            if (!mobileVal || mobileVal.length < 7) {
                showToast('Please enter a valid mobile number first', 'error');
                regMobile.focus();
                return;
            }

            btnVerifyMobile.disabled = true;
            btnVerifyMobile.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Generating...';

            const countryCode = document.getElementById('country-code') ? document.getElementById('country-code').value : '+91';
            fetch('/accounts/api/send-mobile-otp/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
                body: JSON.stringify({ mobile: mobileVal, country_code: countryCode })
            })
                .then(r => r.json())
                .then(data => {
                    btnVerifyMobile.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Verify Mobile';
                    btnVerifyMobile.disabled = false;

                    if (data.success && data.otp) {
                        activeDemoOtp.mobile = String(data.otp);
                        showToast(`Mobile OTP generated: ${data.otp}`, 'info');
                        openOtpModal('mobile');
                    } else {
                        showToast(data.error || 'Failed to generate OTP', 'error');
                    }
                })
                .catch(() => {
                    showToast('Network error. Please try again.', 'error');
                    btnVerifyMobile.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Verify Mobile';
                    btnVerifyMobile.disabled = false;
                });
        });
    }

    /* ============================
       VERIFY OTP (INDEPENDENT)
    ============================ */
    if (btnOtpVerify) {
        btnOtpVerify.addEventListener('click', () => {
            const otpVal = getOtpValue();
            if (otpVal.length !== 6) return;

            btnOtpVerify.classList.add('loading');
            hideFeedbackMsg();

            const endpoint = currentOtpType === 'email'
                ? '/accounts/api/verify-email-otp/'
                : '/accounts/api/verify-mobile-otp/';

            fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
                body: JSON.stringify({ otp: otpVal })
            })
                .then(r => r.json())
                .then(data => {
                    btnOtpVerify.classList.remove('loading');
                    if (data.success) {
                        const successText = currentOtpType === 'email' ? 'Email Verified ✓' : 'Mobile Verified ✓';
                        showFeedbackMsg('success', successText);
                        showToast(successText, 'success');

                        if (currentOtpType === 'email') {
                            emailVerified = true;
                            document.getElementById('email-verified-badge').classList.remove('hidden');
                            btnVerifyEmail.classList.add('hidden');
                            regEmail.readOnly = true;
                        } else {
                            mobileVerified = true;
                            document.getElementById('mobile-verified-badge').classList.remove('hidden');
                            btnVerifyMobile.classList.add('hidden');
                            regMobile.readOnly = true;
                        }

                        setTimeout(() => {
                            closeOtpModal();
                            updateVerificationSummary();
                        }, 700);
                    } else {
                        // Error cases: Invalid OTP or Expired OTP
                        const errorMsg = data.error || 'Invalid OTP. Please enter the correct OTP.';
                        showFeedbackMsg('error', errorMsg);
                        showToast(errorMsg, 'error');

                        // Shake animation and reset boxes
                        otpBoxes.forEach(b => {
                            b.classList.add('shake-error');
                            setTimeout(() => b.classList.remove('shake-error'), 500);
                            b.value = '';
                            b.classList.remove('filled');
                        });
                        btnOtpVerify.disabled = true;
                        if (otpBoxes.length > 0) otpBoxes[0].focus();
                    }
                })
                .catch(() => {
                    btnOtpVerify.classList.remove('loading');
                    const err = 'Verification failed. Please try again.';
                    showFeedbackMsg('error', err);
                    showToast(err, 'error');
                });
        });
    }

    /* ============================
       RESEND OTP
    ============================ */
    if (otpResendBtn) {
        otpResendBtn.addEventListener('click', () => {
            hideFeedbackMsg();
            otpBoxes.forEach(b => { b.value = ''; b.classList.remove('filled'); });
            btnOtpVerify.disabled = true;

            if (currentOtpType === 'email' && btnVerifyEmail) {
                btnVerifyEmail.click();
            } else if (currentOtpType === 'mobile' && btnVerifyMobile) {
                btnVerifyMobile.click();
            }
            startOtpTimer();
        });
    }

    /* ============================
       VERIFICATION SUMMARY UPDATE
    ============================ */
    function updateVerificationSummary() {
        const emailDisplay = document.getElementById('verify-email-display');
        const mobileDisplay = document.getElementById('verify-mobile-display');

        if (emailDisplay) {
            emailDisplay.textContent = emailVerified ? '✓ Verified' : 'Not verified';
            emailDisplay.className = `verify-value ${emailVerified ? 'verified' : 'not-verified'}`;
        }
        if (mobileDisplay) {
            mobileDisplay.textContent = mobileVerified ? '✓ Verified' : 'Not verified (optional)';
            mobileDisplay.className = `verify-value ${mobileVerified ? 'verified' : ''}`;
        }
    }

    /* ============================================================
       PASSWORD STRENGTH METER
    ============================================================ */
    const regPassword = document.getElementById('reg-password');
    const strengthLabel = document.getElementById('strength-label');
    const strengthBars = document.querySelectorAll('.str-bar');
    const crLength = document.getElementById('cr-length');
    const crUpper = document.getElementById('cr-upper');
    const crLower = document.getElementById('cr-lower');
    const crNumber = document.getElementById('cr-number');
    const crSpecial = document.getElementById('cr-special');

    if (regPassword) {
        regPassword.addEventListener('input', () => {
            const pw = regPassword.value;
            let score = 0;

            const checks = [
                { el: crLength, met: pw.length >= 8 },
                { el: crUpper, met: /[A-Z]/.test(pw) },
                { el: crLower, met: /[a-z]/.test(pw) },
                { el: crNumber, met: /[0-9]/.test(pw) },
                { el: crSpecial, met: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(pw) }
            ];

            checks.forEach(c => {
                if (c.el) c.el.classList.toggle('met', c.met);
                if (c.met) score++;
            });

            const levelClasses = ['', 'weak', 'fair', 'medium', 'good', 'strong'];
            const labelTexts = ['Enter password', 'Weak', 'Fair', 'Medium', 'Good', 'Strong'];
            const labelColors = ['', '#f43f5e', '#f97316', '#facc15', '#22d3ee', '#4ade80'];

            strengthBars.forEach((bar, i) => {
                bar.className = 'str-bar';
                if (i < score) bar.classList.add(levelClasses[score]);
            });

            if (strengthLabel) {
                strengthLabel.textContent = labelTexts[score];
                strengthLabel.style.color = labelColors[score];
            }

            updateRegisterButton();
        });
    }

    /* ============================================================
       CONFIRM PASSWORD MATCH
    ============================================================ */
    const confirmPw = document.getElementById('reg-confirm-password');
    const pwMatchStatus = document.getElementById('pw-match-status');

    if (confirmPw) {
        confirmPw.addEventListener('input', () => {
            if (!regPassword) return;
            if (confirmPw.value === '') {
                pwMatchStatus.textContent = '';
                pwMatchStatus.className = 'field-status';
            } else if (confirmPw.value === regPassword.value) {
                pwMatchStatus.innerHTML = '<i class="fa-solid fa-check"></i> Match';
                pwMatchStatus.className = 'field-status available';
            } else {
                pwMatchStatus.innerHTML = '<i class="fa-solid fa-xmark"></i> No match';
                pwMatchStatus.className = 'field-status taken';
            }
            updateRegisterButton();
        });
    }

    /* ============================================================
       REGISTER BUTTON STATE
    ============================================================ */
    const btnRegister = document.getElementById('btn-register');
    const termsCheck = document.getElementById('terms-check');

    function updateRegisterButton() {
        if (!btnRegister || !regPassword || !confirmPw || !termsCheck) return;
        const pw = regPassword.value;
        const pwValid = pw.length >= 8 && /[A-Z]/.test(pw) && /[a-z]/.test(pw) && /[0-9]/.test(pw) && /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(pw);
        const match = pw === confirmPw.value && pw.length > 0;
        const terms = termsCheck.checked;

        btnRegister.disabled = !(pwValid && match && terms);
    }

    if (termsCheck) termsCheck.addEventListener('change', updateRegisterButton);

    /* ============================================================
       REGISTER FORM SUBMISSION
    ============================================================ */
    const registerForm = document.getElementById('register-form');

    if (registerForm) {
        registerForm.addEventListener('submit', (e) => {
            e.preventDefault();

            if (!emailVerified) {
                showToast('Please verify your email first', 'error');
                goToStep(1);
                return;
            }

            const fullname = document.getElementById('reg-fullname').value.trim();
            const username = document.getElementById('reg-username').value.trim();
            const email = regEmail.value.trim();
            const countryCode = document.getElementById('country-code').value;
            const mobile = regMobile.value.trim();
            const password = regPassword.value;

            btnRegister.classList.add('loading');

            fetch('/accounts/register/submit/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
                body: JSON.stringify({
                    full_name: fullname,
                    username: username,
                    email: email,
                    country_code: countryCode,
                    mobile: mobile,
                    password: password,
                    email_verified: emailVerified,
                    mobile_verified: mobileVerified
                })
            })
                .then(r => r.json())
                .then(data => {
                    btnRegister.classList.remove('loading');
                    if (data.success) {
                        clearAllFieldErrors();
                        showToast('Account created successfully! Redirecting to login...', 'success');
                        setTimeout(() => {
                            switchTab('login');
                        }, 2000);
                    } else {
                        // Show inline field error if field is specified
                        const errorField = data.field || 'general';
                        const errorMsg = data.error || 'Registration failed. Please try again.';

                        showToast(errorMsg, 'error');

                        if (errorField === 'email') {
                            showFieldError('email', errorMsg);
                            goToStep(1);
                            const emailInput = document.getElementById('reg-email');
                            if (emailInput) emailInput.focus();
                        } else if (errorField === 'username') {
                            showFieldError('username', errorMsg);
                            goToStep(1);
                            const usernameInput = document.getElementById('reg-username');
                            if (usernameInput) usernameInput.focus();
                        } else if (errorField === 'password') {
                            showFieldError('password', errorMsg);
                        }
                    }
                })
                .catch(() => {
                    btnRegister.classList.remove('loading');
                    showToast('Network error. Please try again.', 'error');
                });
        });
    }

    /* ============================================================
       AUTOFILL DETECTION
       Browsers may autofill fields without triggering :focus or
       updating :placeholder-shown. This adds a class so CSS can
       float the label up.
    ============================================================ */
    function checkAutofill() {
        document.querySelectorAll('.input-field').forEach(function (field) {
            // Check if the field has a value (autofilled or typed)
            if (field.value && field.value.trim() !== '') {
                field.classList.add('has-value');
            } else {
                field.classList.remove('has-value');
            }
        });
    }

    // Run immediately and periodically for a few seconds (autofill can be delayed)
    checkAutofill();
    const autofillInterval = setInterval(checkAutofill, 250);
    setTimeout(function () { clearInterval(autofillInterval); }, 3000);

    // Also check on any input event
    document.querySelectorAll('.input-field').forEach(function (field) {
        field.addEventListener('input', checkAutofill);
        field.addEventListener('change', checkAutofill);
    });

})();
