"""Tests for verifications serializers."""

import uuid

import pytest

from apps.verifications.serializers import VerificationSerializer


class TestVerificationSerializerValidateCode:
    def test_strips_whitespace_from_code(self):
        data = {
            "code": "  ABC123  ",
            "verification_code_uuid": str(uuid.uuid4()),
        }
        serializer = VerificationSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["code"] == "ABC123"

    def test_accepts_exact_six_chars(self):
        data = {
            "code": "ABC123",
            "verification_code_uuid": str(uuid.uuid4()),
        }
        serializer = VerificationSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["code"] == "ABC123"

    def test_rejects_more_than_six_chars(self):
        data = {
            "code": "ABCDEFG",  # 7 chars
            "verification_code_uuid": str(uuid.uuid4()),
        }
        serializer = VerificationSerializer(data=data)
        assert not serializer.is_valid()
        # DRF CharField enforces max_length and produces a default error message
        assert "code" in serializer.errors

    def test_rejects_blank_after_stripping(self):
        data = {
            "code": "    ",
            "verification_code_uuid": str(uuid.uuid4()),
        }
        serializer = VerificationSerializer(data=data)
        assert not serializer.is_valid()
        assert "code" in serializer.errors
