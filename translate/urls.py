from django.urls import path, include
from rest_framework.routers import SimpleRouter
from . import views

app_name = 'translate'

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('oauth/begin/', views.oauth_begin, name='oauth_begin'),
    path('oauth/', views.oauth_callback, name='oauth_callback'),
    # Metabase per-user OAuth
    path('metabase/connect/', views.metabase_oauth_begin, name='metabase_oauth_begin'),
    # Callback is multiplexed on /translate/oauth now; dedicated path left unused.
    path('metabase/disconnect/', views.metabase_oauth_disconnect, name='metabase_oauth_disconnect'),
]
                                                                                                                                                                                                                                        