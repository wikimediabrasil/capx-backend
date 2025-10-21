from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import login_required as django_login_required
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
from users.models import CustomUser, Profile, UserBadge
from knox.models import AuthToken
import requests

DASHBOARD_URL_NAME = 'portal:dashboard'

# A login-required decorator that ignores settings.LOGIN_URL and always
# redirects to the portal login page.
def portal_login_required(view_func=None, *, redirect_field_name: str = REDIRECT_FIELD_NAME):
    decorator = django_login_required(
        redirect_field_name=redirect_field_name,
        login_url='/portal/login/'
    )
    # Support being used with and without parentheses
    return decorator(view_func) if view_func else decorator

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
    return portal_login_required(_wrapped)


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

    # Build users table to reflect ProfileSerializer/model fields used by the template
    profiles = (
        Profile.objects.select_related('user')
        .prefetch_related(
            'affiliation',
            'territory',
            'wikimedia_project',
            'skills_known',
            'skills_available',
            'skills_wanted',
            'languageproficiency_set__language',
        )
        .order_by('user__username')
    )

    # Resolve Wikidata QIDs to English labels using Metabase SPARQL
    def fetch_qid_labels(qids):
        qids = [q for q in qids if q]
        if not qids:
            return {}
        try:
            values = ' '.join(f'"{q}"' for q in sorted(set(qids)))
            query = (
                """
                PREFIX wbt: <https://metabase.wikibase.cloud/prop/direct/>
                SELECT ?item ?itemLabel ?itemDescription ?value WHERE {
                    VALUES ?value { %s }
                    ?item wbt:P1 ?value.
                    SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
                }
                """ % values
            )
            resp = requests.get(
                'https://metabase.wikibase.cloud/query/sparql',
                params={'query': query, 'format': 'json'},
                headers={'User-Agent': 'CapX-Portal/1.0'}
            )
            data = resp.json()
            mapping = {}
            for row in data.get('results', {}).get('bindings', []):
                val = row.get('value', {}).get('value')
                label = row.get('itemLabel', {}).get('value')
                if val and label:
                    mapping[val] = label
            return mapping
        except Exception:
            return {}

    qid_labels = fetch_qid_labels(list(profiles.values_list('wikidata_qid', flat=True)))

    # Collect all skill QIDs across profiles and resolve labels
    skill_qids = set()
    for p in profiles:
        for s in p.skills_known.all():
            if s.skill_wikidata_item:
                skill_qids.add(s.skill_wikidata_item)
        for s in p.skills_available.all():
            if s.skill_wikidata_item:
                skill_qids.add(s.skill_wikidata_item)
        for s in p.skills_wanted.all():
            if s.skill_wikidata_item:
                skill_qids.add(s.skill_wikidata_item)
    skill_labels = fetch_qid_labels(list(skill_qids))

    # Prepare manager organization per user to avoid N+1
    managers_map = {}
    for uid, oname in Management.objects.select_related('organization').values_list('user_id', 'organization__display_name'):
        managers_map.setdefault(uid, []).append(oname)

    # Prepare displayed badges per user
    user_ids = list(profiles.values_list('user_id', flat=True))
    badges_map = {}
    for uid, bname in UserBadge.objects.select_related('badge').filter(user_id__in=user_ids, is_displayed=True, progress=100).values_list('user_id', 'badge__name'):
        badges_map.setdefault(uid, []).append(bname)

    users_table = []
    for p in profiles:
        u = p.user

        # Last login via Knox token
        last_token = AuthToken.objects.filter(user=u).order_by('-created').first()
        last_login = last_token.created if last_token else None

        # String representations for multi-relations
        aff_str = ', '.join([org.display_name for org in p.affiliation.all()]) if p.affiliation.exists() else ''
        terr_str = ', '.join([t.territory_name for t in p.territory.all()]) if p.territory.exists() else ''
        proj_str = ', '.join([wp.wikimedia_project_name for wp in p.wikimedia_project.all()]) if p.wikimedia_project.exists() else ''
        skills_known_str = ', '.join([skill_labels.get(s.skill_wikidata_item, s.skill_wikidata_item) for s in p.skills_known.all()]) if p.skills_known.exists() else ''
        skills_available_str = ', '.join([skill_labels.get(s.skill_wikidata_item, s.skill_wikidata_item) for s in p.skills_available.all()]) if p.skills_available.exists() else ''
        skills_wanted_str = ', '.join([skill_labels.get(s.skill_wikidata_item, s.skill_wikidata_item) for s in p.skills_wanted.all()]) if p.skills_wanted.exists() else ''

        # Languages (name + proficiency)
        languages = [
            {'name': getattr(lp.language, 'language_name', None) or str(lp.language), 'proficiency': lp.proficiency or '-'}
            for lp in p.languageproficiency_set.all()
        ]

        users_table.append({
            # Top-level user fields
            'username': u.username,
            'is_staff': u.is_staff,
            'is_active': u.is_active,
            'date_joined': u.date_joined,
            'last_login': last_login,
            'last_update': p.last_update,
            'wikidata_qid': p.wikidata_qid,
            'wikidata_label': qid_labels.get(p.wikidata_qid),
            'wiki_alt': p.wiki_alt,
            'territory': terr_str,
            'language': languages,
            'affiliation': aff_str,
            'wikimedia_project': proj_str,
            'team': p.team,
            'skills_known': skills_known_str,
            'skills_available': skills_available_str,
            'skills_wanted': skills_wanted_str,
            'is_manager': managers_map.get(u.id, []),
            'badges': badges_map.get(u.id, []),
            'automated_lets_connect': p.automated_lets_connect,
        })
    # List of PortalUser records (for admins to manage access)
    portal_users = PortalUser.objects.select_related('user', 'authorizer').order_by('user__username')

    context = {
        'user': request.user,
        'organizations': orgs,
        'events': events,
        'users_table': users_table,
        'portal_users': portal_users,
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


@require_POST
def portal_user_update_notes(request):
    """Update notes for a portal user (staff only)."""
    forbidden = _require_portal_admin(request)
    if forbidden:
        return forbidden
    username = request.POST.get('username', '').strip()
    notes = request.POST.get('notes', '').strip()
    if not username:
        messages.error(request, 'Username is required.')
        return redirect(DASHBOARD_URL_NAME)
    try:
        target = CustomUser.all_objects.get(username=username)
    except CustomUser.DoesNotExist:
        messages.error(request, f'User "{username}" not found.')
        return redirect(DASHBOARD_URL_NAME)

    pu, _ = PortalUser.objects.get_or_create(user=target, defaults={'authorizer': request.user, 'is_authorized': True})
    pu.notes = notes or None
    pu.save(update_fields=['notes', 'updated_at'])
    messages.success(request, f'Notes updated for {target.username}.')
    return redirect(DASHBOARD_URL_NAME)