from django.urls import path, include
from . import views

app_name = 'portal'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('oauth/begin/', views.oauth_begin, name='oauth_begin'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('oauth/', views.oauth_callback, name='oauth_callback'),
    path('portal_user/add/', views.portal_user_add, name='portal_user_add'),
    path('portal_user/remove/', views.portal_user_remove, name='portal_user_remove'),
]