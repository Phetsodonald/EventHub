
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APITestCase

from .models import Event

User = get_user_model()


class EventViewsTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="eventadmin",
            email="admin@example.com",
            password="SecurePass123!",
            role=User.Role.ADMIN,
        )

        self.customer = User.objects.create_user(
            username="customer",
            email="customer@example.com",
            password="SecurePass123!",
            role=User.Role.CUSTOMER,
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
            created_by=self.admin,
        )

        self.list_url = reverse("event-list-create")
        self.detail_url = lambda pk: reverse(
            "event-detail",
            kwargs={"pk": pk},
        )

        self.valid_data = {
            "title": "Django Workshop",
            "description": "Learn Django REST Framework.",
            "venue": "Pretoria",
            "starts_at": (
                timezone.now() + timedelta(days=14)
            ).isoformat(),
            "end_at": (
                timezone.now() + timedelta(days=14, hours=2)
            ).isoformat(),
            "ticket_price": "200.00",
            "total_tickets": 50,
            "status": Event.Status.PUBLISHED,
        }

    # GET /api/events/

    def test_public_list_shows_only_published_events(self):
        Event.objects.create(
            title="Draft Event",
            description="Not public.",
            venue ="Pretoria",
            starts_at=timezone.now() + timedelta(days=10),
            end_at=timezone.now() + timedelta(days=10, hours=2),
            ticket_price=Decimal("100.00"),
            total_tickets=5,
            status=Event.Status.DRAFT,
            created_by=self.admin,
        )

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Python Conference")

    def test_admin_can_list_all_events(self):
        Event.objects.create(
            title="Draft Event",
            description="Not public.",
            venue="Pretoria",
            starts_at=timezone.now() + timedelta(days=10),
            end_at=timezone.now() + timedelta(days=10, hours=2),
            ticket_price=Decimal("100.00"),
            total_tickets=5,
            status=Event.Status.DRAFT,
            created_by=self.admin,
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_public_can_retrieve_published_event(self):
        response = self.client.get(self.detail_url(self.event.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], self.event.title)

    def test_public_cannot_retrieve_draft_event(self):
        draft = Event.objects.create(
            title="Draft Event",
            description="Private event.",
            venue ="Pretoria",
            starts_at=timezone.now() + timedelta(days=10),
            end_at=timezone.now() + timedelta(days=10, hours=2),
            ticket_price=Decimal("100.00"),
            total_tickets=5,
            status=Event.Status.DRAFT,
            created_by=self.admin,
        )

        response = self.client.get(self.detail_url(draft.id))

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    # POST /api/events/

    def test_admin_can_create_event(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.list_url,
            self.valid_data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertTrue(
            Event.objects.filter(title="Django Workshop").exists()
        )

        created_event = Event.objects.get(title="Django Workshop")
        self.assertEqual(created_event.created_by, self.admin)

    def test_unauthenticated_user_cannot_create_event(self):
        response = self.client.post(
            self.list_url,
            self.valid_data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_customer_cannot_create_event(self):
        self.client.force_authenticate(user=self.customer)

        response = self.client.post(
            self.list_url,
            self.valid_data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    # PUT / PATCH / DELETE /api/events/<id>/

    def test_admin_can_update_event(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.detail_url(self.event.id),
            {"title": "Updated Conference"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.event.refresh_from_db()
        self.assertEqual(self.event.title, "Updated Conference")

    def test_customer_cannot_update_event(self):
        self.client.force_authenticate(user=self.customer)

        response = self.client.patch(
            self.detail_url(self.event.id),
            {"title": "Unauthorized Change"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.event.refresh_from_db()
        self.assertEqual(self.event.title, "Python Conference")

    def test_admin_can_delete_event(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(self.detail_url(self.event.id))

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertFalse(
            Event.objects.filter(pk=self.event.id).exists()
        )

    def test_customer_cannot_delete_event(self):
        self.client.force_authenticate(user=self.customer)

        response = self.client.delete(self.detail_url(self.event.id))

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertTrue(
            Event.objects.filter(pk=self.event.id).exists()
        )

    # Validation

    def test_create_rejects_past_start_time(self):
        self.client.force_authenticate(user=self.admin)

        invalid_data = {
            **self.valid_data,
            "starts_at": (
                timezone.now() - timedelta(days=1)
            ).isoformat(),
        }

        response = self.client.post(
            self.list_url,
            invalid_data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("starts_at", response.data)

    def test_create_rejects_end_time_before_start_time(self):
        self.client.force_authenticate(user=self.admin)

        invalid_data = {
            **self.valid_data,
            "end_at": (
                timezone.now() + timedelta(days=13)
            ).isoformat(),
        }

        response = self.client.post(
            self.list_url,
            invalid_data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("end_at", response.data)

    def test_create_rejects_negative_ticket_price(self):
        self.client.force_authenticate(user=self.admin)

        invalid_data = {
            **self.valid_data,
            "ticket_price": "-10.00",
        }

        response = self.client.post(
            self.list_url,
            invalid_data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("ticket_price", response.data)

    def test_create_rejects_zero_tickets(self):
        self.client.force_authenticate(user=self.admin)

        invalid_data = {
            **self.valid_data,
            "total_tickets": 0,
        }

        response = self.client.post(
            self.list_url,
            invalid_data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("total_tickets", response.data)
