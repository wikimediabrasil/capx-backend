import os
import unittest
from unittest.mock import patch
import CapX.settings_local as settings_local

class TestSettingsLocal(unittest.TestCase):
    @unittest.skipIf(not hasattr(settings_local, 'configure_settings'), "settings_local.configure_settings doesn't exist")
    def test_os_path_exists_false(self):
        with patch('os.path.exists', return_value=False):
            settings = settings_local.configure_settings()
            # Your assertions when os.path.exists returns False
            self.assertFalse(os.path.exists('/some/path'))  # This will be False
            self.assertListEqual(settings['ALLOWED_HOSTS'], ['127.0.0.1'])
            self.assertEqual(settings['SOCIAL_AUTH_MEDIAWIKI_CALLBACK'], 'http://127.0.0.1:3000/oauth/')
            self.assertEqual(settings['DATABASES']['default']['ENGINE'], 'django.db.backends.sqlite3')
            self.assertEqual(settings['MESSAGE'], 'You are running in local mode, please make sure to set up the replica.my.cnf file to run in production mode')

    @unittest.skipIf(not hasattr(settings_local, 'configure_settings'), "settings_local.configure_settings doesn't exist")
    def test_os_path_exists_true(self):
        with patch('os.path.exists', return_value=True), patch('os.environ.get', return_value=""):
            settings = settings_local.configure_settings()
            # Your assertions when os.path.exists returns True
            self.assertTrue(os.path.exists('/some/path'))  # This will be True
            self.assertListEqual(settings['ALLOWED_HOSTS'], ['capx-backend.toolforge.org', 'toolforge.org'])
            self.assertEqual(settings['SOCIAL_AUTH_MEDIAWIKI_CALLBACK'], 'https://capx.toolforge.org/oauth')
            self.assertEqual(settings['DATABASES']['default']['ENGINE'], 'django.db.backends.mysql')
            self.assertEqual(settings['MESSAGE'], 'You are running in production mode')
