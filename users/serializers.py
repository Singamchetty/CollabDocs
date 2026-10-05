import re

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from rest_framework import serializers

from .models import User

PHONE_PATTERN = re.compile(r"^\+?\d{7,15}$")


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "first_name", "last_name", "email", "phone", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_email(self, value):
        value = value.strip().lower()
        try:
            validate_email(value)
        except DjangoValidationError:
            raise serializers.ValidationError("Enter a valid email address.")
        return value

    def validate_phone(self, value):
        value = value.strip()
        if not PHONE_PATTERN.match(value):
            raise serializers.ValidationError("Phone must be 7-15 digits, optionally starting with '+'.")
        return value


class UserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "first_name", "last_name"]
        read_only_fields = fields
