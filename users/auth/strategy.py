from django.conf import settings
from social_core.utils import get_strategy, setting_name
from social_django.strategy import DjangoStrategy
from social_django.utils import STORAGE, psa


REDIRECT_URI = getattr(settings, 'REST_SOCIAL_OAUTH_REDIRECT_URI', '/')
STRATEGY = getattr(settings, setting_name('STRATEGY'), 'users.auth.strategy.LocalDRFStrategy')


class LocalDRFStrategy(DjangoStrategy):
    def request_data(self, merge=True):
        if not self.request:
            return {}

        auth_data = getattr(self.request, 'auth_data', None)
        if isinstance(auth_data, dict):
            return auth_data.copy()

        if hasattr(self.request, 'data') and isinstance(self.request.data, dict):
            return self.request.data.copy()

        return super().request_data(merge=merge)


def load_strategy(request=None):
    return get_strategy(STRATEGY, STORAGE, request)


@psa(REDIRECT_URI, load_strategy=load_strategy)
def decorate_request(request, backend):
    pass
