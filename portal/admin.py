from django.contrib import admin
from .models import (
    Partner,
    PartnerMembership,
    PartnerMentorshipAvailability,
    PartnerMentorshipPublicKey,
    PartnerMentorshipFormMentor,
    PartnerMentorshipFormMentee,
    PartnerMentorshipFormMentorResponse,
    PartnerMentorshipFormMenteeResponse,
)

@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)

@admin.register(PartnerMembership)
class PartnerMembershipAdmin(admin.ModelAdmin):
    list_display = ('partner', 'user', 'created_at')
    search_fields = ('partner__name', 'user__username')

@admin.register(PartnerMentorshipAvailability)
class PartnerMentorshipAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('partner', 'status', 'updated_at')
    search_fields = ('partner__name',)

@admin.register(PartnerMentorshipPublicKey)
class PartnerMentorshipPublicKeyAdmin(admin.ModelAdmin):
    list_display = ('partner', 'created_at')
    search_fields = ('partner__name',)

@admin.register(PartnerMentorshipFormMentor)
class PartnerMentorshipFormMentorAdmin(admin.ModelAdmin):
    list_display = ('partner', 'created_at')
    search_fields = ('partner__name',)

@admin.register(PartnerMentorshipFormMentee)
class PartnerMentorshipFormMenteeAdmin(admin.ModelAdmin):
    list_display = ('partner', 'created_at')
    search_fields = ('partner__name',)

@admin.register(PartnerMentorshipFormMentorResponse)
class PartnerMentorshipFormMentorResponseAdmin(admin.ModelAdmin):
    list_display = ('partner', 'created_at')
    search_fields = ('partner__name',)

@admin.register(PartnerMentorshipFormMenteeResponse)
class PartnerMentorshipFormMenteeResponseAdmin(admin.ModelAdmin):
    list_display = ('partner', 'created_at')
    search_fields = ('partner__name',)