from django import forms
from django.contrib.auth.models import User, Group
from escolas.models import Escola
from django.contrib.auth.forms import AuthenticationForm
from .models import Aluno
from django.utils.translation import gettext_lazy as _
from cursos.models import TipoCurso

class CourseMultipleChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return obj.nome

# Existing AlunoForm
class AlunoForm(forms.ModelForm):
    cursos_interesse = CourseMultipleChoiceField(
        queryset=TipoCurso.objects.none(), # Populated in __init__
        widget=forms.CheckboxSelectMultiple,
        label=_("Cursos de Interesse"),
        required=False
    )

    class Meta:
        model = Aluno
        exclude = ['data_criacao', 'data_atualizacao']
        fields = [
            'escola', 'cursos_interesse', 'nome_completo', 'cpf', 'rg', 'orgao_exp', 'data_emissao',
            'data_nascimento', 'sexo', 'estado_civil', 'cor_raca', 'nome_mae', 'naturalidade',
            'uf_naturalidade', 'deficiencia', 'tipo_deficiencia', 'escolaridade', 'email_principal', 'whatsapp',
            'telefone_principal', 'endereco_cep', 'endereco_rua', 'endereco_numero', 'endereco_bairro',
            'endereco_cidade', 'endereco_estado', 'tempo_moradia', 'tipo_moradia', 'valor_moradia',
            'situacao_profissional', 'renda_individual', 'num_moradores', 'quantos_trabalham',
            'renda_moradores', 'como_soube', 'receber_notificacoes'
        ]
        widgets = {
            'escola': forms.Select(attrs={'class': 'form-select form-select-premium'}),
            'cursos_interesse': forms.CheckboxSelectMultiple,
            'nome_completo': forms.TextInput(attrs={'class': 'form-control form-control-premium'}),
            'cpf': forms.TextInput(attrs={'class': 'form-control form-control-premium', 'inputmode': 'numeric', 'pattern': '[0-9]*'}),
            'rg': forms.TextInput(attrs={'class': 'form-control form-control-premium'}),
            'orgao_exp': forms.TextInput(attrs={'class': 'form-control form-control-premium'}),
            'data_emissao': forms.DateInput(attrs={'class': 'form-control form-control-premium', 'type': 'date'}, format='%Y-%m-%d'),
            'data_nascimento': forms.DateInput(attrs={'class': 'form-control form-control-premium', 'type': 'date'}, format='%Y-%m-%d'),
            'sexo': forms.Select(attrs={'class': 'form-select form-select-premium'}),
            'estado_civil': forms.Select(attrs={'class': 'form-select form-select-premium'}),
            'cor_raca': forms.Select(attrs={'class': 'form-select form-select-premium'}),
            'nome_mae': forms.TextInput(attrs={'class': 'form-control form-control-premium'}),
            'naturalidade': forms.TextInput(attrs={'class': 'form-control form-control-premium'}),
            'uf_naturalidade': forms.TextInput(attrs={'class': 'form-control form-control-premium'}),
            'deficiencia': forms.CheckboxInput(attrs={'class': 'form-check-input', 'onchange': 'toggleDeficiencia(this.checked)'}),
            'tipo_deficiencia': forms.TextInput(attrs={'class': 'form-control form-control-premium', 'placeholder': 'Descreva a deficiência'}),
            'escolaridade': forms.Select(attrs={'class': 'form-select form-select-premium'}),
            'email_principal': forms.EmailInput(attrs={'class': 'form-control form-control-premium'}),
            'whatsapp': forms.TextInput(attrs={'class': 'form-control form-control-premium'}),
            'telefone_principal': forms.TextInput(attrs={'class': 'form-control form-control-premium'}),
            'endereco_cep': forms.TextInput(attrs={'class': 'form-control form-control-premium'}),
            'endereco_rua': forms.TextInput(attrs={'class': 'form-control form-control-premium'}),
            'endereco_numero': forms.TextInput(attrs={'class': 'form-control form-control-premium'}),
            'endereco_bairro': forms.TextInput(attrs={'class': 'form-control form-control-premium'}),
            'endereco_cidade': forms.TextInput(attrs={'class': 'form-control form-control-premium'}),
            'endereco_estado': forms.TextInput(attrs={'class': 'form-control form-control-premium'}),
            'tempo_moradia': forms.Select(attrs={'class': 'form-select form-select-premium'}),
            'tipo_moradia': forms.Select(attrs={'class': 'form-select form-select-premium'}),
            'valor_moradia': forms.NumberInput(attrs={'class': 'form-control form-control-premium'}),
            'situacao_profissional': forms.Select(attrs={'class': 'form-select form-select-premium'}),
            'renda_individual': forms.NumberInput(attrs={'class': 'form-control form-control-premium'}),
            'num_moradores': forms.NumberInput(attrs={'class': 'form-control form-control-premium'}),
            'quantos_trabalham': forms.NumberInput(attrs={'class': 'form-control form-control-premium'}),
            'renda_moradores': forms.NumberInput(attrs={'class': 'form-control form-control-premium'}),
            'como_soube': forms.Select(attrs={'class': 'form-select form-select-premium'}),
            'receber_notificacoes': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'escola': _("Escola"),
            'cursos_interesse': _("Cursos de Interesse"),
            'nome_completo': _("Nome Completo"),
            'cpf': _("CPF"),
            'rg': _("RG"),
            'orgao_exp': _("Órgão Expedidor"),
            'data_emissao': _("Data de Emissão"),
            'data_nascimento': _("Data de Nascimento"),
            'sexo': _("Sexo"),
            'estado_civil': _("Estado Civil"),
            'cor_raca': _("Cor/Raça"),
            'nome_mae': _("Nome da Mãe"),
            'naturalidade': _("Naturalidade"),
            'uf_naturalidade': _("UF Naturalidade"),
            'deficiencia': _("Pessoa com Deficiência?"),
            'tipo_deficiencia': _("Qual a deficiência?"),
            'escolaridade': _("Escolaridade"),
            'email_principal': _("Email Principal"),
            'whatsapp': _("WhatsApp"),
            'telefone_principal': _("Telefone Principal"),
            'endereco_cep': _("CEP"),
            'endereco_rua': _("Rua"),
            'endereco_numero': _("Número"),
            'endereco_bairro': _("Bairro"),
            'endereco_cidade': _("Cidade"),
            'endereco_estado': _("Estado"),
            'tempo_moradia': _("Tempo de Moradia"),
            'tipo_moradia': _("Tipo de Moradia"),
            'valor_moradia': _("Valor da Moradia (R$)"),
            'situacao_profissional': _("Situação Profissional"),
            'renda_individual': _("Renda Individual (R$)"),
            'num_moradores': _("Número de Moradores na Casa"),
            'quantos_trabalham': _("Quantos Trabalham na Casa"),
            'renda_moradores': _("Renda de Outros Moradores (R$)"),
            'como_soube': _("Como Soube do Programa"),
            'receber_notificacoes': _("Deseja receber atualizações de cursos?"),
        }
        error_messages = {
            'nome_completo': {'required': _("Este Campo é Obrigatório")},
            'cpf': {'required': _("Este Campo é Obrigatório")},
            'data_nascimento': {'required': _("Este Campo é Obrigatório")},
            'sexo': {'required': _("Este Campo é Obrigatório")},
            'escola': {'required': _("Este Campo é Obrigatório")},

            'whatsapp': {'required': _("Este Campo é Obrigatório")},
            'endereco_cep': {'required': _("Este Campo é Obrigatório")},
            'endereco_rua': {'required': _("Este Campo é Obrigatório")},
            'endereco_numero': {'required': _("Este Campo é Obrigatório")},
            'endereco_bairro': {'required': _("Este Campo é Obrigatório")},
            'endereco_cidade': {'required': _("Este Campo é Obrigatório")},
            'endereco_estado': {'required': _("Este Campo é Obrigatório")},
            'tempo_moradia': {'required': _("Este Campo é Obrigatório")},
            'tipo_moradia': {'required': _("Este Campo é Obrigatório")},
            'situacao_profissional': {'required': _("Este Campo é Obrigatório")},
            'renda_individual': {'required': _("Este Campo é Obrigatório")},
            'num_moradores': {'required': _("Este Campo é Obrigatório")},
            'quantos_trabalham': {'required': _("Este Campo é Obrigatório")},
            'renda_moradores': {'required': _("Este Campo é Obrigatório")},
            'como_soube': {'required': _("Este Campo é Obrigatório")},
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        # Set default queryset for cursos_interesse
        # Se for superusuário, substituímos o campo para usar o ModelMultipleChoiceField padrão
        # que usa o __str__ do modelo (mostrando "Nome (Escola)"), o que ajuda a identificar a escola.
        if user and user.is_superuser:
            self.fields['cursos_interesse'] = forms.ModelMultipleChoiceField(
                queryset=TipoCurso.objects.all(),
                widget=forms.CheckboxSelectMultiple,
                label=_("Cursos de Interesse"),
                required=False
            )
        else:
            # Para não-superusuários, mantemos o campo customizado (CourseMultipleChoiceField) que mostra apenas o nome
            self.fields['cursos_interesse'].queryset = TipoCurso.objects.all()

        if user and not user.is_superuser:
            if hasattr(user, 'profile') and user.profile.escola:
                if 'escola' in self.fields:
                    self.fields['escola'].queryset = Escola.objects.filter(pk=user.profile.escola.pk)
                # Filter cursos_interesse by the user's school
                if 'cursos_interesse' in self.fields:
                    self.fields['cursos_interesse'].queryset = TipoCurso.objects.filter(escola=user.profile.escola)
            else:
                if 'escola' in self.fields:
                    self.fields['escola'].queryset = Escola.objects.none()
                if 'cursos_interesse' in self.fields:
                    self.fields['cursos_interesse'].queryset = TipoCurso.objects.none()

        required_fields = [
            'whatsapp', 'renda_individual', 'num_moradores', 
            'quantos_trabalham', 'renda_moradores', 'tempo_moradia', 'tipo_moradia'
        ]
        for field_name in required_fields:
            if field_name in self.fields:
                self.fields[field_name].required = True

    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf')
        if cpf:
            cpf_digits = ''.join(filter(str.isdigit, cpf))
            if len(cpf_digits) != 11:
                raise forms.ValidationError('O CPF deve conter exatamente 11 dígitos numéricos.')
            if not cpf_digits.isdigit():
                 raise forms.ValidationError('O CPF deve conter apenas números.')
        return cpf

    def clean_endereco_cep(self):
        cep = self.cleaned_data.get('endereco_cep')
        if cep:
            cep_digits = ''.join(filter(str.isdigit, cep))
            if len(cep_digits) != 8:
                raise forms.ValidationError('O CEP deve conter exatamente 8 dígitos numéricos.')
            if not cep_digits.isdigit():
                 raise forms.ValidationError('O CEP deve conter apenas números.')
        return cep

# Existing AuxiliarAlunoForm
class AuxiliarAlunoForm(AlunoForm):
    """
    Formulário para o Auxiliar Administrativo.
    Permite editar todos os dados, EXCETO Identificação (Nome, CPF, RG, etc.) e Escola.
    """
    class Meta(AlunoForm.Meta):
        model = Aluno
        # Listamos explicitamente os campos permitidos para garantir a exclusão dos de identificação
        fields = [
            'cursos_interesse',
            'sexo', 'estado_civil', 'cor_raca', 'nome_mae', 'naturalidade', 'uf_naturalidade',
            'deficiencia', 'tipo_deficiencia', 'escolaridade',
            'email_principal', 'whatsapp', 'telefone_principal',
            'endereco_cep', 'endereco_rua', 'endereco_numero', 'endereco_bairro',
            'endereco_cidade', 'endereco_estado',
            'tempo_moradia', 'tipo_moradia', 'valor_moradia',
            'situacao_profissional', 'renda_individual', 
            'num_moradores', 'quantos_trabalham', 'renda_moradores',
            'como_soube', 'receber_notificacoes'
        ]
        # Widgets e Labels são herdados de AlunoForm.Meta

    # __init__ é herdado de AlunoForm, mantendo a lógica de user e filtering.

class VerificarCPFForm(forms.Form):
    cpf = forms.CharField(
        label="CPF do Aluno",
        max_length=14,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg', 
            'placeholder': '000.000.000-00',
            'autofocus': 'autofocus'
        })
    )

    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf')
        # Remove characters to leave only digits, or format as needed
        # Here we might just want to ensure it has 11 digits if stripped
        return cpf

