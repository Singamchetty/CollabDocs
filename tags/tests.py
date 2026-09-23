from django.test import TestCase

from .serializers import TagSerializer


class TagSerializerTests(TestCase):
    def test_name_is_normalized(self):
        serializer = TagSerializer(data={"name": "  Python  "})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        tag = serializer.save()
        self.assertEqual(tag.name, "python")

    def test_blank_name_rejected(self):
        serializer = TagSerializer(data={"name": "   "})
        self.assertFalse(serializer.is_valid())
