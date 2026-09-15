import json
import time

from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout


def user_logout(request):
    """Log out user (supports both GET and POST) and redirect to login."""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from .models import OTP
from .utils import generate_otp


def register_page(request):
    """Render the unified auth page in register mode."""
    return render(request, 'accounts/auth.html', {'tab': 'register'})


def register(request):
    """Handle registration via AJAX POST."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

        full_name = data.get('full_name', '').strip()
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        country_code = data.get('country_code', '+91')
        mobile = data.get('mobile', '').strip()
        email_verified = data.get('email_verified', False)

        # Validations
        if not all([full_name, username, email, password]):
            return JsonResponse({'success': False, 'error': 'All fields are required', 'field': 'general'})

        # Server-side verification guard: NEVER trust client-supplied boolean flags
        session_email_verified = request.session.get('email_verified', False)
        session_email_target = request.session.get('email_verified_target', '')
        if not session_email_verified or session_email_target.lower() != email.lower():
            return JsonResponse({'success': False, 'error': 'Email must be verified before registration', 'field': 'email'})

        if User.objects.filter(username=username).exists():
            return JsonResponse({'success': False, 'error': 'Username is already taken', 'field': 'username'})

        if User.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'error': 'This email is already taken', 'field': 'email'})

        # Password validation
        if len(password) < 8:
            return JsonResponse({'success': False, 'error': 'Password must be at least 8 characters', 'field': 'password'})

        # Create user
        name_parts = full_name.split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )
        user.is_active = True
        user.save()

        # Save phone to UserProfile if exists
        try:
            from signal_app.models import UserProfile
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.phone = f"{country_code}{mobile}"
            profile.save()
        except Exception:
            pass

        # Invalidate session verification flags after account creation to prevent reuse
        request.session.pop('email_verified', None)
        request.session.pop('email_verified_target', None)
        request.session.pop('mobile_verified', None)
        request.session.pop('mobile_verified_target', None)
        request.session.modified = True

        return JsonResponse({'success': True, 'message': 'Account created successfully'})

    return render(request, 'accounts/register.html')


def verify_otp(request):
    """Legacy OTP verification page (kept for backward compatibility)."""
    if request.method == 'POST':
        otp_input = request.POST.get('otp', '')
        username = request.session.get('username')

        try:
            user = User.objects.get(username=username)
            otp_obj = OTP.objects.get(user=user)

            if otp_obj.otp == otp_input:
                otp_obj.is_verified = True
                otp_obj.save()
                user.is_active = True
                user.save()
                messages.success(request, 'Account verified successfully')
                return redirect('login')
            else:
                messages.error(request, 'Invalid OTP')
        except (User.DoesNotExist, OTP.DoesNotExist):
            messages.error(request, 'Verification failed')

    return render(request, 'accounts/otp_verify.html')


def user_login(request):
    """Standard login view (form-based POST from auth.html)."""
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')

        user = authenticate(username=username, password=password)
        if user:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid credentials')

    return render(request, 'accounts/login.html')


# ============================================================
# API ENDPOINTS (AJAX)
# ============================================================

@require_GET
def check_username(request):
    """Check if a username is available."""
    username = request.GET.get('username', '').strip()
    if not username or len(username) < 3:
        return JsonResponse({'available': False, 'error': 'Username too short'})

    available = not User.objects.filter(username=username).exists()
    return JsonResponse({'available': available})


@require_GET
def check_email(request):
    """Check if an email is available."""
    email = request.GET.get('email', '').strip()
    if not email:
        return JsonResponse({'available': False, 'error': 'Email is required'})

    available = not User.objects.filter(email=email).exists()
    return JsonResponse({'available': available})


OTP_EXPIRY_SECONDS = 600  # 10 minutes


@require_POST
def send_email_otp(request):
    """Generate server-side Email OTP for demo flow and store in session."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

    email = data.get('email', '').strip()
    if not email:
        return JsonResponse({'success': False, 'error': 'Email is required'}, status=400)

    otp = generate_otp()

    # Invalidate previous OTP and store fresh OTP + timestamp in session
    request.session['email_otp'] = otp
    request.session['email_otp_target'] = email
    request.session['email_otp_time'] = time.time()
    request.session['email_verified'] = False
    request.session.modified = True

    return JsonResponse({
        'success': True,
        'message': 'OTP generated successfully',
        'otp': otp,
        'otp_type': 'email',
        'expires_in': OTP_EXPIRY_SECONDS,
    })


