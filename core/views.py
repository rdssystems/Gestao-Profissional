from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from cursos.models import Curso, TipoCurso, Inscricao
from alunos.models import Aluno
from escolas.models import Escola # Import Escola
from django.http import JsonResponse
from django.urls import reverse
from datetime import timedelta, date, time
from django.db.models import Prefetch, Exists, OuterRef # Import Exists and OuterRef
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from core.models import AuditLog, Aviso, Profile
from django.contrib.auth.models import User
from django.contrib import messages # Adicionado o import para messages

# ... (omitted calendar_view, get_course_events, sobre_view, limpar_agenda_cursos_view, AuditLogListView)

@login_required
def marcar_aviso_lido(request, aviso_pk):
    aviso = get_object_or_404(Aviso, pk=aviso_pk)
    aviso.visualizado_por.add(request.user)
    return JsonResponse({'status': 'ok'})

@login_required
@user_passes_test(lambda u: u.is_superuser) # Superuser can manage, but link only shows for 'developer'
def gerenciar_avisos(request):
    # Verificar se é o desenvolvedor (pode ser pelo flag Profile.is_developer)
    if not hasattr(request.user, 'profile') or not request.user.profile.is_developer:
        messages.error(request, "Acesso restrito ao desenvolvedor.")
        return redirect('escolas:dashboard')

    if request.method == 'POST':
        titulo = request.POST.get('titulo')
        conteudo = request.POST.get('conteudo')
        if titulo and conteudo:
            Aviso.objects.create(titulo=titulo, conteudo=conteudo)
            messages.success(request, "Atualização postada com sucesso!")
            return redirect('core:gerenciar_avisos')
    
    avisos = Aviso.objects.all()
    return render(request, 'core/gerenciar_avisos.html', {'avisos': avisos})

@login_required
def ativar_dev_view(request):
    """View secreta para o desenvolvedor ativar seu status em qualquer uma de suas contas admin"""
    if request.method == 'POST':
        senha_dev = request.POST.get('senha_dev')
        # Senha que sugeri ou você pode mudar
        if senha_dev == 'Klisman@Dev2026':
            profile, created = Profile.objects.get_or_create(user=request.user)
            profile.is_developer = True
            profile.save()
            messages.success(request, "Modo Desenvolvedor Ativado com sucesso!")
            return redirect('escolas:dashboard')
        else:
            messages.error(request, "Senha incorreta.")
    
    return render(request, 'core/ativar_dev.html')


@login_required
def calendar_view(request):
    # Filtros
    curso_nome_filter = request.GET.get('curso_nome', '')
    escola_nome_filter = request.GET.get('escola_nome', '')

    # Base query for courses (Apenas 'Aberta' e 'Em Andamento' - exclui 'Concluído' e 'Arquivado')
    cursos_qs = Curso.objects.filter(status__in=['Aberta', 'Em Andamento']).order_by('data_inicio', 'horario')
    
    if curso_nome_filter:
        cursos_qs = cursos_qs.filter(nome__icontains=curso_nome_filter)

    # Fetch schools with their related courses
    schools = Escola.objects.all().order_by('nome').prefetch_related(
        Prefetch('cursos', queryset=cursos_qs)
    )

    if escola_nome_filter:
        schools = schools.filter(nome=escola_nome_filter)

    # Filter out schools with no courses if desired? 
    # Or keep them to show empty tables? 
    # User said "crie uma tabela para cada unidade com seus respectivos cursos".
    # I'll pass all schools.

    context = {
        'schools': schools,
        'curso_nome_filter': curso_nome_filter,
        'escola_nome_filter': escola_nome_filter,
        'todas_escolas': Escola.objects.all().order_by('nome'), # For filter dropdown
    }
    return render(request, 'core/calendar.html', context)

# Esta view não é mais usada diretamente no template calendar.html, mas mantida para referência se o FullCalendar for reintroduzido.
@login_required
def get_course_events(request):
    events = []
    for curso in Curso.objects.filter(status__in=['Aberta', 'Em Andamento']):
        # Convertendo data_inicio e data_fim para string no formato ISO 8601
        # e adicionando o horário se disponível
        start_datetime = f"{curso.data_inicio.isoformat()}"
        if curso.horario:
            start_datetime += f"T{curso.horario.isoformat()}"

        end_datetime = f"{curso.data_fim.isoformat()}"
        
        if not curso.horario:
            end_date_for_fullcalendar = curso.data_fim + timedelta(days=1)
            end_datetime = f"{end_date_for_fullcalendar.isoformat()}"

        events.append({
            'title': f'{curso.nome} ({curso.escola.nome})',
            'start': start_datetime,
            'end': end_datetime,
            'url': reverse('cursos:detalhe_curso', kwargs={'pk': curso.pk}), # Link para o detalhe do curso
            'backgroundColor': '#4C7DF0', # Cor de exemplo
            'borderColor': '#4C7DF0',
            'allDay': not bool(curso.horario), # Se não tem horário, é um evento de dia inteiro
        })
    return JsonResponse(events, safe=False)


