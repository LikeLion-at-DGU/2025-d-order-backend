from django.urls import path, include
from .views import *

urlpatterns = [
    path('carts/', AddToCartView.as_view()),
    path('tables/<int:table_id>/cart/', TableCartView.as_view(), name='table-cart'),
]