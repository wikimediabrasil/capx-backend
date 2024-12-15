from rest_social_auth.views import SocialKnoxUserAuthView, SocialKnoxOnlyAuthView
from rest_framework.response import Response
from datetime import timedelta
from django.utils.timezone import now
from drf_spectacular.utils import extend_schema
from .submodels import AuthExtraInfo
    

class AuthView(SocialKnoxOnlyAuthView):
    request = {
        'type': 'object',
        'properties': {
            'provider': {
                'type': 'string', 
                'enum': ['mediawiki'],
                'required': True,
                'description': 'The provider of the OAuth token. This can be only "mediawiki".'
            },
            'extra': {'type': 'string', 'description': 'Extra information to store with the token'},
        },
    }

    @extend_schema(
        summary='Retrieve OAuth token',
        description='This endpoint is used to retrieve the OAuth token for the user. The token is used to authenticate the user in the future.',
        request={
            ('application/json'): request,
            ('application/x-www-form-urlencoded'): request,
            ('multipart/form-data'): request,
        },
        responses={(200, 'application/json'): {
            'description': 'OAuth token retrieved successfully',
            'type': 'object',
            'properties': {
                'oauth_token': {'type': 'string', 'description': 'The OAuth token'},
                'oauth_token_secret': {'type': 'string', 'description': 'The OAuth token secret'},
                'oauth_callback_confirmed': {'type': 'string', 'description': 'Whether the OAuth callback is confirmed or not'}
            }
        }}
    )
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        AuthExtraInfo.objects.filter(created_at__lt=now() - timedelta(minutes=5)).delete()
        if request.data.get('extra'):
            AuthExtraInfo.objects.create(
                token=response.data['oauth_token'],
                extra=request.data['extra']
            )
        return response


class UserAuthView(SocialKnoxUserAuthView):
    @extend_schema(
        summary='Authenticate user using OAuth token',
        description='This endpoint is used to authenticate the user using the OAuth token verifier. The OAuth token verifier is obtained from the OAuth provider.',
        responses={(200, 'application/json'): {
            'description': 'User authenticated successfully',
            'type': 'object',
            'properties': {
                'id': {'type': 'integer', 'description': 'The user ID in the database'},
                'token': {'type': 'string', 'description': 'The authorization token for use in the HTTP headers for future API requests'},
                'username': {'type': 'string', 'description': 'The MediaWiki username'},
                'email': {'type': 'string', 'description': 'The email address (should be empty for MediaWiki)'},
                'user_groups': {'type': 'array', 'description': 'The user groups (should be null for MediaWiki)'},
                'extra': {'type': 'string', 'description': 'Extra information stored with the token'}
            }
        }}
    )
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if not isinstance(response, Response):
            return response

        token = request.data['oauth_token']
        if AuthExtraInfo.objects.filter(token=token).exists():
            response.data['extra'] = AuthExtraInfo.objects.get(token=token).extra
        return response
