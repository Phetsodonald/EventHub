
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class RegisterUserTests(APITestCase):

    def setUp(self):
        # Get the URL using the name defined in accounts/urls.py
        self.url = reverse("register")

        self.valid_data = {
            "username": "testuser",
            "email": "testuser@example.com",
            "password": "SecurePass123!",
        }

    def test_register_user_successfully(self):
        response = self.client.post(
            self.url,
            self.valid_data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            response.data["message"],
            "Account created successfully.",
        )

        # Confirm the user was saved in the database.
        user = User.objects.get(username="testuser")

        self.assertEqual(user.email, "testuser@example.com")
        self.assertEqual(user.role, User.Role.CUSTOMER)

        # Confirm the password is hashed.
        self.assertTrue(user.check_password("SecurePass123!"))
        self.assertNotEqual(user.password, "SecurePass123!")

    def test_register_rejects_duplicate_username(self):
        self.client.post(self.url, self.valid_data, format="json")

        duplicate_data = {
            "username": "testuser",
            "email": "another@example.com",
            "password": "AnotherPass123!",
        }

        response = self.client.post(
            self.url,
            duplicate_data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("username", response.data)

        # The duplicate user must not be created.
        self.assertEqual(
            User.objects.filter(username="testuser").count(),
            1,
        )

    def test_register_rejects_duplicate_email(self):
        self.client.post(self.url, self.valid_data, format="json")

        duplicate_data = {
            "username": "anotheruser",
            "email": "testuser@example.com",
            "password": "AnotherPass123!",
        }

        response = self.client.post(
            self.url,
            duplicate_data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("email", response.data)

    def test_register_rejects_short_password(self):
        invalid_data = {
            **self.valid_data,
            "password": "short",
        }

        response = self.client.post(
            self.url,
            invalid_data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("password", response.data)

        self.assertFalse(
            User.objects.filter(username="testuser").exists()
        )

    def test_register_rejects_missing_username(self):
        invalid_data = {
            "email": "testuser@example.com",
            "password": "SecurePass123!",
        }

        response = self.client.post(
            self.url,
            invalid_data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("username", response.data)

    def test_register_rejects_missing_password(self):
        invalid_data = {
            "username": "testuser",
            "email": "testuser@example.com",
        }

        response = self.client.post(
            self.url,
            invalid_data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("password", response.data)

