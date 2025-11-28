from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from escolas.models import Escola
from .models import Aluno

class AlunoFilterTest(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='admin_filter', 
            password='password123', 
            email='admin_filter@example.com'
        )
        
        self.escola_a = Escola.objects.create(nome='Escola A', email='a@test.com')
        self.escola_b = Escola.objects.create(nome='Escola B', email='b@test.com')
        
        self.aluno_a = Aluno.objects.create(
            escola=self.escola_a,
            nome_completo='Aluno A',
            cpf='111.111.111-11',
            data_nascimento='2000-01-01',
            sexo='M',
            estado_civil='Solteiro',
            email_principal='a@test.com',
            telefone_principal='1111-1111',
            endereco_rua='Rua A',
            endereco_numero='1',
            endereco_bairro='Bairro A',
            endereco_cidade='Cidade A',
            endereco_estado='SP',
            endereco_cep='11111-111'
        )
        
        self.aluno_b = Aluno.objects.create(
            escola=self.escola_b,
            nome_completo='Aluno B',
            cpf='222.222.222-22',
            data_nascimento='2000-01-01',
            sexo='M',
            estado_civil='Solteiro',
            email_principal='b@test.com',
            telefone_principal='2222-2222',
            endereco_rua='Rua B',
            endereco_numero='2',
            endereco_bairro='Bairro B',
            endereco_cidade='Cidade B',
            endereco_estado='SP',
            endereco_cep='22222-222'
        )
        
        self.url = reverse('alunos:lista_alunos')

    def test_superuser_can_filter_by_school(self):
        self.client.login(username='admin_filter', password='password123')
        response = self.client.get(self.url, {'escola': self.escola_a.pk})
        
        self.assertEqual(response.status_code, 200)
        alunos = response.context['alunos']
        self.assertIn(self.aluno_a, alunos)
        self.assertNotIn(self.aluno_b, alunos)

    def test_superuser_sees_all_schools_option(self):
        self.client.login(username='admin_filter', password='password123')
        response = self.client.get(self.url)
        self.assertContains(response, '<select name="escola"')
        self.assertContains(response, 'Todas as Escolas')
        self.assertContains(response, self.escola_a.nome)
        self.assertContains(response, self.escola_b.nome)

    def test_coordinator_cannot_see_filter(self):
        coord_user = User.objects.create_user(username='coord_user', password='password123')
        # Bind to school A
        coord_user.profile.escola = self.escola_a
        coord_user.profile.save()
        
        self.client.login(username='coord_user', password='password123')
        response = self.client.get(self.url)
        self.assertNotContains(response, '<select name="escola"')
