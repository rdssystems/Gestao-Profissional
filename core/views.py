from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from cursos.models import Curso, TipoCurso
from alunos.models import Aluno
from escolas.models import Escola # Import Escola
from django.http import JsonResponse
from django.urls import reverse
from datetime import timedelta, date, time

# @login_required
# def dashboard_view(request):
#     total_cursos = Curso.objects.count()
#     total_alunos = Aluno.objects.count()
#     cursos_ativos = Curso.objects.filter(status='Aberta').count()
#     cursos_concluidos = Curso.objects.filter(status='Concluído').count()

#     context = {
#         'total_cursos': total_cursos,
#         'total_alunos': total_alunos,
#         'cursos_ativos': cursos_ativos,
#         'cursos_concluidos': cursos_concluidos,
#     }
#     return render(request, 'core/dashboard.html', context)


@login_required
def calendar_view(request):
    cursos_queryset = Curso.objects.all()
    todas_escolas = Escola.objects.all().order_by('nome')
    todos_nomes_cursos = Curso.objects.values_list('nome', flat=True).distinct().order_by('nome')

    # Filtros
    curso_nome_filter = request.GET.get('curso_nome', '') # Default to empty string
    escola_nome_filter = request.GET.get('escola_nome', '') # Default to empty string

    if curso_nome_filter:
        cursos_queryset = cursos_queryset.filter(nome=curso_nome_filter) # Exact match for selectbox
    if escola_nome_filter:
        cursos_queryset = cursos_queryset.filter(escola__nome=escola_nome_filter) # Exact match for selectbox

    context = {
        'cursos': cursos_queryset.order_by('data_inicio', 'horario'),
        'todas_escolas': todas_escolas,
        'todos_nomes_cursos': todos_nomes_cursos,
        'curso_nome_filter': curso_nome_filter,
        'escola_nome_filter': escola_nome_filter,
    }
    return render(request, 'core/calendar.html', context)

# Esta view não é mais usada diretamente no template calendar.html, mas mantida para referência se o FullCalendar for reintroduzido.
@login_required
def get_course_events(request):
    events = []
    for curso in Curso.objects.all():
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
- **Cálculo Automático de Score**: O sistema calcula uma pontuação para cada aluno com base em critérios de vulnerabilidade social (Renda, Nº de Moradores, Situação de Trabalho, etc.), facilitando a priorização no preenchimento de vagas.
- **Importação em Massa**: Upload de alunos via arquivo **CSV** ou planilha **XLSX**, com validação de dados.
- Histórico de matrículas do aluno.

### <i class="bi bi-journal-bookmark"></i> Gestão de Cursos
- Criação de cursos com definição de carga horária, turnos (Manhã, Tarde, Noite) e horários específicos.
- Categorização por **Tipos de Curso** (ex: Informática, Beleza, Gastronomia) com etiquetas coloridas personalizáveis.
- Status do curso: Aberta, Em Andamento, Concluído.
- Validação de datas (Início e Fim).
- **Importação de Cursos**: Upload em massa via CSV.

### <i class="bi bi-pencil-square"></i> Matrículas e Inscrições
- Processo de matrícula inteligente.
- **Validação de Conflitos**: O sistema impede que um aluno se matricule em dois cursos que ocorrem no mesmo horário/período.
- Lista de espera/sugestão baseada no **Score** do aluno e seus cursos de interesse.
- Gestão de status da matrícula: Cursando, Concluído, Desistente.

### <i class="bi bi-check-circle"></i> Frequência e Chamada
- Registro diário de aulas.
- Lista de chamada digital para marcar presença, falta ou ausência justificada.
- Histórico de chamadas por curso.

### <i class="bi bi-gear"></i> Configuração de Score (Ranking)
- Interface administrativa para definir pesos e pontuações dos critérios socioeconômicos.
- Critérios configuráveis:
  - Renda Familiar
  - Renda Per Capita
  - Número de Moradores
  - Membros que Trabalham
  - Tempo de Moradia
  - Tipo de Moradia

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
- **Gestão Completa da Escola**: Pode criar cursos, matricular alunos, editar dados e gerenciar a equipe daquela unidade.
- **Relatórios**: Acesso ao Dashboard da sua escola.

### 3. Auxiliar Administrativo
- **Operacional**: Focado no dia a dia da secretaria da escola.
- **Permissões**:
  - Pode cadastrar e editar alunos.
  - Pode realizar matrículas.
  - Pode lançar chamadas/frequência.
- **Restrições**: **Não pode excluir** registros críticos (como apagar um aluno do sistema) para evitar perda acidental de dados.

---

## <i class="bi bi-tools"></i> Tecnologias Utilizadas

- **Backend**: Python 3.12+, Django 5.2.8
- **Banco de Dados**: SQLite (padrão), compatível com PostgreSQL/MySQL.
- **Frontend**: HTML5, CSS3, Bootstrap 5 (Design responsivo e moderno), JavaScript.
- **Bibliotecas Principais**:
  - `openpyxl`: Geração e leitura de planilhas Excel.
  - `django-widget-tweaks`: Manipulação de formulários.

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
