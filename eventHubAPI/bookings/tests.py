from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APITestCase

from events.models import Event
from .models import Booking

User = get_user_model()


class BookingViewsTests(APITestCase):
    def setUp(self):
        # Create two separate users to test booking ownership.
        self.user = User.objects.create_user(
            username="customer1",
            email="customer1@example.com",
            password="SecurePass123!",
        )
        self.other_user = User.objects.create_user(
            username="customer2",
            email="customer2@example.com",
            password="SecurePass123!",
        )

        self.event = Event.objects.create(
            title="Python Conference",
            description="A technology conference.",
            venue="Johannesburg",
            starts_at=timezone.now() + timedelta(days=7),
            end_at=timezone.now() + timedelta(days=7, hours=3),
            ticket_price=Decimal("150.00"),
            total_tickets=10,
            status=Event.Status.PUBLISHED,
            created_by=self.user,
        )

        self.list_url = reverse("booking-list-create")
        self.detail_url = lambda booking_id: reverse(
            "booking-detail",
            kwargs={"pk": booking_id},
        )

        self.client.force_authenticate(user=self.user)

    def create_booking(self, user=None, event=None, quantity=2):
        return Booking.objects.create(
            user=user or self.user,
            event=event or self.event,
            quantity=quantity,
            status=Booking.Status.CONFIRMED,
        )

    # GET /api/bookings/

    def test_list_returns_only_current_users_bookings(self):
        own_booking = self.create_booking()
        self.create_booking(user=self.other_user)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], own_booking.id)

    # POST /api/bookings/

    def test_create_booking_successfully(self):
        response = self.client.post(
            self.list_url,
            {"event": self.event.id, "quantity": 2},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(Booking.objects.count(), 1)

        booking = Booking.objects.get()
        self.assertEqual(booking.user, self.user)
        self.assertEqual(booking.event, self.event)
        self.assertEqual(booking.quantity, 2)
        self.assertEqual(booking.status, Booking.Status.CONFIRMED)

    def test_create_booking_rejects_unpublished_event(self):
        self.event.status = Event.Status.DRAFT
        self.event.save(update_fields=["status"])

        response = self.client.post(
            self.list_url,
            {"event": self.event.id, "quantity": 1},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(Booking.objects.count(), 0)

    def test_create_booking_rejects_event_that_has_started(self):
        self.event.starts_at = timezone.now() - timedelta(hours=1)
        self.event.end_at = timezone.now() + timedelta(hours=2)
        self.event.save(update_fields=["starts_at", "end_at"])

        response = self.client.post(
            self.list_url,
            {"event": self.event.id, "quantity": 1},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(Booking.objects.count(), 0)

    def test_create_booking_rejects_insufficient_tickets(self):
        self.event.total_tickets = 3
        self.event.save(update_fields=["total_tickets"])

        self.create_booking(quantity=2)

        response = self.client.post(
            self.list_url,
            {"event": self.event.id, "quantity": 2},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(Booking.objects.count(), 1)

    def test_create_booking_rejects_zero_quantity(self):
        response = self.client.post(
            self.list_url,
            {"event": self.event.id, "quantity": 0},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(Booking.objects.count(), 0)

    # GET /api/bookings/<id>/

    def test_retrieve_own_booking(self):
        booking = self.create_booking()

        response = self.client.get(self.detail_url(booking.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], booking.id)
        self.assertEqual(response.data["quantity"], 2)

    def test_cannot_retrieve_another_users_booking(self):
        booking = self.create_booking(user=self.other_user)

        response = self.client.get(self.detail_url(booking.id))

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    # PATCH /api/bookings/<id>/

    def test_update_booking_quantity(self):
        booking = self.create_booking(quantity=2)

        response = self.client.patch(
            self.detail_url(booking.id),
            {"quantity": 4},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        booking.refresh_from_db()
        self.assertEqual(booking.quantity, 4)

    def test_update_quantity_rejects_insufficient_tickets(self):
        self.event.total_tickets = 5
        self.event.save(update_fields=["total_tickets"])

        booking = self.create_booking(quantity=2)
        self.create_booking(user=self.other_user, quantity=2)

        response = self.client.patch(
            self.detail_url(booking.id),
            {"quantity": 4},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        booking.refresh_from_db()
        self.assertEqual(booking.quantity, 2)

    def test_update_rejects_fields_other_than_quantity(self):
        booking = self.create_booking()

        response = self.client.patch(
            self.detail_url(booking.id),
            {"status": "CANCELLED"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CONFIRMED)

    # DELETE /api/bookings/<id>/

    def test_cancel_booking(self):
        booking = self.create_booking()

        response = self.client.delete(self.detail_url(booking.id))

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CANCELLED)

        # Cancellation preserves the record instead of deleting it.
        self.assertTrue(Booking.objects.filter(pk=booking.id).exists())

    def test_cannot_cancel_another_users_booking(self):
        booking = self.create_booking(user=self.other_user)

        response = self.client.delete(self.detail_url(booking.id))

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CONFIRMED)

    # Authentication

    def test_list_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_create_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(
            self.list_url,
            {"event": self.event.id, "quantity": 1},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(Booking.objects.count(), 0)
