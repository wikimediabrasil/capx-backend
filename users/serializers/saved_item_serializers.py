from rest_framework import serializers
from orgs.models import Organization

from users.models import SavedItem, CustomUser


class EntityIdField(serializers.Field):
    @staticmethod
    def _get_user_id(instance):
        return instance.related_user.id if instance.related_user else None

    @staticmethod
    def _get_org_id(instance):
        return instance.related_org.id if instance.related_org else None

    def get_attribute(self, instance):
        # Dynamically retrieve the entity_id based on the entity type.
        if instance.entity == 'org':
            return self._get_org_id(instance)
        if instance.entity == 'user':
            return self._get_user_id(instance)
        return None

    def to_representation(self, value):
        return value

    def to_internal_value(self, data):
        return data


class SavedItemSerializer(serializers.ModelSerializer):
    entity_id = EntityIdField()

    class Meta:
        model = SavedItem
        fields = ['id', 'relation', 'entity', 'entity_id', 'created_at']
        read_only_fields = ['created_at']

    def validate(self, data):
        entity = data.get('entity')
        entity_id = data.get('entity_id')

        if entity == 'org':
            if not Organization.objects.filter(id=entity_id).exists():
                raise serializers.ValidationError("Invalid organization ID.")
        elif entity == 'user':
            if not CustomUser.objects.filter(id=entity_id).exists():
                raise serializers.ValidationError("Invalid user ID.")
        else:
            raise serializers.ValidationError("Invalid entity type.")

        return data

    def create(self, validated_data):
        entity = validated_data['entity']
        entity_id = validated_data.pop('entity_id')

        if entity == 'org':
            validated_data['related_org'] = Organization.objects.get(id=entity_id)
        elif entity == 'user':
            validated_data['related_user'] = CustomUser.objects.get(id=entity_id)

        return super().create(validated_data)
