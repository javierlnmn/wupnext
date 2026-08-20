"""
URL configuration for wupnext project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path
from django.views.generic.base import RedirectView

urlpatterns = [
    path(
        'favicon.ico',
        RedirectView.as_view(url='/static/favicon/favicon.ico', permanent=True),
    ),
    # JET urls
    path('jet/', include('jet.urls', 'jet')),
    path('jet/dashboard/', include('jet.dashboard.urls', 'jet-dashboard')),
    # Django Browser Reload
    path('__reload__/', include('django_browser_reload.urls')),
    path('admin/', admin.site.urls),
    # Project
    path('', include('tasks.urls')),
    path('accounts/', include('accounts.urls')),
    path('pomodoro/', include('pomodoro.urls')),
    path('notifications/', include('notifications.urls')),
    # MCP server
    path('', include('mcp_server.urls')),
    # OAuth2 for MCP clients
    path('', include('oauth2_provider.urls')),
]
