from rest_framework import serializers
from django.utils import timezone
from .models import Event

class EventSerializer(serializers.ModelSerializer):
    created_by =serializers.ReadOnlyField(source="created_by.username")

    class Meta:
        model = Event
        fields = ["id", "title", "description", "vanue", "starts_at", "ends_at", "ticket_price", "total_tickets", "status", "created_by", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        starts_at = attrs.get("starts_at", getattr(self.instance, "starts_at", None))
        ends_at = attrs.get("ends_at", getattr(self.instance, "ends_at", None))
        ticket_price = attrs.get("ticket_price", getattr(self.instance, None))
        total_tickets = attrs.get("total_tickets", getattr(self.instance, "total_tickets", None))

        if starts_at and ends_at and ends_at <= starts_at:
            raise serializers.ValidationError({
                "end_at": "The end time must be after the start time."
            })

        if starts_at and starts_at <= timezone.now():
            raise serializers.ValidationError({
                "starts_at": "The events events must start in the future."
            })

        if ticket_price is not None and ticket_price < 0:
            raise serializers.ValidationError({
                "ticket_price": "Ticket price cannot be negative"
            }) 

        if total_tickets is not None and total_tickets < 1:
            raise serializers.ValidationError({
                "total_tickets": "At least one ticket is required."
            })

        return attrs