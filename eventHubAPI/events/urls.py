from django.urls import path
from .views import event_detail, event_list_create

urlpatterns = [
    path("", event_list_create, name="event-list-create"),
    path("<int:pk>/", event_detail, name="event-detail"),
]
