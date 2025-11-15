from django.http import JsonResponse, HttpResponse
from django.db.utils import OperationalError, InterfaceError, DatabaseError
from django.db import connection


def _is_service_unavailable_db_error(exc: BaseException) -> bool:
    """
    Decide if the exception should be surfaced as a 503 Service Unavailable due to DB issues,
    without having to enumerate every possible PyMySQL error message.

    Strategy:
    - Catch broad django DB errors (OperationalError/InterfaceError/DatabaseError).
    - If an error code is present and is a well-known transient/connection code, treat as 503.
      Keep the set small to avoid overfitting.
    - Otherwise, ping the connection using connection.is_usable(). If ping fails or raises,
      treat it as a DB outage and return 503. This avoids message parsing.
    """

    if not isinstance(exc, (OperationalError, InterfaceError, DatabaseError)):
        return False

    code = None
    if getattr(exc, "args", None):
        first = exc.args[0]
        if isinstance(first, int):
            code = first

    # Minimal, focused set of transient/connection-oriented MySQL codes:
    # 2002: Connection refused; 2003: Can't connect; 2006: Server gone away; 2013: Lost connection
    # 1205: Lock wait timeout; 1213: Deadlock found
    transient_or_conn = {2002, 2003, 2006, 2013, 1205, 1213}
    if code in transient_or_conn:
        return True

    # Fallback: if the connection isn't usable (ping fails), treat as service unavailable
    try:
        usable = connection.is_usable()
    except Exception:
        # If the ping itself raises, we consider the DB unavailable
        return True
    return not usable


def _service_unavailable_response(request, detail: str, message: str):
    accept = request.META.get("HTTP_ACCEPT", "")
    wants_html = "text/html" in accept and "application/json" not in accept and not request.path.startswith("/api")
    if wants_html:
        resp = HttpResponse(
            "<h1>Service temporarily unavailable</h1>"
            "<p>The database is temporarily unavailable. Please try again later.</p>",
            status=503,
            content_type="text/html",
        )
        resp["Retry-After"] = "60"
        return resp
    resp = JsonResponse(
        {
            "detail": "Toolforge' database is not available at the moment. Please try again later.",
            "message": message,
        },
        status=503,
    )
    resp["Retry-After"] = "60"
    return resp


class DatabaseErrorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            return self.get_response(request)
        except Exception as exc:
            if _is_service_unavailable_db_error(exc):
                return _service_unavailable_response(request, "DB unavailable", str(exc))
            raise

    def process_exception(self, request, exception):
        if _is_service_unavailable_db_error(exception):
            return _service_unavailable_response(request, "DB unavailable", str(exception))
        return None
