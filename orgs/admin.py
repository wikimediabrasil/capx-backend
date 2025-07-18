from django.contrib import admin
from .models import Organization, OrganizationType, Management, TagDiff, Document

admin.site.register(Organization)
admin.site.register(OrganizationType)
admin.site.register(Management)
admin.site.register(TagDiff)
admin.site.register(Document)
