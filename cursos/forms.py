from django import forms
from .models import (
    Curso, TipoCurso, Inscricao, RegistroAula, Chamada, Parceiro, 
    EmentaPadrao, AvaliacaoProfessorAluno, AvaliacaoAlunoCurso
)
from alunos.models import Aluno
from escolas.models import Escola
from django.forms import inlineformset_factory

class CursoForm(forms.ModelForm):
    class Meta:
        model = Curso
        fields = ['escola', 'tipo_curso', 'nome', 'nome_professor', 'parceiro', 'carga_horaria', 'vagas', 'data_inicio', 'data_fim', 'turno', 'horario', 'horario_fim', 'dia_inicio_semana', 'dia_fim_semana', 'status']
        widgets = {
            'escola': forms.Select(attrs={'class': 'form-select form-select-premium'}),
            'tipo_curso': forms.Select(attrs={'class': 'form-select form-select-premium'}),
            'nome': forms.TextInput(attrs={'class': 'form-control form-control-premium'}),
            'nome_professor': forms.TextInput(attrs={'class': 'form-control form-control-premium', 'placeholder': 'Opcional'}),
            'parceiro': forms.Select(attrs={'class': 'form-select form-select-premium'}),
            'carga_horaria': forms.NumberInput(attrs={'class': 'form-control form-control-premium'}),
            'vagas': forms.NumberInput(attrs={'class': 'form-control form-control-premium', 'placeholder': 'Ex: 30'}),
            'data_inicio': forms.DateInput(attrs={'class': 'form-control form-control-premium', 'type': 'date'}, format='%Y-%m-%d'),
            'data_fim': forms.DateInput(attrs={'class': 'form-control form-control-premium', 'type': 'date'}, format='%Y-%m-%d'),
            'turno': forms.Select(attrs={'class': 'form-select form-select-premium'}),
            'horario': forms.TimeInput(attrs={'class': 'form-control form-control-premium', 'type': 'time'}, format='%H:%M'),
            'horario_fim': forms.TimeInput(attrs={'class': 'form-control form-control-premium', 'type': 'time'}, format='%H:%M'),
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
                self.fields['parceiro'].queryset = Parceiro.objects.filter(escola=escola)
            else:
                self.fields['escola'].queryset = Escola.objects.none()
                self.fields['tipo_curso'].queryset = TipoCurso.objects.none()
                self.fields['parceiro'].queryset = Parceiro.objects.none()
        else:
            self.fields['escola'].queryset = Escola.objects.all()
            self.fields['tipo_curso'].queryset = TipoCurso.objects.all()
            self.fields['parceiro'].queryset = Parceiro.objects.all()

        self.fields['data_inicio'].required = True
        self.fields['data_fim'].required = True
        self.fields['turno'].required = True
        self.fields['horario'].required = True
        self.fields['carga_horaria'].required = True
        self.fields['vagas'].required = True

        if not self.instance.pk:
            self.fields['status'].initial = 'Aberta'

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
        else:
            self.fields['curso'].queryset = Curso.objects.filter(status='Aberta')

        if curso_id:
            self.fields['curso'].initial = curso_id
            self.fields['curso'].disabled = True

    def clean(self):
        cleaned_data = super().clean()
        aluno = cleaned_data.get('aluno')
        curso = cleaned_data.get('curso')

        if aluno and curso:
            from .validators import validar_conflito_matricula
            from django.core.exceptions import ValidationError
            try:
                validar_conflito_matricula(aluno, curso)
            except ValidationError as e:
                raise forms.ValidationError(e.message)

        return cleaned_data

class RegistroAulaForm(forms.ModelForm):
    class Meta:
        model = RegistroAula
        fields = ['data_aula', 'observacoes']
        widgets = {
            'data_aula': forms.DateInput(attrs={'class': 'form-control form-control-premium', 'type': 'date'}, format='%Y-%m-%d'),
            'observacoes': forms.Textarea(attrs={'class': 'form-control form-control-premium', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.curso = kwargs.pop('curso', None)
        super().__init__(*args, **kwargs)
        if not self.instance.pk and not self.initial.get('data_aula'):
            from datetime import date
            self.initial['data_aula'] = date.today()

class ChamadaForm(forms.ModelForm):
    class Meta:
        model = Chamada
        fields = ['inscricao', 'status_presenca']
        widgets = {
            'inscricao': forms.HiddenInput(),
            'status_presenca': forms.RadioSelect(attrs={'class': 'btn-check'}),
        }
    
    aluno_nome = forms.CharField(label="Aluno", required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-premium', 'readonly': 'readonly'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['inscricao'].queryset = Inscricao.objects.filter(pk=self.instance.inscricao.pk)
            self.fields['aluno_nome'].initial = self.instance.inscricao.aluno.nome_completo

ChamadaFormSet = inlineformset_factory(
    RegistroAula, 
    Chamada, 
    form=ChamadaForm, 
    extra=0, 
    can_delete=False,
    fields=['inscricao', 'status_presenca']
)

class CursoCSVUploadForm(forms.Form):
    csv_file = forms.FileField(label="Selecionar arquivo CSV", help_text="Faça o upload de um arquivo CSV com os dados dos cursos.", widget=forms.FileInput(attrs={'class': 'form-control form-control-premium'}))

class ParceiroForm(forms.ModelForm):
    class Meta:
        model = Parceiro
        fields = ['escola', 'nome']
        widgets = {
            'escola': forms.Select(attrs={'class': 'form-select form-select-premium'}),
            'nome': forms.TextInput(attrs={'class': 'form-control form-control-premium', 'placeholder': 'Nome da empresa ou parceiro'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user and not user.is_superuser and hasattr(user, 'profile') and user.profile.escola:
            self.fields['escola'].queryset = Escola.objects.filter(pk=user.profile.escola.pk)
            self.fields['escola'].initial = user.profile.escola
            self.fields['escola'].disabled = True
        elif not user.is_superuser:
            self.fields['escola'].queryset = self.fields['escola'].queryset.none()

class EmentaPadraoForm(forms.ModelForm):
    class Meta:
        model = EmentaPadrao
        fields = ['titulo', 'conteudo']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control form-control-premium', 'placeholder': 'Ex: Informática Básica'}),
            'conteudo': forms.Textarea(attrs={'class': 'form-control form-control-premium', 'rows': 15, 'placeholder': 'Digite o conteúdo programático aqui...'}),
        }

# --- Novos Formulários de Avaliação ---

class AvaliacaoProfessorAlunoForm(forms.ModelForm):
    class Meta:
        model = AvaliacaoProfessorAluno
        fields = [
            'conceptual_pratico', 'conceptual_teorico', 'conceptual_nota',
            'behavioral_pratico', 'behavioral_teorico', 'behavioral_nota',
            'attitudinal_pratico', 'attitudinal_teorico', 'attitudinal_nota'
        ]
        widgets = {
            'conceptual_pratico': forms.RadioSelect(attrs={'class': 'btn-check'}),
            'conceptual_teorico': forms.RadioSelect(attrs={'class': 'btn-check'}),
            'conceptual_nota': forms.RadioSelect(attrs={'class': 'btn-check'}),
            'behavioral_pratico': forms.RadioSelect(attrs={'class': 'btn-check'}),
            'behavioral_teorico': forms.RadioSelect(attrs={'class': 'btn-check'}),
            'behavioral_nota': forms.RadioSelect(attrs={'class': 'btn-check'}),
            'attitudinal_pratico': forms.RadioSelect(attrs={'class': 'btn-check'}),
            'attitudinal_teorico': forms.RadioSelect(attrs={'class': 'btn-check'}),
            'attitudinal_nota': forms.RadioSelect(attrs={'class': 'btn-check'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove default selection and the empty "---------" choice
        for field_name in self.fields:
            field = self.fields[field_name]
            if isinstance(field.widget, forms.RadioSelect):
                field.initial = None
                # Force choice list to exclude the empty choice (usually index 0)
                if field.choices and field.choices[0][0] in (None, ''):
                    field.choices = field.choices[1:]
                field.required = True

class AvaliacaoAlunoCursoForm(forms.ModelForm):
    class Meta:
        model = AvaliacaoAlunoCurso
        fields = [
            'c1_1', 'c1_2', 'c1_3',
            'c2_1', 'c2_2', 'c2_3', 'c2_4', 'c2_5', 'c2_6', 'c2_7', 'c2_8', 'c2_9',
            'c3_1', 'c3_2', 'c3_3', 'c3_4',
            'c4_1', 'c4_2', 'c4_3', 'c4_4',
            'como_soube', 'como_soube_outro', 'comentarios'
        ]
        widgets = {
            'c1_1': forms.RadioSelect(attrs={'class': 'btn-check'}),
            'c1_2': forms.RadioSelect(attrs={'class': 'btn-check'}),
            'c1_3': forms.RadioSelect(attrs={'class': 'btn-check'}),
            'c2_1': forms.RadioSelect(attrs={'class': 'btn-check'}),
            'c2_2': forms.RadioSelect(attrs={'class': 'btn-check'}),
            'c2_3': forms.RadioSelect(attrs={'class': 'btn-check'}),
            'c2_4': forms.RadioSelect(attrs={'class': 'btn-check'}),
            'c2_5': forms.RadioSelect(attrs={'class': 'btn-check'}),
            'c2_6': forms.RadioSelect(attrs={'class': 'btn-check'}),
            'c2_7': forms.RadioSelect(attrs={'class': 'btn-check'}),
            'c2_8': forms.RadioSelect(attrs={'class': 'btn-check'}),
            'c2_9': forms.RadioSelect(attrs={'class': 'btn-check'}),
            'c3_1': forms.RadioSelect(attrs={'class': 'btn-check'}),
            'c3_2': forms.RadioSelect(attrs={'class': 'btn-check'}),
            'c3_3': forms.RadioSelect(attrs={'class': 'btn-check'}),
            'c3_4': forms.RadioSelect(attrs={'class': 'btn-check'}),
            'c4_1': forms.RadioSelect(attrs={'class': 'btn-check'}),
            'c4_2': forms.RadioSelect(attrs={'class': 'btn-check'}),
            'c4_3': forms.RadioSelect(attrs={'class': 'btn-check'}),
            'c4_4': forms.RadioSelect(attrs={'class': 'btn-check'}),
            'como_soube': forms.RadioSelect(attrs={'class': 'btn-check'}),
            'como_soube_outro': forms.TextInput(attrs={'class': 'form-control form-control-premium', 'placeholder': 'Se outros, especifique...'}),
            'comentarios': forms.Textarea(attrs={'class': 'form-control form-control-premium', 'rows': 4, 'placeholder': 'Deixe seu comentário ou sugestão...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove default selection and the empty "---------" choice
        for field_name in self.fields:
            field = self.fields[field_name]
            if isinstance(field.widget, forms.RadioSelect):
                field.initial = None
                # Force choice list to exclude the empty choice (usually index 0)
                if field.choices and field.choices[0][0] in (None, ''):
                    field.choices = field.choices[1:]
                field.required = True
