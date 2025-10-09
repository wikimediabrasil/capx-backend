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
from django.urls import path, include, re_path
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from skills.views import SkillViewSet, SkillByTypeViewSet
from users.views import (
    ProfileViewSet, UsersViewSet, QuickListViewSet, AvatarViewSet, SavedItemViewSet,
    UsersBySkillViewSet, UsersByTagViewSet, TerritoryViewSet, WikimediaProjectViewSet,
    BadgeViewSet, UserBadgeViewSet, StatisticsView
)
from users.letsconnect import LetsConnectViewSet
from bugs.views import BugViewSet, AttachmentViewSet
from orgs.views import OrganizationViewSet, OrganizationTypeViewSet, TagDiffViewSet, DocumentViewSet
from events.views import EventViewSet
from message.views import MessageViewSet
from projects.views import ProjectViewSet, ProjectMemberViewSet, ProjectMemberAcceptanceViewSet
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from users.oauth import UserAuthView, AuthView, CheckView


router = DefaultRouter()
router.register('skill', SkillViewSet, basename='skill')
router.register('users', UsersViewSet, basename='users')
router.register('profile', ProfileViewSet, basename='profile')
router.register('wikimedia_project', WikimediaProjectViewSet, basename='wikimedia_project')
router.register('territory', TerritoryViewSet, basename='territory')
router.register('avatar', AvatarViewSet, basename='avatar')
router.register('saved_item', SavedItemViewSet, basename='saved_item')
router.register('organizations', OrganizationViewSet, basename='organizations')
router.register('organization_type', OrganizationTypeViewSet, basename='organization_type')
router.register('tag_diff', TagDiffViewSet, basename='tag_diff')
router.register('document', DocumentViewSet, basename='document')
router.register('bugs', BugViewSet, basename='bugs')
router.register('attachment', AttachmentViewSet, basename='attachment')
router.register('users_by_skill', UsersBySkillViewSet, basename='users_by_skill')
router.register('skills_by_type', SkillByTypeViewSet, basename='skills_by_type')
router.register('events', EventViewSet)
router.register('messages', MessageViewSet, basename='messages')
router.register('projects', ProjectViewSet, basename='projects')
router.register('project_members', ProjectMemberViewSet, basename='project_members')
router.register('project_member_acceptance', ProjectMemberAcceptanceViewSet, basename='project_member_acceptance')
router.register('list', QuickListViewSet, basename='list')
router.register('letsconnect', LetsConnectViewSet, basename='letsconnect')
router.register('badges', BadgeViewSet, basename='badges')
router.register('user_badge', UserBadgeViewSet, basename='user_badge')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('portal/', include('portal.urls', namespace='portal')),
    path('api-auth/', include("rest_framework.urls", namespace="rest_framework")),
    path('', include('social_django.urls')),
    path('tags/<str:tag_type>/<int:tag_id>/', UsersByTagViewSet.as_view({'get': 'list'}), name='tags'),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("", SpectacularSwaggerView.as_view(url_name="schema"),name="swagger-ui",),
    re_path(r'^api/login/social/knox_user/(?:(?P<provider>[a-zA-Z0-9_-]+)/?)?$', UserAuthView.as_view(), name='login_social_knox_user'),
    re_path(r'^api/login/social/knox/(?:(?P<provider>[a-zA-Z0-9_-]+)/?)?$', AuthView.as_view(), name='login_social_knox'),
    path('api/login/social/check/', CheckView.as_view(), name='login_social_check'),
    path('statistics/', StatisticsView.as_view(), name='statistics'),
    path('', include(router.urls)),
]

urlpatterns += staticfiles_urlpatterns()

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)