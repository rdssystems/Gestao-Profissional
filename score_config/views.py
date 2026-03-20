from django.shortcuts import render, redirect
from django.views.generic import View
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib import messages
from django.db import transaction
from core.models import AuditLog
from django.contrib.contenttypes.models import ContentType
import json

from .forms import (
    RendaFamiliarScoreForm,
    RendaPerCapitaScoreForm,
    NumeroMoradoresScoreForm,
    MembrosTrabalhamScoreForm,
    TempoMoradiaFormSet,
    TipoMoradiaFormSet
)
from .models import (
    RendaFamiliarFaixa,
    RendaPerCapitaFaixa,
    NumeroMoradoresFaixa,
    MembrosTrabalhamFaixa,
    TempoMoradiaFaixa,
    TipoMoradiaFaixa
)
from alunos.models import Aluno

class SuperuserRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser

class ConfiguracaoScoreView(SuperuserRequiredMixin, View):
    template_name = 'score_config/configuracao_form.html'

    def get(self, request, *args, **kwargs):
        context = self.get_context_data()
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        forms = self._get_forms(request.POST)
        formsets = self._get_formsets(request.POST)

        all_valid = all(f.is_valid() for f in forms.values()) and all(fs.is_valid() for fs in formsets.values())

        if all_valid:
            try:
                with transaction.atomic():
                    self._save_valor_form(forms['Renda Familiar'], RendaFamiliarFaixa)
                    self._save_valor_form(forms['Renda Per Capita'], RendaPerCapitaFaixa)
                    self._save_qtd_form(forms['Número de Moradores'], NumeroMoradoresFaixa)
                    self._save_qtd_form(forms['Membros que Trabalham'], MembrosTrabalhamFaixa)
                    
                    formsets['Tempo de Moradia'].save()
                    formsets['Tipo de Moradia'].save()

                    # LOG DE AUDITORIA MANUAL
                    try:
                        # Usamos RendaFamiliarFaixa como referência de ContentType para "Configuração de Score"
                        ct = ContentType.objects.get_for_model(RendaFamiliarFaixa)
                        AuditLog.objects.create(
                            usuario=request.user,
                            acao='UPDATE',
                            content_type=ct,
                            object_id='GLOBAL_CONFIG',
                            detalhes=json.dumps({'info': 'Alteração nas regras de pontuação (Score)'}),
                            ip_address=request.META.get('REMOTE_ADDR')
                        )
                    except Exception as e:
                        print(f"Erro ao salvar log: {e}")

                messages.success(request, "Configurações de score salvas com sucesso!")
                return redirect('score_config:configurar')

            except Exception as e:
                messages.error(request, f"Ocorreu um erro ao salvar as configurações: {e}")
        else:
            messages.error(request, "Por favor, corrija os erros abaixo.")
        
        context = {
            'forms': forms,
            'formsets': formsets
        }
        return render(request, self.template_name, context)

    def get_context_data(self, **kwargs):
        return {
            'forms': self._get_forms(),
            'formsets': self._get_formsets()
        }

    def _get_forms(self, data=None):
        return {
            'Renda Familiar': RendaFamiliarScoreForm(data, prefix='renda_familiar', initial=self._get_initial_valor(RendaFamiliarFaixa)),
            'Renda Per Capita': RendaPerCapitaScoreForm(data, prefix='renda_per_capita', initial=self._get_initial_valor(RendaPerCapitaFaixa)),
            'Número de Moradores': NumeroMoradoresScoreForm(data, prefix='num_moradores', initial=self._get_initial_qtd(NumeroMoradoresFaixa)),
            'Membros que Trabalham': MembrosTrabalhamScoreForm(data, prefix='membros_trabalham', initial=self._get_initial_qtd(MembrosTrabalhamFaixa)),
        }

    def _get_formsets(self, data=None):
        for choice, _ in Aluno.TEMPO_MORADIA_CHOICES:
            TempoMoradiaFaixa.objects.get_or_create(titulo=choice)
        for choice, _ in Aluno.TIPO_MORADIA_CHOICES:
            TipoMoradiaFaixa.objects.get_or_create(titulo=choice)

        return {
            'Tempo de Moradia': TempoMoradiaFormSet(data, prefix='tempo_moradia', queryset=TempoMoradiaFaixa.objects.all()),
            'Tipo de Moradia': TipoMoradiaFormSet(data, prefix='tipo_moradia', queryset=TipoMoradiaFaixa.objects.all()),
        }

    def _get_initial_valor(self, model_class):
        faixas = list(model_class.objects.order_by('-valor_maior_que'))
        initial = {}
        faixas_com_valor = [f for f in faixas if f.valor_maior_que > 0]
        for i, faixa in enumerate(faixas_com_valor[:3]):
            initial[f'valor_{i+1}'] = faixa.valor_maior_que
            initial[f'pontos_{i+1}'] = faixa.pontos
        faixa_base = next((f for f in faixas if f.valor_maior_que == 0), None)
        if faixa_base:
            initial['pontos_base'] = faixa_base.pontos
        return initial

    def _get_initial_qtd(self, model_class):
        faixas = list(model_class.objects.order_by('-qtd_maior_ou_igual'))
        initial = {}
        faixas_com_valor = [f for f in faixas if f.qtd_maior_ou_igual > 0]
        for i, faixa in enumerate(faixas_com_valor[:3]):
            initial[f'qtd_{i+1}'] = faixa.qtd_maior_ou_igual
            initial[f'pontos_{i+1}'] = faixa.pontos
        faixa_base = next((f for f in faixas if f.qtd_maior_ou_igual == 0), None)
        if faixa_base:
            initial['pontos_base'] = faixa_base.pontos
        return initial

    def _save_valor_form(self, form, model_class):
        model_class.objects.all().delete()
        for i in range(1, 4):
            valor = form.cleaned_data.get(f'valor_{i}')
            pontos = form.cleaned_data.get(f'pontos_{i}')
            if valor is not None and pontos is not None:
                model_class.objects.create(valor_maior_que=valor, pontos=pontos)
        pontos_base = form.cleaned_data.get('pontos_base')
        if pontos_base is not None:
            model_class.objects.create(valor_maior_que=0, pontos=pontos_base)

    def _save_qtd_form(self, form, model_class):
        model_class.objects.all().delete()
        for i in range(1, 4):
            qtd = form.cleaned_data.get(f'qtd_{i}')
            pontos = form.cleaned_data.get(f'pontos_{i}')
            if qtd is not None and pontos is not None:
                model_class.objects.create(qtd_maior_ou_igual=qtd, pontos=pontos)
        pontos_base = form.cleaned_data.get('pontos_base')
        if pontos_base is not None:
            model_class.objects.create(qtd_maior_ou_igual=0, pontos=pontos_base)