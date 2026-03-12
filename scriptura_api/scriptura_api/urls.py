from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from core.frontend_views import FrontendView, auth_status_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/google/', FrontendView.as_view(), name='google-signin-page'),
    path('auth/status/', auth_status_view, name='auth-status'),
    path('api/', include('core.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('', FrontendView.as_view(), name='frontend'),
]