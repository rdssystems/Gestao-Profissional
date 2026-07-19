# CLAUDE.md — Gestão Qualificação Profissional

Contexto para o Claude retomar o trabalho. Última atualização: 2026-07-18.

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

## Segurança — PENDÊNCIAS (retomar daqui)
Descoberta chave: a VPS tem **IPv6 público roteável e NENHUM firewall de host**
(política INPUT ACCEPT; ZimaOS/Docker gerencia iptables, sem persistência).
Vários serviços ficam/ficavam expostos na internet via IPv6. O que falta:

1. **Rotacionar a senha do banco** — ainda é `gestao_pass` (fraca). Agora o banco
   só é acessível pelo loopback, então a urgência caiu, mas é a 2ª camada.
   Plano: `ALTER USER gestao_user WITH PASSWORD` + atualizar `POSTGRES_PASSWORD`
   e `DB_PASSWORD` no `.env` da VPS + recriar containers. Fazer com script de
   auto-rollback (o `.env` persiste; sequência: ALTER → .env → up -d).

2. **Fase 2 — firewall / portas ainda abertas na internet (IPv6 público):**
   - **Portainer (`:9000`)** — painel de controle do Docker. **Maior risco
     restante** (acesso = controle de todos os containers). Fechar primeiro.
   - App Django direto (`:8000`) — reduzido pelo ALLOWED_HOSTS restrito (Host
     não-confiável → 400), mas ainda alcançável. Cloudflared usa `localhost:8000`
     (verificar se é host-network antes de prender em 127.0.0.1).
   - **ttyd (`:7681`)** — terminal web no host (systemd `ttyd.service`,
     `/bin/ttyd -W /usr/libexec/ttyd-login`), HTTP puro. Restringir.
   - Samba (445/139), NFS (2049) — serviços NAS do ZimaOS.
   - Outro Postgres exposto: `gestao-ong-postgres-1` (`:5433`).
   - Abordagem: firewall de host liberando loopback + Tailscale
     (`tailscale0` / `100.64.0.0/10` / `fd7a::/48`) + LAN, DROP no resto, com
     **auto-rollback temporizado** (não travar o acesso). Usuário acessa admin
     via Tailscale + LAN; NAS só Tailscale/LAN (confirmado).
   - Alternativa preferida quando possível: rebind das portas Docker para
     Tailscale/localhost no compose do repo (persistente, sem risco de lockout).

## Modo de trabalho (restrição do ambiente)
O harness **bloqueia comandos que alteram estado na VPS** (sudo, ALTER, deploy).
Padrão que funciona: **Claude monta/valida scripts (com auto-rollback); o usuário
cola e roda na VPS e devolve a saída.** Leitura via SSH e SFTP para `/tmp`
funcionam; execução com sudo e force-push são bloqueados (usuário executa).
Nunca gravar credenciais (SSH/DB/SECRET_KEY) em arquivos versionados nem em memória.

## GitHub
Repo: `rdssystems/Gestao-Profissional` (branch `main`). Histórico já foi
reescrito duas vezes (purga do dump e da senha SSH) — commits pós-2026-07-18 têm
hashes novos. Fluxo: commitar local → `git push` → `atualizar.sh` na VPS.
