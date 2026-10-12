from django.db import models
from django.conf import  settings
from django.core.validators import MinValueValidator

class Booking(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = "CONFIRMED", "Confirmed"
        CANCELLED = "CANCELLED", "Cancelled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="bookings"
    )
    event = models.ForeignKey(
        "events.Event", 
        on_delete=models.PROTECT,
        related_name="bookings"
    )
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CONFIRMED, db_index=True)
    booked_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-booked_at"]
        indexes = [
            models.Index(fields=["user", "status"]), 
            models.Index(fields=["event", "status"])
        ]

    def __str__(self):
        return f"Booking {self.pk}: {self.user} - {self.event}"