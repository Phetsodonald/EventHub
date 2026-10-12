from django.db import models
from  django.conf import settings

class Event(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PUBLISHED = "PUBLISHED", "Published"
        CANCELLED = "CANCELLED", "Cancelled"

    title = models.CharField(max_length=200)
    description = models.TextField()
    vanue = models.CharField(max_length=255)
    starts_at = models.DateTimeField(db_index=True)
    end_at = models.DateTimeField()
    ticket_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_tickets = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_events")
    created_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["starts_at"]
        indexes = [models.Index(fields=["status", "starts_at"])]

    def __str__(self):
        return self.title