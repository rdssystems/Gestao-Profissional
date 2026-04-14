from django import forms
from .models import Escola

from django.contrib.auth.models import User

class EscolaForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtra apenas usuários que pertencem ao grupo 'Coordenador'
        qs = User.objects.filter(groups__name='Coordenador').order_by('first_name', 'last_name')
        self.fields['coordenador_user'].queryset = qs
        # Define como o nome deve aparecer no dropdown (Nome + Sobrenome)
        self.fields['coordenador_user'].label_from_instance = lambda obj: f"{obj.get_full_name()}" if obj.get_full_name() else obj.username

    class Meta:
        model = Escola
        fields = ['nome', 'endereco', 'email', 'telefone', 'whatsapp', 'coordenador_user']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'endereco': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(99) 9999-9999 ou (99) 99999-9999'}),
            'whatsapp': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(99) 99999-9999'}),
            'coordenador_user': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean_telefone(self):
        telefone = self.cleaned_data['telefone']
        if telefone:
            # Remove todos os caracteres não numéricos
            apenas_numeros = ''.join(filter(str.isdigit, telefone))
            
            # Validação básica de tamanho, se desejar
            if not (10 <= len(apenas_numeros) <= 11):
                raise forms.ValidationError("Número de telefone inválido. Deve ter 10 ou 11 dígitos.")
            
            return apenas_numeros
        return telefone
    def clean_whatsapp(self):
        whatsapp = self.cleaned_data.get('whatsapp')
        if whatsapp:
            apenas_numeros = ''.join(filter(str.isdigit, whatsapp))
            if not (10 <= len(apenas_numeros) <= 11):
                raise forms.ValidationError("Número de WhatsApp inválido.")
            return apenas_numeros
        return whatsapp
