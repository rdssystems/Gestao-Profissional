# Plano de próximos passos — pós-auditoria 2026-08-01

Todo o backlog levantado em `2026-08-01-seguranca.md`,
`2026-08-01-arquitetura-codigo.md` e `2026-08-01-infraestrutura.md`,
organizado por **risco de alterar o comportamento em produção**, não por
severidade. A pergunta que separa as duas colunas é: *"se eu aplicar isso e
tiver um bug, o que quebra para o usuário final?"*

**Status: Grupos A e B concluídos** (mesmo dia, 2026-08-01). Todos os itens
abaixo foram implementados e verificados com `manage.py check` +
`manage.py test` (suite completa de todas as apps, rodando contra um
Postgres real) depois de cada mudança. Grupo C segue pendente — depende de
acesso à VPS ou decisão do usuário.

## Achados novos durante a execução do Grupo A (não previstos no plano original)

1. **Default inseguro em `Profile.nivel_acesso`**: o campo tinha
   `default='ADMIN_CP'` (`core/models.py`), e `core/mixins.py` só negava
   esse nível de "admin de segmento" quando `profile.escola` estava
   definido — mas isso significava que **qualquer perfil novo sem escola
   nem grupo nenhum** (ex.: uma conta criada sem querer via `/admin/`
   "Add user", sem tocar no dropdown) virava automaticamente admin de toda
   a rede CP. Corrigido: novo default `'NENHUM'` (só afeta perfis novos;
   linhas já existentes em produção continuam com o valor que já tinham).
2. **Migration `core/0003_assign_permissions.py` nunca funcionou**: os
   grupos "Coordenador"/"Auxiliar Administrativo" estavam com **zero
   permissões** em qualquer banco criado do zero — erro clássico de
   ordenação do Django (a migration tentava atribuir `Permission` que
   ainda não existiam, porque `post_migrate` só cria os `Permission` de
   cada app DEPOIS que todas as migrations daquela chamada de `migrate`
   terminam). Corrigido com um receiver de `post_migrate` em
   `core/apps.py` + `core/group_permissions.py` (idempotente, roda em todo
   `migrate`). **Verificar no banco de PRODUÇÃO** se os grupos já tinham
   sido corrigidos manualmente via Django admin em algum momento, ou se
   este bug também está ativo lá — isso muda a avaliação de quão exposto
   o achado #3 de `2026-08-01-seguranca.md` (escalação de privilégio via
   `usuarios/views.py`) estava de fato na prática.

## Grupo A — Não altera funcionamento (zero risco de regressão visível) — ✅ CONCLUÍDO

Pode ser feito a qualquer momento, sem coordenar com deploy, sem testar
fluxo de usuário — na pior hipótese, quebra um teste ou o build, nunca um
comportamento em produção.

| # | Item | Onde | Esforço | Status |
|---|---|---|---|---|
| A1 | Testes de regressão para os bugs críticos corrigidos (escolas, cursos, usuarios, publico, declaracao, alunos IDOR) | `usuarios/tests.py`, `publico/tests.py` (novo), `escolas/tests.py`, `cursos/tests.py`, `alunos/tests.py`, `declaracao/tests.py` (novo) | Médio | ✅ |
| A2 | Cobertura mínima em `core/mixins.py` (`StaffRequiredMixin`/`CoordenadorRequiredMixin`) | `core/tests.py` (criado) | Médio | ✅ |
| A3 | Apagar scripts mortos: `find_copy.py`, `fix_aluno_form.py`, `test_verify.txt`, `test_write.txt` | raiz do repo | Trivial | ✅ |
| A4 | Remover branch morta em `ChamadaPublicaView.post` e comentários obsoletos em `alunos/views.py`/`usuarios/views.py` | `cursos/views/chamada.py`, `alunos/views.py`, `usuarios/views.py` | Trivial | ✅ |
| A5 | Configurar `LOGGING` em `settings.py` (console + arquivo rotativo em `logs/app.log`, já no `.gitignore` via `*.log`) | `settings.py` | Pequeno | ✅ |
| A6 | Remover o `print()` de debug do `alunos/score.py`; convertidos os 2 casos reais de erro (`Tempo/Tipo de Moradia` sem faixa) para `logger.warning` | `alunos/score.py` | Trivial | ✅ |

## Grupo B — Muda comportamento, mas contido e testável (baixo risco, precisa validação antes de subir) — ✅ CONCLUÍDO

Altera como o sistema se comporta em algum cenário, mas de forma previsível
e testável em dev antes do deploy. Não precisa de decisão de produto — só
de rodar a suite de testes e um teste manual do fluxo afetado.

