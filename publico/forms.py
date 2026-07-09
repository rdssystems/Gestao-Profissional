from django import forms
from .models import BlocoConteudo, CursoEmentaPublico


class BlocoConteudoForm(forms.ModelForm):
    class Meta:
        model = BlocoConteudo
        fields = ['tipo', 'titulo', 'texto', 'data_inicio', 'data_fim',
                  'dias_semana', 'horario_inicio', 'horario_fim', 'ordem', 'ativo']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'texto': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'data_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_fim': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'dias_semana': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Seg, Qua, Sex'}),
            'horario_inicio': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'horario_fim': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'ordem': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class CursoEmentaPublicoForm(forms.ModelForm):
    class Meta:
        model = CursoEmentaPublico
        fields = ['titulo', 'texto', 'ordem', 'ativo']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Informática Básica'}),
            'texto': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Digite a ementa do curso...'}),
            'ordem': forms.NumberInput(attrs={'class': 'form-control'}),
        }
