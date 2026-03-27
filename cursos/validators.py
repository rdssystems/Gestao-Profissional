from django.core.exceptions import ValidationError
from .models import Inscricao, Curso, TipoCurso 

def validar_idade_minima_no_curso(aluno, curso):
    """
    Verifica se o aluno terá 16 anos completos na data de início do curso.
    Levanta ValidationError caso contrário.
    """
    if not aluno.data_nascimento or not curso.data_inicio:
        return True

    data_nasc = aluno.data_nascimento
    data_inicio = curso.data_inicio

    # Cálculo preciso da idade na data de início
    idade = data_inicio.year - data_nasc.year - (
        (data_inicio.month, data_inicio.day) < (data_nasc.month, data_nasc.day)
    )

    if idade < 16:
        raise ValidationError(
            f"O aluno {aluno.nome_completo} terá apenas {idade} anos na data de início do curso ({data_inicio.strftime('%d/%m/%Y')}). "
            "A idade mínima exigida no início das aulas é de 16 anos."
        )
    return True

def validar_conflito_matricula(aluno, novo_curso):
    """
    Valida se um aluno pode ser matriculado em um novo curso, verificando conflitos e idade.
    Retorna True se não houver conflitos, levanta ValidationError caso contrário.
    """
    # 1. Validar Idade Mínima na Data de Início
    validar_idade_minima_no_curso(aluno, novo_curso)

    # 2. Obter todas as inscrições ATIVAS do aluno (status 'cursando')
    inscricoes_existente_aluno = Inscricao.objects.filter(aluno=aluno, status='cursando')

    for inscricao_existente in inscricoes_existente_aluno:
        curso_existente = inscricao_existente.curso

        # Regra 1: Mesmo Tipo (Bloqueio mesmo se horários forem diferentes)
        if novo_curso.tipo_curso and novo_curso.tipo_curso == curso_existente.tipo_curso:
            raise ValidationError(
                f'O aluno já está inscrito em um curso do tipo "{novo_curso.tipo_curso.nome}" ({curso_existente.nome}).'
            )

        # Regra 2: Conflito de Horário e Data
        conflito_turno = (
            novo_curso.turno and curso_existente.turno and novo_curso.turno == curso_existente.turno
        )
        
        conflito_data = (
            (novo_curso.data_inicio <= curso_existente.data_fim) and
            (novo_curso.data_fim >= curso_existente.data_inicio)
        )

        if conflito_turno and conflito_data:
            raise ValidationError(
                f'Conflito de horário/data: O aluno já está inscrito no curso "{curso_existente.nome}" '
                f'({curso_existente.get_turno_display()} - {curso_existente.data_inicio} a {curso_existente.data_fim}), '
                f'que coincide com o período deste novo curso.'
            )
    return True
