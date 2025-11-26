from rest_framework import serializers


class CapacityItemSerializer(serializers.Serializer):
    qid = serializers.CharField()
    metabase_id = serializers.CharField(allow_null=True, required=False)
    lang = serializers.CharField()
    label = serializers.CharField(allow_null=True, required=False)
    description = serializers.CharField(allow_null=True, required=False)
    fallback_label = serializers.CharField(allow_null=True, required=False)
    fallback_description = serializers.CharField(allow_null=True, required=False)


class TranslationSubmitSerializer(serializers.Serializer):
    qid = serializers.CharField()
    lang = serializers.CharField()
    label = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    description = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    def validate(self, attrs):
        qid = attrs.get('qid', '').strip()
        lang = attrs.get('lang', '').strip()
        label = attrs.get('label')
        description = attrs.get('description')
        if not qid or not lang:
            raise serializers.ValidationError('Missing qid or lang.')
        if label is None and description is None:
            raise serializers.ValidationError('Provide at least label or description.')
        if lang == 'en':
            raise serializers.ValidationError('English (en) is the base language and cannot be edited.')
        attrs['qid'] = qid
        attrs['lang'] = lang
        return attrs

class OauthBeginSerializer(serializers.Serializer):
    authorization_url = serializers.URLField()
    state = serializers.CharField()

class OauthStatusSerializer(serializers.Serializer):
    connected = serializers.BooleanField()
    username = serializers.CharField(allow_null=True, required=False)

class OauthDisconnectSerializer(serializers.Serializer):
    status = serializers.CharField()