# CustomAuthenticationForm (from previous context)
class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Usuário",
        widget=forms.TextInput(attrs={'autofocus': True, 'class': 'form-control form-control-premium'})
    )
    password = forms.CharField(
        label="Senha",
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control form-control-premium'})
    )

# AlunoCSVUploadForm (from previous context)
class AlunoCSVUploadForm(forms.Form):
    csv_file = forms.FileField(label="Selecionar arquivo CSV", help_text="Faça o upload de um arquivo CSV com os dados dos alunos.", widget=forms.FileInput(attrs={'class': 'form-control form-control-premium'}))

# UserCreationForm (from previous context)
class UserCreationForm(forms.ModelForm):
    ROLE_CHOICES = (
        ('Coordenador', 'Coordenador'),
        ('Auxiliar Administrativo', 'Auxiliar Administrativo'),
    )
    
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control form-control-premium'}), label="Senha")
    password_confirm = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control form-control-premium'}), label="Confirmar Senha")
    escola = forms.ModelChoiceField(queryset=Escola.objects.all(), widget=forms.Select(attrs={'class': 'form-select form-select-premium'}), label="Escola")
    role = forms.ChoiceField(choices=ROLE_CHOICES, widget=forms.Select(attrs={'class': 'form-select form-select-premium'}), label="Papel")

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control form-control-premium'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control form-control-premium'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control form-control-premium'}),
        }
        labels = {
            'username': 'Nome de Usuário',
            'first_name': 'Nome',
            'last_name': 'Sobrenome',
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
            role_name = self.cleaned_data.get('role')
            if role_name:
                group, created = Group.objects.get_or_create(name=role_name)
                user.groups.add(group)
            
            escola = self.cleaned_data.get('escola')
            if escola:
                user.profile.escola = escola
                user.profile.save()
        return user