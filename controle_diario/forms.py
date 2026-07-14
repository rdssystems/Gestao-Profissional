from django import forms
from .models import ControleDiario, RelatorioDiarioSine

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


class RelatorioDiarioSineForm(forms.ModelForm):
    class Meta:
        model = RelatorioDiarioSine
        exclude = ['data', 'usuario']
        widgets = {
            'atendimento_trabalhador': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'atendimento_trabalhador_online': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'atendimento_empregador': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'atendimento_empregador_online': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'seguro_desemprego': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'ctps_digital': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'vagas_captadas': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'curriculos': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'entrevistados': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'processo_seletivo': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'orientacao_profissional': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'ligacoes_recebidas': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'ligacoes_realizadas': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }
