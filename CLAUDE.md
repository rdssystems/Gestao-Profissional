# CLAUDE.md — Gestão Qualificação Profissional

Contexto para o Claude retomar o trabalho. Última atualização: 2026-08-02.

## O que é o app
Sistema Django (Django 5.2.8, Python 3.12) de gestão de inscrições/qualificação
profissional. Dois "portais" por tipo de escola: **CP** e **UDITECH** (o campo
`sistema` na sessão controla qual portal está ativo). Também há um **portal
público** (`publico/`) para autocadastro de alunos sem login.

Apps principais: `alunos`, `escolas`, `cursos`, `usuarios`, `score_config`,
`declaracao`, `documentos`, `controle_diario`, `treinamento`, `publico`, `core`
(auditoria, middleware, mixins), `whatsapp` (integração Evolution API —
atualmente **desativada**, comentada nas URLs).

Stack: PostgreSQL 16, Redis (channels + cache), Daphne/Channels (ASGI),
WhiteNoise (static), django-dbbackup + Google Cloud Storage.

## Deploy / Infraestrutura
- **VPS rodando ZimaOS** (base CasaOS/Debian). Acesso via **Tailscale SSH** e
  presencialmente na LAN. (Credenciais NÃO ficam neste arquivo.)
- App servido ao público via **Cloudflare Tunnel** (`cloudflared`, ingress
  `app.gestaoqualificacao.com.br` → `http://localhost:8000`). Túnel = não precisa
  de portas públicas abertas para o site funcionar.
- Compose de produção em `/DATA/AppData/Gestao-Profissional/` (bind mount `.:/app`).
  Containers: `gq-app`, `gq-db` (postgres:16), `gq-redis`.
- **Google Drive montado** em `/media/qualificacaoudia_google_drive_1777986114/`
  (backups em `.../Gestao-Profissional/backups/{diario,pre_update,manual}`).

### Fluxo de atualização (IMPORTANTE)
O script `atualizar.sh` (rodar na VPS com `sudo bash atualizar.sh`) faz:
`backup opcional → git fetch + git reset --hard origin/main → git clean -fd →
docker compose up -d --build → migrate → collectstatic`.

Regras que decorrem disso — sempre respeitar:
1. **Ele puxa do `origin` (GitHub).** É preciso **commitar e dar push ANTES** de
   rodar o atualizar.sh, senão a mudança não vai.
2. **`git reset --hard` sobrescreve arquivos versionados** (inclusive
   `docker-compose.yml`). Nunca editar arquivos versionados direto na VPS —
   tudo pelo repo. Mudanças de infra (ex.: binding de portas) vão no repo.
3. **`.env` é gitignored e sobrevive** ao update (git clean -fd sem -x). Segredos
   e config de ambiente ficam no `.env` da VPS, não no git.
4. **Se uma mudança de código exigir uma NOVA variável de ambiente, adicionar ao
   `.env` da VPS ANTES de rodar o atualizar.sh** — senão o app quebra no boot.
   (Foi o que aconteceu com `SECRET_KEY` em 2026-07-18: deploy sem a chave no
   `.env` → `RuntimeError` → app em crash-loop. Corrigido adicionando a chave.)
5. `atualizar.sh` **não tem rollback**. O backup que ele faz protege os DADOS,
   não o deploy. Se quebrar, fica fora do ar até corrigir.

### Backup sob demanda
`backup_agora.sh` (na raiz do repo e na VPS): gera dump do Postgres e envia para
o Google Cloud Storage + Google Drive montado (subpasta `manual/`), mantendo os
10 mais recentes. Rodar: `sudo bash /DATA/AppData/Gestao-Profissional/backup_agora.sh`.

### localhost (dev) vs VPS (prod)
Mesmo **código** (ambos seguem `origin/main`). Diferem por design em:
`.env` (cada ambiente tem o seu — banco, SECRET_KEY, DEBUG, chaves), **dados**
(dev usa Postgres local via `docker-compose.dev.yml`; prod tem os dados reais).

## Segurança — trabalho feito (2026-07-18)
Auditoria completa realizada. **Concluído e em produção:**
- Removido dump de banco (PII) do histórico do Git + `.gitignore` de `*.dump`.
- `SECRET_KEY` movida para variável de ambiente (raise se ausente em produção);
  chave antiga (hardcoded) invalidada. Rotacionada.
- `DEBUG` default `False`; `ALLOWED_HOSTS` restrito e configurável por env.
- Flags de produção: SSL redirect, HSTS, cookies Secure/HttpOnly, nosniff,
  referrer-policy (bloco `if not DEBUG`).
