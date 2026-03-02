# Sistema de Gestão de Qualificação Profissional

## 📘 Sobre o Projeto

O **Sistema de Gestão de Qualificação Profissional** é uma plataforma web desenvolvida em **Django** para gerenciar cursos de qualificação, matrículas de alunos, escolas e controle de frequência. O sistema foi projetado para atender à Diretoria de Qualificação Profissional, permitindo o gerenciamento centralizado de múltiplas escolas/unidades de ensino, com foco em critérios socioeconômicos para priorização de vagas (Score).

O software oferece um fluxo completo desde o cadastro de alunos, criação de cursos, matrícula (com validação de conflitos de horário), lista de chamada e relatórios via dashboard.

---

## 🚀 Principais Funcionalidades

### 🏢 Gestão de Escolas
- Cadastro e gerenciamento de unidades de ensino (Escolas).
- Painel (Dashboard) específico para cada escola ou visão global para administradores.
- Métricas em tempo real: total de alunos, matrículas, desistências, cursos ativos.

### 👥 Gestão de Alunos (Candidatos)
- Cadastro completo de alunos com dados pessoais, socioeconômicos e de contato.
- **Busca Inteligente**: Localize alunos rapidamente pelo Nome ou CPF na listagem.
- **Gestão Multi-Escola**:
  - O sistema permite o cadastro do mesmo aluno em diferentes escolas (unidades).
  - **Clonagem de Cadastro**: Ao tentar cadastrar um aluno já existente em outra unidade, o sistema alerta e oferece a opção de importar os dados cadastrais, evitando retrabalho e duplicidade de digitação.
  - **Prevenção de Duplicidade**: Bloqueia o cadastro de um CPF se ele já estiver matriculado na mesma escola.
- **Cálculo Automático de Score**: O sistema calcula uma pontuação para cada aluno com base em critérios de vulnerabilidade social (Renda, Nº de Moradores, Situação de Trabalho, etc.), facilitando a priorização no preenchimento de vagas.
- **Importação em Massa**: Upload de alunos via arquivo **CSV** ou planilha **XLSX**, com validação de dados.
- Histórico de matrículas do aluno.

### 📚 Gestão de Cursos
- Criação de cursos com definição de carga horária, turnos (Manhã, Tarde, Noite) e horários específicos.
- Categorização por **Tipos de Curso** (ex: Informática, Beleza, Gastronomia) com etiquetas coloridas personalizáveis.
- Status do curso: Aberta, Em Andamento, Concluído.
- Validação de datas (Início e Fim).
- **Importação de Cursos**: Upload em massa via CSV.

### 📝 Matrículas e Inscrições
- Processo de matrícula inteligente.
- **Validação de Conflitos**: O sistema impede que um aluno se matricule em dois cursos que ocorrem no mesmo horário/período.
- Lista de espera/sugestão baseada no **Score** do aluno e seus cursos de interesse.
- Gestão de status da matrícula: Cursando, Concluído, Desistente.

### ✅ Frequência e Chamada
- Registro diário de aulas.
- Lista de chamada digital para marcar presença, falta ou ausência justificada.
- Histórico de chamadas por curso.

### 📜 Declarações e Certificados
- Geração automática de declarações de status (**Matriculado**, **Cursando**, **Concluído**).
- **Assinatura Digital**: Captura de assinatura via tela sensível ao toque ou mouse.
- **Validação de Autenticidade**: Cada declaração possui um hash de validação único para conferência de veracidade.
- Impressão otimizada em papel timbrado da escola.

### 🛡️ Auditoria de Sistema (Logs)
- Monitoramento completo de ações críticas (**CREATE**, **UPDATE**, **DELETE**).
- Registro detalhado de quem alterou o quê e em qual horário.
- Abrange Alunos, Cursos, Matrículas, Escolas e Declarações.

### ⚙️ Configuração de Score (Ranking)
- Interface administrativa para definir pesos e pontuações dos critérios socioeconômicos.
- Critérios configuráveis:
  - Renda Familiar
  - Renda Per Capita
  - Número de Moradores
  - Membros que Trabalham
  - Tempo de Moradia
  - Tipo de Moradia

---

## 🔐 Perfis de Usuário e Permissões

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

## 🛠️ Tecnologias Utilizadas

- **Backend**: Python 3.12+, Django 5.2.8
- **Tempo Real**: Django Channels & WebSockets (Comunicação bidirecional)
- **Cache & Filas**: Redis
- **Bancos de Dados**:
  - **Desenvolvimento**: SQLite (padrão)
  - **Produção**: PostgreSQL 16+ (via Docker)
- **Frontend**: HTML5, CSS3, Bootstrap 5 (Premium Design), JavaScript Vanilla.
- **Infraestrutura**: Docker & Docker Compose.
- **Bibliotecas Principais**:
  - `openpyxl`: Geração e leitura de planilhas Excel.
  - `django-widget-tweaks`: Manipulação de formulários.

---

## 📦 Instalação e Execução

### Pré-requisitos
- Python 3.12 ou superior instalado.
- Git (opcional, para clonar o repositório).

### Passo a Passo

1. **Clone o repositório ou baixe o código fonte:**
   ```bash
   git clone <url-do-repositorio>
   cd gestao-qualificacao
   ```

2. **Crie e ative um ambiente virtual:**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```
   *(Caso não tenha o arquivo requirements.txt, instale: `django openpyxl`)*

4. **Configure o Banco de Dados:**
   ```bash
   python manage.py migrate
   ```

5. **Crie um Superusuário:**
   ```bash
   python manage.py createsuperuser
   ```

6. **Inicie o Servidor:**
   ```bash
   python manage.py runserver
   ```

### 🐳 Execução via Docker (Recomendado para Produção)

O projeto está totalmente containerizado para facilitar o deploy e garantir consistência de ambiente:

1. **Suba os containers (App, Postgres, Redis):**
   ```bash
   docker-compose up --build -d
   ```
2. **Execute as migrações no container:**
   ```bash
   docker-compose exec web python manage.py migrate
   ```
3. **Crie o superusuário:**
   ```bash
   docker-compose exec web python manage.py createsuperuser
   ```

O sistema estará disponível em `http://localhost:8000`.

7. **Acesse o sistema:**
   Abra o navegador em `http://127.0.0.1:8000/`.

---

## 💾 Backup e Segurança
- Integração com `django-dbbackup` para dumps periódicos do banco de dados e arquivos de mídia.
- Scripts de automação incluídos (`deploy_servidor.sh`).

---

## 💡 Como Usar (Fluxo Básico)

1. **Login**: Acesse com suas credenciais. Você será redirecionado para o **Dashboard**.
2. **Cadastrar Aluno**: Vá em "Alunos" > "Novo". Preencha os dados. O Score será calculado automaticamente.
3. **Criar Curso**: Vá em "Cursos" > "Novo". Defina nome, tipo, datas e horários.
4. **Matricular**: 
   - Vá em "Matrículas" ou na tela de "Cursos".
   - Selecione o curso. O sistema sugerirá alunos com interesse naquele tipo de curso, ordenados pelo Score (maior vulnerabilidade primeiro).
   - Confirme a matrícula (o sistema validará conflitos de horário).
5. **Chamada**: No curso, clique em "Chamada" para registrar a presença do dia.
6. **Declarações**: Na ficha do aluno ou curso, selecione a opção para gerar a declaração com a assinatura digital.

---

**Desenvolvido por:** Klisman rDs
**Ano:** 2026
