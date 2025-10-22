from django.urls import path, include
from . import views

app_name = 'portal'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('oauth/begin/', views.oauth_begin, name='oauth_begin'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('oauth/', views.oauth_callback, name='oauth_callback'),
    path('partner_badge/assign/', views.partner_badge_assign, name='partner_badge_assign'),
    path('partner_badge/remove/', views.partner_badge_remove, name='partner_badge_remove'),
    path('partner_badge/create/', views.partner_badge_create, name='partner_badge_create'),
    path('partner_badge/delete/', views.partner_badge_delete, name='partner_badge_delete'),
    path('partner/create/', views.partner_create, name='partner_create'),
    path('partner/delete/', views.partner_delete, name='partner_delete'),
    path('partner/membership/add/', views.partner_membership_add, name='partner_membership_add'),
    path('partner/membership/remove/', views.partner_membership_remove, name='partner_membership_remove'),
]