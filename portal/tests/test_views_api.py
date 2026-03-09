import secrets, json, base64
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from portal.views_api import PartnerViewSet, PartnerMentorshipFormMentorViewSet, PartnerMentorshipFormMenteeViewSet, PartnerMentorshipFormMentorResponseViewSet, PartnerMentorshipFormMenteeResponseViewSet
from portal.models import PartnerMentorshipPublicKey, Partner, PartnerMentorshipFormMentor, PartnerMentorshipFormMentee
from orgs.models import Organization
from users.models import CustomUser
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from orgs.models import Organization
from cryptography.hazmat.primitives import serialization, hashes, asymmetric, ciphers


class PartnerViewSetTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.organization = Organization.objects.create(acronym="TEST")
        self.organization_name = self.organization.i18n_names.create(language_code="en", name="TEST")
        self.partner = Partner.objects.create(organization=self.organization, mentorship=True)

    def test_list_partners(self):
        response = self.client.get("/partners/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], self.organization.id)
        self.assertEqual(response.data['results'][0]['name'], "TEST")

    def test_retrieve_partner(self):
        response = self.client.get(f"/partners/{self.organization.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.organization.id)
        self.assertEqual(response.data['name'], "TEST")

    def test_update_partner_not_allowed(self):
        response = self.client.put(f"/partners/{self.organization.id}/", data={"mentorship": False})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PartnerMentorshipFormViewSetTestCase(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='test', password=str(secrets.randbits(16)))
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.organization = Organization.objects.create(acronym="TEST")
        self.organization_name = self.organization.i18n_names.create(language_code="en", name="TEST")
        self.partner = Partner.objects.create(organization=self.organization, mentorship=True)
        
        # Generate a RSA PEM public/private key pair for testing
        self.private_key = asymmetric.rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_pem = self.private_key.public_key().public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo).decode("utf-8")
        self.public_key = PartnerMentorshipPublicKey.objects.create(partner=self.partner, public_key=public_pem)

        self.mentor_form = PartnerMentorshipFormMentor.objects.create(partner=self.partner, public_key=self.public_key, json={"question": "mentor?"})
        self.mentee_form = PartnerMentorshipFormMentee.objects.create(partner=self.partner, public_key=self.public_key, json={"question": "mentee?"})

    def test_list_mentor_forms(self):
        response = self.client.get("/mentorship_form_mentor/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], self.mentor_form.id)
        self.assertEqual(response.data['results'][0]['json'], {"question": "mentor?"})

    def test_list_mentee_forms(self):
        response = self.client.get("/mentorship_form_mentee/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], self.mentee_form.id)
        self.assertEqual(response.data['results'][0]['json'], {"question": "mentee?"})

    def test_list_multiple_mentor_forms(self):
        PartnerMentorshipFormMentor.objects.create(partner=self.partner, public_key=self.public_key, json={"question": "mentor2?"})
        response = self.client.get("/mentorship_form_mentor/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['json'], {"question": "mentor2?"})

    def test_submit_mentor_response(self):
        response = self.client.post(
            "/mentorship_form_mentor_response/",
            data={"form": self.mentor_form.id, "data": '{"answer": "I can mentor"}'},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["form"], self.mentor_form.id)

        encrypted = response.data["data"]
        if isinstance(encrypted, str):
            encrypted = json.loads(encrypted)

        self.assertTrue(encrypted["__encrypted__"])
        self.assertEqual(encrypted["algorithm"], "RSA-OAEP-SHA256+AES-256-GCM")

        aes_key = self.private_key.decrypt(
            base64.b64decode(encrypted["key"]),
            asymmetric.padding.OAEP(
                mgf=asymmetric.padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

        plaintext = ciphers.aead.AESGCM(aes_key).decrypt(
            base64.b64decode(encrypted["nonce"]), 
            base64.b64decode(encrypted["ciphertext"]), 
            None
        )
        decrypted_payload = json.loads(plaintext.decode("utf-8"))

        self.assertEqual(decrypted_payload["answer"], "I can mentor")        

    def test_submit_mentee_response(self):
        response = self.client.post(
            "/mentorship_form_mentee_response/",
            data={"form": self.mentee_form.id, "data": '{"answer": "I need mentorship"}'},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['form'], self.mentee_form.id)
        
        encrypted = response.data["data"]
        if isinstance(encrypted, str):
            encrypted = json.loads(encrypted)

        self.assertTrue(encrypted["__encrypted__"])
        self.assertEqual(encrypted["algorithm"], "RSA-OAEP-SHA256+AES-256-GCM")

        aes_key = self.private_key.decrypt(
            base64.b64decode(encrypted["key"]),
            asymmetric.padding.OAEP(
                mgf=asymmetric.padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

        plaintext = ciphers.aead.AESGCM(aes_key).decrypt(
            base64.b64decode(encrypted["nonce"]), 
            base64.b64decode(encrypted["ciphertext"]), 
            None
        )
        decrypted_payload = json.loads(plaintext.decode("utf-8"))

        self.assertEqual(decrypted_payload["answer"], "I need mentorship")        
