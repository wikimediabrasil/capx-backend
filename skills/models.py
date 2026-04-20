from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone
from django.core.exceptions import ValidationError


qid_form_validator = RegexValidator(regex=r"^Q\d+$", message="Field must be in the format \"Q123456789\"")


class Skill(models.Model):
    skill_wikidata_item = models.CharField(
        "Wikidata item associated", 
        max_length=30, default='', unique=True,
        help_text="Wikidata item ID of the skill.",
        validators=[qid_form_validator]
    )
    skill_type = models.ForeignKey(
        "self", 
        verbose_name="Skill type", blank=True, on_delete=models.SET_NULL, null=True,
        help_text="ID of the another skill that this skill is a subtype of."
    )
    skill_date_of_creation = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.skill_wikidata_item

    def save(self, *args, **kwargs):
        if self.skill_type:
            parent_skill = self.skill_type
            level = 1
            while parent_skill.skill_type:
                parent_skill = parent_skill.skill_type
                level += 1
                if level >= 3:
                    raise ValidationError("Skills cannot be nested more than 3 levels deep.")
        super().save(*args, **kwargs)


class Hashtag(models.Model):
    name = models.CharField(max_length=255, unique=True)
    skills = models.ManyToManyField('Skill', blank=True, related_name='hashtags')

    def __str__(self):
        return self.name
