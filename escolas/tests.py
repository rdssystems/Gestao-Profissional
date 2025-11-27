from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Escola

class EscolaListViewTest(TestCase):
    def setUp(self):
        # Criar um superusuário
        self.superuser = User.objects.create_superuser(
            username='admin', 
            password='password123', 
            email='admin@example.com'
        )

        # Criar um usuário coordenador
        self.coordenador_user = User.objects.create_user(
            username='coordenador', 
            password='password123', 
            email='coordenador@escola1.com'
        )

        # Criar duas escolas
        self.escola1 = Escola.objects.create(
            nome='Escola Teste 1', 
            email='coordenador@escola1.com', 
            coordenador_user=self.coordenador_user
        )
        self.escola2 = Escola.objects.create(
            nome='Escola Teste 2', 
            email='outro@escola2.com'
        )

        self.url = reverse('escolas:lista_escolas')

    def test_unauthenticated_user_is_redirected(self):
        """Verifica se um usuário não autenticado é redirecionado para a página de login."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, f"{reverse('login')}?next={self.url}")

    def test_superuser_can_see_all_escolas(self):
        """Verifica se o superusuário consegue ver todas as escolas."""
        self.client.login(username='admin', password='password123')
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.escola1.nome)
        self.assertContains(response, self.escola2.nome)
        self.assertIn(self.escola1, response.context['escolas'])
        self.assertIn(self.escola2, response.context['escolas'])

    def test_coordinator_sees_only_their_escola(self):
        """Verifica se um coordenador vê apenas a sua própria escola."""
        self.client.login(username='coordenador', password='password123')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.escola1.nome)
        self.assertNotContains(response, self.escola2.nome)
        self.assertIn(self.escola1, response.context['escolas'])
        self.assertNotIn(self.escola2, response.context['escolas'])


class EscolaCrudViewTest(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser('admin_crud', email='admin_crud@test.com', password='password123')
        self.regular_user = User.objects.create_user('user_crud', password='password123')
        self.escola = Escola.objects.create(nome='Escola CRUD', email='crud@test.com')

        self.create_url = reverse('escolas:criar_escola')
        self.update_url = reverse('escolas:editar_escola', kwargs={'pk': self.escola.pk})
        self.delete_url = reverse('escolas:excluir_escola', kwargs={'pk': self.escola.pk})

    def test_superuser_can_access_create_view(self):
        login_success = self.client.login(username='admin_crud', password='password123')
        self.assertTrue(login_success)
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 200)

    def test_regular_user_is_forbidden_from_create_view(self):
        self.client.login(username='user_crud', password='password123')
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 403)

    def test_superuser_can_create_escola(self):
        self.client.login(username='admin_crud', password='password123')
        form_data = {'nome': 'Nova Escola Via Teste', 'email': 'nova@teste.com', 'endereco': 'Rua Teste', 'telefone': '12345', 'coordenador': 'Teste'}
        response = self.client.post(self.create_url, data=form_data)
        self.assertEqual(response.status_code, 302) # Redireciona após sucesso
        self.assertTrue(Escola.objects.filter(nome='Nova Escola Via Teste').exists())

    def test_superuser_can_access_update_view(self):
        login_success = self.client.login(username='admin_crud', password='password123')
        self.assertTrue(login_success)
        response = self.client.get(self.update_url)
        self.assertEqual(response.status_code, 200)

    def test_regular_user_is_forbidden_from_update_view(self):
        self.client.login(username='user_crud', password='password123')
        response = self.client.get(self.update_url)
        self.assertEqual(response.status_code, 403)

    def test_superuser_can_access_delete_view(self):
        login_success = self.client.login(username='admin_crud', password='password123')
        self.assertTrue(login_success)
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 200)

    def test_regular_user_is_forbidden_from_delete_view(self):
        self.client.login(username='user_crud', password='password123')
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 403)

    def test_superuser_can_delete_escola(self):
        self.client.login(username='admin_crud', password='password123')
        response = self.client.post(self.delete_url)
        self.assertEqual(response.status_code, 302) # Redireciona após sucesso
        self.assertFalse(Escola.objects.filter(pk=self.escola.pk).exists())