import requests
import json
import time
import jwt
from cryptography.hazmat.primitives import serialization
from rest_framework import viewsets
import uuid
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
            answer = self.send_form(data, request)
            if answer.get('success', None):
                response_data = {
                    'user': request.user.id,
                    'confirmation': answer.get('confirmation'),
                }
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                return Response(answer, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def send_form(self, data, request):
        payload = {
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

        try:
            private_key = serialization.load_pem_private_key(
                open(settings.HOME + '/private_key.pem', 'rb').read(), 
                password=None
            )
        except FileNotFoundError:
            return {'success': False, 'error': 'Private key not found'}

        token = jwt.encode(payload, private_key, algorithm="RS256")
        
        headers = {
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(
                "https://letsconn.toolforge.org/endpoint/",
                json={"token": token},
                headers=headers
            )
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

        finally:
            del payload
            del token
            del headers