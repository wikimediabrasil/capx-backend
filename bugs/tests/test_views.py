import secrets, os
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from users.models import CustomUser
from django.core.files.uploadedfile import SimpleUploadedFile


class BugViewSetTestCase(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='test', password=str(secrets.randbits(16)))
        self.client = APIClient()

    def test_bug_list_unauthenticated(self):
        response = self.client.get('/bugs/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
    def test_bug_create_unauthenticated(self):
        bug_data = {
            'title': 'New Bug',
            'description': 'New Bug Description',
        }

        response = self.client.post('/bugs/', bug_data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_creation(self):
        self.assertEqual(self.user.username, 'test')
        self.assertIsInstance(self.user, CustomUser)
        self.assertTrue(self.user.is_active)

    def test_bug_create_authenticated(self):
        bug_data = {
            'title': 'New Bug',
            'description': 'New Bug Description',
        }

        self.client.force_authenticate(self.user)
        response = self.client.post('/bugs/', bug_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_bug_list_authenticated(self):
        self.client.force_authenticate(self.user)
        response = self.client.get('/bugs/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_bug_list_staff(self):
        self.user.is_staff = True
        self.user.save()
        self.client.force_authenticate(self.user)
        response = self.client.get('/bugs/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_bug_update(self):
        self.client.force_authenticate(self.user)
        bug = self.client.post('/bugs/', {'title': 'Bug', 'description': 'Bug',})
        bug_data = {
            'title': 'Updated Bug',
            'description': 'Updated Bug Description',
        }
        response = self.client.put(f'/bugs/{bug.data["id"]}/', bug_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.user.is_staff = True
        self.user.save()
        response = self.client.put(f'/bugs/{bug.data["id"]}/', bug_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_bug_partial_update(self):
        self.client.force_authenticate(self.user)
        bug = self.client.post('/bugs/', {'title': 'Bug', 'description': 'Bug',})
        bug_data = {
            'title': 'Updated Bug',
        }
        response = self.client.patch(f'/bugs/{bug.data["id"]}/', bug_data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        self.user.is_staff = True
        self.user.save()
        response = self.client.patch(f'/bugs/{bug.data["id"]}/', bug_data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_bug_delete(self):
        self.client.force_authenticate(self.user)
        bug = self.client.post('/bugs/', {'title': 'Bug', 'description': 'Bug',})
        response = self.client.delete(f'/bugs/{bug.data["id"]}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_bug_delete_staff(self):
        self.user.is_staff = True
        self.user.save()
        self.client.force_authenticate(self.user)
        bug = self.client.post('/bugs/', {'title': 'Bug', 'description': 'Bug',})
        response = self.client.delete(f'/bugs/{bug.data["id"]}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class AttachmentViewSetTestCase(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='test', password=str(secrets.randbits(16)))
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.bug = self.client.post('/bugs/', {'title': 'Bug', 'description': 'Bug',})
        attachment_data = {
            'file': SimpleUploadedFile('attachment.test', b'attachment content'),
            'bug': self.bug.data['id'],
        }
        self.attachment = self.client.post('/attachment/', attachment_data)

    def test_attachment_list(self):
        response = self.client.get('/attachment/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_attachment_list_staff(self):
        self.user.is_staff = True
        self.user.save()
        self.client.force_authenticate(self.user)
        response = self.client.get('/attachment/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_attachment_retrieve(self):
        response = self.client.get(f'/attachment/{self.attachment.data["id"]}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['file'].split('/')[-1].split('_')[0], 'attachment.test')

    def test_attachment_create(self):
        attachment_data = {
            'file': SimpleUploadedFile('new_attach.test', b'new attachment content'),
            'bug': self.bug.data['id'],
        }
        response = self.client.post('/attachment/', attachment_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_attachment_update(self):
        attachment_data = {
            'file': SimpleUploadedFile('updated_attachment.test', b'updated attachment content'),
            'bug': self.bug.data['id'],
        }
        response = self.client.put(f'/attachment/{self.attachment.data["id"]}/', attachment_data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_attachment_partial_update(self):
        attachment_data = {
            'file': SimpleUploadedFile('updated_attachment.test', b'updated attachment content'),
        }
        response = self.client.patch(f'/attachment/{self.attachment.data["id"]}/', attachment_data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_attachment_create_exceed_size(self):
        attachment_data = {
            'file': SimpleUploadedFile('exceed_size.test', b'a' * 1024 * 1025),
            'bug': self.bug.data['id'],
        }
        response = self.client.post('/attachment/', attachment_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_attachment_create_exceed_count(self):
        attachment_data = {
            'file': SimpleUploadedFile('attachment1.test', b'attachment content'),
            'bug': self.bug.data['id'],
        }
        self.client.post('/attachment/', attachment_data)
        attachment_data = {
            'file': SimpleUploadedFile('attachment2.test', b'attachment content'),
            'bug': self.bug.data['id'],
        }
        self.client.post('/attachment/', attachment_data)
        attachment_data = {
            'file': SimpleUploadedFile('attachment3.test', b'attachment content'),
            'bug': self.bug.data['id'],
        }
        response = self.client.post('/attachment/', attachment_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_attachment_no_bug(self):
        attachment_data = {
            'file': SimpleUploadedFile('no_bug.test', b'attachment content'),
        }
        response = self.client.post('/attachment/', attachment_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_attachment_delete(self):
        response = self.client.delete(f'/attachment/{self.attachment.data["id"]}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.user.is_staff = True
        self.user.save()
        response = self.client.delete(f'/attachment/{self.attachment.data["id"]}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
 
    # Delete *.test files on folder after test
    def tearDown(self):
        for file in os.listdir('media/attachments/'):
            if file.endswith('.test'):
                os.remove(f'media/attachments/{file}')
