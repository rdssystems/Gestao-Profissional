from django.test import TestCase
from django.contrib.auth.models import User, Group
from django.urls import reverse

from escolas.models import Escola


class UsuariosPrivilegeEscalationRegressionTest(TestCase):
    """
    Regressão do bug crítico de 2026-08-01: o grupo 'Coordenador' tem as
    permissões globais do Django add_user/change_user/delete_user/view_user
    (core/migrations/0003_assign_permissions.py), e usuarios/views.py não
    fazia NENHUM escopo por escola/tenant — um Coordenador de qualquer
    escola conseguia listar todos os usuários do sistema, editar/trocar a
    senha de QUALQUER usuário (inclusive superusuário) e apagar qualquer
    conta, só usando o pk na URL.
    """

    def setUp(self):
        self.escola_a = Escola.objects.create(nome='Escola A', email='a@escola-a.com')
        self.escola_b = Escola.objects.create(nome='Escola B', email='b@escola-b.com')

        grupo_coordenador, _ = Group.objects.get_or_create(name='Coordenador')

        self.coord_a = User.objects.create_user(username='coord_a', password='password123')
        self.coord_a.groups.add(grupo_coordenador)
        self.coord_a.profile.escola = self.escola_a
        self.coord_a.profile.save()

        self.coord_b = User.objects.create_user(username='coord_b', password='password123')
        self.coord_b.groups.add(grupo_coordenador)
        self.coord_b.profile.escola = self.escola_b
        self.coord_b.profile.save()

        self.superuser = User.objects.create_superuser(
            username='root', password='password123', email='root@example.com'
        )

        self.lista_url = reverse('usuarios:lista_usuarios')
        self.editar_coord_b_url = reverse('usuarios:editar_usuario', args=[self.coord_b.pk])
        self.editar_superuser_url = reverse('usuarios:editar_usuario', args=[self.superuser.pk])
        self.excluir_superuser_url = reverse('usuarios:excluir_usuario', args=[self.superuser.pk])
        self.criar_url = reverse('usuarios:criar_usuario')

    def test_coordenador_nao_lista_usuario_de_outra_escola(self):
        self.client.login(username='coord_a', password='password123')
        response = self.client.get(self.lista_url)
        self.assertEqual(response.status_code, 200)
        usuarios_listados = list(response.context['usuarios'])
        self.assertNotIn(self.coord_b, usuarios_listados)
        self.assertNotIn(self.superuser, usuarios_listados)
        self.assertIn(self.coord_a, usuarios_listados)

    def test_coordenador_nao_acessa_edicao_de_usuario_de_outra_escola(self):
        self.client.login(username='coord_a', password='password123')
        response = self.client.get(self.editar_coord_b_url)
        self.assertEqual(response.status_code, 404)

    def test_coordenador_nao_consegue_trocar_senha_de_outro_usuario_via_post(self):
        self.client.login(username='coord_a', password='password123')
        response = self.client.post(self.editar_coord_b_url, data={
            'username': 'coord_b', 'email': 'hack@x.com', 'first_name': '', 'last_name': '',
            'password': 'senhahackeada123', 'password_confirm': 'senhahackeada123',
            'escola': self.escola_b.pk, 'role': 'Coordenador',
        })
        self.assertEqual(response.status_code, 404)
        self.coord_b.refresh_from_db()
        self.assertFalse(self.coord_b.check_password('senhahackeada123'))

    def test_coordenador_nao_acessa_edicao_de_superusuario(self):
        self.client.login(username='coord_a', password='password123')
        response = self.client.get(self.editar_superuser_url)
        self.assertEqual(response.status_code, 404)

    def test_coordenador_nao_consegue_trocar_senha_do_superusuario(self):
        self.client.login(username='coord_a', password='password123')
        response = self.client.post(self.editar_superuser_url, data={
            'username': 'root', 'email': 'hack@x.com', 'first_name': '', 'last_name': '',
            'password': 'senhahackeada123', 'password_confirm': 'senhahackeada123',
            'escola': self.escola_a.pk, 'role': 'Coordenador',
        })
        self.assertEqual(response.status_code, 404)
        self.superuser.refresh_from_db()
        self.assertFalse(self.superuser.check_password('senhahackeada123'))

    def test_coordenador_nao_consegue_excluir_superusuario(self):
        self.client.login(username='coord_a', password='password123')
        response = self.client.post(self.excluir_superuser_url)
        self.assertEqual(response.status_code, 404)
        self.assertTrue(User.objects.filter(pk=self.superuser.pk).exists())

    def test_coordenador_acessa_e_edita_usuario_da_propria_escola(self):
        self.client.login(username='coord_a', password='password123')
        response = self.client.get(reverse('usuarios:editar_usuario', args=[self.coord_a.pk]))
        self.assertEqual(response.status_code, 200)

    def test_formulario_de_criacao_restringe_escola_ao_escopo_do_coordenador(self):
        """
        Antes do fix, UserCreationForm.escola aceitava Escola.objects.all()
        sem filtro nenhum — um Coordenador podia criar/mover um usuário para
        qualquer escola do sistema, inclusive de outra rede.
        """
        self.client.login(username='coord_a', password='password123')
        response = self.client.get(self.criar_url)
        self.assertEqual(response.status_code, 200)
        escola_queryset = response.context['form'].fields['escola'].queryset
        self.assertIn(self.escola_a, escola_queryset)
        self.assertNotIn(self.escola_b, escola_queryset)

    def test_superuser_continua_acessando_qualquer_usuario(self):
        self.client.login(username='root', password='password123')
        response = self.client.get(self.editar_coord_b_url)
        self.assertEqual(response.status_code, 200)
