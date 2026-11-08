import importlib
from django.test import Client, SimpleTestCase, override_settings
from django.conf import settings
import os

class UrlPatternsTestCase(SimpleTestCase):
    def test_swagger_ui_only_accepts_get(self):
        client = Client()

        self.assertEqual(client.get('/').status_code, 200)
        self.assertEqual(client.post('/').status_code, 405)

    @override_settings(DEBUG=True, MEDIA_URL='/media/', MEDIA_ROOT=os.path.join(settings.BASE_DIR, 'media'))
    def test_media_url_pattern_added_in_debug_mode(self):
        # Import and reload the urlpatterns to ensure changes take effect
        from CapX import urls
        importlib.reload(urls)
        urlpatterns = urls.urlpatterns

        # Look for the pattern that serves media files
        media_pattern = rf'^{settings.MEDIA_URL.lstrip("/")}(?P<path>.*)$'
        media_url_found = any(
            hasattr(pattern, 'pattern') and pattern.pattern.regex.pattern == media_pattern
            for pattern in urlpatterns
        )
        
        self.assertTrue(media_url_found, "MEDIA_URL pattern not added in DEBUG mode")

    @override_settings(DEBUG=False)
    def test_media_url_pattern_not_added_in_production_mode(self):
        # Import and reload the urlpatterns to ensure changes take effect
        from CapX import urls
        importlib.reload(urls)
        urlpatterns = urls.urlpatterns

        # Look for the pattern that serves media files
        media_pattern = rf'^{settings.MEDIA_URL.lstrip("/")}(?P<path>.*)$'
        media_url_found = any(
            hasattr(pattern, 'pattern') and pattern.pattern.regex.pattern == media_pattern
            for pattern in urlpatterns
        )
        
        self.assertFalse(media_url_found, "MEDIA_URL pattern should not be added in production mode")
