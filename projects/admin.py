from django.contrib import admin
from .models import Project, ProjectMember, ProjectMemberAcceptance

admin.site.register(Project)
admin.site.register(ProjectMember)
admin.site.register(ProjectMemberAcceptance)