def sobre_view(request):
    sobre_content = """
# Sistema de Gestão de Qualificação Profissional

## <i class="bi bi-book"></i> Sobre o Projeto

O **Sistema de Gestão de Qualificação Profissional** é uma plataforma web desenvolvida em **Django** para gerenciar cursos de qualificação, matrículas de alunos, escolas e controle de frequência. O sistema foi projetado para atender à Diretoria de Qualificação Profissional, permitindo o gerenciamento centralizado de múltiplas escolas/unidades de ensino, com foco em critérios socioeconômicos para priorização de vagas (Score).

O software oferece um fluxo completo desde o cadastro de alunos, criação de cursos, matrícula (com validação de conflitos de horário), lista de chamada e relatórios via dashboard.

---

## <i class="bi bi-rocket-takeoff"></i> Principais Funcionalidades

### <i class="bi bi-building"></i> Gestão de Escolas
- Cadastro e gerenciamento de unidades de ensino (Escolas).
- Painel (Dashboard) específico para cada escola ou visão global para administradores.
- Métricas em tempo real: total de alunos, matrículas, desistências, cursos ativos.

### <i class="bi bi-people"></i> Gestão de Alunos (Candidatos)
- Cadastro completo de alunos com dados pessoais, socioeconômicos e de contato.
- **Busca Inteligente**: Localize alunos rapidamente pelo Nome ou CPF na listagem.
- **Gestão Multi-Escola**:
  - O sistema permite o cadastro do mesmo aluno em diferentes escolas (unidades).
  - **Clonagem de Cadastro**: Ao tentar cadastrar um aluno já existente em outra unidade, o sistema alerta e oferece a opção de importar os dados cadastrais, evitando retrabalho e duplicidade de digitação.
  - **Prevenção de Duplicidade**: Bloqueia o cadastro de um CPF se ele já estiver matriculado na mesma escola.
- **Cálculo Automático de Score**: O sistema calcula uma pontuação para cada aluno com base em critérios de vulnerabilidade social (Renda, Nº de Moradores, Situação de Trabalho, etc.), facilitando a priorização no preenchimento de vagas.
- **Importação em Massa**: Upload de alunos via arquivo **CSV** ou planilha **XLSX**, com validação de dados.
- Histórico de matrículas do aluno.

### <i class="bi bi-journal-bookmark"></i> Gestão de Cursos
- Criação de cursos com definição de carga horária, turnos (Manhã, Tarde, Noite) e horários específicos.
- Categorização por **Tipos de Curso** (ex: Informática, Beleza, Gastronomia) com etiquetas coloridas personalizáveis.
- Status do curso: Aberta, Em Andamento, Concluído.
- Validação de datas (Início e Fim).
- **Importação de Cursos**: Upload em massa via CSV.

### <i class="bi bi-file-earmark-pdf"></i> Documentos e Declarações
- **Geração Automática**: Emissão de declarações de matrícula, cursando ou concluído.
- **Validação de Regras**: 
  - O sistema impede a emissão de declarações para alunos menores de 16 anos.
  - Bloqueio automático para alunos com status de **Desistente**.
- **Assinatura Digital**: Recurso para coleta de assinatura digital no momento da emissão.
- **Validação por QR/Hash**: Cada declaração emitida possui um código único de autenticidade para verificação posterior.

---

## <i class="bi bi-shield-lock"></i> Perfis de Usuário e Permissões

O sistema possui hierarquia de acesso para garantir segurança e organização:

### 1. Superusuário (Administrador Geral)
- **Acesso Total**: Visualiza dados de todas as escolas.
- **Gestão Administrativa**: Pode criar novas escolas, novos usuários e configurar as regras de Score.
- **Auditoria**: Acesso a logs e ferramentas de importação em massa (CSV/XLSX).
- **Menu Exclusivo**: Acesso ao Django Admin e configurações globais.

### 2. Coordenador de Escola
- **Escopo Local**: Acesso restrito aos dados da sua escola vinculada.
- **Documentação**: Pode emitir, assinar e salvar novas declarações para os alunos.
- **Gestão Completa da Escola**: Pode criar cursos, matricular alunos, editar dados de identificação e gerenciar a equipe daquela unidade.

### 3. Auxiliar Administrativo
- **Operacional**: Focado no dia a dia da secretaria da escola.
- **Permissões**:
  - Pode cadastrar e editar dados de contato/endereço dos alunos (os campos CPF, RG e Nome são fixos).
  - Pode realizar matrículas através da guia específica.
  - Pode consultar e imprimir histórico de declarações já existentes.
  - Pode lançar chamadas/frequência.
- **Restrições**: **Não pode emitir/salvar** novas declarações e não pode excluir registros críticos.

---

## <i class="bi bi-tools"></i> Tecnologias utilizadas

- **Backend**: Python 3.12+, Django 5.2.8
- **Banco de Dados**: PostgreSQL (Principal em produção/Docker), com suporte a SQLite para testes.
- **Cache & Real-time**: Redis e Django Channels (para notificações e atualizações dinâmicas).
- **Infraestrutura**: Docker e Docker Compose (Containerização completa).
- **Frontend**: HTML5, CSS3, Bootstrap 5 (Design responsivo e moderno), JavaScript.
- **Bibliotecas Principais**:
  - `openpyxl`: Geração e leitura de planilhas Excel.
  - `django-widget-tweaks`: Manipulação de formulários.
  - `django-dbbackup`: Sistema automatizado de backups do banco e mídia.
  - `daphne`: Servidor ASGI para suporte a WebSockets.

---

## <i class="bi bi-person-lines-fill"></i> Contato do Desenvolvedor

**Klisman rDs**  
📱 (34) 99764-8892 <a href="https://wa.me/5534997648892" target="_blank" class="text-success"><i class="bi bi-whatsapp"></i></a>
✉️ klismanrds@gmail.com
"""
    # Using a simple template for now. Markdown rendering might need a library if not handled by frontend.
    # For now, I'll assume the template will just display this raw string.
    # If the user wants markdown rendered, we'd need to convert it to HTML.
    context = {
        'sobre_content': sobre_content
    }
    return render(request, 'core/about.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser or (hasattr(u, 'profile') and u.profile.escola))
def limpar_agenda_cursos_view(request):
    if request.method == 'POST':
        if not request.user.is_superuser and hasattr(request.user, 'profile') and request.user.profile.escola:
            escola_do_usuario = request.user.profile.escola
            cursos_para_excluir = Curso.objects.filter(
                escola=escola_do_usuario,
                status='Aberta'
            ).annotate(
                has_inscricoes=Exists(
                    Inscricao.objects.filter(curso=OuterRef('pk'))
                )
            ).filter(has_inscricoes=False)
            
            count = cursos_para_excluir.update(status='Arquivado')
            messages.success(request, f"{count} cursos 'Aberta' sem inscrições foram ARQUIVADOS da agenda da escola {escola_do_usuario.nome}.")
        elif request.user.is_superuser:
            cursos_para_excluir = Curso.objects.filter(
                status='Aberta'
            ).annotate(
                has_inscricoes=Exists(
                    Inscricao.objects.filter(curso=OuterRef('pk'))
                )
            ).filter(has_inscricoes=False)
            
            count = cursos_para_excluir.update(status='Arquivado')
            messages.success(request, f"{count} cursos 'Aberta' sem inscrições foram ARQUIVADOS de todas as agendas.")
        else:
            messages.error(request, "Permissão negada para esta ação.")
    else:
        messages.error(request, "Método não permitido para esta ação.")

    return redirect('core:agenda') # Redireciona de volta para a agenda

class AuditLogListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = AuditLog
    template_name = 'core/audit_log_list.html'
    context_object_name = 'logs'
    paginate_by = 25

    def test_func(self):
        return self.request.user.is_superuser

    def get_queryset(self):
        qs = AuditLog.objects.select_related('usuario', 'content_type').all()
        
        # Filtros
        usuario_id = self.request.GET.get('usuario')
        data_inicio = self.request.GET.get('data_inicio')
        data_fim = self.request.GET.get('data_fim')

        if usuario_id:
            qs = qs.filter(usuario_id=usuario_id)
        if data_inicio:
            qs = qs.filter(data_hora__date__gte=data_inicio)
        if data_fim:
            qs = qs.filter(data_hora__date__lte=data_fim)
            
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['usuarios'] = User.objects.filter(audit_logs__isnull=False).distinct()
        return context
