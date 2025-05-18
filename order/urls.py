from django.urls import path, include
from .views import *
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('carts/', AddToCartView.as_view()),
    path('tables/<int:table_id>/carts/', TableCartView.as_view()),
    path('tables/<int:table_id>/orders/', TableOrderView.as_view()),
    path('booths/<int:booth_id>/orders/', BoothOrderView.as_view()),
    path('carts/<int:cart_id>/', OrderFixView.as_view()),
    path('manager/menu/add/', MenuCreateView.as_view()),
    path('manager/menu/<int:menu_id>/', MenuPatchDeleteView.as_view()),
    path('manager/menu/', MenuListView.as_view()),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

