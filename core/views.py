from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from cursos.models import Curso, TipoCurso, Inscricao
from alunos.models import Aluno
from escolas.models import Escola # Import Escola
from django.http import JsonResponse
from django.urls import reverse
from datetime import timedelta, date, time
from django.db.models import Prefetch, Exists, OuterRef # Import Exists and OuterRef
from django.views.generic import ListView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from core.models import AuditLog, Aviso, Profile
from django.contrib.auth.models import User
from django.contrib import messages # Adicionado o import para messages
from django.contrib.auth.views import LoginView

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
@user_passes_test(lambda u: u.is_superuser)
def gerenciar_email_destinatarios(request):
    """Gerencia os destinatários e o agendamento do relatório do Controle Diário por e-mail."""
    from core.models import EmailDestinatario, AgendamentoEmail

    agendamento = AgendamentoEmail.get_config()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add':
            nome = request.POST.get('nome', '').strip()
            email = request.POST.get('email', '').strip()
            if nome and email:
                obj, created = EmailDestinatario.objects.get_or_create(
                    email=email,
                    defaults={
                        'nome': nome, 
                        'adicionado_por': request.user,
                        'receber_cp': 'receber_cp' in request.POST,
                        'receber_uditech': 'receber_uditech' in request.POST,
                        'receber_sine': 'receber_sine' in request.POST,
                    }
                )
                if created:
                    messages.success(request, f"✅ {nome} ({email}) adicionado com sucesso!")
                else:
                    messages.warning(request, f"⚠️ O e-mail {email} já estava cadastrado.")
            else:
                messages.error(request, "Preencha o nome e o e-mail.")

        elif action == 'toggle_pref':
            pk = request.POST.get('pk')
            pref = request.POST.get('pref')
            dest = get_object_or_404(EmailDestinatario, pk=pk)
            if pref == 'cp':
                dest.receber_cp = not dest.receber_cp
            elif pref == 'uditech':
                dest.receber_uditech = not dest.receber_uditech
            elif pref == 'sine':
                dest.receber_sine = not dest.receber_sine
            dest.save()
            status_pref = "ativado" if getattr(dest, f'receber_{pref}') else "desativado"
            messages.info(request, f"Recebimento de dados de {pref.upper()} para {dest.nome} {status_pref}.")

        elif action == 'toggle':
            pk = request.POST.get('pk')
            dest = get_object_or_404(EmailDestinatario, pk=pk)
            dest.ativo = not dest.ativo
            dest.save()
            status = "ativado" if dest.ativo else "desativado"
            messages.info(request, f"E-mail de {dest.nome} {status}.")

        elif action == 'delete':
            pk = request.POST.get('pk')
            dest = get_object_or_404(EmailDestinatario, pk=pk)
            nome = dest.nome
            dest.delete()
            messages.success(request, f"🗑️ {nome} removido da lista.")

        elif action == 'salvar_agendamento':
            agendamento.segunda = 'segunda' in request.POST
            agendamento.terca   = 'terca'   in request.POST
            agendamento.quarta  = 'quarta'  in request.POST
            agendamento.quinta  = 'quinta'  in request.POST
            agendamento.sexta   = 'sexta'   in request.POST
            agendamento.sabado  = 'sabado'  in request.POST
            agendamento.domingo = 'domingo' in request.POST
            horario = request.POST.get('horario_envio', '18:00')
            agendamento.horario_envio = horario
            agendamento.ativo = 'ativo' in request.POST
            agendamento.atualizado_por = request.user
            agendamento.save()
            messages.success(request, "⏰ Agendamento salvo com sucesso!")

        return redirect('core:gerenciar_email_destinatarios')

    destinatarios = EmailDestinatario.objects.all()
    return render(request, 'core/gerenciar_email_destinatarios.html', {
        'destinatarios': destinatarios,
        'agendamento': agendamento,
    })


@login_required
@user_passes_test(lambda u: u.is_superuser)
def enviar_email_agora(request):
    """Dispara o e-mail do Controle Diário imediatamente, ignorando o agendamento."""
    if request.method == 'POST':
        from django.core.management import call_command
        try:
            call_command('enviar_resumo_diario', force=True)
            messages.success(request, "✅ E-mail do Controle Diário enviado com sucesso!")
        except Exception as e:
            messages.error(request, f"❌ Erro ao enviar: {str(e)}")
    return redirect('core:gerenciar_email_destinatarios')


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
class LoginSuccessRedirectView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        
        # Redirecionar usuário SINE para a tela de lançamento do SINE
        if not user.is_superuser and (user.groups.filter(name='SINE').exists() or user.has_perm('controle_diario.add_relatoriodiariosine')):
            return redirect('controle_diario:preencher_sine')

        if user.is_superuser or (hasattr(user, 'profile') and not user.profile.escola and user.profile.nivel_acesso in ['ADMIN_CP', 'ADMIN_UDITECH']):
            # Forçar a escolha do contexto após login se for superuser ou administrador de segmento sem escola fixa
            return redirect('escolas:selecionar_contexto')
        return redirect('escolas:dashboard')

def get_active_escola(request):
    """
    Função utilitária para obter a escola ativa do contexto (superuser) 
    ou a escola do perfil (staff).
    """
    user = request.user
    if not user.is_authenticated:
        return None
        
    sistema = request.session.get('sistema', 'cp').upper()

    if user.is_superuser:
        escola_id = request.session.get('active_escola_id')
        if escola_id:
            from escolas.models import Escola
            return Escola.objects.filter(id=escola_id, tipo=sistema).first()
        return None
        
    if hasattr(user, 'profile') and user.profile.escola:
        if user.profile.escola.tipo == sistema:
            return user.profile.escola
    return None

class CustomLoginView(LoginView):
    template_name = 'registration/login.html'

    def form_valid(self, form):
        user = form.get_user()
        
        sistema = 'cp' # Default fallback for superusers without specific profile config

        if not user.is_superuser:
            profile = getattr(user, 'profile', None)
            if profile:
                if profile.nivel_acesso == 'ADMIN_UDITECH' or (profile.escola and profile.escola.tipo == 'UDITECH'):
                    sistema = 'uditech'
                elif profile.nivel_acesso == 'ADMIN_CP' or (profile.escola and profile.escola.tipo == 'CP'):
                    sistema = 'cp'
            else:
                form.add_error(None, "Esta conta não possui um perfil de acesso configurado no sistema.")
                return self.form_invalid(form)

        # Salva o sistema validado na sessão do usuário
        self.request.session['sistema'] = sistema
        return super().form_valid(form)


def custom_logout_view(request):
    from django.contrib.auth import logout as auth_logout
    # Efetua o logout e limpa a sessão
    auth_logout(request)
    # Redireciona para o login sem parâmetro de sistema
    return redirect('login')


