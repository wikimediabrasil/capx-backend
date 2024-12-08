"""
URL configuration for CapX project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf import settings
from django.urls import path, include
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from skills.views import SkillViewSet, SkillByTypeViewSet
from users.views import (
    ProfileViewSet, UsersViewSet, QuickListViewSet,
    UsersBySkillViewSet, UsersByTagViewSet, TerritoryViewSet,
)
from bugs.views import BugViewSet, AttachmentViewSet
from orgs.views import OrganizationViewSet, OrganizationTypeViewSet
from events.views import EventViewSet, EventParticipantViewSet, EventOrganizationsViewSet
from message.views import MessageViewSet
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


router = DefaultRouter()
router.register('skill', SkillViewSet, basename='skill')
router.register('users', UsersViewSet, basename='users')
router.register('profile', ProfileViewSet, basename='profile')
router.register('territory', TerritoryViewSet, basename='territory')
router.register('organizations', OrganizationViewSet, basename='organizations')
router.register('organization_type', OrganizationTypeViewSet, basename='organization_type')
router.register('bugs', BugViewSet, basename='bugs')
router.register('attachment', AttachmentViewSet, basename='attachment')
router.register('users_by_skill', UsersBySkillViewSet, basename='users_by_skill')
router.register('skills_by_type', SkillByTypeViewSet, basename='skills_by_type')
router.register('events', EventViewSet)
router.register('events_participants', EventParticipantViewSet)
router.register('events_organizations', EventOrganizationsViewSet)
router.register('messages', MessageViewSet)
router.register('list', QuickListViewSet, basename='list')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api-auth/', include("rest_framework.urls", namespace="rest_framework")),
    path('', include('social_django.urls')),
    path('api/login/', include('rest_social_auth.urls_knox')),
    path('tags/<str:tag_type>/<int:tag_id>/', UsersByTagViewSet.as_view({'get': 'list'}), name='tags'),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("", SpectacularSwaggerView.as_view(url_name="schema"),name="swagger-ui",),
    path('', include(router.urls)),
]

urlpatterns += staticfiles_urlpatterns()

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)