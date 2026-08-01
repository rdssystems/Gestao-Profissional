from django.test import TestCase
from django.urls import reverse

from escolas.models import Escola
from alunos.models import Aluno


class PublicoCadastroCrossEscolaLeakRegressionTest(TestCase):
    """
    Regressão do bug crítico de 2026-08-01: quando o CPF não existia na
    escola atual, PublicoCadastroView.get caía num fallback que buscava em
    QUALQUER escola do sistema (Aluno.objects.filter(cpf=cpf_limpo).first(),
    sem filtro de escola) e devolvia o cadastro completo (nome, endereço,
    renda, dados de saúde) de um aluno de outra escola/rede para o
    visitante anônimo que só digitou aquele CPF — vazamento de PII sem
    nenhuma autenticação.
    """

    def setUp(self):
        self.escola_uditech = Escola.objects.create(
            nome='Uditech Teste', email='uditech@example.com', tipo='UDITECH',
        )
        self.escola_outra_rede = Escola.objects.create(
            nome='CP Teste', email='cp@example.com', tipo='CP',
        )
        self.cpf_de_outra_escola = '44444444444'
        self.aluno_outra_escola = Aluno.objects.create(
            escola=self.escola_outra_rede,
            nome_completo='Fulano de Outra Rede',
            cpf=self.cpf_de_outra_escola,
            data_nascimento='2000-01-01',
            renda_individual=5000,
        )
        self.url = reverse('publico:cadastro', args=[self.escola_uditech.slug])

    def test_cpf_de_outra_escola_nao_vaza_dados_do_aluno(self):
        response = self.client.get(self.url, {'cpf': self.cpf_de_outra_escola})
        self.assertEqual(response.status_code, 200)
        # Nem o nome nem a flag de "já cadastrado"/"encontrado" devem
        # aparecer — para este slug, o CPF simplesmente não existe.
        self.assertNotContains(response, 'Fulano de Outra Rede')
        self.assertFalse(response.context['ja_cadastrado'])
        self.assertFalse(response.context['aluno_encontrado'])
        self.assertEqual(response.context['aluno_nome'], '')

    def test_cpf_da_propria_escola_ainda_funciona(self):
        aluno_local = Aluno.objects.create(
            escola=self.escola_uditech,
            nome_completo='Ciclana Local',
            cpf='55555555555',
            data_nascimento='2000-01-01',
        )
        response = self.client.get(self.url, {'cpf': '55555555555'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['ja_cadastrado'])
        self.assertEqual(response.context['aluno_nome'], 'Ciclana Local')

    def test_rate_limit_bloqueia_apos_muitas_consultas(self):
        for _ in range(30):
            self.client.get(self.url, {'cpf': self.cpf_de_outra_escola})
        response = self.client.get(self.url, {'cpf': self.cpf_de_outra_escola})
        self.assertTrue(response.context['erro_rate_limit'])
