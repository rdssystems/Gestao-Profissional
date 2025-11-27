from django import forms
from .models import (
    TempoMoradiaFaixa,
    TipoMoradiaFaixa
)

class BaseFaixaNumericaForm(forms.Form):
    # Faixa 1 (Maior valor)
    valor_1 = forms.DecimalField(label="Valor 1", required=False, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    pontos_1 = forms.IntegerField(label="Pontos 1", required=False, widget=forms.NumberInput(attrs={'class': 'form-control'}))

    # Faixa 2
    valor_2 = forms.DecimalField(label="Valor 2", required=False, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    pontos_2 = forms.IntegerField(label="Pontos 2", required=False, widget=forms.NumberInput(attrs={'class': 'form-control'}))

    # Faixa 3
    valor_3 = forms.DecimalField(label="Valor 3", required=False, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    pontos_3 = forms.IntegerField(label="Pontos 3", required=False, widget=forms.NumberInput(attrs={'class': 'form-control'}))

    # Faixa Base (menor ou igual ao valor_3)
    pontos_base = forms.IntegerField(label="Pontos Base (valor <= Valor 3)", required=False, widget=forms.NumberInput(attrs={'class': 'form-control'}))

    def clean(self):
        cleaned_data = super().clean()
        # Verifica o preenchimento dos pares e a sequência
        for i in range(1, 4):
            valor = cleaned_data.get(f'valor_{i}')
            pontos = cleaned_data.get(f'pontos_{i}')

            # Se um do par for preenchido, o outro também deve ser
            if (valor is not None and pontos is None) or (valor is None and pontos is not None):
                raise forms.ValidationError(f"A Faixa {i} está incompleta. Preencha o valor e os pontos.")

            # Se uma faixa posterior for preenchida, a anterior também deve ser
            if i > 1:
                valor_anterior = cleaned_data.get(f'valor_{i-1}')
                if valor is not None and valor_anterior is None:
                    raise forms.ValidationError(f"A Faixa {i-1} deve ser preenchida antes da Faixa {i}.")

        # Validação de ordenação
        v1 = cleaned_data.get('valor_1')
        v2 = cleaned_data.get('valor_2')
        v3 = cleaned_data.get('valor_3')

        if v1 is not None and v2 is not None and not (v1 > v2):
            raise forms.ValidationError("Valor 1 deve ser maior que Valor 2.")
        if v2 is not None and v3 is not None and not (v2 > v3):
            raise forms.ValidationError("Valor 2 deve ser maior que Valor 3.")
        
        return cleaned_data

class RendaFamiliarScoreForm(BaseFaixaNumericaForm):
    pass

class RendaPerCapitaScoreForm(BaseFaixaNumericaForm):
    pass

class BaseQtdNumericaForm(forms.Form):
    # Faixa 1 (Maior quantidade)
    qtd_1 = forms.IntegerField(label="Qtd 1", required=False, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    pontos_1 = forms.IntegerField(label="Pontos 1", required=False, widget=forms.NumberInput(attrs={'class': 'form-control'}))

    # Faixa 2
    qtd_2 = forms.IntegerField(label="Qtd 2", required=False, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    pontos_2 = forms.IntegerField(label="Pontos 2", required=False, widget=forms.NumberInput(attrs={'class': 'form-control'}))

    # Faixa 3
    qtd_3 = forms.IntegerField(label="Qtd 3", required=False, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    pontos_3 = forms.IntegerField(label="Pontos 3", required=False, widget=forms.NumberInput(attrs={'class': 'form-control'}))

    # Faixa Base (menor que qtd_3)
    pontos_base = forms.IntegerField(label="Pontos Base (qtd < Qtd 3)", required=False, widget=forms.NumberInput(attrs={'class': 'form-control'}))

    def clean(self):
        cleaned_data = super().clean()

        # Verifica o preenchimento dos pares e a sequência
        for i in range(1, 4):
            qtd = cleaned_data.get(f'qtd_{i}')
            pontos = cleaned_data.get(f'pontos_{i}')

            if (qtd is not None and pontos is None) or (qtd is None and pontos is not None):
                raise forms.ValidationError(f"A Faixa {i} está incompleta. Preencha a quantidade e os pontos.")

            if i > 1:
                qtd_anterior = cleaned_data.get(f'qtd_{i-1}')
                if qtd is not None and qtd_anterior is None:
                    raise forms.ValidationError(f"A Faixa {i-1} deve ser preenchida antes da Faixa {i}.")

        # Validação de ordenação
        q1 = cleaned_data.get('qtd_1')
        q2 = cleaned_data.get('qtd_2')
        q3 = cleaned_data.get('qtd_3')

        if q1 is not None and q2 is not None and not (q1 > q2):
            raise forms.ValidationError("Qtd 1 deve ser maior que Qtd 2.")
        if q2 is not None and q3 is not None and not (q2 > q3):
            raise forms.ValidationError("Qtd 2 deve ser maior que Qtd 3.")
        
        return cleaned_data

class NumeroMoradoresScoreForm(BaseQtdNumericaForm):
    pass

class MembrosTrabalhamScoreForm(BaseQtdNumericaForm):
    pass


# Mantém o formset para os de título, pois a interface é diferente
TipoMoradiaFormSet = forms.modelformset_factory(
    TipoMoradiaFaixa,
    fields=('titulo', 'pontos'),
    extra=0,
    can_delete=False,
    widgets={
        'titulo': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
        'pontos': forms.NumberInput(attrs={'class': 'form-control'}),
    }
)

TempoMoradiaFormSet = forms.modelformset_factory(
    TempoMoradiaFaixa,
    fields=('titulo', 'pontos'),
    extra=0,
    can_delete=False,
    widgets={
        'titulo': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
        'pontos': forms.NumberInput(attrs={'class': 'form-control'}),
    }
)