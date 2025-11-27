from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from escolas.models import Escola
from .models import Aluno

class AlunoListViewTest(TestCase):
    def setUp(self):
        # Criar superusuário
        self.superuser = User.objects.create_superuser(
            username='admin_aluno', 
            password='password123', 
            email='admin_aluno@example.com'
        )

        # Criar escolas e usuários coordenadores
        self.coordenador1_user = User.objects.create_user(
            username='coord_aluno1', 
            password='password123', 
            email='coord_aluno1@escola1.com'
        )
        self.escola1 = Escola.objects.create(
            nome='Escola Teste Aluno 1', 
            email='coord_aluno1@escola1.com', 
            coordenador_user=self.coordenador1_user
        )

        self.coordenador2_user = User.objects.create_user(
            username='coord_aluno2', 
            password='password123', 
            email='coord_aluno2@escola2.com'
        )
        self.escola2 = Escola.objects.create(
            nome='Escola Teste Aluno 2', 
            email='coord_aluno2@escola2.com', 
            coordenador_user=self.coordenador2_user
        )

        # Criar alunos para cada escola
        self.aluno1_escola1 = Aluno.objects.create(
            escola=self.escola1, 
            nome_completo='Aluno 1 Escola 1', 
            cpf='111.111.111-11', 
            data_nascimento='2000-01-01', 
            sexo='M', 
            estado_civil='Solteiro', 
            email_principal='aluno1@escola1.com', 
            telefone_principal='1111-1111', 
            endereco_rua='Rua A', 
            endereco_numero='1', 
            endereco_bairro='Bairro A', 
            endereco_cidade='Cidade A', 
            endereco_estado='SP', 
            endereco_cep='11111-111'
        )
        self.aluno2_escola1 = Aluno.objects.create(
            escola=self.escola1, 
            nome_completo='Aluno 2 Escola 1', 
            cpf='222.222.222-22', 
            data_nascimento='2001-02-02', 
            sexo='F', 
            estado_civil='Casado', 
            email_principal='aluno2@escola1.com', 
            telefone_principal='2222-2222', 
            endereco_rua='Rua B', 
            endereco_numero='2', 
            endereco_bairro='Bairro B', 
            endereco_cidade='Cidade B', 
            endereco_estado='RJ', 
            endereco_cep='22222-222'
        )
        self.aluno1_escola2 = Aluno.objects.create(
            escola=self.escola2, 
            nome_completo='Aluno 1 Escola 2', 
            cpf='333.333.333-33', 
            data_nascimento='2002-03-03', 
            sexo='M', 
            estado_civil='Solteiro', 
            email_principal='aluno1@escola2.com', 
            telefone_principal='3333-3333', 
            endereco_rua='Rua C', 
            endereco_numero='3', 
            endereco_bairro='Bairro C', 
            endereco_cidade='Cidade C', 
            endereco_estado='MG', 
            endereco_cep='33333-333'
        )

        self.list_url = reverse('alunos:lista_alunos')

    def test_unauthenticated_user_is_redirected(self):
        """Verifica se um usuário não autenticado é redirecionado para a página de login."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, f"{reverse('login')}?next={self.list_url}")

    def test_superuser_can_see_all_alunos(self):
        """Verifica se o superusuário consegue ver todos os alunos."""
        self.client.login(username='admin_aluno', password='password123')
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.aluno1_escola1.nome_completo)
        self.assertContains(response, self.aluno2_escola1.nome_completo)
        self.assertContains(response, self.aluno1_escola2.nome_completo)
        self.assertIn(self.aluno1_escola1, response.context['alunos'])
        self.assertIn(self.aluno2_escola1, response.context['alunos'])
        self.assertIn(self.aluno1_escola2, response.context['alunos'])

    def test_coordinator_sees_only_their_alunos(self):
        """Verifica se um coordenador vê apenas os alunos da sua própria escola."""
        self.client.login(username='coord_aluno1', password='password123')
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.aluno1_escola1.nome_completo)
        self.assertContains(response, self.aluno2_escola1.nome_completo)
        self.assertNotContains(response, self.aluno1_escola2.nome_completo)
        self.assertIn(self.aluno1_escola1, response.context['alunos'])
        self.assertIn(self.aluno2_escola1, response.context['alunos'])
        self.assertNotIn(self.aluno1_escola2, response.context['alunos'])

    def test_coordinator_cannot_see_other_schools_aluno_detail(self):
        """Verifica se um coordenador não consegue ver o detalhe de um aluno de outra escola."""
        self.client.login(username='coord_aluno1', password='password123')
        detail_url_other_school = reverse('alunos:detalhe_aluno', kwargs={'pk': self.aluno1_escola2.pk})
        response = self.client.get(detail_url_other_school)
        self.assertEqual(response.status_code, 404) # Deve retornar 404 Not Found

class AlunoCrudViewTest(TestCase):
    def setUp(self):
        # Criar superusuário
        self.superuser = User.objects.create_superuser(
            username='admin_crud_aluno', 
            password='password123', 
            email='admin_crud_aluno@example.com'
        )

        # Criar escolas e usuários coordenadores
        self.coordenador1_user = User.objects.create_user(
            username='coord_crud_aluno1', 
            password='password123', 
            email='coord_crud_aluno1@escola1.com'
        )
        self.escola1 = Escola.objects.create(
            nome='Escola CRUD Aluno 1', 
            email='coord_crud_aluno1@escola1.com', 
            coordenador_user=self.coordenador1_user
        )

        self.coordenador2_user = User.objects.create_user(
            username='coord_crud_aluno2', 
            password='password123', 
            email='coord_crud_aluno2@escola2.com'
        )
        self.escola2 = Escola.objects.create(
            nome='Escola CRUD Aluno 2', 
            email='coord_crud_aluno2@escola2.com', 
            coordenador_user=self.coordenador2_user
        )

        # Criar um aluno para a escola 1
        self.aluno_escola1 = Aluno.objects.create(
            escola=self.escola1, 
            nome_completo='Aluno CRUD Escola 1', 
            cpf='444.444.444-44', 
            data_nascimento='2003-04-04', 
            sexo='M', 
            estado_civil='Solteiro', 
            email_principal='crud_aluno1@escola1.com', 
            telefone_principal='4444-4444', 
            endereco_rua='Rua D', 
            endereco_numero='4', 
            endereco_bairro='Bairro D', 
            endereco_cidade='Cidade D', 
            endereco_estado='SC', 
            endereco_cep='44444-444'
        )
        # Criar um aluno para a escola 2
        self.aluno_escola2 = Aluno.objects.create(
            escola=self.escola2, 
            nome_completo='Aluno CRUD Escola 2', 
            cpf='555.555.555-55', 
            data_nascimento='2004-05-05', 
            sexo='F', 
            estado_civil='Casado', 
            email_principal='crud_aluno2@escola2.com', 
            telefone_principal='5555-5555', 
            endereco_rua='Rua E', 
            endereco_numero='5', 
            endereco_bairro='Bairro E', 
            endereco_cidade='Cidade E', 
            endereco_estado='PR', 
            endereco_cep='55555-555'
        )

        self.create_url = reverse('alunos:criar_aluno')
        self.update_url_escola1 = reverse('alunos:editar_aluno', kwargs={'pk': self.aluno_escola1.pk})
        self.delete_url_escola1 = reverse('alunos:excluir_aluno', kwargs={'pk': self.aluno_escola1.pk})
        self.update_url_escola2 = reverse('alunos:editar_aluno', kwargs={'pk': self.aluno_escola2.pk})
        self.delete_url_escola2 = reverse('alunos:excluir_aluno', kwargs={'pk': self.aluno_escola2.pk})

    # --- Testes de Criação (CreateView) ---
    def test_superuser_can_access_create_view(self):
        self.client.login(username='admin_crud_aluno', password='password123')
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 200)

    def test_coordinator_can_access_create_view(self):
        self.client.login(username='coord_crud_aluno1', password='password123')
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 200)

    def test_superuser_can_create_aluno_for_any_escola(self):
        self.client.login(username='admin_crud_aluno', password='password123')
        form_data = {
            'escola': self.escola2.pk, 
            'nome_completo': 'Novo Aluno Admin', 
            'cpf': '666.666.666-66', 
            'data_nascimento': '2005-06-06', 
            'sexo': 'M', 
            'estado_civil': 'Solteiro', 
            'email_principal': 'novo_admin@escola2.com', 
            'telefone_principal': '6666-6666', 
            'endereco_rua': 'Rua F', 
            'endereco_numero': '6', 
            'endereco_bairro': 'Bairro F', 
            'endereco_cidade': 'Cidade F', 
            'endereco_estado': 'RS', 
            'endereco_cep': '66666-666',
            'score_aluno': 0 # Adicionado
        }
        response = self.client.post(self.create_url, data=form_data)
        if response.status_code != 302:
            print(f"Form errors for superuser create: {response.context['form'].errors}")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Aluno.objects.filter(nome_completo='Novo Aluno Admin', escola=self.escola2).exists())

    def test_coordinator_can_create_aluno_for_their_escola(self):
        self.client.login(username='coord_crud_aluno1', password='password123')
        form_data = {
            'escola': self.escola1.pk, 
            'nome_completo': 'Novo Aluno Coord1', 
            'cpf': '777.777.777-77', 
            'data_nascimento': '2006-07-07', 
            'sexo': 'F', 
            'estado_civil': 'Casado', 
            'email_principal': 'novo_coord1@escola1.com', 
            'telefone_principal': '7777-7777', 
            'endereco_rua': 'Rua G', 
            'endereco_numero': '7', 
            'endereco_bairro': 'Bairro G', 
            'endereco_cidade': 'Cidade G', 
            'endereco_estado': 'SP', 
            'endereco_cep': '77777-777',
            'score_aluno': 0 # Adicionado
        }
        response = self.client.post(self.create_url, data=form_data)
        if response.status_code != 302:
            print(f"Form errors for coordinator create: {response.context['form'].errors}")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Aluno.objects.filter(nome_completo='Novo Aluno Coord1', escola=self.escola1).exists())
        self.assertEqual(Aluno.objects.get(nome_completo='Novo Aluno Coord1').escola, self.escola1)

    # --- Testes de Atualização (UpdateView) ---
    def test_superuser_can_access_update_view_any_aluno(self):
        self.client.login(username='admin_crud_aluno', password='password123')
        response = self.client.get(self.update_url_escola2)
        self.assertEqual(response.status_code, 200)

    def test_coordinator_can_access_update_view_their_aluno(self):
        self.client.login(username='coord_crud_aluno1', password='password123')
        response = self.client.get(self.update_url_escola1)
        self.assertEqual(response.status_code, 200)

    def test_coordinator_is_forbidden_from_update_view_other_aluno(self):
        self.client.login(username='coord_crud_aluno1', password='password123')
        response = self.client.get(self.update_url_escola2) 
        self.assertEqual(response.status_code, 403)

    def test_superuser_can_update_any_aluno(self):
        self.client.login(username='admin_crud_aluno', password='password123')
        form_data = {
            'escola': self.escola1.pk, 
            'nome_completo': 'Aluno Admin Atualizado', 
            'cpf': '444.444.444-44', 
            'data_nascimento': '2003-04-04', 
            'sexo': 'M', 
            'estado_civil': 'Solteiro', 
            'email_principal': 'crud_aluno1_updated@escola1.com', 
            'telefone_principal': '4444-4444', 
            'endereco_rua': 'Rua D', 
            'endereco_numero': '4', 
            'endereco_bairro': 'Bairro D', 
            'endereco_cidade': 'Cidade D', 
            'endereco_estado': 'SC', 
            'endereco_cep': '44444-444',
            'score_aluno': 0 # Adicionado
        }
        response = self.client.post(self.update_url_escola1, data=form_data)
        if response.status_code != 302:
            print(f"Form errors for superuser update: {response.context['form'].errors}")
        self.assertEqual(response.status_code, 302)
        self.aluno_escola1.refresh_from_db()
        self.assertEqual(self.aluno_escola1.nome_completo, 'Aluno Admin Atualizado')

    def test_coordinator_can_update_their_aluno(self):
        self.client.login(username='coord_crud_aluno1', password='password123')
        form_data = {
            'escola': self.escola1.pk, 
            'nome_completo': 'Aluno Coord1 Atualizado', 
            'cpf': '444.444.444-44', 
            'data_nascimento': '2003-04-04', 
            'sexo': 'M', 
            'estado_civil': 'Solteiro', 
            'email_principal': 'crud_aluno1_updated_coord@escola1.com', 
            'telefone_principal': '4444-4444', 
            'endereco_rua': 'Rua D', 
            'endereco_numero': '4', 
            'endereco_bairro': 'Bairro D', 
            'endereco_cidade': 'Cidade D', 
            'endereco_estado': 'SC', 
            'endereco_cep': '44444-444',
            'score_aluno': 0 # Adicionado
        }
        response = self.client.post(self.update_url_escola1, data=form_data)
        if response.status_code != 302:
            print(f"Form errors for coordinator update: {response.context['form'].errors}")
        self.assertEqual(response.status_code, 302)
        self.aluno_escola1.refresh_from_db()
        self.assertEqual(self.aluno_escola1.nome_completo, 'Aluno Coord1 Atualizado')

    def test_coordinator_cannot_update_other_schools_aluno(self):
        self.client.login(username='coord_crud_aluno1', password='password123')
        form_data = {
            'escola': self.escola2.pk, 
            'nome_completo': 'Aluno Invasor', 
            'cpf': '555.555.555-55', 
            'data_nascimento': '2004-05-05', 
            'sexo': 'F', 
            'estado_civil': 'Casado', 
            'email_principal': 'crud_aluno2_updated@escola2.com', 
            'telefone_principal': '5555-5555', 
            'endereco_rua': 'Rua E', 
            'endereco_numero': '5', 
            'endereco_bairro': 'Bairro E', 
            'endereco_cidade': 'Cidade E', 
            'endereco_estado': 'PR', 
            'endereco_cep': '55555-555',
            'score_aluno': 0 # Adicionado
        }
        response = self.client.post(self.update_url_escola2, data=form_data)
        self.assertEqual(response.status_code, 403) 

    # --- Testes de Exclusão (DeleteView) ---
    def test_superuser_can_access_delete_view_any_aluno(self):
        self.client.login(username='admin_crud_aluno', password='password123')
        response = self.client.get(self.delete_url_escola2)
        self.assertEqual(response.status_code, 200)

    def test_coordinator_can_access_delete_view_their_aluno(self):
        self.client.login(username='coord_crud_aluno1', password='password123')
        response = self.client.get(self.delete_url_escola1)
        self.assertEqual(response.status_code, 200)

    def test_coordinator_is_forbidden_from_delete_view_other_aluno(self):
        self.client.login(username='coord_crud_aluno1', password='password123')
        response = self.client.get(self.delete_url_escola2)
        self.assertEqual(response.status_code, 403)

    def test_superuser_can_delete_any_aluno(self):
        self.client.login(username='admin_crud_aluno', password='password123')
        response = self.client.post(self.delete_url_escola1)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Aluno.objects.filter(pk=self.aluno_escola1.pk).exists())

    def test_coordinator_can_delete_their_aluno(self):
        self.client.login(username='coord_crud_aluno1', password='password123')
        response = self.client.post(self.delete_url_escola1)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Aluno.objects.filter(pk=self.aluno_escola1.pk).exists())

    def test_coordinator_cannot_delete_other_schools_aluno(self):
        self.client.login(username='coord_crud_aluno1', password='password123')
        response = self.client.post(self.delete_url_escola2)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Aluno.objects.filter(pk=self.aluno_escola2.pk).exists())

    def test_coordinator_cannot_update_other_schools_aluno(self):
        self.client.login(username='coord_crud_aluno1', password='password123')
        form_data = {
            'escola': self.escola2.pk, 
            'nome_completo': 'Aluno Invasor', 
            'cpf': '555.555.555-55', 
            'data_nascimento': '2004-05-05', 
            'sexo': 'F', 
            'estado_civil': 'Casado', 
            'email_principal': 'crud_aluno2_updated@escola2.com', 
            'telefone_principal': '5555-5555', 
            'endereco_rua': 'Rua E', 
            'endereco_numero': '5', 
            'endereco_bairro': 'Bairro E', 
            'endereco_cidade': 'Cidade E', 
            'endereco_estado': 'PR', 
            'endereco_cep': '55555-555'
        }
        response = self.client.post(self.update_url_escola2, data=form_data)
        self.assertEqual(response.status_code, 403) 

    # --- Testes de Exclusão (DeleteView) ---
    def test_superuser_can_access_delete_view_any_aluno(self):
        self.client.login(username='admin_crud_aluno', password='password123')
        response = self.client.get(self.delete_url_escola2)
        self.assertEqual(response.status_code, 200)

    def test_coordinator_can_access_delete_view_their_aluno(self):
        self.client.login(username='coord_crud_aluno1', password='password123')
        response = self.client.get(self.delete_url_escola1)
        self.assertEqual(response.status_code, 200)

    def test_coordinator_is_forbidden_from_delete_view_other_aluno(self):
        self.client.login(username='coord_crud_aluno1', password='password123')
        response = self.client.get(self.delete_url_escola2)
        self.assertEqual(response.status_code, 403)

    def test_superuser_can_delete_any_aluno(self):
        self.client.login(username='admin_crud_aluno', password='password123')
        response = self.client.post(self.delete_url_escola1)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Aluno.objects.filter(pk=self.aluno_escola1.pk).exists())

    def test_coordinator_can_delete_their_aluno(self):
        self.client.login(username='coord_crud_aluno1', password='password123')
        response = self.client.post(self.delete_url_escola1)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Aluno.objects.filter(pk=self.aluno_escola1.pk).exists())

    def test_coordinator_cannot_delete_other_schools_aluno(self):
        self.client.login(username='coord_crud_aluno1', password='password123')
        response = self.client.post(self.delete_url_escola2)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Aluno.objects.filter(pk=self.aluno_escola2.pk).exists())