from django.contrib import admin
from .models import (
    Partner,
    PartnerMembership,
    PartnerMentorshipPublicKey,
    PartnerMentorshipFormMentor,
    PartnerMentorshipFormMentee,
    PartnerMentorshipFormMentorResponse,
    PartnerMentorshipFormMenteeResponse,
)

@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ('pk', 'organization', 'created_at')
    search_fields = ('organization__acronym', 'organization__i18n_names__name')

@admin.register(PartnerMembership)
class PartnerMembershipAdmin(admin.ModelAdmin):
    list_display = ('partner', 'user', 'created_at')
    search_fields = ('partner__organization__acronym', 'partner__organization__i18n_names__name', 'user__username')


@admin.register(PartnerMentorshipPublicKey)
class PartnerMentorshipPublicKeyAdmin(admin.ModelAdmin):
    list_display = ('partner', 'created_at')
    search_fields = ('partner__organization__acronym', 'partner__organization__i18n_names__name')

@admin.register(PartnerMentorshipFormMentor)
class PartnerMentorshipFormMentorAdmin(admin.ModelAdmin):
    list_display = ('partner', 'created_at')
    search_fields = ('partner__organization__acronym', 'partner__organization__i18n_names__name')

@admin.register(PartnerMentorshipFormMentee)
class PartnerMentorshipFormMenteeAdmin(admin.ModelAdmin):
    list_display = ('partner', 'created_at')
    search_fields = ('partner__organization__acronym', 'partner__organization__i18n_names__name')

@admin.register(PartnerMentorshipFormMentorResponse)
class PartnerMentorshipFormMentorResponseAdmin(admin.ModelAdmin):
    list_display = ('partner', 'created_at')
    search_fields = ('partner__organization__acronym', 'partner__organization__i18n_names__name')

@admin.register(PartnerMentorshipFormMenteeResponse)
class PartnerMentorshipFormMenteeResponseAdmin(admin.ModelAdmin):
    list_display = ('partner', 'created_at')
    search_fields = ('partner__organization__acronym', 'partner__organization__i18n_names__name')