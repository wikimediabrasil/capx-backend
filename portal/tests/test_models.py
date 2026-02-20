import base64
import json
import secrets
from django.test import TestCase
from django.contrib.auth import get_user_model
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from portal.models import (
    Partner,
    PartnerMentorshipFormMenteeResponse,
    PartnerMentorshipFormMentorResponse,
    PartnerMentorshipPublicKey,
)


User = get_user_model()


class BasePartnerMentorshipEncryptedResponseModelTests(TestCase):
    response_model = None
    username = "user"
    partner_name = "Partner Test"

    def setUp(self):
        self.user = User.objects.create_user(username=self.username, password=str(secrets.randbits(16)))
        self.partner = Partner.objects.create(name=self.partner_name)
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_pem = self.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")
        self.partner_public_key = PartnerMentorshipPublicKey.objects.create(
            partner=self.partner,
            public_key=public_pem,
        )

    def _decrypt_payload(self, encrypted_data):
        payload = json.loads(encrypted_data)
        encrypted_key = base64.b64decode(payload["key"])
        nonce = base64.b64decode(payload["nonce"])
        ciphertext = base64.b64decode(payload["ciphertext"])

        aes_key = self.private_key.decrypt(
            encrypted_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        return AESGCM(aes_key).decrypt(nonce, ciphertext, None).decode("utf-8")

    def create_response(self, data):
        return self.response_model.objects.create(
            partner=self.partner,
            user=self.user,
            data=data,
            public_key=self.partner_public_key,
        )

    def get_plaintext(self):
        raise NotImplementedError

    def get_expected_decrypted_plaintext(self, plaintext):
        raise NotImplementedError

    def test_encrypts_data_on_create(self):
        plaintext = self.get_plaintext()
        response = self.create_response(plaintext)

        self.assertNotEqual(response.data, plaintext)
        payload = json.loads(response.data)
        self.assertTrue(payload["__encrypted__"])
        self.assertEqual(self._decrypt_payload(response.data), self.get_expected_decrypted_plaintext(plaintext))

    def test_does_not_reencrypt_when_data_is_unchanged(self):
        response = self.create_response(self.get_plaintext())

        first_encrypted = response.data
        response.save()
        response.refresh_from_db()
        self.assertEqual(response.data, first_encrypted)


class PartnerMentorshipFormMentorResponseModelTests(BasePartnerMentorshipEncryptedResponseModelTests):
    response_model = PartnerMentorshipFormMentorResponse
    username = "mentor"
    partner_name = "Partner Mentor Test"

    def get_plaintext(self):
        return '{"experience":"python"}'

    def get_expected_decrypted_plaintext(self, plaintext):
        return plaintext


class PartnerMentorshipFormMenteeResponseModelTests(BasePartnerMentorshipEncryptedResponseModelTests):
    response_model = PartnerMentorshipFormMenteeResponse
    username = "mentee"
    partner_name = "Partner Mentee Test"

    def get_plaintext(self):
        return {"availability": "weekdays", "language": "pt"}

    def get_expected_decrypted_plaintext(self, plaintext):
        return json.dumps(plaintext, ensure_ascii=False)
