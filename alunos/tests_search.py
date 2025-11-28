from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from escolas.models import Escola
from .models import Aluno

class AlunoSearchTest(TestCase):
    def setUp(self):
        # Create superuser
        self.superuser = User.objects.create_superuser(
            username='admin_search', 
            password='password123', 
            email='admin_search@example.com'
        )
        
        # Create School
        self.escola = Escola.objects.create(
            nome='Escola Teste Search', 
            email='escola_search@test.com'
        )

        # Create Students
        self.aluno1 = Aluno.objects.create(
            escola=self.escola,
            nome_completo='João da Silva',
            cpf='111.111.111-11',
            data_nascimento='2000-01-01',
            sexo='M',
            estado_civil='Solteiro',
            email_principal='joao@test.com',
            telefone_principal='1111-1111',
            endereco_rua='Rua A',
            endereco_numero='1',
            endereco_bairro='Bairro A',
            endereco_cidade='Cidade A',
            endereco_estado='SP',
            endereco_cep='11111-111'
        )
        
        self.aluno2 = Aluno.objects.create(
            escola=self.escola,
            nome_completo='Maria Oliveira',
            cpf='222.222.222-22',
            data_nascimento='2001-01-01',
            sexo='F',
            estado_civil='Casado',
            email_principal='maria@test.com',
            telefone_principal='2222-2222',
            endereco_rua='Rua B',
            endereco_numero='2',
            endereco_bairro='Bairro B',
            endereco_cidade='Cidade B',
            endereco_estado='SP',
            endereco_cep='22222-222'
        )
        
        self.aluno3 = Aluno.objects.create(
            escola=self.escola,
            nome_completo='Carlos Silva',
            cpf='333.333.333-33',
            data_nascimento='2002-01-01',
            sexo='M',
            estado_civil='Solteiro',
            email_principal='carlos@test.com',
            telefone_principal='3333-3333',
            endereco_rua='Rua C',
            endereco_numero='3',
            endereco_bairro='Bairro C',
            endereco_cidade='Cidade C',
            endereco_estado='SP',
            endereco_cep='33333-333'
        )

        self.url = reverse('alunos:lista_alunos')

    def test_search_by_name(self):
        self.client.login(username='admin_search', password='password123')
        response = self.client.get(self.url, {'search': 'Silva'})
        self.assertEqual(response.status_code, 200)
        
        alunos = response.context['alunos']
        self.assertIn(self.aluno1, alunos)
        self.assertIn(self.aluno3, alunos)
        self.assertNotIn(self.aluno2, alunos)

    def test_search_by_cpf(self):
        self.client.login(username='admin_search', password='password123')
        response = self.client.get(self.url, {'search': '222'})
        self.assertEqual(response.status_code, 200)
        
        alunos = response.context['alunos']
        self.assertIn(self.aluno2, alunos)
        self.assertNotIn(self.aluno1, alunos)
        self.assertNotIn(self.aluno3, alunos)

    def test_search_no_results(self):
        self.client.login(username='admin_search', password='password123')
        response = self.client.get(self.url, {'search': 'XyzBlaBla'})
        self.assertEqual(response.status_code, 200)
        
        alunos = response.context['alunos']
        self.assertEqual(len(alunos), 0)

    def test_search_preserves_parameter_in_pagination(self):
        self.client.login(username='admin_search', password='password123')
        # We need enough students to trigger pagination (paginate_by=20)
        # Create 18 more "Silva"s to have 20 Silvas total (aluno1, aluno3 + 18)
        for i in range(18):
            Aluno.objects.create(
                escola=self.escola,
                nome_completo=f'Silva Clone {i}',
                cpf=f'000.000.000-{i:02d}',
                data_nascimento='2000-01-01',
                sexo='M',
                estado_civil='Solteiro',
                email_principal=f'clone{i}@test.com',
                telefone_principal='0000-0000',
                endereco_rua='Rua X',
                endereco_numero='0',
                endereco_bairro='Bairro X',
                endereco_cidade='Cidade X',
                endereco_estado='SP',
                endereco_cep='00000-000'
            )
        
        # Now we have 20 Silvas. The view is paginated by 20.
        # If we add one more, we have 21, so 2 pages.
        Aluno.objects.create(
            escola=self.escola,
            nome_completo='Extra Silva',
            cpf='999.999.999-99',
            data_nascimento='2000-01-01',
            sexo='M',
            estado_civil='Solteiro',
            email_principal='extra@test.com',
            telefone_principal='0000-0000',
            endereco_rua='Rua X',
            endereco_numero='0',
            endereco_bairro='Bairro X',
            endereco_cidade='Cidade X',
            endereco_estado='SP',
            endereco_cep='00000-000'
        )

        response = self.client.get(self.url, {'search': 'Silva'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_paginated'])
        
        # Check if the pagination link contains the search parameter
        content = response.content.decode('utf-8')
        self.assertIn('search=Silva', content)
