import uuid
from datetime import datetime, time

from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework import serializers, viewsets

from .models import AuditLog
from .serializers import AuditLogSerializer


def parse_bound(raw, field, end_of_day):
    try:
        day = parse_date(raw)
        moment = datetime.combine(day, time.max if end_of_day else time.min) if day else parse_datetime(raw)
    except ValueError:
        moment = None
    if moment is None:
        raise serializers.ValidationError({field: "Use an ISO date (YYYY-MM-DD) or datetime."})
    return timezone.make_aware(moment) if timezone.is_naive(moment) else moment


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer

    def get_queryset(self):
        queryset = AuditLog.objects.order_by("-timestamp", "id")
        if self.action != "list":
            return queryset

        params = self.request.query_params

        actor = params.get("actor")
        if actor:
            try:
                uuid.UUID(actor)
            except ValueError:
                raise serializers.ValidationError({"actor": "Must be a valid UUID."})
            queryset = queryset.filter(actor_id=actor)

        raw_from, raw_to = params.get("date_from"), params.get("date_to")
        start = parse_bound(raw_from, "date_from", end_of_day=False) if raw_from else None
        end = parse_bound(raw_to, "date_to", end_of_day=True) if raw_to else None
        if start and end and start > end:
            raise serializers.ValidationError({"date_to": "Must not be earlier than date_from."})
        if start:
            queryset = queryset.filter(timestamp__gte=start)
        if end:
            queryset = queryset.filter(timestamp__lte=end)

        return queryset
