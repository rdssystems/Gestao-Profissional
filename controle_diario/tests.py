from datetime import date

from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse

from .models import RelatorioDiarioSine


class ControleDiarioSineVisibilityTest(TestCase):
    """
    Regressão de 2026-08-02: o card "Registros SINE" no dashboard de
    Controle Diário (controle_diario_admin.html) aparecia sem nenhuma
    checagem de permissão no template — admin_cp e admin_uditech, que
    passam no @user_passes_test da view (admin de segmento), também viam
    os indicadores do SINE, que deveriam ser só de admin de verdade
    (superuser ou Profile.nivel_acesso == 'SUPERUSER').
    """

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='root_sine', password='x', email='root_sine@example.com'
        )
        self.admin_cp = User.objects.create_user(username='admin_cp_sine', password='x')
        self.admin_cp.profile.nivel_acesso = 'ADMIN_CP'
        self.admin_cp.profile.save()

        self.admin_uditech = User.objects.create_user(username='admin_uditech_sine', password='x')
        self.admin_uditech.profile.nivel_acesso = 'ADMIN_UDITECH'
        self.admin_uditech.profile.save()

        RelatorioDiarioSine.objects.create(
            data=date.today(), usuario=self.superuser, atendimento_trabalhador=5,
        )

    def test_superuser_ve_card_sine(self):
        self.client.login(username='root_sine', password='x')
        response = self.client.get(reverse('controle_diario:admin_view'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Indicadores do SINE')
        self.assertIsNotNone(response.context['sine_relatorio'])

    def test_admin_cp_nao_ve_card_sine(self):
        self.client.login(username='admin_cp_sine', password='x')
        response = self.client.get(reverse('controle_diario:admin_view'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Indicadores do SINE')
        self.assertIsNone(response.context['sine_relatorio'])

    def test_admin_uditech_nao_ve_card_sine(self):
        self.client.login(username='admin_uditech_sine', password='x')
        response = self.client.get(reverse('controle_diario:admin_view'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Indicadores do SINE')
        self.assertIsNone(response.context['sine_relatorio'])
