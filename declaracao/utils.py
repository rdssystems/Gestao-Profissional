from datetime import date

def get_aluno_status_para_inscricao(inscricao):
    """
    Determina o status de um aluno em um curso (matriculado, cursando, concluído)
    com base na data atual e no status da inscrição e do curso.
    """
    hoje = date.today()
    curso = inscricao.curso

    # 0. Inscrição de desistente não gera declaração
    if inscricao.status == 'desistente':
        return 'desistente'

    # 1. Inscrição concluída tem a maior prioridade.
    if inscricao.status == 'concluido':
        return 'concluido'

    # 2. Utiliza o status do curso
    if curso.status == 'Aberta':
        return 'matriculado'
    if curso.status == 'Em Andamento':
        return 'cursando'
    if curso.status in ['Concluído', 'Arquivado']:
        return 'aguardando_regularizacao'

    # 3. Fallback para lógica baseada em datas
    if hoje < curso.data_inicio:
        return 'matriculado'
    if curso.data_inicio <= hoje <= curso.data_fim:
        return 'cursando'
    if hoje > curso.data_fim:
         return 'aguardando_regularizacao'

    # Outros casos
    return 'invalido'


def generate_declaration_text(status, inscricao):
    """
    Constrói o texto principal da declaração com base no status do aluno.
    """
    aluno = inscricao.aluno
    curso = inscricao.curso

    if status == "concluido":
        verbo = "concluiu"
    elif status == "matriculado":
        verbo = "está matriculado(a)"
    elif status == "cursando":
        verbo = "está cursando"
    else:
        return None

    # Texto do período (Sempre incluído agora)
    periodo_texto = f"no período de {curso.data_inicio.strftime('%d/%m/%Y')} à {curso.data_fim.strftime('%d/%m/%Y')}"
    if curso.turno:
        periodo_texto += f", no turno {curso.turno}, "
    else:
        periodo_texto += ", "

    text = (f"Declaramos para os devidos fins que, {aluno.nome_completo.upper()}, portador(a) do CPF nº {aluno.cpf}, "
            f"{verbo} o curso de {curso.nome}, com carga horária de {curso.carga_horaria} horas, "
            f"{periodo_texto}"
            f"ministrado pela Diretoria de Qualificação Profissional, Geração de Trabalho e Renda.")
    
    return text