| # | Item | Onde | Por que muda comportamento | Status |
|---|---|---|---|---|
| B1 | `transaction.atomic()` por linha no import de CSV (`alunos`, `cursos`) | `alunos/views.py`, `cursos/views/csv_import.py` | Mantém o comportamento "melhor esforço" (linha com erro é pulada, resto continua) — só fecha o risco real: no import de cursos, uma linha podia criar/atualizar um `TipoCurso` e falhar logo depois no `Curso`, deixando o `TipoCurso` órfão. Agora cada linha é um savepoint — falha no meio desfaz só aquela linha | ✅ |
| B2 | Índices de banco (`db_index=True`) em `Escola.tipo`, `Curso.status`, `Inscricao.status`, `Aluno.data_criacao`, `Aluno.cpf` | `escolas/models.py`, `cursos/models.py`, `alunos/models.py` | Gera migration; não muda resultado de query nenhuma, só performance | ✅ |
| B3 | `select_for_update()` no signal de `WebSocialMember` para fechar a race condition (dois cadastros simultâneos do mesmo CPF em escolas diferentes) | `alunos/signals.py` | Adiciona lock nas linhas de `Aluno` com aquele CPF antes de checar/criar o `WebSocialMember` — fecha a janela de concorrência sem mudar o resultado no caso normal (sem concorrência) | ✅ |
| B4 | Unificados 5 dos 6 pontos de log de auditoria manual duplicado em `cursos/views.py` para usar `AuditLogMixin.save_log()` | `cursos/views/curso.py`, `matricula.py`, `chamada.py` | `CursoQualitativosView` foi deixado como estava — seu `detalhes="Qualitativo enviado para a Turma"` é comparado por igualdade exata em `core/models.py get_notification_text()`; migrar pra `save_log()` (que sempre serializa em JSON) quebraria essa notificação. Os outros 5 não tinham essa dependência | ✅ |
| B5 | `cursos/views.py` (~2000 linhas, 50 classes) quebrado em pacote `cursos/views/` (`curso.py`, `matricula.py`, `chamada.py`, `csv_import.py`, `parceiro_ementa.py`, `avaliacao.py` + `__init__.py` reexportando tudo) | `cursos/views/` | Puro reposicionamento de código — `cursos/urls.py` e qualquer outro import continuam funcionando sem alteração (`from . import views; views.XxxView` resolve via `__init__.py`). Extração feita por script (sem digitação manual) para evitar erro de cópia; `manage.py check` + suite completa de `cursos` (38 testes) verificados depois | ✅ |

## Grupo C — Precisa decisão do usuário e/ou não posso validar sem acesso à VPS

Aqui o risco não é "vai ter um bug", é "pode tirar o site do ar" ou "muda
uma regra de negócio que só você pode aprovar". Nada aqui deveria ser feito
sem sua confirmação explícita antes.

| # | Item | Por que é sensível | Status |
|---|---|---|---|
| C1 | Rebind da porta `8000:8000` para loopback/Tailscale no `docker-compose.yml` | Se o `cloudflared` na VPS não roda em host-network, isso derruba o acesso público ao site. | Superado pelo C3 — o firewall de host já fecha a `:8000` pra internet sem precisar mexer no bind da porta (evita o risco de derrubar o cloudflared). |
| C2 | Rotação da senha do Postgres (`gestao_pass`) | Precisa `ALTER USER` + atualizar `.env` da VPS + recriar containers, na ordem certa. | Ainda pendente. |
| C3 | Firewall de host (Portainer, ttyd, Samba/NFS) — Fase 2 já mapeada no CLAUDE.md | Mexe em acesso da VPS, risco de lockout. | ✅ Feito em 2026-08-01 (executado direto via SSH, verificado com Tailscale desligado). Portainer e o app `gestao-ong` (não relacionado) também foram removidos da VPS na mesma sessão. Detalhe em `CLAUDE.md`, seção "Fase 2 de infra CONCLUÍDA". |
| C4 | `Escola` com `on_delete=CASCADE` → `PROTECT` + fluxo de arquivamento | Muda uma regra de negócio real: hoje apagar uma escola apaga tudo em cascata; trocar para `PROTECT` significa que apagar vai **falhar** até você decidir o que fazer com os dados — é uma mudança de UX pro superusuário, não só técnica. |
| C5 | Fluxo "clonar aluno" cross-escola (`AlunoVerificarCPFView`/`AlunoClonarView`) | Não é bug — mas é uma superfície ampla (staff de uma escola vê dado de aluno de outra escola da mesma rede). Precisa sua confirmação de que é assim mesmo que deveria funcionar. |
| C6 | CAPTCHA no autocadastro público (hCaptcha/Turnstile) | Nova dependência + muda a experiência do usuário final no cadastro — não é algo pra decidir sozinho. |
| C7 | Dockerfile com usuário não-root + build multi-stage | Mexe em permissão de arquivo dentro do container (bind mount `.:/app`) — risco real de quebrar escrita de `media/`/logs se o usuário/UID não bater certinho; precisa testar num ambiente igual ao de produção antes de aplicar direto. |
| C8 | Migrar `Aluno.turno_interesse` (string) para `ManyToMany` | Migration de dados real em cima de uma coluna hoje usada em produção — precisa de um plano de migração de dados (converter valores existentes), não só mudar o model. |

## Ordem sugerida

1. ~~Grupo A primeiro, inteiro~~ — ✅ feito.
2. ~~B1 e B4~~ — ✅ feito. B2, B3 e B5 também foram feitos na mesma sessão.
3. ~~C1 e C3~~ — ✅ feito em 2026-08-01 (firewall de host + remoção de
   Portainer/gestao-ong; C1 ficou superado por C3, ver tabela acima).
4. **Próximo passo: C2** (rotação da senha do Postgres) — o item de
   segurança de infra mais importante que resta.
5. Resto do Grupo C fica pra quando surgir tempo/necessidade — nenhum deles
   é urgente hoje.

Estado final desta sessão: 110 testes automatizados passando (suite
completa de todas as apps, banco de dados zerado e recriado do zero para a
verificação final — `manage.py test --noinput`), `manage.py check` limpo,
nenhuma mudança commitada (working tree pronto para revisão).
