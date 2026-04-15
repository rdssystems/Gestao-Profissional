# Plano: Refatoração da Auditoria e Notificações (Atividades)

## 1. Expansão de Captura da Auditoria

O sistema `AuditLog` já é robusto gravando "quem fez, que dia, o que fez (Criou, Editou) e onde". Vamos anexar as novas ações da plataforma ao sistema.

### [core/audit_signals.py] e [Views manuais]

#### [MODIFY] `core/audit_signals.py`
Vamos plugar os sinais (signals) para gravar `CREATE`, `UPDATE` e `DELETE` nativos dos seguintes modelos novos:
*   `RegistroAula` (Quando o professor ou coordenação preenche o formulário online de chamada)
*   `AvaliacaoProfessorAluno` (Ficha do conceital do curso feita para os alunos pelo educador)
*   `AvaliacaoAlunoCurso` (Avaliação do curso feita pelos alunos online)
*   `ArquivoAluno` (Quando adicionam novos PDFs/Imagens na Ficha/Docs do aluno)

#### [MODIFY] `cursos/views.py` `(CursoQualitativosView)`
Ao invés de registrar uma notificação por "cada aluno que sofreu lançamento qualitativo", gravaremos apenas **uma** ação agrupada "Qualitativo enviado para a Turma X" logo após você clicar em "Salvar Lançamento" dessa turma específica, mantendo as notificações limpas e agrupando as edições das chamadas.

---

## 2. Mensagens Personalizadas nas Notificações (WebSockets & Dashboard)

"A auditoria continuará sendo somente CREATE/UPDATE/DELETE. Mas nas notificações, queremos frases bonitas explicativas e rastreáveis."

### [MODIFY] `core/models.py` `(Classe AuditLog)`
Vou criar uma funcionalidade no `AuditLog` chamada `get_notification_text()`. Ela fará a tradução em string humanizada baseada em qual "Tabela" (Content-Type) gerou o log. Exemplos propostos:

1.  **Registro de Aula:** "{usuario} enviou a lista de chamadas do curso {curso}"
2.  **Qualitativo:** "{usuario} lançou qualitativos do curso {curso}"
3.  **Avaliação:** "{usuario} preencheu a avaliação do curso {curso}" ou "{professor} avaliou o aluno {aluno} no curso {curso}"
4.  **Arquivo Ficha:** "{usuario} atualizou um arquivo na ficha do aluno {aluno}"
5.  **Genérico** (outros modelos antigos da Auditoria): "Klisman rDs criou um registro em Escola (Polo Oeste)"

### [MODIFY] `gestao_qualificacao_profissional/templates/base.html` & `escolas/templates/escolas/dashboard.html`
Substituirei o código técnico na Dashboard `<span class="text-muted">{{ log.get_acao_display|lower }}</span> <span class="fw-bold">{{ log.content_type.name }}</span>` por referenciar a nossa conversão humanizada inteligente: `{{ log.get_notification_text|safe }}`.

### [MODIFY] `core/signals.py` `(broadcast_audit_log)`
O sistema WebSocket (que notifica em tempo-real na tela as bolinhas dos staffs) também trocará a string técnica para a string humanizada.
