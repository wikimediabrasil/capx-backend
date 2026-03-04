import csv, secrets, os

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.conf import settings
from django.urls import reverse
from django.contrib.auth import get_user_model

from orgs.models import Organization, OrganizationName
from portal.models import Partner, PartnerMembership, PartnerMentorshipFormMentor

try:  # Optional dependency; skip test when Playwright is not installed
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except Exception:  # pragma: no cover - guard for missing playwright
    PLAYWRIGHT_AVAILABLE = False


User = get_user_model()

class DashboardE2E(StaticLiveServerTestCase):

    def setUp(self):
        if not PLAYWRIGHT_AVAILABLE:
            self.skipTest("Playwright is not installed; skipping dashboard smoke test")

        self.user = User.objects.create_user(
            username="portaluser", password=str(secrets.randbits(16)), is_staff=True
        )
        User.objects.create_user(username="alice", password=str(secrets.randbits(16)))
        User.objects.create_user(username="bob", password=str(secrets.randbits(16)))
        User.objects.create_user(username="charlie", password=str(secrets.randbits(16)))

    def test_users_csv_download(self):
        self.client.force_login(self.user)
        session_cookie = self.client.cookies.get('sessionid')

        self.pw = sync_playwright().start()
        self.browser = self.pw.chromium.launch(headless=True)
        self.page = self.browser.new_page()
        
        self.page.context.add_cookies([{
            "name": session_cookie.key,
            "value": session_cookie.value,
            "url": self.live_server_url,
        }])
        self.page.goto(f"{self.live_server_url}{reverse('portal:dashboard')}#users")
        self.page.wait_for_selector("#users-csv-btn")

        with self.page.expect_download() as dl_info:
            self.page.click("#users-csv-btn")
        download = dl_info.value
        path = download.path()
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
            
        assert any("alice" in row for row in rows)
        assert any("bob" in row for row in rows)
        assert any("charlie" in row for row in rows)
        os.remove(path)

    def test_mentorship_process(self):
        org = Organization.objects.create(acronym="Test")
        OrganizationName.objects.create(organization=org, language_code="en", name="Test Org Name")
        partner = Partner.objects.create(organization=org, mentorship=True)
        PartnerMembership.objects.create(partner=partner, user=self.user)

        self.client.force_login(self.user)
        session_cookie = self.client.cookies.get('sessionid')

        self.pw = sync_playwright().start()
        self.browser = self.pw.chromium.launch(headless=True)
        self.page = self.browser.new_page()
        self.page.context.add_cookies([{
            "name": session_cookie.key,
            "value": session_cookie.value,
            "url": self.live_server_url,
        }])
        self.page.goto(f"{self.live_server_url}{reverse('portal:dashboard')}#mentorship")

        # Click on button tab-mentorship-keys
        try:
            self.page.wait_for_selector("#tab-mentorship-keys", timeout=5000)
        except PlaywrightTimeoutError:
            self.fail("Mentorship button did not appear within 5 seconds")
        self.page.click("#tab-mentorship-keys")

        # On select #mentorship-key-delivery, choose option with value "download"
        self.page.select_option("#mentorship-key-delivery", "download")

        # Submit form and expect a download to start
        with self.page.expect_download() as dl_info:
            self.page.click("#mentorship-key-generate-btn")
        download = dl_info.value
        path = download.path()
        
        # Open PEM file and check it starts with "-----BEGIN"
        with open(path, "r", encoding="utf-8") as f:
            private_key = f.read()
            assert private_key.startswith("-----BEGIN")
        os.remove(path)

        # Refresh page to reset form state
        self.page.reload()

        # Changes tab to create mentorship form
        try:
            self.page.wait_for_selector("#tab-mentorship-forms", timeout=5000)
        except PlaywrightTimeoutError:
            self.fail("Mentorship button did not appear within 5 seconds")
        self.page.click("#tab-mentorship-forms")

        # Creates form using jQuery formBuilder plugin
        self.page.click(".formbuilder-icon-text")
        self.page.click(".formbuilder-icon-date")

        # On select #mentorship-form-partner, choose the first option
        self.page.select_option("#mentorship-form-partner", str(partner.organization_id))

        # On select #mentorship-form-type, choose "mentor"
        self.page.select_option("#mentorship-form-type", "mentor")

        # On #mentorship-form-public-key, choose the first
        self.page.select_option("#mentorship-form-public-key", "1")

        # Submit form and expect "<li class="success">" success message after page loaded
        self.page.click("#mentorship-form-save-btn")
        try:
            self.page.wait_for_selector("li.success", timeout=10000)
        except PlaywrightTimeoutError:
            self.fail("Did not see success message after saving mentorship form")
        
        # Closes browser for now
        self.page.close()
        self.browser.close()
        self.pw.stop()
        self.client.logout()

        # Submit form responses via API
        form = PartnerMentorshipFormMentor.objects.first()
        json_form = form.json

        self.client.force_login(User.objects.get(username="alice"))
        answers = {}
        for field in json_form:
            if field["type"] == "text":
                answers[field["name"]] = "Sample answer"
            elif field["type"] == "date":
                answers[field["name"]] = "2024-01-01"

        response = self.client.post(
            reverse('partner_mentorship_form_mentor_response-list'),
            data={"form": form.id, "data": str(answers)},
            content_type="application/json"
        )
        assert response.status_code == 201, f"Expected 201 Created, got {response.status_code}"
        self.client.logout()

        self.client.force_login(User.objects.get(username="bob"))
        answers = {}
        for field in json_form:
            if field["type"] == "text":
                answers[field["name"]] = "Another answer"
            elif field["type"] == "date":
                answers[field["name"]] = "2024-02-01"

        response = self.client.post(
            reverse('partner_mentorship_form_mentor_response-list'),
            data={"form": form.id, "data": str(answers)},
            content_type="application/json"
        )
        assert response.status_code == 201, f"Expected 201 Created, got {response.status_code}"
        self.client.logout()

        # Reopen browser and check that mentorship responses are included in CSV export
        self.client.force_login(self.user)
        session_cookie = self.client.cookies.get('sessionid')
        self.pw = sync_playwright().start()
        self.browser = self.pw.chromium.launch(headless=True)
        self.page = self.browser.new_page()
        self.page.context.add_cookies([{
            "name": session_cookie.key,
            "value": session_cookie.value,
            "url": self.live_server_url,
        }])
        self.page.goto(f"{self.live_server_url}{reverse('portal:dashboard')}#mentorship")

        # Click on button tab-mentorship-csv
        try:
            self.page.wait_for_selector("#tab-mentorship-csv", timeout=5000)
        except PlaywrightTimeoutError:
            self.fail("Mentorship button did not appear within 5 seconds")
        self.page.click("#tab-mentorship-csv")

        # Paste PEM private key into #mentorship-csv-private-key
        self.page.fill("#mentorship-csv-private-key", private_key)

        # Click #mentorship-csv-download-btn and expect download to start
        with self.page.expect_download() as dl_info:
            self.page.click("#mentorship-csv-download-btn")
        download = dl_info.value
        path = download.path()
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))

        # Check that CSV contains the mentorship responses submitted by Alice and Bob
        assert any("Sample answer" in str(row) for row in rows), "First mentorship response not found in CSV"
        assert any("Another answer" in str(row) for row in rows), "Second mentorship response not found in CSV"
        os.remove(path)


    def tearDown(self):
        self.page.close()
        self.browser.close()
        self.pw.stop()
        super().tearDown()