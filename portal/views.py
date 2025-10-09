from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib import messages
from django.http import HttpResponseForbidden
from orgs.models import Organization, Management
from events.models import Events
from django.urls import reverse
from django.conf import settings
from .models import PortalUser
from social_django.utils import load_strategy, load_backend
from users.submodels import AuthExtraInfo
from django.views.decorators.http import require_GET, require_POST
from users.models import CustomUser, Profile
from knox.models import AuthToken

DASHBOARD_URL_NAME = 'portal:dashboard'

def is_portal_user(user):
    if not user.is_authenticated:
        return False
    return PortalUser.objects.filter(user=user, is_authorized=True).exists()


def is_portal_admin(user):
    # Use the CustomUser.is_staff flag as requested
    return user.is_authenticated and getattr(user, 'is_staff', False)


def require_portal_access(view_func):
    def _wrapped(request, *args, **kwargs):
        if not (is_portal_user(request.user) or is_portal_admin(request.user)):
            return HttpResponseForbidden("You don't have access to this portal.")
        return view_func(request, *args, **kwargs)
    return login_required(_wrapped)


@require_GET
def login_view(request):
    if request.user.is_authenticated:
        if is_portal_user(request.user) or is_portal_admin(request.user):
            return redirect(DASHBOARD_URL_NAME)
        # Show login page with info but without auto-redirecting
        messages.error(request, "Your account is not authorized for the portal yet. Please contact an administrator.")
    # Use our wrapper that also writes AuthExtraInfo; keep template variable name
    oauth_begin_url = reverse('portal:oauth_begin')
    return render(request, 'portal/login.html', {'social_login_url': oauth_begin_url})


@require_GET
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('portal:login')


@require_GET
@require_portal_access
def dashboard(request):
    # Show orgs the user manages and recent events for those orgs
    orgs = Organization.objects.filter(managers=request.user).distinct()
    events = Events.objects.filter(organization__in=orgs).order_by('-time_begin')[:50]

    # Build users table for all portal users
    # Prefetch affiliations to avoid N+1 queries
    all_users = (
        CustomUser.objects.all()
        .order_by('username')
        .prefetch_related('profile__affiliation')
    )

    # Precompute manager user ids
    manager_user_ids = set(Management.objects.values_list('user_id', flat=True))

    users_table = []
    for u in all_users:
        # Determine role: Staff > Manager > User
        if getattr(u, 'is_staff', False):
            role = 'Staff'
        elif u.id in manager_user_ids:
            role = 'Manager'
        else:
            role = 'User'

        # Affiliation names
        affiliations = []
        if hasattr(u, 'profile') and u.profile:
            affiliations = [org.display_name for org in u.profile.affiliation.all()]

        # Get last login from AuthToken
        last_token = AuthToken.objects.filter(user=u).order_by('-created').first()
        last_login = last_token.created if last_token else None

        users_table.append({
            'username': u.username,
            'role': role,
            'affiliation': ', '.join(affiliations) if affiliations else '',
            'date_joined': u.date_joined,
            'last_login': last_login,
        })
    context = {
        'user': request.user,
        'organizations': orgs,
        'events': events,
        'users_table': users_table,
    }
    return render(request, 'portal/dashboard.html', context)


@require_GET
def oauth_begin(request):
    """
    Start MediaWiki OAuth using social_django, but also create an AuthExtraInfo entry
    keyed by the request token with 'extra' set to the portal return path.
    """
    strategy = load_strategy(request)
    portal_return_path = reverse(DASHBOARD_URL_NAME)
    # Ensure post-auth redirect target
    strategy.session_set('next', portal_return_path)
    backend = load_backend(strategy, 'mediawiki', redirect_uri=None)
    response = backend.start()

    # Capture the request token from session and store mapping
    oauth_url = getattr(response, 'url', None)
    oauth_token = oauth_url.split('oauth_token=')[1].split('&')[0]  # Extract token from URL
    if oauth_token:
        portal_url = request.build_absolute_uri(portal_return_path).split("://", 1)[-1].rstrip('/')
        AuthExtraInfo.objects.update_or_create(
            token=oauth_token,
            defaults={'extra': portal_url}
        )

    return response

@require_GET
def oauth_callback(request):
    """
    Forward the provider callback to social_django's built-in completion endpoint,
    preserving the query string. This returns a proper HttpResponse and avoids
    returning a User instance directly.
    """
    complete_url = reverse('social:complete', kwargs={'backend': 'mediawiki'})
    qs = request.META.get('QUERY_STRING')
    if qs:
        complete_url = f"{complete_url}?{qs}"
    return redirect(complete_url)


def _require_portal_admin(request):
    if not is_portal_admin(request.user):
        return HttpResponseForbidden("Admin permissions are required.")
    return None


@require_POST
def portal_user_add(request):
    """Grant portal access to a user (staff only)."""
    forbidden = _require_portal_admin(request)
    if forbidden:
        return forbidden
    username = request.POST.get('username', '').strip()
    if not username:
        messages.error(request, 'Username is required.')
        return redirect(DASHBOARD_URL_NAME)
    try:
        target = CustomUser.all_objects.get(username=username)
    except CustomUser.DoesNotExist:
        messages.error(request, f'User "{username}" not found.')
        return redirect(DASHBOARD_URL_NAME)

    PortalUser.objects.update_or_create(
        user=target,
        defaults={'authorizer': request.user, 'is_authorized': True}
    )
    messages.success(request, f'Portal access granted to {target.username}.')
    return redirect(DASHBOARD_URL_NAME)


@require_POST
def portal_user_remove(request):
    """Revoke portal access from a user (staff only)."""
    forbidden = _require_portal_admin(request)
    if forbidden:
        return forbidden
    username = request.POST.get('username', '').strip()
    if not username:
        messages.error(request, 'Username is required.')
        return redirect(DASHBOARD_URL_NAME)
    try:
        target = CustomUser.all_objects.get(username=username)
    except CustomUser.DoesNotExist:
        messages.error(request, f'User "{username}" not found.')
        return redirect(DASHBOARD_URL_NAME)

    PortalUser.objects.update_or_create(
        user=target,
        defaults={'authorizer': request.user, 'is_authorized': False}
    )
    messages.success(request, f'Portal access revoked for {target.username}.')
    return redirect(DASHBOARD_URL_NAME)