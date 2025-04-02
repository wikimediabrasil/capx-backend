from .models import Bug, Attachment
from .serializers import BugSerializer, AttachmentSerializer
from rest_framework import viewsets, status, filters
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes, OpenApiResponse

@extend_schema_view(
    list=extend_schema(
        summary="List all bugs.",
        description="This endpoint lists all bugs created by the user. If the user is a staff member, all bugs are listed."
    ),
    create=extend_schema(
        summary="Create a new bug.",
        description="This endpoint creates a new bug."
    ),
    retrieve=extend_schema(
        summary="Retrieve a bug.",
        description="This endpoint retrieves a bug by its ID.",
        parameters=[
            OpenApiParameter("id", OpenApiTypes.INT, OpenApiParameter.PATH),
        ]
    )
)
class BugViewSet(viewsets.ModelViewSet):
    serializer_class = BugSerializer
    filter_backends = [filter.OrderingFilter]
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            queryset = Bug.objects.all()
        else:
            queryset = Bug.objects.filter(user=user)
        return queryset
    
    @extend_schema(
        summary="Delete a bug.",
        description="This endpoint deletes a bug by its ID. Only staff members can delete bugs.",
        parameters=[
            OpenApiParameter("id", OpenApiTypes.INT, OpenApiParameter.PATH),
        ]
    )
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.user.is_staff:
            return super().destroy(request, *args, **kwargs)
        return Response(
            {"detail": "You do not have permission to perform this action."},
            status=status.HTTP_403_FORBIDDEN
        )       
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @extend_schema(
        summary="Updates a bug.",
        description="This endpoint updates a bug by its ID. Only staff members can update it.",
        parameters=[
            OpenApiParameter("id", OpenApiTypes.INT, OpenApiParameter.PATH),
        ]
    )
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.user.is_staff:
            return super().update(request, *args, **kwargs)
        return Response(
            {"detail": "You do not have permission to perform this action."},
            status=status.HTTP_403_FORBIDDEN
        )

    @extend_schema(exclude=True)        
    def partial_update(self, request, *args, **kwargs):
        return Response("PATCH method not allowed", status=status.HTTP_405_METHOD_NOT_ALLOWED) 

@extend_schema_view(
    list=extend_schema(
        summary="List all attachments.",
        description="This endpoint lists all attachments created by the user. If the user is a staff member, all attachments are listed."
    ),
    create=extend_schema(
        summary="Create a new attachment.",
        description="This endpoint creates a new attachment.",
        parameters=[
            OpenApiParameter(
                "bug", 
                OpenApiTypes.INT, 
                OpenApiParameter.QUERY, 
                required=True,
                description="The bug ID to which the attachment belongs."
            ),
            OpenApiParameter(
                name="file",
                type=OpenApiTypes.BINARY,
                required=True,
                description="The file to be uploaded."
            )
        ]
    ),
    retrieve=extend_schema(
        summary="Retrieve an attachment.",
        description="This endpoint retrieves an attachment by its ID.",
        parameters=[
            OpenApiParameter("id", OpenApiTypes.INT, OpenApiParameter.PATH),
        ]        
    )
)
class AttachmentViewSet(viewsets.ModelViewSet):
    serializer_class = AttachmentSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            queryset = Attachment.objects.all()
        else:
            queryset = Attachment.objects.filter(bug__user=user)
        return queryset

    @extend_schema(exclude=True)        
    def partial_update(self, request, *args, **kwargs):
        return Response("PATCH method not allowed", status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @extend_schema(exclude=True)
    def update(self, request, *args, **kwargs):
        return Response("PUT method not allowed", status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @extend_schema(
        summary="Delete an attachment.",
        description="This endpoint deletes an attachment by its ID. Only staff members can delete attachments.",
        parameters=[
            OpenApiParameter("id", OpenApiTypes.INT, OpenApiParameter.PATH),
        ]
    )
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.user.is_staff:
            return super().destroy(request, *args, **kwargs)
        return Response(
            {"detail": "You do not have permission to perform this action."},
            status=status.HTTP_403_FORBIDDEN
        )