import requests
import json
import time
import jwt
import uuid
import os
from cryptography.hazmat.primitives import serialization
from rest_framework import viewsets
from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .serializers import LetsConnectLogSerializer
from .models import LetsConnectLog
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes


class LetsConnectViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = LetsConnectLogSerializer
    
    def get_queryset(self):
        return LetsConnectLog.objects.filter(user=self.request.user)

    @extend_schema(
        summary="Retrieve a specific LetsConnectLog entry",
        description="Retrieve a specific LetsConnectLog entry by ID.",
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @extend_schema(
        summary="List all LetsConnectLog entries",
        description="List all LetsConnectLog entries for the authenticated user.",
    )
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Create a new LetsConnectLog entry",
        description="Create a new LetsConnectLog entry, including sending the form to the LetsConnect API.",
    )
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
        payload = {
            "user": request.user.username,
            "timestamp": int(time.time()),
            "nonce": str(uuid.uuid4()),
        }
        for field in LetsConnectLogSerializer.Meta.fields:
            if field not in ["user", "confirmation"]:  # Exclude read-only fields
                payload[field] = data.get(field)
        return payload

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