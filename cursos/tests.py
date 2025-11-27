from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from escolas.models import Escola
from .models import Curso, TipoCurso

class CursoListViewTest(TestCase):
    def setUp(self):
        # Criar superusuário
        self.superuser = User.objects.create_superuser(
            username='admin_curso', 
            password='password123', 
            email='admin_curso@example.com'
        )

        # Criar escolas e usuários coordenadores
        self.coordenador1_user = User.objects.create_user(
            username='coord1', 
            password='password123', 
            email='coord1@escola1.com'
        )
        self.escola1 = Escola.objects.create(
            nome='Escola Teste Curso 1', 
            email='coord1@escola1.com', 
            coordenador_user=self.coordenador1_user
        )

        self.coordenador2_user = User.objects.create_user(
            username='coord2', 
            password='password123', 
            email='coord2@escola2.com'
        )
        self.escola2 = Escola.objects.create(
            nome='Escola Teste Curso 2', 
            email='coord2@escola2.com', 
            coordenador_user=self.coordenador2_user
        )

        # Criar tipos de curso para cada escola
        self.tipo_info_escola1 = TipoCurso.objects.create(escola=self.escola1, nome='Informática')
        self.tipo_prog_escola1 = TipoCurso.objects.create(escola=self.escola1, nome='Programação')
        self.tipo_art_escola2 = TipoCurso.objects.create(escola=self.escola2, nome='Artes')

        # Criar cursos para cada escola
        self.curso1_escola1 = Curso.objects.create(
            escola=self.escola1, 
            tipo_curso=self.tipo_info_escola1,
            nome='Curso 1 Escola 1', 
            carga_horaria=10, 
            data_inicio='2023-01-01', 
            data_fim='2023-01-31', 
            status='Aberta'
        )
        self.curso2_escola1 = Curso.objects.create(
            escola=self.escola1, 
            tipo_curso=self.tipo_prog_escola1,
            nome='Curso 2 Escola 1', 
            carga_horaria=20, 
            data_inicio='2023-02-01', 
            data_fim='2023-02-28', 
            status='Em Andamento'
        )
        self.curso1_escola2 = Curso.objects.create(
            escola=self.escola2, 
            tipo_curso=self.tipo_art_escola2,
            nome='Curso 1 Escola 2', 
            carga_horaria=15, 
            data_inicio='2023-03-01', 
            data_fim='2023-03-31', 
            status='Concluído'
        )

        self.list_url = reverse('cursos:lista_cursos')

    def test_unauthenticated_user_is_redirected(self):
        """Verifica se um usuário não autenticado é redirecionado para a página de login."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, f"{reverse('login')}?next={self.list_url}")

    def test_superuser_can_see_all_cursos(self):
        """Verifica se o superusuário consegue ver todos os cursos."""
        self.client.login(username='admin_curso', password='password123')
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.curso1_escola1.nome)
        self.assertContains(response, self.curso2_escola1.nome)
        self.assertContains(response, self.curso1_escola2.nome)
        self.assertContains(response, self.tipo_info_escola1.nome) # Verifica exibição do tipo de curso
        self.assertIn(self.curso1_escola1, response.context['cursos'])
        self.assertIn(self.curso2_escola1, response.context['cursos'])
        self.assertIn(self.curso1_escola2, response.context['cursos'])

    def test_coordinator_sees_only_their_cursos(self):
        """Verifica se um coordenador vê apenas os cursos da sua própria escola."""
        self.client.login(username='coord1', password='password123')
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.curso1_escola1.nome)
        self.assertContains(response, self.curso2_escola1.nome)
        self.assertContains(response, self.tipo_info_escola1.nome) # Verifica exibição do tipo de curso
        self.assertNotContains(response, self.curso1_escola2.nome)
        self.assertIn(self.curso1_escola1, response.context['cursos'])
        self.assertIn(self.curso2_escola1, response.context['cursos'])
        self.assertNotIn(self.curso1_escola2, response.context['cursos'])

    def test_coordinator_cannot_see_other_schools_curso_detail(self):
        """Verifica se um coordenador não consegue ver o detalhe de um curso de outra escola."""
        self.client.login(username='coord1', password='password123')
        detail_url_other_school = reverse('cursos:detalhe_curso', kwargs={'pk': self.curso1_escola2.pk})
        response = self.client.get(detail_url_other_school)
        self.assertEqual(response.status_code, 404) # Deve retornar 404 Not Found

class CursoCrudViewTest(TestCase):
    def setUp(self):
        # Criar superusuário
        self.superuser = User.objects.create_superuser(
            username='admin_crud_curso', 
            password='password123', 
            email='admin_crud_curso@example.com'
        )

        # Criar escolas e usuários coordenadores
        self.coordenador1_user = User.objects.create_user(
            username='coord_crud1', 
            password='password123', 
            email='coord_crud1@escola1.com'
        )
        self.escola1 = Escola.objects.create(
            nome='Escola CRUD Curso 1', 
            email='coord_crud1@escola1.com', 
            coordenador_user=self.coordenador1_user
        )

        self.coordenador2_user = User.objects.create_user(
            username='coord_crud2', 
            password='password123', 
            email='coord_crud2@escola2.com'
        )
        self.escola2 = Escola.objects.create(
            nome='Escola CRUD Curso 2', 
            email='coord_crud2@escola2.com', 
            coordenador_user=self.coordenador2_user
        )

        # Criar tipos de curso para cada escola
        self.tipo_info_escola1 = TipoCurso.objects.create(escola=self.escola1, nome='Informática CRUD')
        self.tipo_prog_escola1 = TipoCurso.objects.create(escola=self.escola1, nome='Programação CRUD')
        self.tipo_art_escola2 = TipoCurso.objects.create(escola=self.escola2, nome='Artes CRUD')

        # Criar um curso para a escola 1
        self.curso_escola1 = Curso.objects.create(
            escola=self.escola1, 
            tipo_curso=self.tipo_info_escola1,
            nome='Curso CRUD Escola 1', 
            carga_horaria=10, 
            data_inicio='2023-01-01', 
            data_fim='2023-01-31', 
            status='Aberta'
        )
        # Criar um curso para a escola 2
        self.curso_escola2 = Curso.objects.create(
            escola=self.escola2, 
            tipo_curso=self.tipo_art_escola2,
            nome='Curso CRUD Escola 2', 
            carga_horaria=20, 
            data_inicio='2023-02-01', 
            data_fim='2023-02-28', 
            status='Em Andamento'
        )

        self.create_url = reverse('cursos:criar_curso')
        self.update_url_escola1 = reverse('cursos:editar_curso', kwargs={'pk': self.curso_escola1.pk})
        self.delete_url_escola1 = reverse('cursos:excluir_curso', kwargs={'pk': self.curso_escola1.pk})
        self.update_url_escola2 = reverse('cursos:editar_curso', kwargs={'pk': self.curso_escola2.pk})
        self.delete_url_escola2 = reverse('cursos:excluir_curso', kwargs={'pk': self.curso_escola2.pk})

    # --- Testes de Criação (CreateView) ---
    def test_superuser_can_access_create_view(self):
        self.client.login(username='admin_crud_curso', password='password123')
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 200)

    def test_coordinator_can_access_create_view(self):
        self.client.login(username='coord_crud1', password='password123')
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 200)

    def test_superuser_can_create_curso_for_any_escola(self):
        self.client.login(username='admin_crud_curso', password='password123')
        form_data = {
            'escola': self.escola2.pk, 
            'tipo_curso': self.tipo_art_escola2.pk, # Adicionado
            'nome': 'Novo Curso Admin', 
            'carga_horaria': 30, 
            'data_inicio': '2023-04-01', 
            'data_fim': '2023-04-30', 
            'status': 'Aberta'
        }
        response = self.client.post(self.create_url, data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Curso.objects.filter(nome='Novo Curso Admin', escola=self.escola2).exists())

    def test_coordinator_can_create_curso_for_their_escola(self):
        self.client.login(username='coord_crud1', password='password123')
        form_data = {
            'escola': self.escola1.pk, # Este campo será ignorado/preenchido pela view/form
            'tipo_curso': self.tipo_info_escola1.pk, # Adicionado
            'nome': 'Novo Curso Coord1', 
            'carga_horaria': 25, 
            'data_inicio': '2023-05-01', 
            'data_fim': '2023-05-31', 
            'status': 'Em Andamento'
        }
        response = self.client.post(self.create_url, data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Curso.objects.filter(nome='Novo Curso Coord1', escola=self.escola1).exists())
        self.assertEqual(Curso.objects.get(nome='Novo Curso Coord1').escola, self.escola1)

    # --- Testes de Atualização (UpdateView) ---
    def test_superuser_can_access_update_view_any_curso(self):
        self.client.login(username='admin_crud_curso', password='password123')
        response = self.client.get(self.update_url_escola2)
        self.assertEqual(response.status_code, 200)

    def test_coordinator_can_access_update_view_their_curso(self):
        self.client.login(username='coord_crud1', password='password123')
        response = self.client.get(self.update_url_escola1)
        self.assertEqual(response.status_code, 200)

    def test_coordinator_is_forbidden_from_update_view_other_curso(self):
        self.client.login(username='coord_crud1', password='password123')
        response = self.client.get(self.update_url_escola2) # Tenta acessar curso da escola 2
        self.assertEqual(response.status_code, 403)

    def test_superuser_can_update_any_curso(self):
        self.client.login(username='admin_crud_curso', password='password123')
        form_data = {
            'escola': self.escola1.pk, 
            'tipo_curso': self.tipo_prog_escola1.pk, # Adicionado
            'nome': 'Curso Admin Atualizado', 
            'carga_horaria': 12, 
            'data_inicio': '2023-01-01', 
            'data_fim': '2023-01-31', 
            'status': 'Concluído'
        }
        response = self.client.post(self.update_url_escola1, data=form_data)
        self.assertEqual(response.status_code, 302)
        self.curso_escola1.refresh_from_db()
        self.assertEqual(self.curso_escola1.nome, 'Curso Admin Atualizado')

    def test_coordinator_can_update_their_curso(self):
        self.client.login(username='coord_crud1', password='password123')
        form_data = {
            'escola': self.escola1.pk, 
            'tipo_curso': self.tipo_info_escola1.pk, # Adicionado
            'nome': 'Curso Coord1 Atualizado', 
            'carga_horaria': 15, 
            'data_inicio': '2023-01-01', 
            'data_fim': '2023-01-31', 
            'status': 'Aberta'
        }
        response = self.client.post(self.update_url_escola1, data=form_data)
        self.assertEqual(response.status_code, 302)
        self.curso_escola1.refresh_from_db()
        self.assertEqual(self.curso_escola1.nome, 'Curso Coord1 Atualizado')

    def test_coordinator_cannot_update_other_schools_curso(self):
        self.client.login(username='coord_crud1', password='password123')
        form_data = {
            'escola': self.escola2.pk, 
            'tipo_curso': self.tipo_art_escola2.pk, # Adicionado
            'nome': 'Curso Invasor', 
            'carga_horaria': 99, 
            'data_inicio': '2023-01-01', 
            'data_fim': '2023-01-31', 
            'status': 'Aberta'
        }
        response = self.client.post(self.update_url_escola2, data=form_data)
        self.assertEqual(response.status_code, 403) # Deve ser proibido

    # --- Testes de Exclusão (DeleteView) ---
    def test_superuser_can_access_delete_view_any_curso(self):
        self.client.login(username='admin_crud_curso', password='password123')
        response = self.client.get(self.delete_url_escola2)
        self.assertEqual(response.status_code, 200)

    def test_coordinator_can_access_delete_view_their_curso(self):
        self.client.login(username='coord_crud1', password='password123')
        response = self.client.get(self.delete_url_escola1)
        self.assertEqual(response.status_code, 200)

    def test_coordinator_is_forbidden_from_delete_view_other_curso(self):
        self.client.login(username='coord_crud1', password='password123')
        response = self.client.get(self.delete_url_escola2)
        self.assertEqual(response.status_code, 403)

    def test_superuser_can_delete_any_curso(self):
        self.client.login(username='admin_crud_curso', password='password123')
        response = self.client.post(self.delete_url_escola1)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Curso.objects.filter(pk=self.curso_escola1.pk).exists())

    def test_coordinator_can_delete_their_curso(self):
        self.client.login(username='coord_crud1', password='password123')
        response = self.client.post(self.delete_url_escola1)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Curso.objects.filter(pk=self.curso_escola1.pk).exists())

    def test_coordinator_cannot_delete_other_schools_curso(self):
        self.client.login(username='coord_crud1', password='password123')
        response = self.client.post(self.delete_url_escola2)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Curso.objects.filter(pk=self.curso_escola2.pk).exists()) # Garante que não foi excluído

    # --- Testes de Alteração de Status (CursoStatusUpdateView) ---
    def test_superuser_can_change_curso_status(self):
        self.client.login(username='admin_crud_curso', password='password123')
        response = self.client.post(reverse('cursos:alterar_status_curso', kwargs={'pk': self.curso_escola1.pk}), {'status': 'Concluído'})
        self.assertEqual(response.status_code, 302)
        self.curso_escola1.refresh_from_db()
        self.assertEqual(self.curso_escola1.status, 'Concluído')

    def test_coordinator_can_change_their_curso_status(self):
        self.client.login(username='coord_crud1', password='password123')
        response = self.client.post(reverse('cursos:alterar_status_curso', kwargs={'pk': self.curso_escola1.pk}), {'status': 'Concluído'})
        self.assertEqual(response.status_code, 302)
        self.curso_escola1.refresh_from_db()
        self.assertEqual(self.curso_escola1.status, 'Concluído')

        self.assertTrue(Curso.objects.filter(pk=self.curso_escola2.pk).exists()) # Garante que não foi excluído

    # --- Testes de Alteração de Status (CursoStatusUpdateView) ---
    def test_superuser_can_change_curso_status(self):
        self.client.login(username='admin_crud_curso', password='password123')
        response = self.client.post(reverse('cursos:alterar_status_curso', kwargs={'pk': self.curso_escola1.pk}), {'status': 'Concluído'})
        self.assertEqual(response.status_code, 302)
        self.curso_escola1.refresh_from_db()
        self.assertEqual(self.curso_escola1.status, 'Concluído')

    def test_coordinator_can_change_their_curso_status(self):
        self.client.login(username='coord_crud1', password='password123')
        response = self.client.post(reverse('cursos:alterar_status_curso', kwargs={'pk': self.curso_escola1.pk}), {'status': 'Concluído'})
        self.assertEqual(response.status_code, 302)
        self.curso_escola1.refresh_from_db()
        self.assertEqual(self.curso_escola1.status, 'Concluído')

    def test_coordinator_cannot_change_other_schools_curso_status(self):
        self.client.login(username='coord_crud1', password='password123')
        response = self.client.post(reverse('cursos:alterar_status_curso', kwargs={'pk': self.curso_escola2.pk}), {'status': 'Concluído'})
        self.assertEqual(response.status_code, 403)
        self.curso_escola2.refresh_from_db()
        self.assertNotEqual(self.curso_escola2.status, 'Concluído') # Garante que o status não foi alterado

class TipoCursoCrudViewTest(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='admin_tipocurso', 
            password='password123', 
            email='admin_tipocurso@example.com'
        )
        self.coordenador1_user = User.objects.create_user(
            username='coord_tipocurso1', 
            password='password123', 
            email='coord_tipocurso1@escola1.com'
        )
        self.escola1 = Escola.objects.create(
            nome='Escola TipoCurso 1', 
            email='coord_tipocurso1@escola1.com', 
            coordenador_user=self.coordenador1_user
        )
        self.coordenador2_user = User.objects.create_user(
            username='coord_tipocurso2', 
            password='password123', 
            email='coord_tipocurso2@escola2.com'
        )
        self.escola2 = Escola.objects.create(
            nome='Escola TipoCurso 2', 
            email='coord_tipocurso2@escola2.com', 
            coordenador_user=self.coordenador2_user
        )

        self.tipo_curso_escola1 = TipoCurso.objects.create(escola=self.escola1, nome='Matemática')
        self.tipo_curso_escola2 = TipoCurso.objects.create(escola=self.escola2, nome='Física')

        self.list_url = reverse('cursos:lista_tipos_curso')
        self.create_url = reverse('cursos:criar_tipo_curso')
        self.update_url_escola1 = reverse('cursos:editar_tipo_curso', kwargs={'pk': self.tipo_curso_escola1.pk})
        self.delete_url_escola1 = reverse('cursos:excluir_tipo_curso', kwargs={'pk': self.tipo_curso_escola1.pk})
        self.update_url_escola2 = reverse('cursos:editar_tipo_curso', kwargs={'pk': self.tipo_curso_escola2.pk})
        self.delete_url_escola2 = reverse('cursos:excluir_tipo_curso', kwargs={'pk': self.tipo_curso_escola2.pk})

    # --- Testes de Listagem (TipoCursoListView) ---
    def test_superuser_can_see_all_tipos_curso(self):
        self.client.login(username='admin_tipocurso', password='password123')
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.tipo_curso_escola1.nome)
        self.assertContains(response, self.tipo_curso_escola2.nome)
        self.assertIn(self.tipo_curso_escola1, response.context['tipos_curso'])
        self.assertIn(self.tipo_curso_escola2, response.context['tipos_curso'])

    def test_coordinator_sees_only_their_tipos_curso(self):
        self.client.login(username='coord_tipocurso1', password='password123')
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.tipo_curso_escola1.nome)
        self.assertNotContains(response, self.tipo_curso_escola2.nome)
        self.assertIn(self.tipo_curso_escola1, response.context['tipos_curso'])
        self.assertNotIn(self.tipo_curso_escola2, response.context['tipos_curso'])

    # --- Testes de Criação (TipoCursoCreateView) ---
    def test_superuser_can_create_tipocurso_for_any_escola(self):
        self.client.login(username='admin_tipocurso', password='password123')
        form_data = {
            'escola': self.escola2.pk,
            'nome': 'Química'
        }
        response = self.client.post(self.create_url, data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(TipoCurso.objects.filter(nome='Química', escola=self.escola2).exists())

    def test_coordinator_can_create_tipocurso_for_their_escola(self):
        self.client.login(username='coord_tipocurso1', password='password123')
        form_data = {
            'escola': self.escola1.pk,
            'nome': 'Biologia'
        }
        response = self.client.post(self.create_url, data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(TipoCurso.objects.filter(nome='Biologia', escola=self.escola1).exists())
        self.assertEqual(TipoCurso.objects.get(nome='Biologia').escola, self.escola1)

    # --- Testes de Atualização (TipoCursoUpdateView) ---
    def test_superuser_can_update_any_tipocurso(self):
        self.client.login(username='admin_tipocurso', password='password123')
        form_data = {
            'escola': self.escola1.pk,
            'nome': 'Matemática Avançada'
        }
        response = self.client.post(self.update_url_escola1, data=form_data)
        self.assertEqual(response.status_code, 302)
        self.tipo_curso_escola1.refresh_from_db()
        self.assertEqual(self.tipo_curso_escola1.nome, 'Matemática Avançada')

    def test_coordinator_can_update_their_tipocurso(self):
        self.client.login(username='coord_tipocurso1', password='password123')
        form_data = {
            'escola': self.escola1.pk,
            'nome': 'Matemática Básica'
        }
        response = self.client.post(self.update_url_escola1, data=form_data)
        self.assertEqual(response.status_code, 302)
        self.tipo_curso_escola1.refresh_from_db()
        self.assertEqual(self.tipo_curso_escola1.nome, 'Matemática Básica')

    def test_coordinator_cannot_update_other_schools_tipocurso(self):
        self.client.login(username='coord_tipocurso1', password='password123')
        form_data = {
            'escola': self.escola2.pk,
            'nome': 'Física Quântica'
        }
        response = self.client.post(self.update_url_escola2, data=form_data)
        self.assertEqual(response.status_code, 403) # Deve ser proibido

    # --- Testes de Exclusão (TipoCursoDeleteView) ---
    def test_superuser_can_delete_any_tipocurso(self):
        self.client.login(username='admin_tipocurso', password='password123')
        response = self.client.post(self.delete_url_escola1)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(TipoCurso.objects.filter(pk=self.tipo_curso_escola1.pk).exists())

    def test_coordinator_can_delete_their_tipocurso(self):
        self.client.login(username='coord_tipocurso1', password='password123')
        response = self.client.post(self.delete_url_escola1)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(TipoCurso.objects.filter(pk=self.tipo_curso_escola1.pk).exists())

    def test_coordinator_cannot_delete_other_schools_tipocurso(self):
        self.client.login(username='coord_tipocurso1', password='password123')
        response = self.client.post(self.delete_url_escola2)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(TipoCurso.objects.filter(pk=self.tipo_curso_escola2.pk).exists()) # Garante que não foi excluído