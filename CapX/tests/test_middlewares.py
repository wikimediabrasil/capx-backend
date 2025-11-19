from django.test import TestCase, RequestFactory
from django.http import JsonResponse
from django.db.utils import OperationalError
from ..middlewares import DatabaseErrorMiddleware
from ..middlewares import _is_service_unavailable_db_error
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

    def test_middleware_returns_503_for_db_conn_errors_json(self):
        # Simulate a MySQL connection error (code 2003) to trigger 503 JSON
        request = self.factory.get('/', HTTP_ACCEPT='application/json')

        def error_response(request):
            raise OperationalError(2003, "Can't connect to MySQL server")

        middleware = DatabaseErrorMiddleware(error_response)
        response = middleware(request)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response["Retry-After"], "60")

    def test_middleware_returns_503_for_db_conn_errors_html(self):
        # Simulate HTML Accept header leading to HTML 503 response
        request = self.factory.get('/some/page', HTTP_ACCEPT='text/html')

        def error_response(request):
            raise OperationalError(2006, "MySQL server has gone away")

        middleware = DatabaseErrorMiddleware(error_response)
        response = middleware(request)
        self.assertEqual(response.status_code, 503)
        self.assertIn(b"Service temporarily unavailable", response.content)
        self.assertEqual(response["Retry-After"], "60")

    def test_helper_is_service_unavailable_recognizes_codes(self):
        self.assertTrue(_is_service_unavailable_db_error(OperationalError(2013, "Lost connection")))
        self.assertFalse(_is_service_unavailable_db_error(ValueError("nope")))

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