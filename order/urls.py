from django.urls import path, include
from .views import *

urlpatterns = [
    path('carts/', AddToCartView.as_view()),
    path('tables/<int:table_id>/carts/', TableCartView.as_view()),
    path('tables/<int:table_id>/orders/', TableOrderView.as_view()),
]

