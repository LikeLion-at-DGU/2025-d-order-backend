from django.urls import path, include
from rest_framework.routers import DefaultRouter,SimpleRouter

from .views import *

urlpatterns = [
    path('manager/login/', ManagerLoginView.as_view()),
    path('manager/logout/', ManagerLogoutView.as_view()),
    path('manager/check/', UsernameCheckView.as_view()),
    path('manager/signup/', ManagerSignupView.as_view()),
    path('manager/mypage/',ManagerMyPageView.as_view()),

]
