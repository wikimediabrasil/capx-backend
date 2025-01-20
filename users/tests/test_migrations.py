from django.test import TestCase
from django.db import connection
from django.apps import apps
from users.models import WikimediaProject
import importlib

migration_module = importlib.import_module('users.migrations.0015_wikimediaproject_wikimedia_project_picture')
fill_wikimedia_project_picture = migration_module.fill_wikimedia_project_picture
undo_fill_wikimedia_project_picture = migration_module.undo_fill_wikimedia_project_picture

class FillWikimediaProjectPictureTestCase(TestCase):
    def setUp(self):
        self.wikimedia_projects = [
            WikimediaProject.objects.create(wikimedia_project_code='wiki'),
            WikimediaProject.objects.create(wikimedia_project_code='wiktionarywiki'),
            WikimediaProject.objects.create(wikimedia_project_code='wikibookswiki'),
            WikimediaProject.objects.create(wikimedia_project_code='wikinews'),
            WikimediaProject.objects.create(wikimedia_project_code='wikiquotewiki'),
            WikimediaProject.objects.create(wikimedia_project_code='wikisourcewiki'),
            WikimediaProject.objects.create(wikimedia_project_code='wikiversitywiki'),
            WikimediaProject.objects.create(wikimedia_project_code='wikivoyagewiki'),
            WikimediaProject.objects.create(wikimedia_project_code='commonswiki'),
            WikimediaProject.objects.create(wikimedia_project_code='wikidatawiki'),
            WikimediaProject.objects.create(wikimedia_project_code='wikispecieswiki'),
            WikimediaProject.objects.create(wikimedia_project_code='wikifunctionswiki'),
            WikimediaProject.objects.create(wikimedia_project_code='metawiki'),
            WikimediaProject.objects.create(wikimedia_project_code='mediawiki'),
            WikimediaProject.objects.create(wikimedia_project_code='wikimaniawiki'),
            WikimediaProject.objects.create(wikimedia_project_code='incubatorwiki'),
        ]

    def test_fill_wikimedia_project_picture(self):
        fill_wikimedia_project_picture(apps=apps, schema_editor=None)
        for project in self.wikimedia_projects:
            project.refresh_from_db()
            self.assertTrue(project.wikimedia_project_picture.startswith('https://upload.wikimedia.org/wikipedia/commons/'))

    def test_undo_fill_wikimedia_project_picture(self):
        undo_fill_wikimedia_project_picture(apps=apps, schema_editor=None)
        for project in self.wikimedia_projects:
            project.refresh_from_db()
            self.assertEqual(project.wikimedia_project_picture, '')