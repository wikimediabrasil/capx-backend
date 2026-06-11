import secrets, json, base64
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from portal.views_api import PartnerViewSet, PartnerMentorshipFormMentorViewSet, PartnerMentorshipFormMenteeViewSet, PartnerMentorshipFormMentorResponseViewSet, PartnerMentorshipFormMenteeResponseViewSet
from portal.models import (
    PartnerMentorshipPublicKey,
    Partner,
    PartnerMentorshipFormMentor,
    PartnerMentorshipFormMentorResponse,
    PartnerMentorshipFormMentee,
    PartnerMentorshipFormMenteeResponse,
    PartnerMentorshipSettings,
)
from orgs.models import Organization
from users.models import CustomUser, Territory
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
        self.organization_other = Organization.objects.create(acronym="TST2")
        self.organization_other_name = self.organization_other.i18n_names.create(language_code="en", name="TST2")
        self.partner_other = Partner.objects.create(organization=self.organization_other, mentorship=True)
        
        # Generate a RSA PEM public/private key pair for testing
        self.private_key = asymmetric.rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_pem = self.private_key.public_key().public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo).decode("utf-8")
        self.public_key = PartnerMentorshipPublicKey.objects.create(partner=self.partner, public_key=public_pem)

        self.mentor_form = PartnerMentorshipFormMentor.objects.create(partner=self.partner, public_key=self.public_key, json={"question": "mentor?"})
        self.mentee_form = PartnerMentorshipFormMentee.objects.create(partner=self.partner, public_key=self.public_key, json={"question": "mentee?"})

        self.public_key_other = PartnerMentorshipPublicKey.objects.create(partner=self.partner_other, public_key=public_pem)
        self.mentor_form_other = PartnerMentorshipFormMentor.objects.create(partner=self.partner_other, public_key=self.public_key_other, json={"question": "mentor-other?"})
        self.mentee_form_other = PartnerMentorshipFormMentee.objects.create(partner=self.partner_other, public_key=self.public_key_other, json={"question": "mentee-other?"})

    def test_list_mentor_forms(self):
        response = self.client.get(f"/mentorship_form_mentor/?partner={self.organization.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], self.mentor_form.id)
        self.assertEqual(response.data['results'][0]['json'], {"question": "mentor?"})
        self.assertEqual(response.data['results'][0]['public_key_id'], self.public_key.id)
        self.assertEqual(response.data['results'][0]['public_key_fingerprint'], self.public_key.fingerprint)

    def test_list_mentee_forms(self):
        response = self.client.get(f"/mentorship_form_mentee/?partner={self.organization.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], self.mentee_form.id)
        self.assertEqual(response.data['results'][0]['json'], {"question": "mentee?"})
        self.assertEqual(response.data['results'][0]['public_key_id'], self.public_key.id)
        self.assertEqual(response.data['results'][0]['public_key_fingerprint'], self.public_key.fingerprint)

    def test_list_multiple_mentor_forms(self):
        PartnerMentorshipFormMentor.objects.create(partner=self.partner, public_key=self.public_key, json={"question": "mentor2?"})
        response = self.client.get("/mentorship_form_mentor/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 3)

    def test_list_mentor_forms_by_partner(self):
        PartnerMentorshipFormMentor.objects.create(partner=self.partner, public_key=self.public_key, json={"question": "mentor2?"})
        response = self.client.get(f"/mentorship_form_mentor/?partner={self.organization.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['organization'], self.organization.id)
        self.assertEqual(response.data['results'][0]['json'], {"question": "mentor2?"})

    def test_list_mentee_forms_by_partner(self):
        PartnerMentorshipFormMentee.objects.create(partner=self.partner, public_key=self.public_key, json={"question": "mentee2?"})
        response = self.client.get(f"/mentorship_form_mentee/?partner={self.organization.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['organization'], self.organization.id)
        self.assertEqual(response.data['results'][0]['json'], {"question": "mentee2?"})

    def test_submit_mentor_response(self):
        response = self.client.post(
            "/mentorship_form_mentor_response/",
            data={"form": self.mentor_form.id, "data": '{"answer": "I can mentor"}'},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["form"], self.mentor_form.id)
        self.assertEqual(response.data['public_key_id'], self.public_key.id)
        self.assertEqual(response.data['public_key_fingerprint'], self.public_key.fingerprint)
        self.assertEqual(response.data['encrypted_with_public_key_id'], self.public_key.id)
        self.assertEqual(response.data['encrypted_with_public_key_fingerprint'], self.public_key.fingerprint)

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

        stored = PartnerMentorshipFormMentorResponse.objects.get(form=self.mentor_form, user=self.user)
        self.assertEqual(stored.encrypted_with_public_key_id_snapshot, self.public_key.id)
        self.assertEqual(stored.encrypted_with_public_key_fingerprint, self.public_key.fingerprint)

    def test_submit_mentee_response(self):
        response = self.client.post(
            "/mentorship_form_mentee_response/",
            data={"form": self.mentee_form.id, "data": '{"answer": "I need mentorship"}'},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['form'], self.mentee_form.id)
        self.assertEqual(response.data['public_key_id'], self.public_key.id)
        self.assertEqual(response.data['public_key_fingerprint'], self.public_key.fingerprint)
        self.assertEqual(response.data['encrypted_with_public_key_id'], self.public_key.id)
        self.assertEqual(response.data['encrypted_with_public_key_fingerprint'], self.public_key.fingerprint)
        
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

        stored = PartnerMentorshipFormMenteeResponse.objects.get(form=self.mentee_form, user=self.user)
        self.assertEqual(stored.encrypted_with_public_key_id_snapshot, self.public_key.id)
        self.assertEqual(stored.encrypted_with_public_key_fingerprint, self.public_key.fingerprint)


class PartnerSettingsViewSetTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.organization = Organization.objects.create(acronym="TEST")
        self.organization.i18n_names.create(language_code="en", name="TEST")
        self.partner = Partner.objects.create(organization=self.organization, mentorship=True)
        self.territory = Territory.objects.create(territory_name='Brazil')
        PartnerMentorshipSettings.objects.create(
            partner=self.partner,
            description='Mentoria regional',
            registration_open_date='2026-04-01',
            registration_close_date='2026-04-30',
            territory=self.territory,
        )

    def test_list_partner_settings_includes_dates_and_territory(self):
        response = self.client.get('/partner_mentorship_settings/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

        payload = response.data['results'][0]
        self.assertEqual(payload['organization'], self.organization.id)
        self.assertEqual(payload['registration_open_date'], '2026-04-01')
        self.assertEqual(payload['registration_close_date'], '2026-04-30')
        self.assertEqual(payload['territory'], self.territory.id)
        self.assertEqual(payload['territory_name'], 'Brazil')
