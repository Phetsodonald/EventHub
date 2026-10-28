from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied

from .models import Event
from .serializers import EventSerializer


def is_admin_role(user):
    return user.is_authenticated and (user.is_staff or user.role == "ADMIN")


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def event_list_create(request):
    if request.method == "GET":
        if request.user.is_authenticated and is_admin_role(request.user):
            events = Event.objects.select_related("created_by").all()
        else:
            events = Event.objects.filter(status=Event.Status.PUBLISHED).select_related(
                "created_by"
            )

        serializer = EventSerializer(events, many=True)
        return Response(serializer.data)

    # POST: only admins may create events.
    if not request.user.is_authenticated:
        return Response(
            {"detail": "Authentication credentials were not provided."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if not is_admin_role(request.user):
        raise PermissionDenied("Only admins can create events.")

    serializer = EventSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save(created_by=request.user)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST,
    )


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([AllowAny])
def event_detail(request, pk):
    if request.method == "GET":
        if request.user.is_authenticated and is_admin_role(request.user):
            events = Event.objects.select_related("created_by")
        else:
            events = Event.objects.filter(status=Event.Status.PUBLISHED).select_related(
                "created_by"
            )

        event = events.filter(pk=pk).first()

        if event is None:
            return Response(
                {"detail": "Event not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(EventSerializer(event).data)

    # PUT, PATCH, and DELETE: only admins may modify events.
    if not request.user.is_authenticated:
        return Response(
            {"detail": "Authentication credentials were not provided."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if not is_admin_role(request.user):
        raise PermissionDenied("Only admins can modify events.")

    event = Event.objects.filter(pk=pk).first()

    if event is None:
        return Response(
            {"detail": "Event not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method in ["PUT", "PATCH"]:
        serializer = EventSerializer(
            event,
            data=request.data,
            partial=(request.method == "PATCH"),
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    event.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
