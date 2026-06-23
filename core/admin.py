from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User
from .models import Profile

class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Perfil'
    fk_name = 'user'
    fields = ('escola', 'nivel_acesso', 'is_developer')
    readonly_fields = ()
    show_change_link = True

class CustomUserAdmin(DjangoUserAdmin):
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_nivel_acesso')
    list_select_related = ('profile',)
    list_filter = ('is_staff', 'is_superuser', 'profile__nivel_acesso')
    search_fields = ('username', 'email', 'first_name', 'last_name')

    def get_nivel_acesso(self, obj):
        return getattr(obj.profile, 'nivel_acesso', '-')
    get_nivel_acesso.short_description = 'Nível de Acesso'

# Unregister default User admin and register custom one
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'escola', 'nivel_acesso', 'is_developer')
    list_filter = ('nivel_acesso', 'escola', 'is_developer')
    search_fields = ('user__username', 'escola__nome')