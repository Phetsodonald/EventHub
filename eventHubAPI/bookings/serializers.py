from django.db import transaction
from rest_framework import serializers
from django.utils import timezone
from .models import Booking

class BooklingSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source="user.username")
    event_title = serializers.ReadOnlyField(source="event.title")

    class Meta:
        model = Booking
        fields = ["id", "user", "event", "event_title", "quantity", "status", "booked_at", "updated_at"]
        read_only_fields = ["id", "user", "status", "booked_at", "updated_at"]

        def validate_quantity(self, value):
            if value < 1:
                raise serializers.ValidationError("You must book at least one ticket.")
            return value

        def validate(self, attrs):
            event = attrs.get("event", getattr(self.instance, "event", None))
            quantity = attrs.get("quantity", getattr(self.instance, "quantity", None))

            if event and event.status != event.Status.PUBLISHED:
                raise serializers.ValidationError({
                    "event": "This event is not available for booking."
                })

            if event and event.starts_at <= __import__("django.utils.timezone", fromlist=["now"]).now():
                raise serializers.ValidationError({
                    "event": "This event has already started."
                })

            if quantity is not None and event:
                if quantity > event.total_tickets:
                    raise serializers.ValidationError({
                        "quantity": "The requested quantity exceeds the event capacity"
                    })

            return  attrs