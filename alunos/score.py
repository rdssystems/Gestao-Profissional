import logging

from score_config.models import (
    RendaFamiliarFaixa,
    RendaPerCapitaFaixa,
    NumeroMoradoresFaixa,
    MembrosTrabalhamFaixa,
    TempoMoradiaFaixa,
    TipoMoradiaFaixa
)

logger = logging.getLogger(__name__)

def _get_score_for_numerical_range(value, model_class, field_name):
    """
    Função auxiliar para calcular o score para critérios numéricos.
    """
    # Ordena as faixas do maior valor para o menor
    faixas = model_class.objects.order_by(f'-{field_name}')
    
    # Itera sobre as faixas com valor > 0
    for faixa in faixas.filter(**{f'{field_name}__gt': 0}):
        if value > getattr(faixa, field_name):
            return faixa.pontos
            
    # Se nenhuma faixa 'maior que' corresponder, usa a faixa base (valor 0)
    try:
        faixa_base = faixas.get(**{field_name: 0})
        return faixa_base.pontos
    except model_class.DoesNotExist:
        return 0

def _get_score_for_numerical_quantity(value, model_class, field_name):
    """
    Função auxiliar para calcular o score para critérios de quantidade (>=).
    """
    faixas = model_class.objects.order_by(f'-{field_name}')
    
    for faixa in faixas.filter(**{f'{field_name}__gt': 0}):
        if value >= getattr(faixa, field_name):
            return faixa.pontos
            
    try:
        faixa_base = faixas.get(**{field_name: 0})
        return faixa_base.pontos
    except model_class.DoesNotExist:
        return 0

def calcular_score_aluno(aluno):
    """
    Calcula o score total de um aluno com base nas faixas de score configuradas.
    """
    score = 0

    # 1. Renda Familiar
    score += _get_score_for_numerical_range(aluno.renda_familiar or 0, RendaFamiliarFaixa, 'valor_maior_que')

    # 2. Renda Per Capita
    score += _get_score_for_numerical_range(aluno.renda_per_capita or 0, RendaPerCapitaFaixa, 'valor_maior_que')

    # 3. Número de Moradores
    score += _get_score_for_numerical_quantity(aluno.num_moradores or 0, NumeroMoradoresFaixa, 'qtd_maior_ou_igual')

    # 4. Membros que Trabalham
    score += _get_score_for_numerical_quantity(aluno.quantos_trabalham or 0, MembrosTrabalhamFaixa, 'qtd_maior_ou_igual')

    # 5. Tempo de Moradia
    if aluno.tempo_moradia:
        try:
            faixa = TempoMoradiaFaixa.objects.get(titulo=aluno.tempo_moradia)
            score += faixa.pontos
        except TempoMoradiaFaixa.DoesNotExist:
            # Choice de Aluno.tempo_moradia sem faixa correspondente em
            # score_config — provável dessincronia entre os dois (ver
            # docs/auditoria/2026-08-01-arquitetura-codigo.md, item 12).
            logger.warning(
                "calcular_score_aluno: Tempo de Moradia '%s' (aluno %s) sem faixa correspondente em score_config.",
                aluno.tempo_moradia, aluno.pk,
            )

    # 6. Tipo de Moradia
    if aluno.tipo_moradia:
        try:
            faixa = TipoMoradiaFaixa.objects.get(titulo=aluno.tipo_moradia)
            score += faixa.pontos
        except TipoMoradiaFaixa.DoesNotExist:
            logger.warning(
                "calcular_score_aluno: Tipo de Moradia '%s' (aluno %s) sem faixa correspondente em score_config.",
                aluno.tipo_moradia, aluno.pk,
            )

    return score
