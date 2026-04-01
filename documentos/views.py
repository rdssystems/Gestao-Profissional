import os
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, CreateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.views import View
from .models import DocumentoUnidade, Pasta
from escolas.models import Escola

class HasEscolaOrSuperuserMixin(UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        if user.is_superuser:
            return True
        if hasattr(user, 'profile') and user.profile.escola:
            return True
        return False

class DocumentoListView(LoginRequiredMixin, HasEscolaOrSuperuserMixin, ListView):
    model = DocumentoUnidade
    template_name = 'documentos/lista_documentos.html'
    context_object_name = 'documentos'
    paginate_by = 24

    def get_queryset(self):
        user = self.request.user
        queryset = DocumentoUnidade.objects.all().select_related('escola', 'uploaded_by', 'pasta')
        
        # Filtro de Escola (Obrigatório para usuários comuns, opcional para Admin)
        if not user.is_superuser:
            if hasattr(user, 'profile') and user.profile.escola:
                # Comum vê da sua escola OU globais (escola__isnull=True)
                queryset = queryset.filter(Q(escola=user.profile.escola) | Q(escola__isnull=True))
            else:
                return DocumentoUnidade.objects.none()
        else:
            # Filtro para Admin
            escola_id = self.request.GET.get('escola')
            if escola_id:
                if escola_id == 'todas':
                     queryset = queryset.filter(escola__isnull=True)
                else:
                     # Se selecionar uma escola, Admin vê da escola + Globais na raiz
                     queryset = queryset.filter(Q(escola_id=escola_id) | Q(escola__isnull=True))
            else:
                # Se não selecionar nada, Admin vê TUDO ou apenas globais?
                # Vamos mostrar apenas os Globais na raiz se nada estiver selecionado para organização.
                queryset = queryset.filter(escola__isnull=True)
        
        # Filtro de Pasta
        pasta_id = self.request.GET.get('pasta')
        if pasta_id:
            queryset = queryset.filter(pasta_id=pasta_id)
        else:
            # Se não buscar por pasta, mostra só os da raiz (sem pasta) se não estiver fazendo busca geral
            search = self.request.GET.get('q')
            if not search:
                queryset = queryset.filter(pasta__isnull=True)
        
        # Busca por nome
        search = self.request.GET.get('q')
        if search:
            queryset = queryset.filter(nome__icontains=search)
            
        return queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if user.is_superuser:
            context['escolas'] = Escola.objects.all().order_by('nome')
        context['q'] = self.request.GET.get('q', '')
        context['escola_selecionada'] = self.request.GET.get('escola', '')
        
        pasta_id = self.request.GET.get('pasta')
        pasta_atual = None
        
        # Filtrar Pastas
        pastas_qs = Pasta.objects.all()
        if not user.is_superuser:
            if hasattr(user, 'profile') and user.profile.escola:
                pastas_qs = pastas_qs.filter(Q(escola=user.profile.escola) | Q(escola__isnull=True))
            else:
                pastas_qs = Pasta.objects.none()
        else:
            escola_id = self.request.GET.get('escola')
            if escola_id:
                if escola_id == 'todas':
                     pastas_qs = pastas_qs.filter(escola__isnull=True)
                else:
                     pastas_qs = pastas_qs.filter(Q(escola_id=escola_id) | Q(escola__isnull=True))
            else:
                pastas_qs = pastas_qs.filter(escola__isnull=True)
        
        if pasta_id:
            pasta_atual = get_object_or_404(Pasta, id=pasta_id)
            context['pasta_atual'] = pasta_atual
            context['caminho'] = pasta_atual.get_caminho()
            if not context['q']:
                context['pastas'] = pastas_qs.filter(pasta_pai=pasta_atual)
        else:
            if not context['q']:
                context['pastas'] = pastas_qs.filter(pasta_pai__isnull=True)
                
        return context

class DocumentoUploadView(LoginRequiredMixin, HasEscolaOrSuperuserMixin, CreateView):
    model = DocumentoUnidade
    fields = ['arquivo', 'nome', 'categoria', 'escola']
    template_name = 'documentos/documento_form.html'
    success_url = reverse_lazy('documentos:lista_documentos')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user = self.request.user
        # Se não for superuser, trava a escola do usuário
        if not user.is_superuser:
            if hasattr(user, 'profile') and user.profile.escola:
                form.fields['escola'].queryset = Escola.objects.filter(id=user.profile.escola.id)
                form.fields['escola'].initial = user.profile.escola
                # Em Django forms normais, marcar como disabled às vezes causa problema no submit (campo vazio).
                # Pode usar initial e ocultar ou apenas restringir o queryset (já feito).
        return form

    def form_valid(self, form):
        form.instance.uploaded_by = self.request.user
        # O nome é opcional, se não preenchido o model assume o nome do arquivo, mas a view lida com a msg
        messages.success(self.request, "Documento enviado com sucesso!")
        return super().form_valid(form)

class DocumentoDeleteView(LoginRequiredMixin, HasEscolaOrSuperuserMixin, DeleteView):
    model = DocumentoUnidade
    success_url = reverse_lazy('documentos:lista_documentos')
    
    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return DocumentoUnidade.objects.all()
        if hasattr(user, 'profile') and user.profile.escola:
            return DocumentoUnidade.objects.filter(escola=user.profile.escola)
        return DocumentoUnidade.objects.none()

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        # Remover arquivo físico
        if obj.arquivo:
            if os.path.isfile(obj.arquivo.path):
                os.remove(obj.arquivo.path)
        messages.success(self.request, "Documento removido com sucesso.")
        return super().delete(request, *args, **kwargs)

class PastaCreateView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_superuser

    def post(self, request, *args, **kwargs):
        nome = request.POST.get('nome')
        escola_id = request.POST.get('escola')
        pasta_pai_id = request.POST.get('pasta_pai')
        
        if not nome:
            messages.error(request, "Nome é obrigatórios para criar a pasta.")
        else:
            pasta_pai = get_object_or_404(Pasta, id=pasta_pai_id) if pasta_pai_id else None
            escola = None
            if escola_id and escola_id != 'todas':
                escola = get_object_or_404(Escola, id=escola_id)
            
            Pasta.objects.create(
                nome=nome,
                escola=pasta_pai.escola if pasta_pai else escola,
                pasta_pai=pasta_pai,
                criado_por=request.user
            )
            messages.success(request, f"Pasta '{nome}' criada com sucesso!")
            
        url = reverse_lazy('documentos:lista_documentos')
        # Limpar parâmetros de redirecionamento ou manter contextual?
        # É melhor redirecionar para a pasta criada ou pai.
        if pasta_pai_id:
            return redirect(f"{url}?pasta={pasta_pai_id}")
        return redirect(url)

class PastaDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Pasta
    success_url = reverse_lazy('documentos:lista_documentos')

    def test_func(self):
        return self.request.user.is_superuser

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Pasta removida com sucesso.")
        return super().delete(request, *args, **kwargs)

class DocumentoAjaxUploadView(LoginRequiredMixin, HasEscolaOrSuperuserMixin, View):
    def post(self, request, *args, **kwargs):
        arquivo = request.FILES.get('arquivo')
        nome = request.POST.get('nome', '')
        pasta_id = request.POST.get('pasta_id')
        
        user = request.user
        
        if not arquivo:
            return JsonResponse({'sucesso': False, 'erro': 'Nenhum arquivo enviado.'}, status=400)
            
        if user.is_superuser:
            escola_id = request.POST.get('escola_id')
            if escola_id == 'todas' or not escola_id:
                 escola = None
            else:
                 escola = get_object_or_404(Escola, id=escola_id)
        else:
            if not hasattr(user, 'profile') or not user.profile.escola:
                return JsonResponse({'sucesso': False, 'erro': 'Usuário sem escola vinculada.'}, status=403)
            escola = user.profile.escola
            
        pasta = None
        if pasta_id:
            pasta = get_object_or_404(Pasta, id=pasta_id)
            # Se não for superuser, verifica se a pasta é compatível (seja da escola dele ou Global)
            if not user.is_superuser:
                 if pasta.escola and pasta.escola != escola:
                      return JsonResponse({'sucesso': False, 'erro': 'Acesso negado à pasta dessa escola.'}, status=403)
            
            # Se a pasta existe, o documento DEVE herdar a escola da pasta (pode ser None/Global)
            escola = pasta.escola
                 
                 
        doc = DocumentoUnidade.objects.create(
            escola=escola,
            pasta=pasta,
            nome=nome or arquivo.name,
            arquivo=arquivo,
            uploaded_by=user,
            categoria='outros'
        )
        
        return JsonResponse({
            'sucesso': True, 
            'mensagem': 'Upload concluído!',
            'documento': {
                'id': doc.id,
                'nome': doc.nome
            }
        })
