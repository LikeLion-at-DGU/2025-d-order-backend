from django.urls import path
from .views import *
from rest_framework.routers import DefaultRouter,SimpleRouter


# router = DefaultRouter()
# router.register(r'manager', UserViewSet, basename='manager')



urlpatterns = [
    path('manager/tables/', TableListView.as_view()),
    path("manager/tables/<int:table_num>/", TableDetailView.as_view()),
    path("manager/tables/<int:table_num>/orders/<int:order_id>/", CancelOrUpdateOrderView.as_view()),
    path("manager/tables/<int:table_num>/reset/", ResetTableView.as_view()),
]