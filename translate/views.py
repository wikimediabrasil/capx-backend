import os
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import login_required as django_login_required
from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib import messages
from django.urls import reverse
from django.views.decorators.http import require_GET
from requests_oauthlib import OAuth1Session
from .models import MetabaseOAuthToken, MetabaseOAuthRequest
from social_django.utils import load_strategy, load_backend
from users.models import AuthExtraInfo

INDEX_URL_NAME = 'translate:index'

# A login-required decorator that ignores settings.LOGIN_URL and always
# redirects to the translate login page.

def translate_login_required(view_func=None, *, redirect_field_name: str = REDIRECT_FIELD_NAME):
    decorator = django_login_required(
        redirect_field_name=redirect_field_name,
        login_url='/translate/login/'
    )
    return decorator(view_func) if view_func else decorator


@require_GET
@translate_login_required
def index(request):
    connected = False
    mb_username = None
    if request.user.is_authenticated:
        tok = getattr(request.user, 'metabase_oauth', None)
        if tok:
            connected, mb_username = True, tok.mb_username
    return render(request, 'translate/index.html', {
        'user': request.user,
        'metabase_connected': connected,
        'metabase_username': mb_username,
    })


@require_GET
def login_view(request):
    if request.user.is_authenticated:
        return redirect(INDEX_URL_NAME)
    oauth_begin_url = reverse('translate:oauth_begin')
    return render(request, 'translate/login.html', {'social_login_url': oauth_begin_url})


@require_GET
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('translate:login')


@require_GET
def oauth_begin(request):
    """Start MediaWiki OAuth using social_django for translate area."""
    strategy = load_strategy(request)
    translate_return_path = reverse(INDEX_URL_NAME)
    strategy.session_set('next', translate_return_path)
    backend = load_backend(strategy, 'mediawiki', redirect_uri=None)
    response = backend.start()

    oauth_url = getattr(response, 'url', None)
    oauth_token = oauth_url.split('oauth_token=')[1].split('&')[0] if oauth_url and 'oauth_token=' in oauth_url else None
    if oauth_token:
        callback_path = request.build_absolute_uri(reverse('translate:mw_oauth_callback')).split("://", 1)[-1].rstrip('/')
        AuthExtraInfo.objects.update_or_create(
            token=oauth_token,
            defaults={'extra': callback_path}
        )
    return response


@require_GET
def oauth_callback(request):
    # Dedicated Metabase callback only now.
    return metabase_oauth_callback(request)


@require_GET
def mw_oauth_callback(request):
    """MediaWiki (social_django) OAuth callback separated to avoid collision with Metabase."""
    complete_url = reverse('social:complete', kwargs={'backend': 'mediawiki'})
    qs = request.META.get('QUERY_STRING')
    if qs:
        complete_url = f"{complete_url}?{qs}"
    return redirect(complete_url)


# --- Metabase OAuth (per-user) ---

REQUEST_TOKEN_URL = 'https://metabase.wikibase.cloud/w/index.php?title=Special:OAuth/initiate'
AUTHORIZE_URL = 'https://metabase.wikibase.cloud/w/index.php?title=Special:OAuth/authorize'
ACCESS_TOKEN_URL = 'https://metabase.wikibase.cloud/w/index.php?title=Special:OAuth/token'
METABASE_API_ENDPOINT = 'https://metabase.wikibase.cloud/w/api.php'


@translate_login_required
def metabase_oauth_begin(request):    
    consumer_key = os.environ.get('METABASE_OAUTH_CONSUMER_KEY')
    consumer_secret = os.environ.get('METABASE_OAUTH_CONSUMER_SECRET')
    if not consumer_key or not consumer_secret:
        messages.error(request, 'Metabase OAuth is not configured. Missing consumer credentials.')
        return redirect(INDEX_URL_NAME)
    callback_uri = "oob"
    oauth = OAuth1Session(client_key=consumer_key, client_secret=consumer_secret, callback_uri=callback_uri)
    try:
        fetch_response = oauth.fetch_request_token(REQUEST_TOKEN_URL)
    except Exception as e:
        messages.error(request, f'Failed to start Metabase OAuth: {e}')
        return redirect(INDEX_URL_NAME)
    request.session['mb_oauth_req_secret'] = fetch_response.get('oauth_token_secret')
    authorization_url = oauth.authorization_url(AUTHORIZE_URL)
    return redirect(authorization_url)


