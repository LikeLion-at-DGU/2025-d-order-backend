from django.urls import path, include
from .views import *

urlpatterns = [
    path('carts/', AddToCartView.as_view()),
]