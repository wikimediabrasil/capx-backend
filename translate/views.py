from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import login_required as django_login_required
from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib import messages
from django.urls import reverse
from django.views.decorators.http import require_GET
from social_django.utils import load_strategy, load_backend

INDEX_URL_NAME = 'translate:index'

# A login-required decorator that ignores settings.LOGIN_URL and always
# redirects to the translate login page.

def translate_login_required(view_func=None, *, redirect_field_name: str = REDIRECT_FIELD_NAME):
    decorator = django_login_required(
        redirect_field_name=redirect_field_name,
        login_url='/translate/login/'
    )
    return decorator(view_func) if view_func else decorator


@require_GET
@translate_login_required
def index(request):
    return render(request, 'translate/index.html', {
        'user': request.user,
    })


@require_GET
def login_view(request):
    if request.user.is_authenticated:
        return redirect(INDEX_URL_NAME)
    oauth_begin_url = reverse('translate:oauth_begin')
    return render(request, 'translate/login.html', {'social_login_url': oauth_begin_url})


@require_GET
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('translate:login')


@require_GET
def oauth_begin(request):
    """Start MediaWiki OAuth using social_django for translate area."""
    strategy = load_strategy(request)
    translate_return_path = reverse(INDEX_URL_NAME)
    strategy.session_set('next', translate_return_path)
    backend = load_backend(strategy, 'mediawiki', redirect_uri=None)
    response = backend.start()
    return response


@require_GET
def oauth_callback(request):
    complete_url = reverse('social:complete', kwargs={'backend': 'mediawiki'})
    qs = request.META.get('QUERY_STRING')
    if qs:
        complete_url = f"{complete_url}?{qs}"
    return redirect(complete_url)
