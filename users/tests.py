import uuid

from rest_framework import status
from rest_framework.test import APITestCase

from .models import User

VALID_USER = {
    "first_name": "Ada",
    "last_name": "Lovelace",
    "email": "ada@example.com",
    "phone": "+14155550101",
}


class UserApiTests(APITestCase):
    def test_create_user(self):
        response = self.client.post("/api/users/", VALID_USER, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["email"], "ada@example.com")
        self.assertTrue(User.objects.filter(id=response.data["id"]).exists())

    def test_email_is_normalized_to_lowercase(self):
        response = self.client.post("/api/users/", {**VALID_USER, "email": "  ADA@Example.com "}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["email"], "ada@example.com")

    def test_duplicate_email_is_rejected(self):
        self.client.post("/api/users/", VALID_USER, format="json")
        response = self.client.post("/api/users/", {**VALID_USER, "phone": "+14155550102"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_invalid_email_is_rejected(self):
        response = self.client.post("/api/users/", {**VALID_USER, "email": "not-an-email"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_invalid_phone_is_rejected(self):
        response = self.client.post("/api/users/", {**VALID_USER, "phone": "abc"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone", response.data)

    def test_missing_fields_are_rejected(self):
        response = self.client.post("/api/users/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(set(response.data), {"first_name", "last_name", "email", "phone"})

    def test_get_user_by_id(self):
        user_id = self.client.post("/api/users/", VALID_USER, format="json").data["id"]
        response = self.client.get(f"/api/users/{user_id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], user_id)

    def test_get_unknown_user_returns_404(self):
        response = self.client.get(f"/api/users/{uuid.uuid4()}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_malformed_id_returns_404(self):
        response = self.client.get("/api/users/not-a-uuid/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_and_delete_are_not_exposed(self):
        user_id = self.client.post("/api/users/", VALID_USER, format="json").data["id"]
        self.assertEqual(self.client.put(f"/api/users/{user_id}/", VALID_USER, format="json").status_code, 405)
        self.assertEqual(self.client.delete(f"/api/users/{user_id}/").status_code, 405)
