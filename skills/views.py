from .models import Skill, Hashtag
from .serializers import SkillSerializer, HashtagSerializer
from rest_framework import status, viewsets, filters
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes, OpenApiExample, OpenApiResponse

@extend_schema_view(
    list=extend_schema(
        summary='List all skills.',
        description='This endpoint lists all skills.',
    ),
    retrieve=extend_schema(
        summary='Retrieve a skill by ID.',
        description='This endpoint retrieves a skill by its ID.',
    ),
)
class SkillViewSet(viewsets.ModelViewSet):
    serializer_class = SkillSerializer
    queryset = Skill.objects.all()
    filter_backends = [filters.SearchFilter]
    search_fields = ['skill_wikidata_item']


    @extend_schema(
        summary='Creates a new skill.',
        description='This endpoint creates a new skill based on the Wikidata item ID. ' \
            'Only staff members are allowed to create skills.',
    )
    def create(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return Response(
                {"detail": "Only staff can create skills."},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().create(request, *args, **kwargs)


    @extend_schema(
        summary='Updates a skill.',
        description='This endpoint updates a skill already saved. ' \
            'Only staff members are allowed to update skills.',
    )
    def update(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return Response(
                {"detail": "Only staff can update skills."},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)

    
    @extend_schema(exclude=True)        
    def partial_update(self, request, *args, **kwargs):
        return Response("PATCH method not allowed", status=status.HTTP_405_METHOD_NOT_ALLOWED)


    @extend_schema(
        summary='Deletes a skill.',
        description='This endpoint deletes a skill. ' \
            'Only staff members are allowed to delete skills.',
    )
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        # Check if user is staff
        if not request.user.is_staff:
            return Response(
                {"detail": "Only staff can delete skills."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check if this skill is referenced by any other item's skill_type
        if Skill.objects.filter(skill_type=instance).exists():
            return Response(
                {"detail": "This skill is referenced by other items and cannot be deleted."},
                status=status.HTTP_403_FORBIDDEN
            )

        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SkillByTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer  

    @extend_schema(
        summary='Retrieve skills by skill type.',
        description='This endpoint retrieves skills by skill type ID.',
        parameters=[
            OpenApiParameter(
                'id',
                OpenApiTypes.INT,
                OpenApiParameter.PATH,
                description='Skill type ID. Use 0 to retrieve skills without a skill type.',
                required=True,
            ),
        ],
    )
    def retrieve(self, request, *args, **kwargs):
        skill_id = self.kwargs.get('pk')
        if not skill_id.isdigit():
            return Response(
                {"detail": "Skill ID must be an integer."},
                status=status.HTTP_400_BAD_REQUEST
            )
        elif skill_id == "0":
            skills = Skill.objects.filter(skill_type__isnull=True)
        else:
            skills = Skill.objects.filter(skill_type=skill_id)
        
        data = {skill.id: str(skill) for skill in skills}
        return Response(data)

    @extend_schema(exclude=True)
    def list(self, request, *args, **kwargs):
        response = {'message': 'Please provide a skill_id to retrieve skills.'}
        return Response(response, status=status.HTTP_400_BAD_REQUEST)

@extend_schema_view(
    list=extend_schema(
        summary='List all hashtags.',
        description='This endpoint lists all hashtags.',
    ),
    retrieve=extend_schema(
        summary='Retrieve a hashtag by ID.',
        description='This endpoint retrieves a hashtag by its ID.',
    ),
)
class HashtagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Hashtag.objects.all()
    serializer_class = HashtagSerializer