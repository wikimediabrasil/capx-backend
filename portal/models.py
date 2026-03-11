from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
import base64
import json
import os
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from users.models import CustomUser, Language
from skills.models import Skill


ENCRYPTED_MARKER = "__encrypted__"


def is_encrypted_data(value):
    if not isinstance(value, str):
        return False
    try:
        payload = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return False
    return isinstance(payload, dict) and payload.get(ENCRYPTED_MARKER) is True


def encrypt_data(plaintext, public_key_text):
    if not isinstance(plaintext, str):
        plaintext = json.dumps(plaintext, ensure_ascii=False)

    try:
        public_key = serialization.load_pem_public_key(public_key_text.encode("utf-8"))
    except Exception as exc:
        raise ValidationError("Invalid mentorship public key") from exc

    aes_key = AESGCM.generate_key(bit_length=256)
    nonce = os.urandom(12)
    ciphertext = AESGCM(aes_key).encrypt(nonce, plaintext.encode("utf-8"), None)
    encrypted_key = public_key.encrypt(
        aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )

    payload = {
        ENCRYPTED_MARKER: True,
        "version": 1,
        "algorithm": "RSA-OAEP-SHA256+AES-256-GCM",
        "key": base64.b64encode(encrypted_key).decode("ascii"),
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
    }
    return json.dumps(payload, separators=(",", ":"))


class Partner(models.Model):
    organization = models.OneToOneField(
        'orgs.Organization',
        on_delete=models.CASCADE,
        related_name='partner',
    )
    description = models.TextField(blank=True, default="")
    mentorship = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def name(self):
        return str(self.organization)

    def __str__(self):
        return str(self.organization)

class PartnerMentorshipSettings(models.Model):
    partner = models.OneToOneField(Partner, on_delete=models.CASCADE, related_name='mentorship_settings')
    description = models.TextField(blank=True, default="")
    skills = models.ManyToManyField(Skill, related_name='mentorship_settings')
    languages = models.ManyToManyField(Language, related_name='mentorship_settings')
    mentor_form = models.ForeignKey('PartnerMentorshipFormMentor', on_delete=models.SET_NULL, null=True, blank=True, related_name='mentorship_settings_as_mentor_form')
    mentee_form = models.ForeignKey('PartnerMentorshipFormMentee', on_delete=models.SET_NULL, null=True, blank=True, related_name='mentorship_settings_as_mentee_form')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.partner.name} Mentorship Settings"

class PartnerMembership(models.Model):
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='partner_memberships')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('partner', 'user')

    def __str__(self):
        return f"{self.user.username} @ {self.partner.name}"


class PartnerMentorshipPublicKey(models.Model):
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name='mentorship_public_keys')
    public_key = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.partner.name} Mentorship Public Key"


class PartnerMentorshipFormMentor(models.Model):
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name='mentorship_form_mentors')
    public_key = models.ForeignKey(PartnerMentorshipPublicKey, on_delete=models.CASCADE, related_name='mentor_forms', null=True, blank=True)
    json = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.partner.name} Mentorship Form Mentor"


class PartnerMentorshipFormMentee(models.Model):
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name='mentorship_form_mentees')
    public_key = models.ForeignKey(PartnerMentorshipPublicKey, on_delete=models.CASCADE, related_name='mentee_forms', null=True, blank=True)
    json = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.partner.name} Mentorship Form Mentee"


class PartnerMentorshipFormMentorResponse(models.Model):
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name='mentorship_form_mentor_responses')
    form = models.ForeignKey(PartnerMentorshipFormMentor, on_delete=models.CASCADE, related_name='responses')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='mentor_responses')
    data = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.partner = self.form.partner  # Ensure partner is always set to form's partner

        if self.pk:
            raise ValidationError("Updating mentor responses is not allowed")

        if not is_encrypted_data(self.data):
            self.data = encrypt_data(self.data, self.form.public_key.public_key)

        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} @ {self.partner.name} Mentor Response"


class PartnerMentorshipFormMenteeResponse(models.Model):
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name='mentorship_form_mentee_responses')
    form = models.ForeignKey(PartnerMentorshipFormMentee, on_delete=models.CASCADE, related_name='responses')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='mentee_responses')
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.partner = self.form.partner  # Ensure partner is always set to form's partner

        if self.pk:
            raise ValidationError("Public key must belong to the same partner")

        if not is_encrypted_data(self.data):
            self.data = encrypt_data(self.data, self.form.public_key.public_key)

        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} @ {self.partner.name} Mentee Response"