from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as AuthUserAdmin
from users.models import Territory, Language, WikimediaProject, CustomUser, Profile, Badge, UserBadge, LetsConnectLog, SavedItem, LanguageProficiency


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False


class AccountUserAdmin(AuthUserAdmin):
    list_display = ('username', 'is_staff', 'is_active')
    # Override default search_fields to remove first_name/last_name which are not present
    search_fields = ('username')
    # Use a custom add form template to display a very prominent warning banner.
    add_form_template = 'admin/users/customuser/add_form.html'

    fieldsets = (
        (None, {
            "fields": (
                'username', 'password'
            ),
        }),
        ('Personal info', {
            'fields': (
                'email',
            ),
        }),
        ('Permissions', {
            'fields': (
                'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'
            ),
        }),
        ('Important dates', {
            'fields': (
                'last_login', 'date_joined'
            ),
        }),        
    )
    
    
    def add_view(self, *args, **kwargs):
        self.inlines = []
        return super(AccountUserAdmin, self).add_view(*args, **kwargs)

    def change_view(self, *args, **kwargs):
        self.inlines = [ProfileInline]
        return super(AccountUserAdmin, self).change_view(*args, **kwargs)


class ProfileAdmin(admin.ModelAdmin):
    # Prevent adding profiles directly; they are created automatically with users
    def has_add_permission(self, request):
        return False


admin.site.register(CustomUser, AccountUserAdmin)
admin.site.register(Territory)
admin.site.register(Language)
admin.site.register(WikimediaProject)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(Badge)
admin.site.register(UserBadge)
admin.site.register(LetsConnectLog)
admin.site.register(SavedItem)
admin.site.register(LanguageProficiency)
