from django.urls import path, include
from .views import *

urlpatterns = [
    path('carts/', AddToCartView.as_view()),
    path('tables/<int:table_id>/carts/', TableCartView.as_view()),
    path('tables/<int:table_id>/orders/', TableOrderView.as_view()),
    path('booths/<int:booth_id>/orders/', BoothOrderView.as_view()),
    path('carts/<int:cart_id>/', OrderFixView.as_view()),
]

