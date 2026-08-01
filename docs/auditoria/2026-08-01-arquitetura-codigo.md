# Auditoria de Arquitetura e Organização de Código — 2026-08-01

Achados de um sub-agente dedicado (leitura completa de todas as apps). Ao
contrário de `2026-08-01-seguranca.md`, **nada aqui foi corrigido nesta
rodada** — é backlog para uma sessão de refatoração dedicada, priorizado do
que mais importa para o menos. Referências `arquivo:linha` podem ter
deslocado uma ou duas linhas por causa dos fixes de segurança aplicados no
mesmo commit (import de `Http404`, novos helpers no topo de alguns arquivos).

## Prioridade alta (risco funcional ou de manutenção real)

1. **Apps de segurança crítica sem teste nenhum**: `usuarios` (onde estava a
   escalação de privilégio) e `publico` (onde estava o vazamento de PII) têm
   ZERO testes. Os dois bugs mais graves desta auditoria de segurança viviam
   exatamente nas duas apps sem cobertura nenhuma — não é coincidência.
   `core` (onde vive `StaffRequiredMixin`/`CoordenadorRequiredMixin`, a
   espinha dorsal de autorização do sistema) também não tem teste nenhum.
   **Recomendação concreta**: pelo menos um teste de regressão por bug
   corrigido nesta rodada (ex.: "Coordenador de escola A não pode editar
   usuário de escola B", "CPF de outra escola não aparece no cadastro
   público"), para essas correções não voltarem silenciosamente num
   refactor futuro.
2. **`cursos/views.py` é um arquivo de ~2000 linhas** com ~50 view classes
   misturando cursos, matrículas, chamada, avaliação, import CSV, ementas —
   sem `services.py`. Qualquer mudança exige navegar um arquivo enorme.
3. **Import de CSV sem transação** (`alunos/views.py`
   `AlunoCSVUploadView.handle_uploaded_file`, `cursos/views.py`
   `CursoCSVUploadView.handle_uploaded_file`, quase idênticos, copiados um do
   outro): erro no meio do arquivo deixa o banco com parte das linhas
   importadas e parte não, sem rollback. Envolver em `transaction.atomic()`
   (ou pelo menos por lote) e extrair a lógica duplicada para um
   `services.py` compartilhado.
4. **Nenhuma configuração de `LOGGING`** em `settings.py`, combinado com
   `except Exception as e: print(...)` espalhado (11+ ocorrências em
   `alunos/views.py`, `cursos/views.py`, `score_config/views.py`,
   `core/mixins.py`) — falhas de auditoria/notificação em produção só
   aparecem se alguém estiver olhando `docker logs` no exato momento. Isso é
   particularmente ruim para um sistema cujo propósito inclui auditoria.
5. **`alunos/score.py` imprime um relatório de pontuação inteiro
   (`print()`) a cada `Aluno.save()`** via signal `post_save` — spam
   constante de log em produção, sem nenhum ganho operacional.
6. **Escolas — `on_delete=CASCADE` em cascata de dados sensíveis**:
   `Aluno.escola`, `Curso.escola`, `Pasta.escola`, `DocumentoUnidade.escola`
   todos cascateiam de `Escola`. Apagar uma escola (ação de superuser)
   apaga silenciosamente todo aluno, curso, matrícula e documento associado —
   sem soft-delete, sem exigir export/anonimização antes. Dado que inclui
   CPF, renda e dados de saúde, considerar `PROTECT` + fluxo explícito de
   arquivamento em vez de um DELETE de um clique.

## Prioridade média

7. **Duplicação de log de auditoria manual** em vez de reusar
   `AuditLogMixin.save_log`: pelo menos 6 lugares em `cursos/views.py`
   reimplementam o mesmo `try: AuditLog.objects.create(...) except
   Exception as e: print(...)` em views que não herdam o mixin.
8. **Bare `except:` na dashboard** (`escolas/views.py:84,111,143-151,164,189`)
   zera KPIs silenciosamente em qualquer exceção, inclusive um `escola_id`
   malformado — mascarava bugs reais nos números do dashboard.
9. **Sem índice de banco em lugar nenhum** (`db_index=True`/`models.Index`
   não aparece em nenhum `models.py`), apesar de filtros constantes por
   `Escola.tipo`, `Curso.status`, `Inscricao.status`, datas do dashboard.
   Provavelmente já é um problema de performance com o volume atual de dados.
10. **`Aluno.turno_interesse` é uma string com valores concatenados**
    (parseada manualmente em `alunos/forms.py`), consultada com
    `icontains` (`cursos/views.py:667`) — frágil e não indexável. Um
    `ManyToManyField` resolveria.
11. **Definição de escolha duplicada**: `cursos/models.py` define
    `STATUS_PRESENCA_CHOICES` duas vezes dentro de `Chamada` (a segunda
    sombra a primeira silenciosamente) — sobra de copy/paste.
12. **`score_config` depende de strings que espelham `Aluno.TEMPO_MORADIA_CHOICES`/
    `TIPO_MORADIA_CHOICES`** sem uma fonte única — renomear uma choice em
    `Aluno` quebra silenciosamente o cálculo de pontuação (`alunos/score.py`
    tem um `try/except DoesNotExist` que retorna 0 pontos em vez de
    estourar erro, então o bug não seria percebido, só a pontuação ficaria
    errada).
13. **`WebSocialMember`**: regra "1 por CPF no sistema todo" só é garantida
    em código de aplicação (`alunos/signals.py`), com race condition
    (TOCTOU) possível entre duas matrículas simultâneas do mesmo CPF em
    escolas diferentes.

## Prioridade baixa / limpeza

14. **Scripts soltos na raiz do repo, sem uso real**: `find_copy.py` (referencia
    um dump que não existe mais), `fix_aluno_form.py` (já aplicado, é
    no-op), `test_verify.txt`, `test_write.txt`. Seguros para apagar.
15. **Dead code**: branch inalcançável em `cursos/views.py`
    `ChamadaPublicaView.post` (linhas após um `return` que nunca são
    atingidas); comentários obsoletos em `alunos/views.py` debatendo se
    `email_principal` é único (não é, desde uma mudança anterior).
16. **`documentos_alunos/` não é uma app Django** — é só o caminho de upload
    de `alunos.ArquivoAluno`, sem `__init__.py`/`models.py`. Nome confuso
    para quem espera encontrar uma app de verdade ali.
17. **Migrações com merge repetido** (`cursos/migrations/0022-0025`,
    `core/migrations/0010-0011`) — sinal de que `makemigrations` foi rodado
    em paralelo por mais de uma pessoa/agente sem coordenação. Reforça por
    que `atualizar.sh` **não deve** rodar `makemigrations` direto na VPS
    (ver `2026-08-01-infraestrutura.md`) — isso só pioraria esse problema.
18. **Duplicação de upload/delete de arquivo** entre
    `alunos.ArquivoAluno` (documentos de aluno) e `documentos.DocumentoUnidade`
    (documentos da unidade) — dois sistemas paralelos de pasta+upload que
    poderiam compartilhar um mixin/service.
19. **Migração de dados com username hardcoded**:
    `core/migrations/0005_set_larissa_admin_cp.py` /
    `0009_ensure_larissa_admin_cp.py` — funciona (tem
    `try/except DoesNotExist: return`), mas é estranho grampear uma conta
    específica na história de migrações; um management command seria mais
    apropriado.
