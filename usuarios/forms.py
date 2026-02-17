from django import forms
from django.contrib.auth.models import User, Group
from escolas.models import Escola
from django.contrib.auth.forms import AuthenticationForm # Importar AuthenticationForm

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Usuário",
        widget=forms.TextInput(attrs={'autofocus': True, 'class': 'form-control'})
    )
    password = forms.CharField(
        label="Senha",
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

class UserCreationForm(forms.ModelForm):
    ROLE_CHOICES = (
        ('Coordenador', 'Coordenador'),
        ('Auxiliar Administrativo', 'Auxiliar Administrativo'),
    )
    
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), label="Senha")
    password_confirm = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), label="Confirmar Senha")
    escola = forms.ModelChoiceField(queryset=Escola.objects.all(), widget=forms.Select(attrs={'class': 'form-select'}), label="Escola")
    role = forms.ChoiceField(choices=ROLE_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}), label="Papel")
    email = forms.EmailField(label="Email", widget=forms.EmailInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'username': 'Nome de Usuário',
            'first_name': 'Nome',
            'last_name': 'Sobrenome',
            'email': 'Email',
        }

    def clean_password_confirm(self):
        password = self.cleaned_data.get('password')
        password_confirm = self.cleaned_data.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError("As senhas não coincidem.")
        return password_confirm

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
            # Assign role
            role_name = self.cleaned_data.get('role')
            if role_name:
                # Remove existing roles managed by this form
                managed_roles = ['Coordenador', 'Auxiliar Administrativo']
                groups_to_remove = Group.objects.filter(name__in=managed_roles)
                user.groups.remove(*groups_to_remove)

                # Add new role
                group, created = Group.objects.get_or_create(name=role_name)
                user.groups.add(group)
            
            # Assign escola to profile
            escola = self.cleaned_data.get('escola')
            if escola:
                user.profile.escola = escola
                user.profile.save()

        return user