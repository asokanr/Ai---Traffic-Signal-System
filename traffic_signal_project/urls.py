from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views

from signal_app import views as signal_views  # import views from your app
from accounts import views as account_views

urlpatterns = [
    # ======================
    # ADMIN
    # ======================
    path('admin/', admin.site.urls),

    # ======================
    # AUTH / ACCOUNTS
    # ======================
    path(
        'accounts/login/',
        auth_views.LoginView.as_view(template_name='accounts/auth.html'),
        name='login'
    ),
    path('login/', RedirectView.as_view(url='/accounts/login/', permanent=False)),
    path('accounts/logout/', account_views.user_logout, name='logout'),
    path('logout/', RedirectView.as_view(url='/accounts/logout/', permanent=False)),
    path('accounts/', include('accounts.urls')),

    # ======================
    # FORGOT PASSWORD FLOW
    # ======================
    path(
        'password_reset/',
        auth_views.PasswordResetView.as_view(template_name='accounts/password_reset.html'),
        name='password_reset'
    ),
    path(
        'password_reset/done/',
        auth_views.PasswordResetDoneView.as_view(template_name='accounts/password_reset_done.html'),
        name='password_reset_done'
    ),
    path(
        'reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(template_name='accounts/password_reset_confirm.html'),
        name='password_reset_confirm'
    ),
    path(
        'reset/done/',
        auth_views.PasswordResetCompleteView.as_view(template_name='accounts/password_reset_complete.html'),
        name='password_reset_complete'
    ),

    # ======================
    # GOOGLE LOGIN (ALLAUTH)
    # ======================
    path('social/', include('allauth.urls')),

    # ======================
    # API ROUTES
    # ======================
    path('api/', include('signal_app.urls')),

    # ======================
    # DASHBOARD & SIGNAL STATE
    # ======================
    path('dashboard/', signal_views.dashboard, name='dashboard_page'),      # renders dashboard.html
    path('dashboard/data/', signal_views.dashboard_data, name='dashboard_data'),  # JSON endpoint
    path('signal-state/', signal_views.signal_state_api, name='root_signal_state_api'),

    # ======================
    # ROOT → LOGIN
    # ======================
    path('', RedirectView.as_view(url='/accounts/login/', permanent=False)),
]

# ======================
# MEDIA FILES (DEV)
# ======================
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
