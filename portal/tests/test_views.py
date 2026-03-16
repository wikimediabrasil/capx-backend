from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from datetime import date
from users.models import Badge, UserBadge
from users.models import Territory
from orgs.models import Organization, OrganizationName
from portal.models import Partner, PartnerMembership, PartnerMentorshipSettings
import secrets


User = get_user_model()


class PortalViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Two regular users and one staff admin
        self.user1 = User.objects.create_user(username="u1", password=str(secrets.randbits(16)))
        self.user2 = User.objects.create_user(username="u2", password=str(secrets.randbits(16)))
        self.missing_username = "ghost"
        self.admin = User.objects.create_user(username="admin", password=str(secrets.randbits(16)), is_staff=True)

        # One organization mapped as partner and membership for user1
        self.organization = Organization.objects.create(acronym="WMBR")
        OrganizationName.objects.create(organization=self.organization, language_code="en", name="WMBR")
        self.partner = Partner.objects.create(
            organization=self.organization,
            description="Test partner",
        )
        PartnerMembership.objects.create(partner=self.partner, user=self.user1)

        # Partner badge scoped to the partner
        self.badge = Badge.objects.create(
            name="Helper",
            picture="https://example.org/badge.png",
            description="Test partner badge",
            logic={"partner": self.partner.organization_id},
            type="partner",
        )

    def test_login_view_redirects_for_portal_member(self):
        # user1 is a partner member -> should redirect to dashboard
        self.client.force_login(user=self.user1)
        url = reverse("portal:login")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse("portal:dashboard"))

    def test_login_view_shows_message_for_non_portal_user(self):
        self.client.force_login(user=self.user2)
        url = reverse("portal:login")
        resp = self.client.get(url)
        # Not authorized for portal; stays on login page with error message queued
        self.assertEqual(resp.status_code, 200)
        self.assertIn(reverse("portal:oauth_begin"), resp.content.decode())

    def test_dashboard_access_control(self):
        # Not logged in -> redirect to portal login
        resp = self.client.get(reverse("portal:dashboard"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/portal/login/", resp.url)

        # Logged in but not a portal user nor admin -> 403
        self.client.force_login(user=self.user2)
        resp = self.client.get(reverse("portal:dashboard"))
        self.assertEqual(resp.status_code, 403)

        # Staff can access even without membership
        self.client.logout()
        self.client.force_login(user=self.admin)
        resp = self.client.get(reverse("portal:dashboard"))
        self.assertEqual(resp.status_code, 200)

    def test_oauth_callback_preserves_query_string(self):
        qs = "oauth_token=abc&oauth_verifier=def"
        url = reverse("portal:oauth_callback") + f"?{qs}"
        # Any authenticated state isn't required; it's just a redirect
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(qs, resp.url)

    def test_partner_badge_assign_staff_multiple_users(self):
        # Staff can assign any partner badge
        self.client.force_login(user=self.admin)
        url = reverse("portal:partner_badge_assign")
        payload = {
            "username": f"{self.user1.username},{self.user2.username},{self.missing_username}",
            "badge_id": str(self.badge.id),
        }
        resp = self.client.post(url, data=payload)
        # Redirect back to dashboard after processing
        self.assertEqual(resp.status_code, 302)

        # Two assignments created, missing user ignored with error message
        self.assertTrue(UserBadge.objects.filter(user=self.user1, badge=self.badge, progress=100).exists())
        self.assertTrue(UserBadge.objects.filter(user=self.user2, badge=self.badge, progress=100).exists())

    def test_partner_badge_assign_non_member_forbidden(self):
        # user2 is not staff and not a member of partner -> cannot assign
        self.client.force_login(user=self.user2)
        url = reverse("portal:partner_badge_assign")
        payload = {"username": self.user1.username, "badge_id": str(self.badge.id)}
        resp = self.client.post(url, data=payload)
        self.assertEqual(resp.status_code, 403)

    def test_partner_badge_create_permissions(self):
        # Non-member cannot create for partner they don't belong to
        self.client.force_login(user=self.user2)
        url = reverse("portal:partner_badge_create")
        payload = {"name": "X", "picture": "https://x", "partner_id": str(self.partner.organization_id)}
        resp = self.client.post(url, data=payload)
        self.assertEqual(resp.status_code, 403)

        # Member can create for their own partner
        self.client.logout()
        self.client.force_login(user=self.user1)
        resp = self.client.post(url, data=payload, follow=True)
        self.assertEqual(resp.status_code, 200)

    def test_logout_view_redirects_to_login(self):
        self.client.force_login(user=self.user1)
        resp = self.client.get(reverse("portal:logout"))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse("portal:login"))

    def test_partner_membership_add_and_remove_as_staff(self):
        # Add membership for user2 then remove it
        self.client.force_login(user=self.admin)
        add_url = reverse("portal:partner_membership_add")
        rem_url = reverse("portal:partner_membership_remove")
        data = {"partner_id": str(self.partner.organization_id), "username": self.user2.username}
        add_resp = self.client.post(add_url, data=data)
        self.assertEqual(add_resp.status_code, 302)
        self.assertTrue(PartnerMembership.objects.filter(partner=self.partner, user=self.user2).exists())
        rem_resp = self.client.post(rem_url, data=data)
        self.assertEqual(rem_resp.status_code, 302)
        self.assertFalse(PartnerMembership.objects.filter(partner=self.partner, user=self.user2).exists())

    def test_partner_badge_remove_delete_update(self):
        # Assign badge to user1, then remove it; delete badge; create another and update
        self.client.force_login(user=self.admin)
        # Assign first
        assign_url = reverse("portal:partner_badge_assign")
        self.client.post(assign_url, data={"username": self.user1.username, "badge_id": str(self.badge.id)})
        self.assertTrue(UserBadge.objects.filter(user=self.user1, badge=self.badge).exists())

        # Remove
        remove_url = reverse("portal:partner_badge_remove")
        rem_resp = self.client.post(remove_url, data={"username": self.user1.username, "badge_id": str(self.badge.id)})
        self.assertEqual(rem_resp.status_code, 302)
        self.assertFalse(UserBadge.objects.filter(user=self.user1, badge=self.badge).exists())

        # Update existing badge
        update_url = reverse("portal:partner_badge_update")
        upd_resp = self.client.post(update_url, data={"badge_id": str(self.badge.id), "name": "Helper2", "picture": "https://new", "description": "desc"})
        self.assertEqual(upd_resp.status_code, 302)

        # Delete badge
        delete_url = reverse("portal:partner_badge_delete")
        del_resp = self.client.post(delete_url, data={"badge_id": str(self.badge.id)})
        self.assertEqual(del_resp.status_code, 302)
        self.assertFalse(Badge.objects.filter(id=self.badge.id).exists())

    def test_mentorship_settings_update_saves_dates_and_territory(self):
        self.partner.mentorship = True
        self.partner.save(update_fields=['mentorship'])
        territory = Territory.objects.create(territory_name='Brazil')

        self.client.force_login(user=self.admin)
        response = self.client.post(
            reverse('portal:mentorship_settings_update'),
            data={
                'partner_id': str(self.partner.organization_id),
                'description': 'Mentoria 2026',
                'registration_open_date': '2026-04-01',
                'registration_close_date': '2026-04-30',
                'territory_id': str(territory.id),
            },
        )

        self.assertEqual(response.status_code, 302)

        settings_obj = PartnerMentorshipSettings.objects.get(partner=self.partner)
        self.assertEqual(settings_obj.description, 'Mentoria 2026')
        self.assertEqual(settings_obj.registration_open_date, date(2026, 4, 1))
        self.assertEqual(settings_obj.registration_close_date, date(2026, 4, 30))
        self.assertEqual(settings_obj.territory, territory)