- Removido backdoor com senha hardcoded (`ativar_dev_view` em `core`).
- Removida chave default da Evolution API (`whatsapp/services.py`).
- Escapado XSS armazenado em `core/models.py` `get_notification_text` (|safe).
- `dev_pull_db.py`: credenciais SSH da VPS movidas para env (estavam hardcoded
  no git). **Senha SSH da VPS rotacionada pelo usuário** + purgada do histórico
  do GitHub (git-filter-repo).
- **Banco de alunos FECHADO na internet**: porta do Postgres publicada só em
  `127.0.0.1:5434` (era `0.0.0.0`, exposta no IPv6 público). Verificado
  externamente (conexão recusada). **Era o risco crítico nº 1.**

## Auditoria de 2026-08-01 (código da aplicação, não só config)
Nova rodada de auditoria, desta vez em **código** (autorização/IDOR, uploads,
brute force), não só `settings.py`. Achou e corrigiu **vulnerabilidades
críticas ativas em produção**: PII de aluno exposta sem login
(`escolas/views.py`), escrita não-autenticada em avaliação de professor
(`cursos/views.py`), escalação de privilégio total via `usuarios/views.py`
(Coordenador conseguia trocar senha de qualquer superusuário), um bug
sistêmico no default de `Profile.nivel_acesso` que furava o escopo por
escola em `core/mixins.py`, e vazamento de PII entre escolas no portal
público (`publico/views.py`). Detalhes completos, com file:line e o que
ainda falta, em:
- `docs/auditoria/2026-08-01-seguranca.md` — o que foi corrigido + pendências.
- `docs/auditoria/2026-08-01-arquitetura-codigo.md` — backlog de
  organização de código levantado na auditoria.
- `docs/auditoria/2026-08-01-infraestrutura.md` — Docker/scripts/dependências
  (bump de Django/Pillow/cryptography/Twisted/requests por CVE, `.dockerignore`
  criado, `atualizar.sh` não roda mais `makemigrations` em produção).
- `docs/auditoria/2026-08-01-plano-proximos-passos.md` — o backlog acima
  organizado em Grupo A (zero risco), Grupo B (baixo risco, testável) e
  Grupo C (precisa VPS ou decisão do usuário). **Grupos A e B já foram
  executados** no mesmo dia (testes de regressão, `transaction.atomic()`
  no import CSV, índices de banco, lock de concorrência em
  `WebSocialMember`, `cursos/views.py` quebrado em pacote
  `cursos/views/`). Isso revelou 2 achados novos: default inseguro de
  `Profile.nivel_acesso` (corrigido) e uma migration de permissões
  (`core/migrations/0003_assign_permissions.py`) que nunca funcionou em
  banco nenhum criado do zero (corrigida via `post_migrate` em
  `core/apps.py`). **Grupo C**: C1 e C3 (firewall de host) foram feitos em
  2026-08-01 — ver seção "Fase 2 de infra CONCLUÍDA" abaixo. C2 (rotação
  de senha do banco) segue pendente, ver "Segurança — PENDÊNCIAS".

**Achado fora do código do app**: o repositório git na pasta pessoal do
usuário (`Documents/`, um nível acima deste repo) estava com `.git`
inicializado na raiz do HOME (`C:\Users\...`) por acidente, rastreando
binários do Redis e um gitlink quebrado para este repo. Nenhum segredo
chegou a ser commitado (verificado), mas um `git add -A` ali arriscava
pegar `.ssh/`, `.aws/`, etc. Sinalizado ao usuário para mover o `.git` para
dentro da pasta do projeto — fora do escopo deste repo, então não documentado
em detalhe aqui.

## Trabalho de 2026-08-02 (Dashboard v2, correções de bugs, feature nova)

**Dashboard redesenhado** (`escolas/views.py`, `escolas/templates/escolas/dashboard.html`,
`core/static/css/premium_theme.css`): KPIs, gráfico de ocupação, top
frequências e perfil demográfico agora renderizados **100% no servidor**
(donuts em CSS `conic-gradient()`, barras em CSS puro) — removida a
dependência do ApexCharts via CDN. Percentuais pré-calculados em Python
(`pct()` helper dentro de `DashboardView.get_context_data`) em vez de JS.
Mesma inspiração aplicada depois em `controle_diario_admin.html`
(substituiu Chart.js/donut de 9 fatias por barras CSS + grid de KPI cards),
reaproveitando os mesmos componentes `.dash-bars`/`.dash-kpi-card`.

**Bugs achados e corrigidos nessa mesma leva** (todos com teste de
regressão em `escolas/tests.py` e `alunos/tests.py`):
- Card "Hoje" contava 2x um cadastro novo de aluno que já vinha com curso
  de interesse marcado (1x pelo aluno criado, 1x pelo `InteresseLog`).
  Corrigido excluindo do card os `InteresseLog` de alunos criados no
  mesmo dia — interesse novo de aluno *já existente* continua contando.
