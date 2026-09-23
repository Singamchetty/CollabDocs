from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


def custom_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is not None:
        return response

    if isinstance(exc, ObjectDoesNotExist):
        return Response({"detail": "The requested object does not exist."}, status=status.HTTP_404_NOT_FOUND)

    if isinstance(exc, IntegrityError):
        return Response({"detail": "This operation conflicts with existing data."}, status=status.HTTP_409_CONFLICT)

    return None
