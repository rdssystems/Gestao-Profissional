# Auditoria de Segurança — 2026-08-01

Continuação da auditoria de 2026-07-18 (ver `CLAUDE.md`). Esta rodada focou em
**código da aplicação** (autorização, IDOR, uploads, brute force), não só
config do Django. Feita com 3 sub-agentes independentes (organização de
código, infraestrutura/dependências, segurança de aplicação) + verificação
manual de cada achado antes de corrigir, com `manage.py check` +
`manage.py test` rodando verde depois de cada mudança, contra um Postgres
real (não é só leitura de código).

Continuada no mesmo dia com a execução do Grupo A/B do
`2026-08-01-plano-proximos-passos.md`: testes de regressão escritos para
todos os bugs abaixo (77 → 110 testes no total), o que revelou os dois
achados novos documentados como addendum no item 3 e no item "Bug
sistêmico" logo abaixo.

## Achados CRÍTICOS corrigidos (estavam ativos em produção)

1. **PII de aluno exposta sem login** — `escolas/views.py`
   `AlunosPorEscolaListView`/`CursosPorEscolaListView` (rota
   `/escolas/<id>/alunos/`) não tinham NENHUM mixin de autenticação.
   Qualquer visitante anônimo via internet, sabendo/adivinhando um `escola_id`,
   via nome completo + CPF + telefone de alunos reais.
   **Corrigido**: `LoginRequiredMixin` + helper `_escola_acessivel_ou_404`
   (escolas/views.py) que também fecha o IDOR de tenant (um Coordenador só
   acessa a própria escola; admin de segmento, só o próprio sistema CP/UDITECH).

2. **Escrita/leitura não autenticada de avaliação de professor** —
   `cursos/views.py` `AvaliarEstudanteAjaxView` (rota
   `avaliacao/aluno/<pk>/ajax/`) não tinha login nem token — só um ID
   sequencial adivinhável, ao contrário de todo o resto do fluxo de avaliação
   (que exige `token_acesso` do curso + sessão `prof_auth_{curso.pk}`).
   Permitia forjar avaliação de qualquer aluno.
   **Corrigido**: reaproveita a mesma sessão `prof_auth_{curso.pk}` já
   estabelecida por `AvaliarProfessorAcessoView`; sem ela, 404.

3. **Escalação de privilégio total no gerenciamento de usuários** —
   `core/migrations/0003_assign_permissions.py` dá ao grupo **Coordenador**
   (papel de UMA escola) as permissões globais do Django `add_user`,
   `change_user`, `delete_user`, `view_user`. `usuarios/views.py` não fazia
   NENHUM escopo por escola/tenant nessas views — um Coordenador de qualquer
   escola conseguia listar todos os usuários do sistema (as duas redes,
   CP e UDITECH), abrir `/usuarios/<pk>/editar/` de **qualquer** usuário
   (inclusive superusuário) e trocar a senha dele. Caminho completo de
   account takeover.
   **Corrigido**: `usuarios/views.py` ganhou `usuarios_gerenciaveis_por()` +
   `EscopoUsuarioMixin` — nenhum não-superuser enxerga/edita outro superuser
   ou admin de segmento; Coordenador/Auxiliar só vê/edita usuários da própria
   escola. `usuarios/forms.py` também restringe o campo `escola` do
   formulário ao escopo do usuário logado (antes aceitava qualquer escola do
   sistema, inclusive de outra rede).

   **Addendum (achado durante a execução do Grupo A/B do plano de
   próximos passos, mesmo dia)**: `core/migrations/0003_assign_permissions.py`
   — a migration que concede essas permissões ao grupo Coordenador —
   **nunca funcionou em nenhum banco criado do zero**. É um erro clássico
   de ordenação do Django: o `Permission` de cada model só é criado pelo
   sinal `post_migrate`, que só dispara depois que TODAS as migrations
   daquela chamada de `migrate` terminam — então a migration 0003 rodava
   ANTES desses `Permission` existirem, e `Permission.objects.filter(...)`
   voltava vazio. Confirmado tanto no banco de dev local quanto num
   Postgres zerado do zero (`docker run` + `manage.py migrate` +
   `manage.py test --noinput`): os grupos Coordenador/Auxiliar
   Administrativo ficavam com **zero permissões**. Corrigido com um
   receiver de `post_migrate` (`core/apps.py` + `core/group_permissions.py`,
   idempotente, roda em todo `migrate`). **Isto significa que o item 3
   acima pode não ter sido explorável na prática, dependendo do estado real
   do banco de produção** — se ninguém corrigiu manualmente essas
   permissões via Django admin em algum momento (perfeitamente possível,
   já que sem elas o Coordenador nem conseguiria criar contas de Auxiliar,
   uma funcionalidade básica esperada), o bug de escalação nunca esteve
   ativo. **Recomendado**: verificar em produção
   (`Group.objects.get(name='Coordenador').permissions.all()`) antes de
   assumir severidade crítica retroativa — mas a correção do item 3 continua
   válida e necessária de qualquer forma, porque a correção da migration
   ativa essas permissões corretamente a partir de agora.