def metabase_oauth_authorize_state(request, state):
    consumer_key = os.environ.get('METABASE_OAUTH_CONSUMER_KEY')
    consumer_secret = os.environ.get('METABASE_OAUTH_CONSUMER_SECRET')
    if not consumer_key or not consumer_secret:
        messages.error(request, 'Metabase OAuth is not configured. Missing consumer credentials.')
        return redirect(INDEX_URL_NAME)
    try:
        oreq = MetabaseOAuthRequest.objects.get(state=state, consumed=False)
    except MetabaseOAuthRequest.DoesNotExist:
        messages.error(request, 'Invalid or expired OAuth request state.')
        return redirect(INDEX_URL_NAME)
    callback_uri = request.build_absolute_uri(reverse('translate:oauth_callback'))
    oauth = OAuth1Session(
        client_key=consumer_key,
        client_secret=consumer_secret,
        resource_owner_key=oreq.request_token,
        resource_owner_secret=oreq.request_secret,
        callback_uri=callback_uri,
    )
    authorization_url = oauth.authorization_url(AUTHORIZE_URL)
    request.session['mb_oauth_popup'] = True
    return redirect(authorization_url)


def metabase_oauth_callback(request):
    # Verify consumer credentials
    consumer_key = os.environ.get('METABASE_OAUTH_CONSUMER_KEY')
    consumer_secret = os.environ.get('METABASE_OAUTH_CONSUMER_SECRET')
    if not consumer_key or not consumer_secret:
        messages.error(request, 'Metabase OAuth is not configured. Missing consumer credentials.')
        request.session.pop('mb_oauth_req_secret', None)
        return redirect(INDEX_URL_NAME)

    # Extract OAuth parameters
    oauth_token = request.GET.get('oauth_token')
    oauth_verifier = request.GET.get('oauth_verifier')
    if not oauth_token or not oauth_verifier:
        messages.error(request, 'Invalid Metabase OAuth callback parameters.')
        return redirect(INDEX_URL_NAME)

    # Retrieve request secret from DB
    try:
        oreq = MetabaseOAuthRequest.objects.get(request_token=oauth_token, consumed=False)
        request_secret = oreq.request_secret
    except MetabaseOAuthRequest.DoesNotExist:
        # Fall back to session-stored secret for non-DB flow
        if request.session.get('mb_oauth_req_secret'):
            request_secret = request.session.get('mb_oauth_req_secret')
            oreq = None
        else:
            # Unknown request token
            messages.error(request, 'Unknown or consumed OAuth request token.')
            return redirect(INDEX_URL_NAME)

    # Exchange request token for access token
    oauth = OAuth1Session(
        client_key=consumer_key,
        client_secret=consumer_secret,
        resource_owner_key=oauth_token,
        resource_owner_secret=request_secret,
        verifier=oauth_verifier,
    )

    try:
        # Fetch access token
        tokens = oauth.fetch_access_token(ACCESS_TOKEN_URL)
        access_token = tokens.get('oauth_token')
        access_secret = tokens.get('oauth_token_secret')

        # Retrieve Metabase username
        r = oauth.get(METABASE_API_ENDPOINT, params={'action': 'query', 'meta': 'userinfo', 'format': 'json'}, timeout=30)
        r.raise_for_status()
        mb_username = (r.json().get('query', {}).get('userinfo', {}) or {}).get('name')
        
        # Store tokens
        MetabaseOAuthToken.objects.update_or_create(
            user=oreq.user if oreq else request.user,
            defaults={'access_token': access_token, 'access_secret': access_secret, 'mb_username': mb_username or ''}
        )

        # Mark request as consumed
        if oreq:
            oreq.consumed = True
            oreq.save(update_fields=['consumed'])
            return render(request, 'translate/oauth_done.html', {'mb_username': mb_username})
        else: 
            if request.session.get('mb_oauth_popup'):
                request.session.pop('mb_oauth_popup', None)
            return redirect(INDEX_URL_NAME)
    finally:
        # Database-backed flow does not require session cleanup.
        # Old request rows are cleaned opportunistically in begin endpoint.
        pass  # intentional no-op


@translate_login_required
def metabase_oauth_disconnect(request):
    tok = MetabaseOAuthToken.objects.filter(user=request.user)
    if tok.exists():
        tok.delete()
        messages.success(request, 'Disconnected Metabase account.')
    else:
        messages.info(request, 'No Metabase connection found.')
    return redirect(INDEX_URL_NAME)
