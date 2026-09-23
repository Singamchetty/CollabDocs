import io
from contextlib import redirect_stdout

from django.test import TestCase


class RequestLoggingMiddlewareTests(TestCase):
    def test_logs_method_path_status_and_duration(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            self.client.get("/admin/login/")
        output = buffer.getvalue()
        self.assertIn("GET", output)
        self.assertIn("/admin/login/", output)
        self.assertIn("ms", output)
