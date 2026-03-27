from django.urls import path, include
from . import views

app_name = 'portal'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('users/', views.dashboard_users, name='dashboard_users'),
    path('membership/', views.dashboard_membership, name='dashboard_membership'),
    path('badges/', views.dashboard_badges, name='dashboard_badges'),
    path('mentorship/', views.dashboard_mentorship, name='dashboard_mentorship'),
    path('admin/', views.dashboard_admin, name='dashboard_admin'),
    path('qid-labels/', views.qid_labels_view, name='qid_labels'),
    path('oauth/begin/', views.oauth_begin, name='oauth_begin'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('oauth/', views.oauth_callback, name='oauth_callback'),
    path('partner_badge/assign/', views.partner_badge_assign, name='partner_badge_assign'),
    path('partner_badge/remove/', views.partner_badge_remove, name='partner_badge_remove'),
    path('partner_badge/create/', views.partner_badge_create, name='partner_badge_create'),
    path('partner_badge/delete/', views.partner_badge_delete, name='partner_badge_delete'),
    path('partner_badge/update/', views.partner_badge_update, name='partner_badge_update'),
    path('partner/create/', views.partner_create, name='partner_create'),
    path('partner/update/', views.partner_update, name='partner_update'),
    path('partner/delete/', views.partner_delete, name='partner_delete'),
    path('partner/membership/add/', views.partner_membership_add, name='partner_membership_add'),
    path('partner/membership/remove/', views.partner_membership_remove, name='partner_membership_remove'),
    path('partner/mentorship/settings/update/', views.mentorship_settings_update, name='mentorship_settings_update'),
    path('partner/mentorship/form/create/', views.mentorship_form_create, name='mentorship_form_create'),
    path('partner/mentorship/form/update/', views.mentorship_form_update, name='mentorship_form_update'),
    path('partner/mentorship/public-key/add/', views.mentorship_public_key_add, name='mentorship_public_key_add'),
    path('partner/mentorship/public-key/generate/', views.mentorship_public_key_generate, name='mentorship_public_key_generate'),
]