- `alunos/signals.py` (`log_interesse_change`) gravava `InteresseLog.data`
  com `timezone.now().date()` — que é sempre **UTC**, mesmo com
  `TIME_ZONE=America/Sao_Paulo`. Entre 21h e 23h59 (horário de Brasília) o
  UTC já tinha virado o dia seguinte, então o log nascia com a data de
  amanhã e sumia do card "Hoje" bem na janela em que foi criado. Trocado
  para `timezone.localdate()`.
- Taxa de ocupação podia passar de 100% (turma com mais "cursando" do que
  "vagas" cadastradas) e quebrava o `conic-gradient` (stop tipo `"305%"`).
  Clampado em `min(100, ...)`.
- Cor do 2º segmento do donut de Ocupação no portal CP (`--accent-gold`)
  era um azul quase idêntico ao `--brand-primary` — veio direto do
  `tertiary-container` do design gerado no Stitch sem checar contraste.
  Trocado por um cinza neutro; Uditech manteve o dourado (contrasta bem
  com o azul daquele tema).

**Outras mudanças**:
- Curso (`cursos/forms.py`, `cursos/templates/cursos/curso_form.html`):
  campo Nome fica `readonly` (não `disabled`, pra não quebrar o POST) —
  já era preenchido automaticamente ao escolher o Tipo de Curso; aviso
  adicionado no form.
- Controle Diário (`controle_diario/views.py`, `.../controle_diario_admin.html`,
  `core/templatetags/auth_extras.py` — novo filtro `is_super_admin`): card
  "Indicadores do SINE" agora só aparece pra admin de verdade (superuser
  ou `nivel_acesso == 'SUPERUSER'`) — `admin_cp`/`admin_uditech` passavam
  no `@user_passes_test` da view (admin de segmento) mas viam o card do
  SINE sem checagem nenhuma no template. View também para de buscar o
  `RelatorioDiarioSine` do banco quando quem pediu não pode ver.
- Nova feature: botão **"Contatar Turma"** no detalhe do Curso
  (`cursos/templates/cursos/curso_detail.html`) — reaproveita o mesmo
  padrão de disparo em loop de WhatsApp já usado em Avaliação (mensagem
  editável com tags `{NOME}`/`{CURSO}`/`{ESCOLA}`, avança aluno por aluno
  abrindo `whatsapp://send`), escopado só aos alunos com `Inscricao.status
  == 'cursando'` naquele curso.

**Notas de ambiente, não são bugs do app**:
- `collectstatic` sempre avisa "Found another file with the destination
  path..." pra alguns arquivos de `core/static/` (ex.: `css/premium_theme.css`,
  `core/logopmu.png`) — é porque `STATICFILES_DIRS` (`settings.py`) lista
  explicitamente `core/static`, que o `AppDirectoriesFinder` **já**
  descobre sozinho por `core` ser um app instalado com pasta `static/`
  própria. Achado duplicado é o mesmo arquivo pelas duas rotas (mesmos
  bytes), então é só um warning cosmético — daria pra limpar removendo a
  entrada redundante de `STATICFILES_DIRS`, mas não foi feito (fora do
  escopo do que estava sendo pedido).
- A partição raiz do sistema na VPS (`/dev/root`, `df -h /`) está **100%
  cheia** (1.2G, é só o SO/boot do ZimaOS) — separada de onde os dados do
  app realmente ficam (`/DATA`, 222G, 24% usado, bastante espaço livre).
  Não é urgente e não causou nenhum problema observado, mas vale
  investigar em algum momento por que o `/` não cresce/libera espaço.

## Segurança — Fase 2 de infra CONCLUÍDA (2026-08-01)
A Fase 2 abaixo (firewall de host + apps expostos indevidamente) foi
**executada e verificada em produção**: Portainer e o app não-relacionado
`gestao-ong` (+ seu Postgres `:5433`) foram **removidos** da VPS; firewall
de host persistente criado (`/etc/firewall-gq-rules.sh` +
`systemd/firewall-gq.service`, `-m conntrack --ctstate NEW`, idempotente),
liberando só SSH:22 e a porta do app:8000, DROP no resto — verificado
externamente (Tailscale desligado de propósito pra confirmar que o
IPv6 público parou de responder nas portas fechadas). Backup diário
também foi corrigido nesse mesmo dia (GCS + Google Drive independentes
um do outro) e ganhou notificação no Discord (status 3x/dia + alerta
imediato de falha + healthcheck periódico a cada 3 dias), replicado
também no app irmão Gestaosuas-django.

