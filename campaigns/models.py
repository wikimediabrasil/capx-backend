from django.core.validators import RegexValidator
from django.db import models

from skills.models import Skill

qid_form_validator = RegexValidator(
    regex=r"^Q\d+$",
    message='Field must be in the format "Q12345"',
)


class Campaign(models.Model):
    metabase_qid = models.CharField(
        "Metabase QID",
        max_length=30,
        unique=True,
        validators=[qid_form_validator],
        help_text="Metabase QID.",
    )
    min_start_date = models.DateField(
        "Minimum start date",
        blank=True,
        null=True,
        help_text="Earliest start date among campaign events.",
    )
    max_end_date = models.DateField(
        "Maximum end date",
        blank=True,
        null=True,
        help_text="Latest end date among campaign events.",
    )
    org_qids = models.TextField(
        "Organization QIDs",
        blank=True,
        default="",
        help_text="Pipe-separated list of organization QIDs from Metabase.",
    )
    location_qids = models.TextField(
        "Location QIDs",
        blank=True,
        default="",
        help_text="Pipe-separated list of location QIDs from Metabase.",
    )
    language_qids = models.TextField(
        "Language QIDs",
        blank=True,
        default="",
        help_text="Pipe-separated list of language QIDs from Metabase.",
    )
    skill_wikidata_qids = models.TextField(
        "Skill Wikidata QIDs",
        blank=True,
        default="",
        help_text="Pipe-separated list of Skill Wikidata QIDs from Metabase.",
    )
    skills = models.ManyToManyField(
        Skill,
        blank=True,
        related_name="campaigns",
        help_text="Skills associated with this campaign.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("metabase_qid",)

    def __str__(self):
        return self.metabase_qid

    def get_pipe_separated_as_array(self, field_name: str) -> list[str]:
        value = getattr(self, field_name, "")
        if not value:
            return []
        return [item.strip() for item in value.split("|") if item.strip()]

    def sync_skills(self, skill_wikidata_qids: str) -> list[int]:
        """
        Sync skills for this campaign based on skill_wikidata_qids.
        skill_wikidata_qids is a pipe-separated string of Skill Wikidata QIDs.
        Silently ignores missing or invalid skill QIDs.

        Returns:
            List of valid skill IDs that were synced.
        """
        if not skill_wikidata_qids:
            self.skills.clear()
            return []

        qids = [qid.strip() for qid in skill_wikidata_qids.split("|") if qid.strip()]

        valid_skill_ids = []
        for qid in qids:
            try:
                skill = Skill.objects.get(skill_wikidata_item=qid)
                valid_skill_ids.append(skill.id)
            except (Skill.DoesNotExist, ValueError):
                # Silently ignore missing or invalid skill QIDs
                pass

        if valid_skill_ids:
            self.skills.set(valid_skill_ids)
        else:
            self.skills.clear()

        return valid_skill_ids
