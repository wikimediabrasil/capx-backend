from django.test import TestCase, RequestFactory
from django.http import JsonResponse
from django.db.utils import OperationalError
from ..middlewares import DatabaseErrorMiddleware
import json

class DatabaseErrorMiddlewareTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.get_response = lambda request: JsonResponse({"detail": "success"})
        self.middleware = DatabaseErrorMiddleware(self.get_response)

    def test_middleware_allows_normal_response(self):
        request = self.factory.get('/')
        response = self.middleware(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), {"detail": "success"})

    def test_middleware_handles_other_operational_error(self):
        request = self.factory.get('/')

        def error_response(request):
            raise OperationalError("Some other error")

        middleware = DatabaseErrorMiddleware(error_response)
        with self.assertRaises(OperationalError):
            middleware(request)

    def test_middleware_handles_other_exceptions(self):
        request = self.factory.get('/')

        def error_response(request):
            raise ValueError("Some other error")

        middleware = DatabaseErrorMiddleware(error_response)
        with self.assertRaises(ValueError):
            middleware(request)

    def test_middleware_with_post_request(self):
        request = self.factory.post('/')
        response = self.middleware(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), {"detail": "success"})

    def test_middleware_with_put_request(self):
        request = self.factory.put('/')
        response = self.middleware(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), {"detail": "success"})