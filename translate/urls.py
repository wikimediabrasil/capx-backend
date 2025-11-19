from django.urls import path
from . import views, views_api

app_name = 'translate'

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('oauth/begin/', views.oauth_begin, name='oauth_begin'),
    path('oauth/', views.oauth_callback, name='oauth_callback'),

    # API endpoints under the same namespace to avoid modifying the global router
    path('api/capacities/', views_api.capacities_list, name='api_capacities_list'),
    path('api/submit/', views_api.submit_translation, name='api_submit_translation'),
]
