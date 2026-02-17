from django import forms
from .models import Escola

class EscolaForm(forms.ModelForm):
    class Meta:
        model = Escola
        fields = ['nome', 'endereco', 'email', 'telefone', 'coordenador_user']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'endereco': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(99) 9999-9999 ou (99) 99999-9999'}),
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
