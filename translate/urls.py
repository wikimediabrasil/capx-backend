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
]
