from rest_framework import serializers
from .models import Skill, Hashtag


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = [
            'id',
            'skill_wikidata_item',
            'skill_type',
        ]

class HashtagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hashtag
        fields = [
            'id',
            'name',
            'skills',
        ]