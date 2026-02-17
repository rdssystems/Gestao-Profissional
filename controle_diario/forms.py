from django import forms
from .models import ControleDiario

class ControleDiarioForm(forms.ModelForm):
    class Meta:
        model = ControleDiario
        fields = ['atendimento', 'inscricoes', 'pessoas_presentes', 'ligacoes_recebidas', 'ligacoes_realizadas']
        widgets = {
            'atendimento': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'inscricoes': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'pessoas_presentes': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'ligacoes_recebidas': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'ligacoes_realizadas': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }
