import qrcode
import qrcode.image.svg
from io import BytesIO, StringIO

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import View, ListView, TemplateView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse

from escolas.models import Escola
from cursos.models import TipoCurso
from alunos.models import Aluno
from alunos.forms import AlunoForm
from .models import BlocoConteudo, CursoEmentaPublico
from .forms import BlocoConteudoForm, CursoEmentaPublicoForm


def generate_qr_svg(url):
    """Gera QR code como SVG raw string."""
    factory = qrcode.image.svg.SvgPathImage
    img = qrcode.make(url, image_factory=factory)
    buf = BytesIO()
    img.save(buf)
    return buf.getvalue().decode()


def can_manage_publico(user):
    """Coordenador ou admin de segmento com acesso Uditech."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    profile = getattr(user, 'profile', None)
    if not profile:
        return False
    if profile.nivel_acesso == 'ADMIN_UDITECH':
        return True
    return user.groups.filter(name='Coordenador').exists() and profile.escola and profile.escola.tipo == 'UDITECH'


class UditechAccessMixin(UserPassesTestMixin):
    def test_func(self):
        return can_manage_publico(self.request.user)


# ============================================================
# PÁGINAS PÚBLICAS (sem login)
# ============================================================

class PublicoHomeView(TemplateView):
    """Cards de todas as Uditechs."""
    template_name = 'publico/publico_home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['escolas'] = Escola.objects.filter(tipo='UDITECH', blocos_conteudo__ativo=True).distinct().order_by('nome')
        context['ementas'] = CursoEmentaPublico.objects.filter(ativo=True)
        return context


class PublicoEscolaView(TemplateView):
    """Blocos de uma Uditech especifica + botao cadastrar."""
    template_name = 'publico/publico_escola.html'

    def dispatch(self, request, *args, **kwargs):
        self.escola = get_object_or_404(Escola, tipo='UDITECH', slug=kwargs.get('slug'))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['escola'] = self.escola
        context['blocos'] = BlocoConteudo.objects.filter(escola=self.escola, ativo=True)
        return context


class PublicoCadastroView(View):
    """CPF lookup + formulario de cadastro."""
    template_name = 'publico/publico_cadastro.html'

    def dispatch(self, request, *args, **kwargs):
        self.escola = get_object_or_404(Escola, tipo='UDITECH', slug=kwargs.get('slug'))
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, slug):
        cpf = request.GET.get('cpf', '')
        aluno = None
        ja_cadastrado = False
        form = None
        cpf_limpo = ''
        if cpf:
            cpf_limpo = ''.join(filter(str.isdigit, cpf))
            if len(cpf_limpo) == 11:
                aluno = Aluno.objects.filter(cpf__icontains=cpf_limpo).first()
                if aluno and aluno.escola == self.escola:
                    ja_cadastrado = True

        if ja_cadastrado:
            pass
        elif aluno:
            form = AlunoForm(instance=aluno, publico_escola=self.escola)
            form.fields.pop('escola', None)
        elif cpf_limpo:
            form = AlunoForm(initial={'cpf': cpf_limpo}, publico_escola=self.escola)
            form.fields.pop('escola', None)

        WHATSAPP_NUMBERS = {
            'uditech-centro': '553432574709',
            'uditech-rondon': '553432298050',
        }
        whatsapp_num = WHATSAPP_NUMBERS.get(slug, '')
        whatsapp_msg = ''
        if ja_cadastrado and aluno:
            from urllib.parse import quote
            whatsapp_msg = quote(f'Olá, sou {aluno.nome_completo} já tenho cadastro nesta unidade e gostaria de me inscrever para um curso.')

        return render(request, self.template_name, {
            'escola': self.escola,
            'cpf': cpf,
            'form': form,
            'aluno_encontrado': bool(aluno) and not ja_cadastrado,
            'ja_cadastrado': ja_cadastrado,
            'aluno_nome': aluno.nome_completo if aluno else '',
            'whatsapp_num': whatsapp_num,
            'whatsapp_msg': whatsapp_msg,
        })

    def post(self, request, slug):
        cpf_raw = request.POST.get('cpf', '')
        cpf_limpo = ''.join(filter(str.isdigit, cpf_raw))
        if not cpf_limpo:
            return redirect(f'{reverse("publico:cadastro", args=[slug])}')

        aluno_existente = Aluno.objects.filter(cpf=cpf_limpo, escola=self.escola).first()

        form = AlunoForm(request.POST, instance=aluno_existente, publico_escola=self.escola)
        form.fields.pop('escola', None)

        if form.is_valid():
            aluno = form.save(commit=False)
            aluno.escola = self.escola
            if cpf_limpo:
                aluno.cpf = cpf_limpo
            aluno.save()
            form.save_m2m()
            messages.success(request, 'Cadastro realizado com sucesso!')
            return redirect(f'{reverse("publico:home")}?success=1')

        return render(request, self.template_name, {
            'escola': self.escola,
            'cpf': cpf_limpo,
            'form': form,
            'aluno_encontrado': bool(aluno_existente),
        })


# ============================================================
# PÁGINAS DE GESTÃO (autenticado, só Uditech)
# ============================================================

class PublicoConfigView(UditechAccessMixin, TemplateView):
    """Lista Uditechs para gerenciar + QR code do link publico."""
    template_name = 'publico/publico_config.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if user.is_superuser:
            escolas = Escola.objects.filter(tipo='UDITECH').order_by('nome')
        else:
            profile = getattr(user, 'profile', None)
            if profile and profile.nivel_acesso == 'ADMIN_UDITECH':
                if profile.escola:
                    escolas = Escola.objects.filter(tipo='UDITECH', id=profile.escola_id).order_by('nome')
                else:
                    escolas = Escola.objects.filter(tipo='UDITECH').order_by('nome')
            elif profile and profile.escola and profile.escola.tipo == 'UDITECH':
                escolas = Escola.objects.filter(tipo='UDITECH', id=profile.escola_id).order_by('nome')
            else:
                escolas = Escola.objects.none()
        context['escolas'] = escolas
        public_url = self.request.build_absolute_uri(reverse('publico:home'))
        context['public_url'] = public_url
        context['qr_svg'] = generate_qr_svg(public_url)
        return context


class BlocoListView(UditechAccessMixin, ListView):
    """Lista blocos de uma Uditech."""
    model = BlocoConteudo
    template_name = 'publico/bloco_list.html'
    context_object_name = 'blocos'

    def dispatch(self, request, *args, **kwargs):
        self.escola = get_object_or_404(Escola, pk=kwargs.get('escola_id'))
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return BlocoConteudo.objects.filter(escola=self.escola)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['escola'] = self.escola
        return context


class BlocoCreateView(UditechAccessMixin, CreateView):
    model = BlocoConteudo
    form_class = BlocoConteudoForm
    template_name = 'publico/bloco_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.escola = get_object_or_404(Escola, pk=kwargs.get('escola_id'))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.escola = self.escola
        messages.success(self.request, 'Bloco criado com sucesso!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('publico:bloco_list', args=[self.escola.pk])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['escola'] = self.escola
        return context


class BlocoUpdateView(UditechAccessMixin, UpdateView):
    model = BlocoConteudo
    form_class = BlocoConteudoForm
    template_name = 'publico/bloco_form.html'

    def form_valid(self, form):
        messages.success(self.request, 'Bloco atualizado com sucesso!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('publico:bloco_list', args=[self.object.escola.pk])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['escola'] = self.object.escola
        return context


class BlocoDeleteView(UditechAccessMixin, DeleteView):
    model = BlocoConteudo
    template_name = 'publico/bloco_confirm_delete.html'

    def get_success_url(self):
        return reverse('publico:bloco_list', args=[self.object.escola.pk])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['escola'] = self.object.escola
        return context


# ============================================================
# GERENCIAMENTO DE CURSOS E EMENTAS PÚBLICAS
# ============================================================

class CursoEmentaListView(UditechAccessMixin, ListView):
    model = CursoEmentaPublico
    template_name = 'publico/ementa_list.html'
    context_object_name = 'ementas'

class CursoEmentaCreateView(UditechAccessMixin, CreateView):
    model = CursoEmentaPublico
    form_class = CursoEmentaPublicoForm
    template_name = 'publico/ementa_form.html'
    success_url = reverse_lazy('publico:ementa_list')

    def form_valid(self, form):
        messages.success(self.request, 'Curso/Ementa criado com sucesso!')
        return super().form_valid(form)

class CursoEmentaUpdateView(UditechAccessMixin, UpdateView):
    model = CursoEmentaPublico
    form_class = CursoEmentaPublicoForm
    template_name = 'publico/ementa_form.html'
    success_url = reverse_lazy('publico:ementa_list')

    def form_valid(self, form):
        messages.success(self.request, 'Curso/Ementa atualizado com sucesso!')
        return super().form_valid(form)

class CursoEmentaDeleteView(UditechAccessMixin, DeleteView):
    model = CursoEmentaPublico
    template_name = 'publico/ementa_confirm_delete.html'
    success_url = reverse_lazy('publico:ementa_list')
