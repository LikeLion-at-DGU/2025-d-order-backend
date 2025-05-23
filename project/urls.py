"""
URL configuration for project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
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
from django.urls import path,include
from django.conf import settings
from manager.views import CookieTokenRefreshView
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenObtainPairView,  # access + refresh 발급
    TokenRefreshView,     # refresh로 access 재발급
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('booth.urls')),
    path('api/', include('manager.urls')),
    path('api/', include('order.urls')),


    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'), # 토근 발급용 임시 api
    path('api/token/refresh/', CookieTokenRefreshView.as_view(), name='token_refresh_cookie')

]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
