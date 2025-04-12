import requests
import json
import time
import jwt
import uuid
import os
from cryptography.hazmat.primitives import serialization
from rest_framework import viewsets
from django.conf import settings
from rest_framework.response import Response
from rest_framework import status
from .serializers import LetsConnectLogSerializer
from .models import LetsConnectLog
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes


class LetsConnectViewSet(viewsets.GenericViewSet):
    serializer_class = LetsConnectLogSerializer

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            answer = self._send_form(data, request)
            if answer.get('success', None):
                response_data = {
                    'user': request.user.id,
                    'confirmation': answer.get('confirmation'),
                }
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                return Response(answer, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _send_form(self, data, request):
        try:
            private_key = serialization.load_pem_private_key(open(os.path.join(settings.HOME, 'private_key.pem'), 'rb').read(), password=None)
        except FileNotFoundError:
            return {'success': False, 'error': 'Private key not found'}

        token = jwt.encode(self._build_payload(data, request), private_key, algorithm="RS256")
        response = requests.post("https://letsconn.toolforge.org/endpoint/", json={"token": token}, headers={"Content-Type": "application/json"})

        return self._process_response(response, request)

    def _build_payload(self, data, request):
        return {
            "user": request.user.username,
            "full_name": data.get("full_name"),
            "email": data.get("email"),
            "role": data.get("role"),
            "area": data.get("area"),
            "gender": data.get("gender"),
            "age": data.get("age"),
            "timestamp": int(time.time()),
            "nonce": str(uuid.uuid4()),
        }

    def _process_response(self, response, request):
        if response.status_code == 200 and response.json().get("confirmation"):
            LetsConnectLog.objects.create(
                user=request.user,
                confirmation=response.json().get("confirmation"),
            )
            return {'success': True, 'confirmation': response.json().get("confirmation")}
        else:
            try:
                error_message = response.json().get("error", "Unknown error")
            except json.JSONDecodeError:
                error_message = response.text if response.text else "Unknown error"
            return {'success': False, 'error': error_message, 'code': response.status_code}