@require_POST
def verify_email_otp(request):
    """Verify the Email OTP from session."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

    otp_input = data.get('otp', '').strip()
    stored_otp = request.session.get('email_otp', '')
    created_time = request.session.get('email_otp_time', 0)

    if not stored_otp or not created_time:
        return JsonResponse({
            'success': False,
            'error': 'No OTP found. Please request a new one.',
            'status': 'missing'
        })

    # Expiry validation (10 minutes)
    if (time.time() - created_time) > OTP_EXPIRY_SECONDS:
        request.session.pop('email_otp', None)
        request.session.pop('email_otp_time', None)
        request.session.modified = True
        return JsonResponse({
            'success': False,
            'error': 'OTP expired. Please generate a new OTP.',
            'status': 'expired'
        })

    # Value comparison
    if otp_input != stored_otp:
        return JsonResponse({
            'success': False,
            'error': 'Invalid OTP. Please enter the correct OTP.',
            'status': 'invalid'
        })

    # Correct OTP verified
    request.session['email_verified'] = True
    request.session['email_verified_target'] = request.session.get('email_otp_target', '')
    # Invalidate OTP after successful verification to prevent reuse
    request.session.pop('email_otp', None)
    request.session.pop('email_otp_time', None)
    request.session.modified = True

    return JsonResponse({'success': True, 'message': 'Email verified successfully'})


@require_POST
def send_mobile_otp(request):
    """Generate server-side Mobile OTP for demo flow and store in session."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

    mobile = data.get('mobile', '').strip()
    country_code = data.get('country_code', '+91').strip()

    if not mobile or len(mobile) < 7:
        return JsonResponse({'success': False, 'error': 'Valid mobile number is required'}, status=400)

    full_target = f"{country_code}{mobile}"
    otp = generate_otp()

    # Invalidate previous OTP and store fresh OTP + timestamp in session
    request.session['mobile_otp'] = otp
    request.session['mobile_otp_target'] = full_target
    request.session['mobile_otp_time'] = time.time()
    request.session['mobile_verified'] = False
    request.session.modified = True

    return JsonResponse({
        'success': True,
        'message': 'OTP generated successfully',
        'otp': otp,
        'otp_type': 'mobile',
        'expires_in': OTP_EXPIRY_SECONDS,
    })


@require_POST
def verify_mobile_otp(request):
    """Verify the Mobile OTP from session."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

    otp_input = data.get('otp', '').strip()
    stored_otp = request.session.get('mobile_otp', '')
    created_time = request.session.get('mobile_otp_time', 0)

    if not stored_otp or not created_time:
        return JsonResponse({
            'success': False,
            'error': 'No OTP found. Please request a new one.',
            'status': 'missing'
        })

    # Expiry validation (10 minutes)
    if (time.time() - created_time) > OTP_EXPIRY_SECONDS:
        request.session.pop('mobile_otp', None)
        request.session.pop('mobile_otp_time', None)
        request.session.modified = True
        return JsonResponse({
            'success': False,
            'error': 'OTP expired. Please generate a new OTP.',
            'status': 'expired'
        })

    # Value comparison
    if otp_input != stored_otp:
        return JsonResponse({
            'success': False,
            'error': 'Invalid OTP. Please enter the correct OTP.',
            'status': 'invalid'
        })

    # Correct OTP verified
    request.session['mobile_verified'] = True
    request.session['mobile_verified_target'] = request.session.get('mobile_otp_target', '')
    # Invalidate OTP after successful verification to prevent reuse
    request.session.pop('mobile_otp', None)
    request.session.pop('mobile_otp_time', None)
    request.session.modified = True

    return JsonResponse({'success': True, 'message': 'Mobile verified successfully'})
