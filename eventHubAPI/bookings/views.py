
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from events.models import Event
from .models import Booking
from .serializers import BookingSerializer


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def booking_list_create(request):
    if request.method == "GET":
        bookings = Booking.objects.filter(
            user=request.user
        ).select_related("event")

        serializer = BookingSerializer(bookings, many=True)
        return Response(serializer.data)

    serializer = BookingSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    event_id = serializer.validated_data["event"].id
    quantity = serializer.validated_data["quantity"]

    with transaction.atomic():
        try:
            event = Event.objects.select_for_update().get(pk=event_id)
        except Event.DoesNotExist:
            return Response(
                {"detail": "Event not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if event.status != Event.Status.PUBLISHED:
            raise ValidationError({
                "event": "This event is not available for booking."
            })

        if event.starts_at <= timezone.now():
            raise ValidationError({
                "event": "This event has already started."
            })

        confirmed_tickets = Booking.objects.filter(
            event=event,
            status=Booking.Status.CONFIRMED,
        ).aggregate(total=Sum("quantity"))["total"] or 0

        available_tickets = event.total_tickets - confirmed_tickets

        if quantity > available_tickets:
            raise ValidationError({
                "quantity": (
                    f"Only {available_tickets} tickets are available."
                )
            })

        booking = serializer.save(user=request.user)

    return Response(
        BookingSerializer(booking).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def booking_detail(request, pk):
    booking = Booking.objects.filter(
        pk=pk,
        user=request.user,
    ).select_related("event").first()

    if booking is None:
        return Response(
            {"detail": "Booking not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "GET":
        return Response(BookingSerializer(booking).data)

    if request.method == "PATCH":
        allowed_fields = {"quantity"}
        if set(request.data.keys()) - allowed_fields:
            raise ValidationError(
                "Only the quantity can be updated. Use cancellation to cancel a booking."
            )

        serializer = BookingSerializer(
            booking,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)

        new_quantity = serializer.validated_data.get(
            "quantity", booking.quantity
        )

        with transaction.atomic():
            event = Event.objects.select_for_update().get(
                pk=booking.event_id
            )

            confirmed_tickets = Booking.objects.filter(
                event=event,
                status=Booking.Status.CONFIRMED,
            ).aggregate(total=Sum("quantity"))["total"] or 0

            # Exclude this booking from the count when checking its new quantity.
            available_without_this = (
                event.total_tickets - confirmed_tickets + booking.quantity
            )

            if new_quantity > available_without_this:
                raise ValidationError({
                    "quantity": (
                        f"Only {available_without_this} tickets are available "
                        "for this booking."
                    )
                })

            serializer.save()

        return Response(BookingSerializer(booking).data)

    if booking.status == Booking.Status.CONFIRMED:
        with transaction.atomic():
            Event.objects.select_for_update().get(pk=booking.event_id)
            booking.status = Booking.Status.CANCELLED
            booking.save(update_fields=["status", "updated_at"])

    return Response(status=status.HTTP_204_NO_CONTENT)
