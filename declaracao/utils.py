from datetime import date

def get_aluno_status_para_inscricao(inscricao):
    """
    Determina o status de um aluno em um curso (matriculado, cursando, concluído)
    com base na data atual e no status da inscrição e do curso.
    """
    hoje = date.today()
    curso = inscricao.curso

    # 1. Inscrição concluída tem a maior prioridade.
    if inscricao.status == 'concluido':
        return 'concluido'

    # 2. Utiliza o status do curso para determinar o tipo de declaração,
    #    apenas se a inscrição não estiver concluída.
    #    Isso permite gerar declarações para cursos 'Aberta' (como matriculado)
    #    e 'Em Andamento' (como cursando), conforme solicitado.
    if curso.status == 'Aberta':
        return 'matriculado' # Course is open, student is enrolled
    if curso.status == 'Em Andamento':
        return 'cursando' # Course is ongoing, student is currently studying

    # 3. Fallback para lógica baseada em datas se o status do curso não se encaixa
    #    ou se a inscrição não está concluída e o curso está "Concluído" (do ponto de vista do curso).
    if hoje < curso.data_inicio:
        return 'matriculado'
        
    if curso.data_inicio <= hoje <= curso.data_fim:
        return 'cursando'

    # 4. Se a inscrição não está concluída e a data do curso já passou,
    # ou curso.status é 'Concluído' mas a inscrição não, e não foi coberto acima.
    if hoje > curso.data_fim and inscricao.status != 'concluido':
         return 'aguardando_regularizacao'

    # Outros casos, como 'desistente' na inscrição ou status inválido do curso
    return 'invalido'


def generate_declaration_text(status, inscricao):
    """
    Constrói o texto principal da declaração com base no status do aluno.
    Retorna None se o status for inválido para gerar declaração.
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
        # Se o status for 'invalido', 'aguardando_regularizacao', etc. não gera texto.
        return None

    # Ajuste no texto para incluir as datas do curso apenas para matriculado/cursando
    periodo_texto = ""
    if status in ["matriculado", "cursando"]:
        periodo_texto = (f"no período de {curso.data_inicio.strftime('%d/%m/%Y')} à {curso.data_fim.strftime('%d/%m/%Y')}, ")

    text = (f"Declaramos para os devidos fins que, {aluno.nome_completo.upper()}, portador(a) do CPF nº {aluno.cpf}, "
            f"{verbo} o curso de {curso.nome}, com carga horária de {curso.carga_horaria} horas, "
            f"{periodo_texto}"
            f"ministrado pela Diretoria de Qualificação Profissional, Geração de Trabalho e Renda.")
    
    return text