4. **Bug sistêmico: default de `nivel_acesso` furava o escopo por escola em
   `StaffRequiredMixin`/`CoordenadorRequiredMixin`** (achado próprio, não
   veio dos sub-agentes). `Profile.nivel_acesso` tem `default='ADMIN_CP'`
   (`core/models.py:22`) e `core/signals.py` cria o Profile sem sobrescrever
   esse default. `core/mixins.py` tratava `nivel_acesso == 'ADMIN_CP'` como
   "admin de segmento com acesso à rede inteira" **sem checar se o perfil
   tinha uma escola específica vinculada** — ao contrário do padrão usado em
   ~15 outros lugares do código (`alunos/views.py`, `cursos/views.py`,
   `escolas/views.py`), que sempre combinam `nivel_acesso in [...]` com
   `not profile.escola`. Na prática: **qualquer Coordenador/Auxiliar comum,
   se nunca teve o `nivel_acesso` explicitamente trocado, era tratado como
   admin de toda a rede CP** em qualquer view protegida só por esses dois
   mixins — o oposto do que o resto do app garante.
   **Corrigido**: `core/mixins.py` agora exige `not profile.escola` antes de
   tratar `nivel_acesso` como admin de segmento, igual ao padrão já usado
   alhures. **Ação recomendada**: conferir no banco de produção (via Django
   admin, `Profile.objects.filter(escola__isnull=False).exclude(nivel_acesso='ADMIN_CP')`
   não serve — o certo é conferir se algum Coordenador comum tem
   `nivel_acesso` diferente do esperado) se algum usuário já usou esse bypass
   indevidamente; não há como saber pelo código se isso já foi explorado.

5. **Vazamento de PII entre escolas no portal público** — `publico/views.py`
   `PublicoCadastroView.get`: quando o CPF não existia na escola atual, caía
   num fallback (`Aluno.objects.filter(cpf=cpf_limpo).first()`, sem filtro de
   escola) que buscava em QUALQUER escola do sistema — inclusive da rede
   oposta (CP) mesmo estando no portal UDITECH — e devolvia o formulário
   pré-preenchido com nome, endereço, renda, dados de saúde do aluno
   encontrado, para o visitante anônimo que só digitou aquele CPF.
   **Corrigido**: busca agora só na escola atual (`self.escola`). O recurso
   de "puxar cadastro de outra unidade" foi removido — se isso for necessário
   como funcionalidade, precisa ser redesenhado com autenticação/verificação
   (ex.: confirmar por WhatsApp antes de mostrar dados), não com um CPF cru.

## Achados ALTOS corrigidos

6. **IDOR em `alunos/views.py`** (views tipo `View` puro, então
   `StaffRequiredMixin` não fazia checagem por objeto — só filtravam por
   `escola__tipo=sistema`, ou seja, por REDE, não pela escola específica do
   usuário): `AlunoUpdateObservacoesView`, `AlunoUpdateCursosInteresseView`,
   `AlunoArquivoAjaxUploadView`, `AlunoArquivoActionView` (get/post/delete).
   Um Coordenador de uma escola conseguia editar observações, cursos de
   interesse e enviar/renomear/apagar arquivos de alunos de OUTRA escola da
   mesma rede, só adivinhando o `pk`.
   **Corrigido**: helper `get_aluno_no_escopo_ou_404()` reaproveitado nas 4
   views — Coordenador/Auxiliar só acessa alunos da própria escola; admin de
   segmento/superuser, qualquer escola da rede.

   *Não mexido de propósito*: `AlunoVerificarCPFView` → `AlunoClonarView`
   (fluxo "clonar aluno de outra escola") continua permitindo busca/importação
   cross-school **dentro da mesma rede** — isso é uma funcionalidade
   deliberada (staff pode puxar cadastro de aluno já existente em escola
   irmã ao matricular em outra unidade), não um bug, e está corretamente
   atrás de `StaffRequiredMixin` (exige login + grupo de staff). Corrigido
   apenas um bug funcional real: `AlunoClonarView` sobrescrevia
   incondicionalmente `escola_destino` na linha seguinte ao cálculo correto,
   quebrando o clone para superusuários.

7. **`declaracao/views.py`**: `declaracao_sucesso_view` e
   `imprimir_declaracao_view` filtravam só por `sistema` (rede), não por
   `profile.escola` — ao contrário de `_check_inscricao_permission` (usado em
   gerar/salvar), que já fazia o check certo. Um Coordenador de uma escola
   via declarações emitidas para alunos de outra escola da mesma rede.
   **Corrigido**: novo helper `_bloqueia_se_fora_da_escola` aplicado às duas views.

## Achados MÉDIOS corrigidos

