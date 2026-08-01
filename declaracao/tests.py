from django.test import TestCase
from django.contrib.auth.models import User, Group
from django.urls import reverse

from escolas.models import Escola
from cursos.models import Curso, TipoCurso, Inscricao
from alunos.models import Aluno
from .models import Declaracao


class DeclaracaoCrossEscolaRegressionTest(TestCase):
    """
    Regressão do bug crítico de 2026-08-01: declaracao_sucesso_view e
    imprimir_declaracao_view filtravam só por 'sistema' (rede CP/UDITECH),
    não por profile.escola — um Coordenador de uma escola conseguia ver
    declarações emitidas para alunos de OUTRA escola da mesma rede.
    """

    def setUp(self):
        grupo_coordenador, _ = Group.objects.get_or_create(name='Coordenador')

        self.escola_a = Escola.objects.create(nome='Escola A', email='a@escola-a.com', tipo='CP')
        self.escola_b = Escola.objects.create(nome='Escola B', email='b@escola-b.com', tipo='CP')

        self.coord_a = User.objects.create_user(username='coord_a', password='password123')
        self.coord_a.groups.add(grupo_coordenador)
        self.coord_a.profile.escola = self.escola_a
        self.coord_a.profile.save()

        tipo_curso_b = TipoCurso.objects.create(escola=self.escola_b, nome='Curso Teste B')
        curso_b = Curso.objects.create(
            escola=self.escola_b, tipo_curso=tipo_curso_b, nome='Curso B',
            carga_horaria=10, data_inicio='2026-01-01', data_fim='2026-01-31',
            status='Em Andamento',
        )
        aluno_b = Aluno.objects.create(
            escola=self.escola_b, nome_completo='Aluno da Escola B',
            cpf='66666666666', data_nascimento='2000-01-01',
        )
        inscricao_b = Inscricao.objects.create(aluno=aluno_b, curso=curso_b, status='cursando')
        self.declaracao_b = Declaracao.objects.create(
            inscricao=inscricao_b, texto='texto de teste', status_aplicado='matriculado',
        )

    def test_coordenador_nao_ve_sucesso_de_declaracao_de_outra_escola(self):
        self.client.login(username='coord_a', password='password123')
        url = reverse('declaracao:declaracao_sucesso', args=[self.declaracao_b.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertNotEqual(response.url, url)

    def test_coordenador_nao_imprime_declaracao_de_outra_escola(self):
        self.client.login(username='coord_a', password='password123')
        url = reverse('declaracao:imprimir_declaracao', args=[self.declaracao_b.hash_validacao])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
