from django.db.utils import OperationalError
from django.http import JsonResponse

class DatabaseErrorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            return self.get_response(request)
        except OperationalError as e:
            error_message = str(e)
            if "Can't connect to MySQL server" in error_message:
                return JsonResponse(
                    {
                        "detail": "Toolforge' database is not available at the moment. Please try again later.",
                        "message": error_message
                    },
                    status=503
                )
            raise