8. **Upload de arquivo sem validação nenhuma** — `alunos.ArquivoAluno` e
   `documentos.DocumentoUnidade` aceitavam qualquer extensão (`.exe`, `.html`,
   `.svg`, `.php`) e qualquer tamanho. Endpoints exigem login, mas qualquer
   Coordenador/Auxiliar podia subir isso.
   **Corrigido**: `core/validators.py` (`validate_upload_file`) — extensões
   permitidas (`.pdf .jpg .jpeg .png .gif .webp .doc .docx .xls .xlsx`) e
   limite de 15 MB. Aplicado como `validators=[...]` nos dois model fields
   (cobre uploads via ModelForm automaticamente) **e** chamado manualmente
   nas duas views AJAX que usam `.objects.create()` direto e por isso não
   rodam `full_clean()` (`AlunoArquivoAjaxUploadView`,
   `DocumentoAjaxUploadView`). Migrations geradas e aplicadas:
   `alunos/migrations/0019_alter_arquivoaluno_arquivo.py`,
   `documentos/migrations/0004_alter_documentounidade_arquivo.py`.

9. **Nenhuma proteção contra força bruta/enumeração** —
   login administrativo (`core/views.py` `CustomLoginView`) e o CPF-lookup
   público (`publico/views.py`) não tinham rate limit nem CAPTCHA.
   **Corrigido** (sem adicionar dependência nova — usa o cache já configurado,
   Redis em produção / locmem em dev): `core/utils.py` ganhou
   `is_rate_limited`/`register_attempt`. Aplicado em:
   - `CustomLoginView`: bloqueia por IP após 10 tentativas com senha errada
     em 5 min (só conta falhas, não afeta uso normal).
   - `PublicoCadastroView.get`: limita a 30 consultas de CPF por IP a cada
     10 min.
   - `PublicoCadastroView.post`: limita a 20 envios de cadastro por IP a
     cada 10 min.
   **Limitação conhecida**: como o cache em dev é `LocMemCache` (por
   processo), esse throttle só é efetivo de verdade em produção, onde o
   cache é Redis compartilhado entre workers. Isso não é uma substituição
   completa de CAPTCHA — apenas eleva o custo de um ataque automatizado
   simples.

## Dependências com CVE corrigidas (bump testado com a suite de testes)

| Pacote | Antes | Depois | Motivo |
|---|---|---|---|
| Django | 5.2.8 | 5.2.16 | SQLi via `order_by()`/`FilteredRelation`, timing attack em `check_password()`, DoS em header ASGI, bypass de autorização em admin inline — corrigidos em patches 5.2.9–5.2.13 |
| Pillow | 12.0.0 | 12.3.0 | CVE-2026-25990 (OOB write via PSD), CVE-2026-42309 (heap overflow), CVE-2026-40192 (decompression bomb) |
| cryptography | 46.0.3 | 46.0.7 | CVE-2026-39892 (buffer overflow), CVE-2026-26007 (validação de subgrupo EC), CVE-2026-34073 (gap em name constraints) |
| Twisted | 25.5.0 | 26.4.0 | CVE-2026-42304 (DoS em `twisted.names` via DNS compression pointers) |
| requests | 2.32.3 | 2.32.5 | CVE-2024-47081 (vazamento de credencial `.netrc`) |

`manage.py test` (77 testes, todas as apps com suite real) rodou OK antes e
depois do bump, contra Postgres real (container descartável, não o banco de
dev do usuário).

## PENDÊNCIAS — não corrigidas nesta rodada (decisão consciente ou fora do meu alcance)

1. **Rebind da porta `8000:8000` do app no `docker-compose.yml` para
   loopback/Tailscale** — é o item nº 1 da lista de pendências do
   `CLAUDE.md` de 2026-07-18, e continua igual hoje: publicado em `0.0.0.0`.
   **Não mudei porque depende de uma informação que só existe na VPS**: se o
   `cloudflared` roda em host-network (aí prender em 127.0.0.1 é seguro) ou
   como container separado usando `localhost:8000` via alguma outra ponte
   (aí prender em loopback quebraria o site público). Verificar isso na VPS
   antes de aplicar.
2. **Rotação da senha do Postgres** (`gestao_pass`) — mesmo item já listado
   no CLAUDE.md, ainda não feito.
3. Itens de firewall de host (Portainer, ttyd, Samba/NFS, outro Postgres
   exposto) — inalterados, ver seção "Fase 2" do CLAUDE.md.
4. **Rate limiting real (CAPTCHA)** no portal público — o throttle por
   cache reduz o problema mas não é uma solução definitiva contra bots.
5. Ver também `2026-08-01-arquitetura-codigo.md` (fat views, dead code, apps
   sem teste nenhum) e `2026-08-01-infraestrutura.md` (Dockerfile rodando
   como root, bind mount `.:/app` sem imutabilidade, etc.) para o restante
   do backlog levantado nesta auditoria.
