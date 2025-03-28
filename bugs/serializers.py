from rest_framework import serializers
from .models import Bug, Attachment


class BugSerializer(serializers.ModelSerializer):
    author = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = Bug
        fields = [
            'id',
            'author',
            'title',
            'description',
            'created_at',
            'updated_at',
        ]


class AttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        fields = [
            'id',
            'bug',
            'file',
            'uploaded_at',
            'updated_at',
        ]

    def validate_file(self, value):
        max_size = 1024 * 1024  # 1 MB in bytes
        if value.size > max_size:
            raise serializers.ValidationError("File size exceeds the limit of 1 MB.")
        return value

    def validate(self, data):
        bug = data.get('bug')
        if bug is None:
            raise serializers.ValidationError("Bug field is required.")
        if bug.attachments.count() >= 3:
            raise serializers.ValidationError("Cannot add more than 3 attachments per bug.")
        return data
