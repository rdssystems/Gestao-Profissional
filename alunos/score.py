from score_config.models import (
    RendaFamiliarFaixa,
    RendaPerCapitaFaixa,
    NumeroMoradoresFaixa,
    MembrosTrabalhamFaixa,
    TempoMoradiaFaixa,
    TipoMoradiaFaixa
)

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
    print(f"--- Calculating score for Aluno: {aluno.nome_completo} (ID: {aluno.pk}) ---")

    # 1. Renda Familiar
    rf_score = _get_score_for_numerical_range(aluno.renda_familiar or 0, RendaFamiliarFaixa, 'valor_maior_que')
    score += rf_score
    print(f"Renda Familiar ({aluno.renda_familiar or 0}): {rf_score} points. Total score: {score}")

    # 2. Renda Per Capita
    rpc_score = _get_score_for_numerical_range(aluno.renda_per_capita or 0, RendaPerCapitaFaixa, 'valor_maior_que')
    score += rpc_score
    print(f"Renda Per Capita ({aluno.renda_per_capita or 0}): {rpc_score} points. Total score: {score}")

    # 3. Número de Moradores
    nm_score = _get_score_for_numerical_quantity(aluno.num_moradores or 0, NumeroMoradoresFaixa, 'qtd_maior_ou_igual')
    score += nm_score
    print(f"Número de Moradores ({aluno.num_moradores or 0}): {nm_score} points. Total score: {score}")

    # 4. Membros que Trabalham
    mqt_score = _get_score_for_numerical_quantity(aluno.quantos_trabalham or 0, MembrosTrabalhamFaixa, 'qtd_maior_ou_igual')
    score += mqt_score
    print(f"Membros que Trabalham ({aluno.quantos_trabalham or 0}): {mqt_score} points. Total score: {score}")

    # 5. Tempo de Moradia
    tm_score = 0
    if aluno.tempo_moradia:
        try:
            faixa = TempoMoradiaFaixa.objects.get(titulo=aluno.tempo_moradia)
            tm_score = faixa.pontos
        except TempoMoradiaFaixa.DoesNotExist:
            print(f"Tempo de Moradia '{aluno.tempo_moradia}' not found in configuration.")
        score += tm_score
    print(f"Tempo de Moradia ('{aluno.tempo_moradia or 'N/A'}'): {tm_score} points. Total score: {score}")

    # 6. Tipo de Moradia
    tipo_m_score = 0
    if aluno.tipo_moradia:
        try:
            faixa = TipoMoradiaFaixa.objects.get(titulo=aluno.tipo_moradia)
            tipo_m_score = faixa.pontos
        except TipoMoradiaFaixa.DoesNotExist:
            print(f"Tipo de Moradia '{aluno.tipo_moradia}' not found in configuration.")
        score += tipo_m_score
    print(f"Tipo de Moradia ('{aluno.tipo_moradia or 'N/A'}'): {tipo_m_score} points. Total score: {score}")

    print(f"--- Final score for Aluno {aluno.nome_completo}: {score} ---")
    return score
