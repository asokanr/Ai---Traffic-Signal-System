from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# =====================================================
# REST API ROUTER
# =====================================================
router = DefaultRouter()
router.register(r'signals', views.TrafficSignalViewSet, basename='signal')
router.register(r'analytics', views.AnalyticsViewSet, basename='analytics')
router.register(r'junctions', views.JunctionViewSet, basename='junction')
router.register(r'emergency', views.EmergencyViewSet, basename='emergency')
router.register(r'heatmap', views.HeatmapViewSet, basename='heatmap')
router.register(r'alerts', views.AlertsViewSet, basename='alerts')
router.register(r'pollution', views.PollutionViewSet, basename='pollution')
router.register(r'admin-logs', views.AdminActionLogViewSet, basename='admin-logs')

# =====================================================
# URL PATTERNS
# =====================================================
urlpatterns = [
    # Include REST API router URLs
    path('', include(router.urls)),

    # Dashboard view (login required)
    path('dashboard/', views.dashboard, name='dashboard'),

    # Optional: JSON endpoint for AJAX dashboard updates
    path('dashboard/data/', views.dashboard_data, name='dashboard_data'),

    # Analytics Dashboard
    path('dashboard/analytics/', views.analytics_dashboard, name='analytics_dashboard'),

    # AI Analysis
    path('ai-analysis/', views.ai_analysis_page, name='ai_analysis'),
    path('ai-analysis/media-videos/', views.list_media_videos, name='list_media_videos'),
    path('ai-analysis/analyze-media-video/', views.analyze_media_video, name='analyze_media_video'),
    path('ai-analysis/upload/', views.upload_video_analysis, name='upload_video_analysis'),
    path('ai-analysis/camera-check/', views.camera_check, name='camera_check'),
    path('ai-analysis/analyze-frame/', views.analyze_frame, name='analyze_frame'),
    path('ai-analysis/apply-to-signals/', views.apply_analysis_to_signals, name='apply_analysis_to_signals'),
    path('ai-analysis/roi-config/', views.roi_config_api, name='roi_config_api'),
    path('ai-analysis/live-feed/', views.live_camera_feed, name='live_camera_feed'),
    path('ai-analysis/live-snapshot/', views.live_analysis_snapshot, name='live_analysis_snapshot'),
    path('ai-analysis/history/', views.analysis_history, name='analysis_history'),
    path('signal-state/', views.signal_state_api, name='signal_state_api'),
]
