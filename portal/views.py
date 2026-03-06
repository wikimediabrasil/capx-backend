from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import login_required as django_login_required
from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib import messages
from django.http import HttpResponseForbidden, HttpResponse
from orgs.models import Organization, Management
from events.models import Events
from django.urls import reverse
from django.conf import settings
from django.core.mail import send_mail
from .models import (
    Partner,
    PartnerMembership,
    PartnerMentorshipPublicKey,
    PartnerMentorshipFormMentor,
    PartnerMentorshipFormMentee,
    PartnerMentorshipFormMentorResponse,
    PartnerMentorshipFormMenteeResponse,
)
from social_django.utils import load_strategy, load_backend
from users.models import AuthExtraInfo
from CapX.useragent import get_user_agent
from django.views.decorators.http import require_GET, require_POST
from users.models import CustomUser, Profile, UserBadge, Badge
from knox.models import AuthToken
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import json
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
    # Any user who belongs to at least one partner has portal access
    return PartnerMembership.objects.filter(user=user).exists()

def is_portal_admin(user):
    # Use the CustomUser.is_staff flag as requested
    return getattr(user, 'is_staff', False)

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
            'affiliation__i18n_names',
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
                headers={'User-Agent': get_user_agent('Portal')}
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
    for uid, oname in Management.objects.select_related('organization').filter(organization__i18n_names__language_code='en').values_list('user_id', 'organization__i18n_names__name'):
        managers_map.setdefault(uid, []).append(oname)

    # Prepare displayed badges per user
    user_ids = list(profiles.values_list('user_id', flat=True))
    badges_map = {}
    for uid, bname in UserBadge.objects.select_related('badge').filter(user_id__in=user_ids, is_displayed=True, progress=100).values_list('user_id', 'badge__name'):
        badges_map.setdefault(uid, []).append(bname)

    def _org_en_name(org: Organization):
        # Find pre-fetched English name without additional queries
        for n in getattr(org, 'i18n_names_all', None) or org.i18n_names.all():
            if n.language_code == 'en':
                return n.name
        # Fallback: try filtering (should be cached by prefetch)
        en = org.i18n_names.filter(language_code='en').first()
        return en.name if en else f"Organization {org.pk}"

    users_table = []
    for p in profiles:
        u = p.user

        # Last login via Knox token
        last_token = AuthToken.objects.filter(user=u).order_by('-created').first()
        last_login = last_token.created if last_token else None

        # String representations for multi-relations
        aff_str = ', '.join([_org_en_name(org) for org in p.affiliation.all()]) if p.affiliation.exists() else ''
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
    # Determine partners current user belongs to (for scoping)
    user_partners = Partner.objects.filter(memberships__user=request.user).distinct()
    # Partner badges available for assignment in portal, scoped by membership unless staff
    if is_portal_admin(request.user):
        partner_badges = Badge.objects.filter(type='partner').order_by('name')
        partners_for_ui = (
            Partner.objects
            .select_related('organization')
            .filter(organization__i18n_names__language_code='en')
            .order_by('organization__i18n_names__name')
            .distinct()
        )
        partner_members = (
            PartnerMembership.objects
            .select_related('partner__organization', 'user')
            .filter(partner__organization__i18n_names__language_code='en')
            .order_by('partner__organization__i18n_names__name', 'user__username')
            .distinct()
        )
        partner_org_candidates = (
            Organization.objects
            .exclude(id__in=Partner.objects.values_list('organization_id', flat=True))
            .filter(i18n_names__language_code='en')
            .order_by('i18n_names__name')
            .distinct()
        )
    else:
        partner_badges = Badge.objects.filter(
            type='partner',
            logic__partner__in=user_partners.values_list('organization_id', flat=True)
        ).order_by('name')
        partners_for_ui = (
            user_partners
            .select_related('organization')
            .filter(organization__i18n_names__language_code='en')
            .order_by('organization__i18n_names__name')
            .distinct()
        )
        partner_members = (
            PartnerMembership.objects
            .filter(user=request.user, partner__in=partners_for_ui, partner__organization__i18n_names__language_code='en')
            .select_related('partner__organization')
            .order_by('partner__organization__i18n_names__name', 'user__username')
            .distinct()
        )
        partner_org_candidates = Organization.objects.none()

    # Attach partner_name to each partner badge, using organization id stored in logic['partner']
    try:
        pids = list({(b.logic or {}).get('partner') for b in partner_badges if (b.logic or {}).get('partner')})
    except Exception:
        pids = []
    if pids:
        name_map = dict(
            Partner.objects
            .filter(organization_id__in=pids)
            .filter(organization__i18n_names__language_code='en')
            .select_related('organization')
            .values_list('organization_id', 'organization__i18n_names__name')
        )
    else:
        name_map = {}
    for b in partner_badges:
        pid = (b.logic or {}).get('partner')
        setattr(b, 'partner_name', name_map.get(pid))

    # Build awarded users map for partner badges to power the UI list
    awarded_map = {}
    if partner_badges:
        bid_list = list(partner_badges.values_list('id', flat=True))
        qs = (
            UserBadge.objects
            .select_related('user')
            .filter(badge_id__in=bid_list)
            .order_by('user__username')
            .values_list('badge_id', 'user__username')
        )
        for bid, uname in qs:
            awarded_map.setdefault(bid, []).append(uname)

    mentorship_enabled_partners = (
        partners_for_ui
        .filter(mentorship=True)
        .distinct()
        .order_by('organization__i18n_names__name')
    )
    mentorship_forms_mentor = (
        PartnerMentorshipFormMentor.objects
        .select_related('partner__organization')
        .filter(partner__in=mentorship_enabled_partners, partner__organization__i18n_names__language_code='en')
        .order_by('partner__organization__i18n_names__name', '-created_at')
        .distinct()
    )
    mentorship_forms_mentee = (
        PartnerMentorshipFormMentee.objects
        .select_related('partner__organization')
        .filter(partner__in=mentorship_enabled_partners, partner__organization__i18n_names__language_code='en')
        .order_by('partner__organization__i18n_names__name', '-created_at')
        .distinct()
    )
    mentorship_public_keys = (
        PartnerMentorshipPublicKey.objects
        .select_related('partner__organization')
        .filter(partner__in=mentorship_enabled_partners, partner__organization__i18n_names__language_code='en')
        .order_by('partner__organization__i18n_names__name', '-created_at')
        .distinct()
    )

    mentorship_mentor_responses = (
        PartnerMentorshipFormMentorResponse.objects
        .select_related('partner__organization', 'form', 'user')
        .filter(partner__in=mentorship_enabled_partners, partner__organization__i18n_names__language_code='en')
        .order_by('partner__organization__i18n_names__name', '-created_at')
        .distinct()
    )
    mentorship_mentee_responses = (
        PartnerMentorshipFormMenteeResponse.objects
        .select_related('partner__organization', 'form', 'user')
        .filter(partner__in=mentorship_enabled_partners, partner__organization__i18n_names__language_code='en')
        .order_by('partner__organization__i18n_names__name', '-created_at')
        .distinct()
    )

    mentor_forms_payload = [
        {
            'id': form.id,
            'partner_id': form.partner.organization_id,
            'partner_name': form.partner.organization.i18n_names.filter(language_code='en').first().name,
            'created_at': form.created_at.isoformat(),
            'json': form.json,
        }
        for form in mentorship_forms_mentor
    ]
    mentee_forms_payload = [
        {
            'id': form.id,
            'partner_id': form.partner.organization_id,
            'partner_name': form.partner.organization.i18n_names.filter(language_code='en').first().name,
            'created_at': form.created_at.isoformat(),
            'json': form.json,
        }
        for form in mentorship_forms_mentee
    ]

    mentor_responses_payload = [
        {
            'id': response.id,
            'partner_id': response.partner.organization_id,
            'form_id': response.form_id,
            'username': response.user.username,
            'created_at': response.created_at.isoformat(),
            'data': response.data,
        }
        for response in mentorship_mentor_responses
    ]
    mentee_responses_payload = [
        {
            'id': response.id,
            'partner_id': response.partner.organization_id,
            'form_id': response.form_id,
            'username': response.user.username,
            'created_at': response.created_at.isoformat(),
            'data': response.data,
        }
        for response in mentorship_mentee_responses
    ]

    context = {
        'user': request.user,
        'organizations': orgs,
        'events': events,
        'users_table': users_table,
        'partner_badges': partner_badges,
        'user_partners': user_partners,
        'partners_for_ui': partners_for_ui,
        'partner_members': partner_members,
        'partner_org_candidates': partner_org_candidates,
        'partner_badges_awarded': awarded_map,
        'mentorship_enabled_partners': mentorship_enabled_partners,
        'mentorship_forms_mentor': mentorship_forms_mentor,
        'mentorship_forms_mentee': mentorship_forms_mentee,
        'mentorship_public_keys': mentorship_public_keys,
        'mentorship_mentor_responses_data': mentor_responses_payload,
        'mentorship_mentee_responses_data': mentee_responses_payload,
        'mentorship_forms_mentor_data': mentor_forms_payload,
        'mentorship_forms_mentee_data': mentee_forms_payload,
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

def _require_partner_scope(request, partner: Partner):
    """Allow staff or members of the partner."""
    if is_portal_admin(request.user):
        return None
    if PartnerMembership.objects.filter(user=request.user, partner=partner).exists():
        return None
    return HttpResponseForbidden("You don't have permission for this partner.")


@require_POST
@require_portal_access
def mentorship_form_create(request):
    partner_id = request.POST.get('partner_id', '').strip()
    public_key_id = request.POST.get('public_key_id', '').strip()
    form_type = request.POST.get('form_type', '').strip().lower()
    form_json_raw = request.POST.get('form_json', '').strip()

    if not partner_id or not public_key_id or not form_type or not form_json_raw:
        messages.error(request, 'Partner, public key, form type, and JSON are required.')
        return redirect(DASHBOARD_URL_NAME)

    try:
        partner = Partner.objects.get(organization_id=partner_id)
    except Partner.DoesNotExist:
        messages.error(request, 'Partner not found.')
        return redirect(DASHBOARD_URL_NAME)

    scope_check = _require_partner_scope(request, partner)
    if scope_check:
        return scope_check

    if not partner.mentorship:
        messages.error(request, 'Mentorship is not enabled for this partner.')
        return redirect(DASHBOARD_URL_NAME)

    try:
        public_key = PartnerMentorshipPublicKey.objects.get(id=public_key_id, partner=partner)
    except PartnerMentorshipPublicKey.DoesNotExist:
        messages.error(request, 'Selected public key is invalid for this partner.')
        return redirect(DASHBOARD_URL_NAME)

    try:
        parsed_json = json.loads(form_json_raw)
    except json.JSONDecodeError:
        messages.error(request, 'Invalid JSON for the mentorship form.')
        return redirect(DASHBOARD_URL_NAME)

    if form_type == 'mentor':
        PartnerMentorshipFormMentor.objects.create(partner=partner, public_key=public_key, json=parsed_json)
    elif form_type == 'mentee':
        PartnerMentorshipFormMentee.objects.create(partner=partner, public_key=public_key, json=parsed_json)
    else:
        messages.error(request, 'Invalid form type.')
        return redirect(DASHBOARD_URL_NAME)

    messages.success(request, f'Mentorship {form_type} form saved for {partner.name}.')
    return redirect(DASHBOARD_URL_NAME)


@require_POST
@require_portal_access
def mentorship_public_key_add(request):
    partner_id = request.POST.get('partner_id', '').strip()
    public_key_text = request.POST.get('public_key', '').strip()

    if not partner_id or not public_key_text:
        messages.error(request, 'Partner and public key are required.')
        return redirect(DASHBOARD_URL_NAME)

    try:
        partner = Partner.objects.get(organization_id=partner_id)
    except Partner.DoesNotExist:
        messages.error(request, 'Partner not found.')
        return redirect(DASHBOARD_URL_NAME)

    scope_check = _require_partner_scope(request, partner)
    if scope_check:
        return scope_check

    try:
        key_obj = serialization.load_pem_public_key(public_key_text.encode('utf-8'))
    except Exception:
        messages.error(request, 'Invalid public key. Use a PEM formatted key.')
        return redirect(DASHBOARD_URL_NAME)

    if not hasattr(key_obj, 'encrypt'):
        messages.error(request, 'Only RSA public keys are supported.')
        return redirect(DASHBOARD_URL_NAME)

    PartnerMentorshipPublicKey.objects.create(partner=partner, public_key=public_key_text)
    messages.success(request, f'Public key saved for {partner.name}.')
    return redirect(DASHBOARD_URL_NAME)


@require_POST
@require_portal_access
def mentorship_public_key_generate(request):
    partner_id = request.POST.get('partner_id', '').strip()
    delivery = request.POST.get('delivery', '').strip().lower()
    email_to = request.POST.get('email_to', '').strip()

    if not partner_id:
        messages.error(request, 'Partner is required.')
        return redirect(DASHBOARD_URL_NAME)

    try:
        partner = Partner.objects.get(organization_id=partner_id)
    except Partner.DoesNotExist:
        messages.error(request, 'Partner not found.')
        return redirect(DASHBOARD_URL_NAME)

    scope_check = _require_partner_scope(request, partner)
    if scope_check:
        return scope_check

    if delivery not in {'download', 'email', 'download_email'}:
        messages.error(request, 'Invalid delivery option.')
        return redirect(DASHBOARD_URL_NAME)

    requires_email = delivery in {'email', 'download_email'}
    if requires_email and not email_to:
        messages.error(request, 'Provide an email address to send the private key.')
        return redirect(DASHBOARD_URL_NAME)

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode('utf-8')
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode('utf-8')

    key_record = PartnerMentorshipPublicKey.objects.create(partner=partner, public_key=public_pem)

    if requires_email:
        try:
            send_mail(
                subject=f'Private mentorship key for {partner.name}',
                message=(
                    f'Partner: {partner.name}\n'
                    f'Public key ID: {key_record.id}\n\n'
                    'Store this private key securely:\n\n'
                    f'{private_pem}'
                ),
                from_email=getattr(settings, 'SERVER_EMAIL', None), 
                recipient_list=[email_to],
                fail_silently=False,
            )
        except Exception:
            key_record.delete()
            messages.error(request, 'Unable to send email. Key generation was reverted to avoid orphan public keys.')
            return redirect(DASHBOARD_URL_NAME)

        if delivery == 'email':
            messages.success(request, f'Private key sent to {email_to}.')
            return redirect(DASHBOARD_URL_NAME)

        messages.success(request, f'Private key sent to {email_to}. Download will start now.')

    filename = f'mentorship-private-key-{key_record.id}.pem'
    response = HttpResponse(private_pem, content_type='application/x-pem-file')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@require_POST
def partner_create(request):
    """Create a Partner (staff only)."""
    forbidden = _require_portal_admin(request)
    if forbidden:
        return forbidden
    organization_id = request.POST.get('organization_id', '').strip()
    description = request.POST.get('description', '').strip()
    if not organization_id:
        messages.error(request, 'Organization is required.')
        return redirect(DASHBOARD_URL_NAME)

    try:
        organization = Organization.objects.get(id=organization_id)
    except Organization.DoesNotExist:
        messages.error(request, 'Organization not found.')
        return redirect(DASHBOARD_URL_NAME)

    partner, created = Partner.objects.get_or_create(
        organization=organization,
        defaults={
            'description': description,
        }
    )

    if created:
        messages.success(request, f'Partner "{partner.name}" created.')
    else:
        if description and partner.description != description:
            partner.description = description
            partner.save(update_fields=['description'])
        messages.info(request, f'Organization "{organization}" is already a partner.')
    return redirect(DASHBOARD_URL_NAME)

@require_POST
def partner_delete(request):
    """Delete a Partner (staff only)."""
    forbidden = _require_portal_admin(request)
    if forbidden:
        return forbidden
    partner_id = request.POST.get('partner_id', '').strip()
    try:
        partner = Partner.objects.get(organization_id=partner_id)
    except Partner.DoesNotExist:
        messages.error(request, 'Partner not found.')
        return redirect(DASHBOARD_URL_NAME)
    name = partner.name
    partner.delete()
    messages.success(request, f'Partner "{name}" deleted.')
    return redirect(DASHBOARD_URL_NAME)

@require_POST
@require_portal_access
def partner_membership_add(request):
    """Add a user to a Partner (staff or partner members)."""
    partner_id = request.POST.get('partner_id', '').strip()
    username = request.POST.get('username', '').strip()
    if not partner_id or not username:
        messages.error(request, 'Partner and username are required.')
        return redirect(DASHBOARD_URL_NAME)
    try:
        partner = Partner.objects.get(organization_id=partner_id)
    except Partner.DoesNotExist:
        messages.error(request, 'Partner not found.')
        return redirect(DASHBOARD_URL_NAME)
    scope_check = _require_partner_scope(request, partner)
    if scope_check:
        return scope_check
    try:
        user = CustomUser.all_objects.get(username=username)
    except CustomUser.DoesNotExist:
        messages.error(request, f'User "{username}" not found.')
        return redirect(DASHBOARD_URL_NAME)
    PartnerMembership.objects.get_or_create(partner=partner, user=user)
    messages.success(request, f'Added {user.username} to {partner.name}.')
    return redirect(DASHBOARD_URL_NAME)

@require_POST
@require_portal_access
def partner_membership_remove(request):
    """Remove a user from a Partner (staff or partner members)."""
    partner_id = request.POST.get('partner_id', '').strip()
    username = request.POST.get('username', '').strip()
    if not partner_id or not username:
        messages.error(request, 'Partner and username are required.')
        return redirect(DASHBOARD_URL_NAME)
    try:
        partner = Partner.objects.get(organization_id=partner_id)
    except Partner.DoesNotExist:
        messages.error(request, 'Partner not found.')
        return redirect(DASHBOARD_URL_NAME)
    scope_check = _require_partner_scope(request, partner)
    if scope_check:
        return scope_check
    try:
        user = CustomUser.all_objects.get(username=username)
    except CustomUser.DoesNotExist:
        messages.error(request, f'User "{username}" not found.')
        return redirect(DASHBOARD_URL_NAME)
    PartnerMembership.objects.filter(partner=partner, user=user).delete()
    messages.success(request, f'Removed {user.username} from {partner.name}.')
    return redirect(DASHBOARD_URL_NAME)

@require_POST
@require_portal_access
def partner_badge_create(request):
    """Create a partner-scoped badge (staff or members of that partner)."""
    name = request.POST.get('name', '').strip()
    picture = request.POST.get('picture', '').strip()
    description = request.POST.get('description', '').strip()
    partner_id = request.POST.get('partner_id', '').strip()
    if not (name and picture and partner_id):
        messages.error(request, 'Name, picture, and partner are required.')
        return redirect(DASHBOARD_URL_NAME)
    try:
        partner = Partner.objects.get(organization_id=partner_id)
    except Partner.DoesNotExist:
        messages.error(request, 'Selected partner not found.')
        return redirect(DASHBOARD_URL_NAME)

    # Permission: staff can create for any partner; members only for their own partner
    if not is_portal_admin(request.user):
        if not PartnerMembership.objects.filter(user=request.user, partner=partner).exists():
            return HttpResponseForbidden("You don't have permission to create badges for this partner.")

    Badge.objects.create(
        name=name,
        picture=picture,
        description=description or '',
        logic={'partner': partner.organization_id},
        type='partner',
    )
    messages.success(request, f'Created partner badge "{name}" for {partner.name}.')
    return redirect(DASHBOARD_URL_NAME)

@require_POST
@require_portal_access
def partner_badge_assign(request):
    """Assign a partner badge to a user (portal access required)."""
    username = request.POST.get('username', '').strip()
    badge_id = request.POST.get('badge_id', '').strip()
    if not username or not badge_id:
        messages.error(request, 'Username and badge are required.')
        return redirect(DASHBOARD_URL_NAME)
    try:
        badge = Badge.objects.get(id=badge_id, type='partner')
    except Badge.DoesNotExist:
        messages.error(request, 'Selected badge not found or not a partner badge.')
        return redirect(DASHBOARD_URL_NAME)

    # Permission: staff can assign any; non-staff must belong to the badge's partner
    if not is_portal_admin(request.user):
        partner = Partner.objects.get(organization_id=badge.logic.get('partner')) if badge.logic else None
        if not partner or not PartnerMembership.objects.filter(user=request.user, partner=partner).exists():
            return HttpResponseForbidden("You don't have permission to assign this partner's badges.")

    # Support assigning to multiple users in a single submission.
    # Accept ONLY comma-separated list: "user1,user2,user3".
    tokens = [t.strip() for t in username.split(',') if t and t.strip()]
    if not tokens:
        messages.error(request, 'Please provide at least one username.')
        return redirect(DASHBOARD_URL_NAME)

    # De-duplicate while preserving order
    seen = set()
    usernames = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            usernames.append(t)

    # Fetch all users in one query
    users = list(CustomUser.all_objects.filter(username__in=usernames))
    user_by_name = {u.username: u for u in users}
    missing = [u for u in usernames if u not in user_by_name]

    assigned = []
    for uname, user in user_by_name.items():
        UserBadge.objects.update_or_create(
            user=user,
            badge=badge,
            defaults={'progress': 100, 'is_displayed': True}
        )
        assigned.append(uname)

    # Build compact messages
    def _list_preview(names, max_items=10):
        if len(names) <= max_items:
            return ', '.join(names)
        return f"{', '.join(names[:max_items])} and {len(names) - max_items} more"

    if assigned:
        messages.success(request, f'Assigned "{badge.name}" to: {_list_preview(assigned)}.')
    if missing:
        messages.error(request, f'Users not found: {_list_preview(missing)}.')
    return redirect(DASHBOARD_URL_NAME)

@require_POST
@require_portal_access
def partner_badge_remove(request):
    """Remove a partner badge from a user (portal access required)."""
    username = request.POST.get('username', '').strip()
    badge_id = request.POST.get('badge_id', '').strip()
    if not username or not badge_id:
        messages.error(request, 'Username and badge are required.')
        return redirect(DASHBOARD_URL_NAME)
    try:
        target = CustomUser.all_objects.get(username=username)
    except CustomUser.DoesNotExist:
        messages.error(request, f'User "{username}" not found.')
        return redirect(DASHBOARD_URL_NAME)
    try:
        badge = Badge.objects.get(id=badge_id, type='partner')
    except Badge.DoesNotExist:
        messages.error(request, 'Selected badge not found or not a partner badge.')
        return redirect(DASHBOARD_URL_NAME)

    # Permission: staff can remove any; non-staff must belong to the badge's partner
    if not is_portal_admin(request.user):
        partner = Partner.objects.get(organization_id=badge.logic.get('partner')) if badge.logic else None
        if not partner or not PartnerMembership.objects.filter(user=request.user, partner=partner).exists():
            return HttpResponseForbidden("You don't have permission to remove this partner's badges.")

    UserBadge.objects.filter(user=target, badge=badge).delete()
    messages.success(request, f'Removed "{badge.name}" from {target.username}.')
    return redirect(DASHBOARD_URL_NAME)

@require_POST
@require_portal_access
def partner_badge_delete(request):
    """Delete a partner badge."""
    badge_id = request.POST.get('badge_id', '').strip()
    if not badge_id:
        messages.error(request, 'Badge is required.')
        return redirect(DASHBOARD_URL_NAME)
    try:
        badge = Badge.objects.get(id=badge_id, type='partner')
    except Badge.DoesNotExist:
        messages.error(request, 'Selected badge not found or not a partner badge.')
        return redirect(DASHBOARD_URL_NAME)

    # Permission: staff can delete any; non-staff must belong to the badge's partner
    if not is_portal_admin(request.user):
        partner = Partner.objects.get(organization_id=badge.logic.get('partner')) if badge.logic else None
        if not partner or not PartnerMembership.objects.filter(user=request.user, partner=partner).exists():
            return HttpResponseForbidden("You don't have permission to delete this partner's badges.")

    name = badge.name
    badge.delete()
    messages.success(request, f'Deleted partner badge "{name}".')
    return redirect(DASHBOARD_URL_NAME)

@require_POST
@require_portal_access
def partner_badge_update(request):
    """Update editable fields of a partner badge (name, picture, description)."""
    badge_id = request.POST.get('badge_id', '').strip()
    name = request.POST.get('name', '').strip()
    picture = request.POST.get('picture', '').strip()
    description = request.POST.get('description', '').strip()
    if not badge_id:
        messages.error(request, 'Badge is required.')
        return redirect(DASHBOARD_URL_NAME)
    try:
        badge = Badge.objects.get(id=badge_id, type='partner')
    except Badge.DoesNotExist:
        messages.error(request, 'Selected badge not found or not a partner badge.')
        return redirect(DASHBOARD_URL_NAME)

    # Permission: staff can edit any; non-staff must belong to the badge's partner
    partner = Partner.objects.get(organization_id=badge.logic.get('partner')) if badge.logic else None
    if not is_portal_admin(request.user):
        if not partner or not PartnerMembership.objects.filter(user=request.user, partner=partner).exists():
            return HttpResponseForbidden("You don't have permission to edit this partner's badges.")

    changed = []
    if name:
        badge.name = name
        changed.append('name')
    if picture:
        badge.picture = picture
        changed.append('picture')
    if description != '':
        badge.description = description
        changed.append('description')
    badge.save()
    messages.success(request, f'Updated badge {badge.name} (changed: {", ".join(changed) or "no fields"}).')
    return redirect(DASHBOARD_URL_NAME)