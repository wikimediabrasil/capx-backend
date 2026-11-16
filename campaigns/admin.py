from django.contrib import admin

from users.models import ProfileCampaign

from .models import Campaign


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = (
        "metabase_qid",
        "min_start_date",
        "max_end_date",
        "org_qids",
        "location_qids",
        "language_qids",
        "skills_count",
        "updated_at",
    )
    list_filter = ("skills",)
    search_fields = ("metabase_qid",)
    ordering = ("metabase_qid",)
    filter_horizontal = ("skills",)

    def skills_count(self, obj):
        return obj.skills.count()

    skills_count.short_description = "Skills"


@admin.register(ProfileCampaign)
class ProfileCampaignAdmin(admin.ModelAdmin):
    verbose_name = "User campaign"
    verbose_name_plural = "User campaigns"

    list_display = ("profile", "campaign", "role_wikidata_qid", "joined_at")
    list_filter = ("role_wikidata_qid",)
    search_fields = ("profile__user__username", "campaign__metabase_qid")
    autocomplete_fields = ("profile", "campaign")
    ordering = ("-joined_at",)
