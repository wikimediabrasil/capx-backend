from urllib.parse import urlencode, urljoin, urlparse
import time

from django.conf import settings
from django.core.cache import cache
from django.utils.encoding import iri_to_uri
from social_core.backends.oauth import BaseOAuth1
from social_core.exceptions import AuthException
from social_core.utils import parse_qs


DOMAIN_FROM_ORIGIN = getattr(settings, 'REST_SOCIAL_DOMAIN_FROM_ORIGIN', True)


def oauth_v1(request):
    return isinstance(request.backend, BaseOAuth1)


def get_provider_name(kwargs, input_data):
    if kwargs.get('provider'):
        return kwargs['provider']
    return input_data.get('provider')


def set_input_data(request, auth_data):
    request.auth_data = auth_data


def get_redirect_uri(manual_redirect_uri):
    if not manual_redirect_uri:
        return getattr(settings, 'REST_SOCIAL_OAUTH_ABSOLUTE_REDIRECT_URI', None)
    return manual_redirect_uri


def normalize_input_data(input_data):
    normalized_data = input_data.copy()
    if 'oauth_secret' in normalized_data and 'oauth_token_secret' not in normalized_data:
        normalized_data['oauth_token_secret'] = normalized_data.get('oauth_secret')

    for key in ('oauth_token', 'oauth_token_secret', 'oauth_verifier'):
        value = normalized_data.get(key)
        if isinstance(value, list) and value:
            value = value[0]
        if isinstance(value, str):
            value = value.strip()
            if ' ' in value and '+' not in value:
                value = value.replace(' ', '+')
            normalized_data[key] = value
    return normalized_data


def apply_redirect_uri(request):
    manual_redirect_uri = request.auth_data.pop('redirect_uri', None)
    manual_redirect_uri = get_redirect_uri(manual_redirect_uri)
    if manual_redirect_uri:
        request.backend.redirect_uri = manual_redirect_uri
        return

    if DOMAIN_FROM_ORIGIN:
        origin = request.strategy.request.META.get('HTTP_ORIGIN')
        if origin:
            relative_path = urlparse(request.backend.redirect_uri).path
            url = urlparse(origin)
            origin_scheme_host = f"{url.scheme}://{url.netloc}"
            location = urljoin(origin_scheme_host, relative_path)
            request.backend.redirect_uri = iri_to_uri(location)


def get_cached_oauth_secret(oauth_token, oauth_token_secret):
    if not oauth_token:
        return oauth_token_secret

    cached_secret_payload = cache.get(f'oauth1_secret:{oauth_token}')
    if isinstance(cached_secret_payload, dict):
        cached_oauth_token_secret = cached_secret_payload.get('secret')
        if isinstance(cached_oauth_token_secret, str) and cached_oauth_token_secret:
            return cached_oauth_token_secret
    elif isinstance(cached_secret_payload, str) and cached_secret_payload:
        return cached_secret_payload

    return oauth_token_secret


def store_unauthorized_token_in_session(request, oauth_token, oauth_token_secret):
    backend = request.backend
    session_token_name = backend.name + backend.UNATHORIZED_TOKEN_SUFIX
    serialized_token = urlencode({
        backend.OAUTH_TOKEN_PARAMETER_NAME: oauth_token,
        'oauth_token_secret': oauth_token_secret,
    })

    strategy = getattr(request, 'strategy', None) or getattr(backend, 'strategy', None)
    if strategy is None:
        return

    existing_tokens = strategy.session_get(session_token_name, [])
    updated_tokens = [serialized_token, *[token for token in existing_tokens if token != serialized_token]]
    strategy.session_set(session_token_name, updated_tokens)


def save_token_param_in_session(request):
    backend = request.backend
    oauth1_token_param = request.auth_data.get(backend.OAUTH_TOKEN_PARAMETER_NAME)
    oauth_token_secret = request.auth_data.get('oauth_token_secret')
    if oauth1_token_param:
        store_unauthorized_token_in_session(request, oauth1_token_param, oauth_token_secret)


def get_oauth1_request_token(request):
    manual_redirect_uri = request.auth_data.pop('redirect_uri', None)
    manual_redirect_uri = get_redirect_uri(manual_redirect_uri)
    if manual_redirect_uri:
        request.backend.redirect_uri = manual_redirect_uri
    return parse_qs(request.backend.set_unauthorized_token())


def authenticate_social_user(request):
    apply_redirect_uri(request)

    request.backend.REDIRECT_STATE = False
    request.backend.STATE_PARAMETER = False

    oauth_token = request.auth_data.get('oauth_token')
    oauth_token_secret = get_cached_oauth_secret(
        oauth_token,
        request.auth_data.get('oauth_token_secret'),
    )

    if oauth_v1(request) and oauth_token:
        token = {
            'oauth_token': oauth_token,
            'oauth_token_secret': oauth_token_secret,
        }
        try:
            access_token = request.backend.access_token(token)
            return request.backend.do_auth(access_token, user=None)
        except AuthException as direct_error:
            if 'verification code provided was not valid' in str(direct_error).lower():
                store_unauthorized_token_in_session(request, oauth_token, oauth_token_secret)
                return request.backend.complete(user=None, request=request)
            raise

    if oauth_v1(request):
        save_token_param_in_session(request)

    return request.backend.complete(user=None, request=request)


def cache_oauth_secret(oauth_token, oauth_token_secret):
    if isinstance(oauth_token, str) and isinstance(oauth_token_secret, str):
        cache.set(
            f'oauth1_secret:{oauth_token}',
            {
                'secret': oauth_token_secret,
                'created_at': time.time(),
            },
            timeout=1800,
        )
