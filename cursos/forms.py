from django import forms
from .models import Curso, TipoCurso, Inscricao, RegistroAula, Chamada # Adicionar RegistroAula, Chamada
from alunos.models import Aluno
from escolas.models import Escola # Import Escola for queryset filtering
from django.forms import inlineformset_factory # Adicionar import

class CursoForm(forms.ModelForm):
    class Meta:
        model = Curso
        fields = ['escola', 'tipo_curso', 'nome', 'nome_professor', 'carga_horaria', 'data_inicio', 'data_fim', 'turno', 'horario', 'horario_fim', 'dia_inicio_semana', 'dia_fim_semana', 'status']
        widgets = {
            'escola': forms.Select(attrs={'class': 'form-select form-select-premium'}),
            'tipo_curso': forms.Select(attrs={'class': 'form-select form-select-premium'}),
            'nome': forms.TextInput(attrs={'class': 'form-control form-control-premium'}),
            'nome_professor': forms.TextInput(attrs={'class': 'form-control form-control-premium', 'placeholder': 'Opcional'}),
            'carga_horaria': forms.NumberInput(attrs={'class': 'form-control form-control-premium'}),
            'data_inicio': forms.DateInput(attrs={'class': 'form-control form-control-premium', 'type': 'date'}),
            'data_fim': forms.DateInput(attrs={'class': 'form-control form-control-premium', 'type': 'date'}),
            'turno': forms.Select(attrs={'class': 'form-select form-select-premium'}),
            'horario': forms.TimeInput(attrs={'class': 'form-control form-control-premium', 'type': 'time'}),
            'horario_fim': forms.TimeInput(attrs={'class': 'form-control form-control-premium', 'type': 'time'}),
            'dia_inicio_semana': forms.Select(attrs={'class': 'form-select form-select-premium'}),
            'dia_fim_semana': forms.Select(attrs={'class': 'form-select form-select-premium'}),
            'status': forms.Select(attrs={'class': 'form-select form-select-premium'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user and not user.is_superuser:
            if hasattr(user, 'profile') and user.profile.escola:
                escola = user.profile.escola
                self.fields['escola'].queryset = Escola.objects.filter(pk=escola.pk)
                self.fields['escola'].initial = escola
                self.fields['escola'].disabled = True
                self.fields['tipo_curso'].queryset = TipoCurso.objects.filter(escola=escola)
            else:
                self.fields['escola'].queryset = Escola.objects.none()
                self.fields['tipo_curso'].queryset = TipoCurso.objects.none()
        else: # Superuser can see all schools and types
            self.fields['escola'].queryset = Escola.objects.all()
            self.fields['tipo_curso'].queryset = TipoCurso.objects.all()

class InscricaoForm(forms.ModelForm):
    class Meta:
        model = Inscricao
        fields = ['aluno', 'curso']
        widgets = {
            'aluno': forms.Select(attrs={'class': 'form-select form-select-premium'}),
            'curso': forms.Select(attrs={'class': 'form-select form-select-premium'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        curso_id = kwargs.pop('curso_id', None)
        super().__init__(*args, **kwargs)

        if user and not user.is_superuser:
            if hasattr(user, 'profile') and user.profile.escola:
                escola = user.profile.escola
                self.fields['aluno'].queryset = Aluno.objects.filter(escola=escola)
                self.fields['curso'].queryset = Curso.objects.filter(escola=escola, status='Aberta')
            else:
                self.fields['aluno'].queryset = Aluno.objects.none()
                self.fields['curso'].queryset = Curso.objects.none()
        else: # Superuser
            self.fields['curso'].queryset = Curso.objects.filter(status='Aberta')

        if curso_id:
            self.fields['curso'].initial = curso_id
            self.fields['curso'].disabled = True

# --- Novos Formulários para Chamada ---

class RegistroAulaForm(forms.ModelForm):
    class Meta:
        model = RegistroAula
        fields = ['data_aula', 'observacoes'] # Curso será definido na view
        widgets = {
            'data_aula': forms.DateInput(attrs={'class': 'form-control form-control-premium', 'type': 'date'}, format='%Y-%m-%d'),
            'observacoes': forms.Textarea(attrs={'class': 'form-control form-control-premium', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk and not self.initial.get('data_aula'):
            from datetime import date
            self.initial['data_aula'] = date.today()

class ChamadaForm(forms.ModelForm):
    class Meta:
        model = Chamada
        fields = ['inscricao', 'status_presenca']
        widgets = {
            'inscricao': forms.HiddenInput(), # Ocultar o select, pois já exibimos o nome
            'status_presenca': forms.RadioSelect(attrs={'class': 'btn-check'}),
        }
    
    # Adiciona um campo apenas para exibir o nome do aluno no template
    aluno_nome = forms.CharField(label="Aluno", required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-premium', 'readonly': 'readonly'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk: # Se for uma instância existente
            # Define o queryset para a inscrição específica para garantir que seja exibida
            self.fields['inscricao'].queryset = Inscricao.objects.filter(pk=self.instance.inscricao.pk)
            # Preenche o campo de nome do aluno para exibição
            self.fields['aluno_nome'].initial = self.instance.inscricao.aluno.nome_completo
            # Não desativar, pois o navegador não envia campos desativados no POST


# Usar modelformset_factory se Chamada não é diretamente "inline" de RegistroAula (ou seja, se a relação não é diretamente pai-filho no contexto da view)
# No entanto, como o inlineformset_factory é para modelos relacionados, ele é mais apropriado aqui.
# ChamadaFormSet = modelformset_factory(Chamada, form=ChamadaForm, extra=0, can_delete=False)

# Usando inlineformset_factory é mais direto para esta relação
ChamadaFormSet = inlineformset_factory(
    RegistroAula, 
    Chamada, 
    form=ChamadaForm, 
    extra=0, 
    can_delete=False, # Não permitir deletar registros de presença facilmente
    fields=['inscricao', 'status_presenca']
)

class CursoCSVUploadForm(forms.Form):
    csv_file = forms.FileField(label="Selecionar arquivo CSV", help_text="Faça o upload de um arquivo CSV com os dados dos cursos.", widget=forms.FileInput(attrs={'class': 'form-control form-control-premium'}))
