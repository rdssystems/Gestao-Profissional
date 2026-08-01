# Auditoria de Infraestrutura e Dependências — 2026-08-01

Ver também `2026-08-01-seguranca.md` (bump de dependências com CVE já
aplicado e testado) e a seção "Segurança — PENDÊNCIAS" do `CLAUDE.md`
(itens de firewall/VPS que dependem de acesso que este ambiente não tem).

## Corrigido nesta rodada

1. **`.dockerignore` criado** (não existia nenhum). Antes, `COPY . /app/` no
   `Dockerfile` + ausência total de ignore-list significava que **todo
   rebuild de imagem** (toda vez que `atualizar.sh` roda
   `docker compose up -d --build`) embutia na camada da imagem: `.env` (com
   `SECRET_KEY`/`DB_PASSWORD`/`EMAIL_HOST_PASSWORD` reais da VPS),
   `google_drive_key.json` (chave de service account do Google ativa),
   `postgres_data/` (arquivos crus do Postgres = todo o PII em produção),
   `media/`, `documentos_alunos/`, `.git/`. Qualquer imagem antiga (backup,
   `docker save`, cópia forense) carregaria esse dump completo de segredos +
   PII. Agora excluídos.
2. **`atualizar.sh`: removido `manage.py makemigrations` do deploy de
   produção.** Antes, esse comando rodava direto na VPS, contra o schema
   real de produção, gerando migrations não revisadas — e o próximo
   `git reset --hard` do mesmo script as apagava de novo no próximo deploy
   (schema e histórico de migrations ficando fora de sincronia
   silenciosamente, ciclo a ciclo). Migrations agora só devem ser geradas em
   dev e commitadas.
3. **`dev_restore_db.sh`: adicionado guard contra apagar o banco errado.**
   O container se chama `gq-db` tanto em dev quanto em produção
   (`docker-compose.yml`), e o script fazia `DROP DATABASE` sem nenhuma
   confirmação nem checagem de ambiente. Agora: aborta se `DOCKER_HOST`
   estiver setado (contexto remoto), aborta se o container não usar o
   volume `postgres_data_dev`, e pede confirmação digitada antes do DROP.
4. **`docker-compose.yml`: `redis:alpine` → `redis:7-alpine`** (tag
    flutuante sem versão nenhuma; rebuild podia trocar de major version
    silenciosamente). Também adicionado `EMAIL_ADMIN_RECEIVER` explícito no
    `environment:` (antes só chegava ao app via o fallback de leitura do
    `.env` bind-mountado, não pelo mecanismo declarado do compose).
5. **`gestao_qualificacao_profissional/settings.py`: `DBBACKUP_CLEANUP_KEEP`
   de `1` para `10`.** O fluxo real de backup usa `pg_dump` direto
   (`backup_agora.sh`/`backup_gcs.sh`, retenção de 10), não o
   `manage.py dbbackup` do `django-dbbackup` — mas os dois apontam para o
   MESMO bucket GCS. Deixar em `1` era uma armadilha: se algum dia alguém
   rodasse `manage.py dbbackup` manualmente, apagaria os backups reais da
   retenção de 10, deixando só 1.
6. **`backup_gcs.sh`: checagem de dump vazio adicionada** (o backup diário
   não tinha essa checagem, ao contrário do `backup_agora.sh` sob demanda —
   um `pg_dump` que retornasse 0 bytes por qualquer motivo, ex. disco cheio,
   seria copiado e sobrescreveria o backup do dia como se tivesse dado
   certo).
7. **Carga de `google_drive_key.json` deixou de travar o boot em dev sem a
   chave** (ver `2026-08-01-seguranca.md` / `settings.py` — mudança feita
   junto com o resto do trabalho de segurança, documentada lá porque também
   é uma correção de configuração de produção).
8. **Bump de dependências com CVE** — ver tabela em
   `2026-08-01-seguranca.md`.

## PENDENTE — precisa de acesso/verificação na VPS (não posso confirmar daqui)

1. **Porta `8000:8000` do app publicada em `0.0.0.0`** — item já conhecido
   do CLAUDE.md (Fase 2), continua igual no `docker-compose.yml` de hoje.
   Não mudei porque não sei se o `cloudflared` na VPS roda em
   host-network — se não rodar, prender a porta em `127.0.0.1` quebraria o
   acesso público ao site pelo túnel. **Verificar isso na VPS antes de
   aplicar** (`docker inspect` do container do cloudflared, ver
   `NetworkMode`).
2. Rotação de senha do Postgres, firewall de host, Portainer/ttyd expostos
   — sem mudança, ver CLAUDE.md.

## Backlog (não corrigido — risco mais baixo ou exige decisão de design)

3. **Dockerfile roda como root** — nenhuma diretiva `USER`. Combinado com o
   bind mount `.:/app`, uma RCE no app rodaria como root contra o diretório
   do host. Considerar um usuário não-root + build multi-stage.
4. **Build single-stage carrega `build-essential`/`libpq-dev` na imagem
   final** apesar de usar `psycopg2-binary` (wheel pré-compilada) — toolchain
   de compilação completo disponível numa RCE, sem necessidade real.
5. **Sem `HEALTHCHECK`** no Dockerfile — Docker/restart-policy não distingue
   um Daphne travado (mas vivo) de um saudável.
6. **Base image `python:3.12-slim` sem pin de patch/digest** — rebuilds não
   são reproduzíveis.
7. **Bind mount `.:/app`** em produção significa que o container roda
   literalmente o filesystem do host como código — qualquer coisa com
   acesso de escrita a `/DATA/AppData/Gestao-Profissional/` na VPS altera o
   app em produção sem rebuild, sem diff, sem commit, sem review. É uma
   escolha de arquitetura (permite hot-reload em dev via
   `docker-compose.dev.yml`), mas vale considerar se produção deveria usar
   uma imagem imutável (COPY em vez de bind mount) em vez do mesmo modelo do
   dev.
8. **`EMAIL_BACKEND` cai silenciosamente no backend de console** se a env
   var não estiver setada/tiver erro de digitação — diferente de
   `SECRET_KEY` (que derruba o app com `RuntimeError`), um e-mail que para
   de sair (reset de senha, notificação) falha silenciosamente, sem erro
   visível.
9. **`dev_pull_db.py`**: usa `paramiko.AutoAddPolicy()` (aceita qualquer
   host key no primeiro connect, sem pin) e embute a senha da VPS numa
   string de shell remota (`echo "$VPS_PASS" | sudo -S ...`) — baixo risco
   prático (uso pessoal, credenciais já vêm de env var), mas vale trocar por
   verificação de host key fixa se for usado por mais alguém.
