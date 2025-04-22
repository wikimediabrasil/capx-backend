from rest_social_auth.views import SocialKnoxUserAuthView, SocialKnoxOnlyAuthView
from rest_framework.response import Response
from rest_framework import status
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
    request = {
        'type': 'object',
        'properties': {
            'oauth_token': {
                'type': 'string',
                'required': True,
                'description': 'The OAuth token'
            },
            'oauth_token_secret': {
                'type': 'string',
                'required': True,
                'description': 'The OAuth token secret'
            },
            'oauth_verifier': {
                'type': 'string',
                'required': True,
                'description': 'The OAuth verifier'
            }
        }
    }

    @extend_schema(
        summary='Authenticate user using OAuth token',
        description='This endpoint is used to authenticate the user using the OAuth token verifier. The OAuth token verifier is obtained from the OAuth provider.',
        request={
            ('application/json'): request,
            ('application/x-www-form-urlencoded'): request,
            ('multipart/form-data'): request,
        },
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
        token = request.data['oauth_token']
        if AuthExtraInfo.objects.filter(token=token).exists():
            if isinstance(response.data, dict):
                response.data['extra'] = AuthExtraInfo.objects.get(token=token).extra
        return response

class CheckView(SocialKnoxOnlyAuthView):
    request = {
        'type': 'object',
        'properties': {
            'oauth_token': {
                'type': 'string',
                'required': True,
                'description': 'The OAuth token to check'
            }
        },
    }
    @extend_schema(
        summary='Check if the OAuth token exists and has extra information',
        description='This endpoint is used to check if the OAuth token exists and has extra information stored with it.',
        request={
            ('application/json'): request,
            ('application/x-www-form-urlencoded'): request,
            ('multipart/form-data'): request,
        },
        responses={(200, 'application/json'): {
            'description': 'OAuth token checked successfully',
            'type': 'object',
            'properties': {
                'exists': {'type': 'boolean', 'description': 'Whether the OAuth token exists or not'},
                'extra': {'type': 'string', 'description': 'The extra information stored with the token'}
            }
        }}
    )
    def post(self, request, *args, **kwargs):
        token = request.data.get('oauth_token')
        if not token:
            return Response({'error': 'oauth_token is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        exists = AuthExtraInfo.objects.filter(token=token).exists()
        extra = AuthExtraInfo.objects.get(token=token).extra if exists else None
        return Response({'exists': exists, 'extra': extra})