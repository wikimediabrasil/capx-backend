from datetime import timedelta

from django.conf import settings
from django.http import HttpResponse
from django.utils.timezone import now
from social_core.exceptions import AuthException, SocialAuthBaseException
from drf_spectacular.utils import extend_schema
from knox.models import AuthToken
from requests.exceptions import HTTPError
from rest_framework import serializers, status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from users.auth.oauth_service import (
    authenticate_social_user,
    cache_oauth_secret,
    get_oauth1_request_token,
    get_provider_name,
    normalize_input_data,
    oauth_v1,
    set_input_data,
)
from users.auth.strategy import decorate_request
from users.models import CustomUser
from users.models import AuthExtraInfo


VERBOSE_ERRORS = getattr(settings, 'REST_SOCIAL_VERBOSE_ERRORS', False)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        exclude = [
            field for field in (
                'is_staff', 'is_active', 'date_joined', 'password', 'last_login',
                'user_permissions', 'groups', 'is_superuser',
            ) if field in [model_field.name for model_field in CustomUser._meta.get_fields()]
        ]


class LocalSocialAuthView(GenericAPIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()

    def respond_error(self, error):
        message = str(error) if isinstance(error, (str, Exception)) else ''
        if not VERBOSE_ERRORS and isinstance(error, SocialAuthBaseException):
            message = str(error)
        return Response(data=message, status=status.HTTP_400_BAD_REQUEST)

    def render_auth_response(self, user):
        token_instance, token_key = AuthToken.objects.create(user)
        del token_instance
        return {
            **UserSerializer(user).data,
            'token': token_key,
        }

    def post(self, request, *args, **kwargs):
        input_data = normalize_input_data(request.data.copy())
        provider_name = get_provider_name(self.kwargs, input_data)
        if not provider_name:
            return self.respond_error('Provider is not specified')

        set_input_data(request, input_data)
        decorate_request(request, provider_name)

        if oauth_v1(request) and request.backend.OAUTH_TOKEN_PARAMETER_NAME not in input_data:
            request_token = get_oauth1_request_token(request)
            return Response(request_token)

        try:
            user = authenticate_social_user(request)
        except (AuthException, HTTPError) as error:
            return self.respond_error(error)

        if isinstance(user, HttpResponse):
            return user

        return Response(self.render_auth_response(user))


class AuthView(LocalSocialAuthView):
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
        if request.data.get('extra') and isinstance(response.data, dict) and response.status_code == status.HTTP_200_OK and 'oauth_token' in response.data:
            AuthExtraInfo.objects.create(
                token=response.data['oauth_token'],
                extra=request.data['extra']
            )
        if isinstance(response.data, dict) and response.status_code == status.HTTP_200_OK:
            oauth_token = response.data.get('oauth_token')
            oauth_token_secret = response.data.get('oauth_token_secret')
            cache_oauth_secret(oauth_token, oauth_token_secret)
        return response


class UserAuthView(LocalSocialAuthView):
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
        token = request.data.get('oauth_token')
        if token and AuthExtraInfo.objects.filter(token=token).exists():
            if isinstance(response.data, dict):
                response.data['extra'] = AuthExtraInfo.objects.get(token=token).extra
        return response

class CheckView(LocalSocialAuthView):
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