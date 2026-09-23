import time


class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started_at = time.monotonic()
        response = self.get_response(request)
        duration_ms = (time.monotonic() - started_at) * 1000
        print(f"{request.method} {request.path} {response.status_code} {duration_ms:.2f}ms")
        return response
