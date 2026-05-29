from unittest.mock import patch

from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import RequestFactory, TestCase, override_settings
from requests import Request
from social_django.utils import load_backend, load_strategy

try:
	from playwright.sync_api import sync_playwright

	PLAYWRIGHT_AVAILABLE = True
except Exception:
	PLAYWRIGHT_AVAILABLE = False


class OAuthPipelineE2E(StaticLiveServerTestCase):
	def setUp(self):
		if not PLAYWRIGHT_AVAILABLE:
			self.skipTest("Playwright is not installed; skipping OAuth e2e test")

		self.pw = sync_playwright().start()
		self.browser = self.pw.chromium.launch(headless=True)
		self.page = self.browser.new_page()

	def tearDown(self):
		if hasattr(self, "page"):
			self.page.close()
		if hasattr(self, "browser"):
			self.browser.close()
		if hasattr(self, "pw"):
			self.pw.stop()
		super().tearDown()

	@patch(
		"social_core.backends.mediawiki.MediaWiki.unauthorized_token",
		return_value="oauth_token=testtoken&oauth_token_secret=testsecret&oauth_callback_confirmed=true",
	)
	@patch(
		"social_core.backends.mediawiki.MediaWiki.access_token",
		return_value={
			"oauth_token": "oauth_token_key",
			"oauth_token_secret": "oauth_token_secret",
		},
	)
	@patch(
		"social_core.backends.mediawiki.MediaWiki.get_user_details",
		return_value={
			"username": "oauth-e2e-user",
			"userID": "999001",
			"email": "",
			"confirmed_email": True,
			"editcount": 42,
			"rights": ["read"],
			"groups": ["user"],
			"registered": "2020-01-01T00:00:00Z",
			"blocked": False,
		},
	)
	def test_oauth_to_knox_complete_flow(self, _mock_details, _mock_access_token, _mock_unauth_token):
		# Step 1: initialize OAuth handshake and persist temporary extra payload.
		start_response = self.page.request.post(
			f"{self.live_server_url}/api/login/social/knox/",
			data={"provider": "mediawiki", "extra": "e2e-extra"},
		)
		start_result = {
			"status": start_response.status,
			"data": start_response.json(),
		}

		self.assertEqual(start_result["status"], 200)
		self.assertEqual(start_result["data"]["oauth_token"], "testtoken")

		# Step 2: complete OAuth handshake and request Knox token.
		complete_response = self.page.request.post(
			f"{self.live_server_url}/api/login/social/knox_user/",
			data={
				"provider": "mediawiki",
				"oauth_token": start_result["data"]["oauth_token"],
				"oauth_secret": "testsecret",
				"oauth_verifier": "verifier-code",
			},
		)
		complete_result = {
			"status": complete_response.status,
			"data": complete_response.json(),
		}

		self.assertEqual(complete_result["status"], 200)
		self.assertEqual(complete_result["data"]["username"], "oauth-e2e-user")
		self.assertIn("token", complete_result["data"])
		self.assertEqual(complete_result["data"].get("extra"), "e2e-extra")


class OAuth10aSignatureTestCase(TestCase):
	@override_settings(
		SOCIAL_AUTH_MEDIAWIKI_KEY="dummy-key",
		SOCIAL_AUTH_MEDIAWIKI_SECRET="dummy-secret",
		SOCIAL_AUTH_MEDIAWIKI_URL="https://meta.wikimedia.org/w/index.php",
		SOCIAL_AUTH_MEDIAWIKI_CALLBACK="http://testserver/oauth/complete/mediawiki/",
	)
	def test_oauth10a_uses_hmac_sha1_signature_method(self):
		request = RequestFactory().get("/")
		middleware = SessionMiddleware(lambda req: None)
		middleware.process_request(request)
		request.session.save()

		strategy = load_strategy(request)
		backend = load_backend(
			strategy=strategy,
			name="mediawiki",
			redirect_uri="http://testserver/oauth/complete/mediawiki/",
		)

		oauth_auth = backend.oauth_auth(
			token={
				"oauth_token": "request-token",
				"oauth_token_secret": "request-secret",
			},
			oauth_verifier="verifier-code",
		)

		self.assertEqual(oauth_auth.client.signature_method, "HMAC-SHA1")

		prepared_request = Request(
			"POST",
			"https://meta.wikimedia.org/w/index.php?title=Special:Oauth/token",
		).prepare()
		signed_request = oauth_auth(prepared_request)
		auth_header = signed_request.headers.get("Authorization", "")
		if isinstance(auth_header, bytes):
			auth_header = auth_header.decode("utf-8")

		self.assertIn('oauth_signature_method="HMAC-SHA1"', auth_header)
		self.assertIn("oauth_signature=", auth_header)
