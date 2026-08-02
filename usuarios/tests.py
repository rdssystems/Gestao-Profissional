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

    def test_link_usuarios_aparece_no_menu_para_coordenador(self):
        """
        Regressão de 2026-08-01: o grupo Coordenador já tinha as permissões
        add_user/change_user/view_user corretas, mas o link "Usuários" no
        menu (base.html) só aparecia dentro de {% if user.is_superuser %} —
        um Coordenador de CP/Uditech não tinha NENHUM caminho na interface
        pra chegar na tela de criação de usuário, mesmo com a view/form já
        preparados e corretamente restritos à própria escola.
        """
        self.client.login(username='coord_a', password='password123')
        response = self.client.get(reverse('escolas:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.lista_url)

    def test_coordenador_consegue_criar_usuario_para_propria_escola(self):
        self.client.login(username='coord_a', password='password123')
        response = self.client.post(self.criar_url, data={
            'username': 'novo_usuario_a',
            'email': 'novo@escola-a.com',
            'first_name': 'Novo',
            'last_name': 'Usuario',
            'password': 'senhaSegura123',
            'password_confirm': 'senhaSegura123',
            'escola': self.escola_a.pk,
            'role': 'Auxiliar Administrativo',
        })
        self.assertEqual(response.status_code, 302)
        novo = User.objects.get(username='novo_usuario_a')
        self.assertEqual(novo.profile.escola, self.escola_a)

    def test_coordenador_nao_consegue_criar_usuario_para_outra_escola(self):
        """O campo escola do form ja restringe as opcoes a propria escola do
        Coordenador — POST forcando outra escola deve falhar a validacao."""
        self.client.login(username='coord_a', password='password123')
        response = self.client.post(self.criar_url, data={
            'username': 'tentativa_cross_escola',
            'email': 'x@escola-b.com',
            'first_name': 'X', 'last_name': 'Y',
            'password': 'senhaSegura123',
            'password_confirm': 'senhaSegura123',
            'escola': self.escola_b.pk,
            'role': 'Auxiliar Administrativo',
        })
        self.assertEqual(response.status_code, 200)  # form invalido, re-renderiza
        self.assertFalse(User.objects.filter(username='tentativa_cross_escola').exists())

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


class AdminSegmentoCriaUsuarioTest(TestCase):
    """
    Regressão de 2026-08-02: admin_cp/admin_uditech (Profile.nivel_acesso
    sem escola vinculada) não conseguiam sequer ABRIR a tela de usuários —
    UserListView/CreateView/UpdateView/DeleteView usavam PermissionRequiredMixin
    checando Permission do Django (auth.add_user etc.), e nivel_acesso nunca
    esteve ligado a nenhum Group/Permission no código (só o grupo
    'Coordenador' tem essas permissões). O form/queryset já escopavam
    corretamente pro admin de segmento — só faltava a view deixar passar.
    """

    def setUp(self):
        self.escola_cp = Escola.objects.create(nome='Escola CP', email='cp@escola.com', tipo='CP')
        self.escola_uditech = Escola.objects.create(nome='Escola Uditech', email='ud@escola.com', tipo='UDITECH')

        self.admin_cp = User.objects.create_user(username='admin_cp_seg', password='password123')
        self.admin_cp.profile.nivel_acesso = 'ADMIN_CP'
        self.admin_cp.profile.save()

        self.admin_uditech = User.objects.create_user(username='admin_uditech_seg', password='password123')
        self.admin_uditech.profile.nivel_acesso = 'ADMIN_UDITECH'
        self.admin_uditech.profile.save()

        self.lista_url = reverse('usuarios:lista_usuarios')
        self.criar_url = reverse('usuarios:criar_usuario')

    def test_admin_cp_acessa_lista_de_usuarios(self):
        self.client.login(username='admin_cp_seg', password='password123')
        response = self.client.get(self.lista_url)
        self.assertEqual(response.status_code, 200)

    def test_link_usuarios_aparece_no_menu_para_admin_cp(self):
        self.client.login(username='admin_cp_seg', password='password123')
        response = self.client.get(reverse('escolas:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.lista_url)

    def test_admin_cp_consegue_criar_usuario_para_escola_cp(self):
        self.client.login(username='admin_cp_seg', password='password123')
        response = self.client.post(self.criar_url, data={
            'username': 'novo_coord_cp',
            'email': 'novo@escola-cp.com',
            'first_name': 'Novo', 'last_name': 'Coordenador',
            'password': 'senhaSegura123',
            'password_confirm': 'senhaSegura123',
            'escola': self.escola_cp.pk,
            'role': 'Coordenador',
        })
        self.assertEqual(response.status_code, 302)
        novo = User.objects.get(username='novo_coord_cp')
        self.assertEqual(novo.profile.escola, self.escola_cp)
        self.assertTrue(novo.groups.filter(name='Coordenador').exists())

    def test_admin_cp_nao_consegue_criar_usuario_para_escola_uditech(self):
        """O campo escola do form ja restringe as opcoes as escolas CP —
        POST forcando uma escola Uditech deve falhar a validacao."""
        self.client.login(username='admin_cp_seg', password='password123')
        response = self.client.post(self.criar_url, data={
            'username': 'tentativa_cross_sistema',
            'email': 'x@escola-uditech.com',
            'first_name': 'X', 'last_name': 'Y',
            'password': 'senhaSegura123',
            'password_confirm': 'senhaSegura123',
            'escola': self.escola_uditech.pk,
            'role': 'Coordenador',
        })
        self.assertEqual(response.status_code, 200)  # form invalido, re-renderiza
        self.assertFalse(User.objects.filter(username='tentativa_cross_sistema').exists())

    def test_admin_uditech_acessa_lista_e_cria_usuario_para_escola_uditech(self):
        self.client.login(username='admin_uditech_seg', password='password123')
        response = self.client.get(self.lista_url)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(self.criar_url, data={
            'username': 'novo_coord_uditech',
            'email': 'novo@escola-uditech.com',
            'first_name': 'Novo', 'last_name': 'Coordenador',
            'password': 'senhaSegura123',
            'password_confirm': 'senhaSegura123',
            'escola': self.escola_uditech.pk,
            'role': 'Coordenador',
        })
        self.assertEqual(response.status_code, 302)
        novo = User.objects.get(username='novo_coord_uditech')
        self.assertEqual(novo.profile.escola, self.escola_uditech)
