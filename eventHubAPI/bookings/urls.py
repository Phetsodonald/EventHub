
from django.urls import path
from .views import booking_list_create, booking_detail

urlpatterns = [
    path("", booking_list_create, name="booking-list-create"),
    path("<int:pk>/", booking_detail, name="booking-detail"),
]