## Segurança — PENDÊNCIAS (retomar daqui)
1. **Rotacionar a senha do banco** — ainda é `gestao_pass` (fraca), ainda não
   feito. Banco só é acessível pelo loopback (Fase 1) + firewall de host
   (Fase 2), então a urgência caiu bastante, mas é a 2ª camada que falta.
   Plano: `ALTER USER gestao_user WITH PASSWORD` + atualizar `POSTGRES_PASSWORD`
   e `DB_PASSWORD` no `.env` da VPS + recriar containers. Fazer com script de
   auto-rollback (o `.env` persiste; sequência: ALTER → .env → up -d).
2. ttyd (`:7681`, terminal web do host) e Samba/NFS (NAS do ZimaOS) ficaram
   bloqueados na internet como efeito colateral do firewall de 2026-08-01
   (só SSH+app foram liberados, o resto cai no DROP padrão) — confirmar com
   o usuário se algum desses precisa voltar a ficar acessível fora de
   Tailscale/LAN (hoje só dá pra acessar por ali).

## Segurança — checklist obrigatório para toda view nova
O Django **não protege rota nenhuma sozinho**. `urls.py` só mapeia URL → view;
qualquer pessoa pode requisitar qualquer URL cadastrada, autenticada ou não.
Quem decide se aquilo exige login é **cada view individualmente**, via
decorator (`@login_required`) ou mixin (`LoginRequiredMixin`,
`StaffRequiredMixin`/`CoordenadorRequiredMixin` em `core/mixins.py`). Se o
mixin for esquecido, a view fica exposta sem nenhum aviso — nem erro, nem log
estranho, só funciona normalmente para qualquer um que descubra a URL.

Foi exatamente esse padrão de esquecimento que causou os achados críticos das
auditorias de 2026-07-18/08-01 (PII exposta em `escolas/views.py`, escrita
não-autenticada em `cursos/views.py`, vazamento entre escolas em
`publico/views.py`). **Antes de mergear qualquer view nova, perguntar
explicitamente: "essa daqui devia mesmo ser pública, ou falta mixin?"** —
isso vale tanto para views novas quanto para revisão de views existentes que
forem tocadas por qualquer motivo (refactor, bugfix, etc.).

## Modo de trabalho (atualizado 2026-08-02 — substitui a nota antiga)
**Claude executa direto na VPS via SSH (paramiko), inclusive `sudo` e o
`atualizar.sh` completo.** Não é mais "monta script, usuário cola e roda" —
isso era uma restrição de uma sessão anterior que não se aplica mais neste
ambiente. Padrão usado com sucesso repetidas vezes (firewall de host,
remoção de containers, múltiplos deploys, leitura de logs em produção):
```python
import paramiko, os
PASS = os.environ["VPS_PASS"]
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("100.76.30.36", username="klismanrds", password=PASS, timeout=15)
stdin, stdout, stderr = client.exec_command("cd /DATA/AppData/Gestao-Profissional && sudo -S -p '' bash atualizar.sh", timeout=600)
stdin.write(f"{PASS}\nN\n")  # senha do sudo + "N" pro prompt de backup do atualizar.sh
```
- **Senha SSH nunca fica salva** (nem em arquivo, nem em memória entre
  sessões) — pedir ao usuário no chat toda vez que for precisar (ele já
  espera isso, responde rápido).
- Script fica em `scratchpad`, roda via `Bash` com `VPS_PASS='...' python
  script.py`. Depois de rodar o `atualizar.sh`, **sempre verificar** que o
  deploy funcionou: `manage.py check` não basta (roda local); confirmar via
  `curl` na URL pública real (`https://app.gestaoqualificacao.com.br/...`)
  e checar `docker logs gq-app --tail N` por traceback.
- **Depois de recriar o container (`docker compose up -d --build`), o
  túnel `cloudflared` pode cair por ~1 minuto** (erros IPv6 "network is
  unreachable" nos logs) e se reconectar sozinho — é um efeito colateral
  observado da rede do Docker sendo recriada, não um bug do app. Se o
  usuário reportar "bad gateway" logo após um deploy, checar
  `docker logs cloudflared-tunnel --tail 60` antes de assumir que é o app;
  provavelmente já vai ter se recuperado sozinho.
- Backgrounding de comandos longos (`manage.py test` na VPS/local) pelo
  Bash tool às vezes **trunca a saída capturada sem aviso** (fica faltando
  o resumo final "Ran N tests / OK", mesmo com exit code correto) — se
  acontecer, refazer escrevendo o resultado num arquivo dentro do
  container (bind mount) e ler esse arquivo depois, em vez de confiar só
  no stdout capturado pela tool.
- Nunca gravar credenciais (SSH/DB/SECRET_KEY) em arquivos versionados nem em memória.

## GitHub
Repo: `rdssystems/Gestao-Profissional` (branch `main`). Histórico já foi
reescrito duas vezes (purga do dump e da senha SSH) — commits pós-2026-07-18 têm
hashes novos. Fluxo: commitar local → `git push` → `atualizar.sh` na VPS.
