from PIL import Image
import io, os, secrets
from django.test import TestCase
from ..models import Bug, Attachment
from users.models import CustomUser
from django.core.files.uploadedfile import SimpleUploadedFile


class BugModelTest(TestCase):
    def setUp(self):
        # Create a user
        test_user = CustomUser.objects.create_user(username='testuser', password=str(secrets.randbits(16)))
        test_user.save()

        # Create a Bug instance to use in tests
        self.bug = Bug.objects.create(
            user=test_user,
            title='Sample Bug',
            description='Sample Description',
            bug_type='error',
            status='to_do'
        )

    def test_bug_creation(self):
        bug = self.bug
        expected_user = f'{bug.user}'
        expected_title = f'{bug.title}'
        expected_description = f'{bug.description}'
        expected_bug_type = f'{bug.bug_type}'
        expected_status = f'{bug.status}'

        self.assertEqual(expected_user, 'testuser')
        self.assertEqual(expected_title, 'Sample Bug')
        self.assertEqual(expected_description, 'Sample Description')
        self.assertEqual(expected_bug_type, 'error')
        self.assertEqual(expected_status, 'to_do')

    def test_bug_str(self):
        bug = self.bug
        expected_str = f'{bug.title}'
        self.assertEqual(expected_str, str(bug))


class AttachmentModelTest(TestCase):
    def setUp(self):
        # Setup a user and a bug for the attachment
        self.user = CustomUser.objects.create_user(username="testuser", password=str(secrets.randbits(16)))
        self.bug = Bug.objects.create(
            user=self.user,
            title="Sample Bug",
            description="This is a sample description.",
            bug_type="error",
            status="to_do"
        )

    def test_attachment_creation(self):
        file = io.BytesIO()
        image = Image.new("RGB", (100, 100), color="red")
        image.save(file, "PNG")
        file.name = 'test_image.png'
        file.seek(0)
        
        self.file_content = SimpleUploadedFile("test_image.png", content=file.read(), content_type="image/png")

        self.attachment = Attachment.objects.create(
            bug=self.bug,
            file=self.file_content
        )

        self.assertTrue(isinstance(self.attachment, Attachment))
        self.assertIn("attachments/", self.attachment.file.name)
        expected_str = f"Attachment for {self.attachment.bug.bug_type} - {self.attachment.uploaded_at.strftime('%Y-%m-%d')}"
        self.assertEqual(str(self.attachment), expected_str)

    def tearDown(self):
        os.remove(self.attachment.file.path)



