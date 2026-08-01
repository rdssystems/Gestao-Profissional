from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User, Group

from core.mixins import StaffRequiredMixin, CoordenadorRequiredMixin
from escolas.models import Escola
from alunos.models import Aluno


class _DummyView(StaffRequiredMixin):
    """View mínima só para exercitar StaffRequiredMixin.test_func() isolado,
    sem precisar de uma view real com template/queryset."""
    def __init__(self, request, model=None, pk=None):
        self.request = request
        if model is not None:
            self.model = model
        self.kwargs = {'pk': pk} if pk is not None else {}


class _DummyCoordenadorView(CoordenadorRequiredMixin):
    def __init__(self, request):
        self.request = request


def _make_request(user, sistema='cp'):
    request = RequestFactory().get('/')
    request.user = user
    request.session = {'sistema': sistema}
    return request


class StaffRequiredMixinTest(TestCase):
    """
    Cobre core/mixins.py, que não tinha nenhum teste apesar de ser a
    checagem de autorização usada em praticamente todo o app. Inclui
    regressão do bug de 2026-08-01: Profile.nivel_acesso tem default
    'ADMIN_CP' (core/models.py), e sem checar 'not profile.escola' antes de
    tratar isso como "admin de segmento", qualquer Coordenador comum
    (com escola vinculada) herdava acesso a objetos de QUALQUER escola da
    rede CP.
    """

    def setUp(self):
        self.escola_a = Escola.objects.create(
            nome='Escola A', endereco='Rua A', email='escola.a@example.com',
            telefone='1111-1111', tipo='CP',
        )
        self.escola_b = Escola.objects.create(
            nome='Escola B', endereco='Rua B', email='escola.b@example.com',
            telefone='2222-2222', tipo='CP',
        )

        self.superuser = User.objects.create_superuser(
            username='root', password='x', email='root@example.com'
        )

        grupo_coordenador, _ = Group.objects.get_or_create(name='Coordenador')

        self.coord_a = User.objects.create_user(username='coord_a', password='x')
        self.coord_a.groups.add(grupo_coordenador)
        self.coord_a.profile.escola = self.escola_a
        self.coord_a.profile.save()

        self.segment_admin_cp = User.objects.create_user(username='admin_cp', password='x')
        self.segment_admin_cp.profile.nivel_acesso = 'ADMIN_CP'
        self.segment_admin_cp.profile.save()

        self.aluno_a = Aluno.objects.create(
            escola=self.escola_a, nome_completo='Aluno da Escola A', cpf='11111111111',
            data_nascimento='2000-01-01',
        )
        self.aluno_b = Aluno.objects.create(
            escola=self.escola_b, nome_completo='Aluno da Escola B', cpf='22222222222',
            data_nascimento='2000-01-01',
        )

    def test_superuser_always_passes(self):
        request = _make_request(self.superuser)
        self.assertTrue(_DummyView(request).test_func())

    def test_segment_admin_sem_escola_passa_no_proprio_sistema(self):
        request = _make_request(self.segment_admin_cp, sistema='cp')
        self.assertTrue(_DummyView(request).test_func())

    def test_segment_admin_sem_escola_nao_passa_em_outro_sistema(self):
        request = _make_request(self.segment_admin_cp, sistema='uditech')
        self.assertFalse(_DummyView(request).test_func())

    def test_usuario_sem_grupo_de_staff_nao_passa(self):
        ninguem = User.objects.create_user(username='ninguem', password='x')
        request = _make_request(ninguem)
        self.assertFalse(_DummyView(request).test_func())

    def test_novo_perfil_tem_default_seguro_nenhum(self):
        """
        Segunda parte do fix de 2026-08-01: o default do model passou de
        'ADMIN_CP' para 'NENHUM' (core/models.py), porque um Coordenador
        comum recém-criado (ou até um usuário criado sem querer via
        /admin/ "Add user", sem tocar no dropdown) não deveria nascer com
        acesso de administrador de segmento.
        """
        self.assertEqual(self.coord_a.profile.nivel_acesso, 'NENHUM')

    def test_regressao_coordenador_legado_com_admin_cp_nao_acessa_objeto_de_outra_escola(self):
        """
        Simula um perfil "legado": nivel_acesso == 'ADMIN_CP' só porque essa
        era a linha já salva no banco antes do fix do default (o fix do
        default não altera linhas existentes). Mesmo assim, ter uma escola
        vinculada precisa impedir o bypass do bloco de admin de segmento —
        essa é a regressão original do bug de 2026-08-01 em core/mixins.py.
        """
        self.coord_a.profile.nivel_acesso = 'ADMIN_CP'
        self.coord_a.profile.save()
        request = _make_request(self.coord_a, sistema='cp')
        view = _DummyView(request, model=Aluno, pk=self.aluno_b.pk)
        self.assertFalse(view.test_func())

    def test_coordenador_acessa_objeto_da_propria_escola(self):
        request = _make_request(self.coord_a, sistema='cp')
        view = _DummyView(request, model=Aluno, pk=self.aluno_a.pk)
        self.assertTrue(view.test_func())


class CoordenadorRequiredMixinTest(TestCase):
    """Mesma regressão de nivel_acesso default, para o segundo mixin que tem a mesma lógica."""

    def setUp(self):
        self.escola_a = Escola.objects.create(
            nome='Escola A', endereco='Rua A', email='escola.a2@example.com',
            telefone='1111-1111', tipo='CP',
        )
        grupo_coordenador, _ = Group.objects.get_or_create(name='Coordenador')
        self.coord_a = User.objects.create_user(username='coord_a2', password='x')
        self.coord_a.groups.add(grupo_coordenador)
        self.coord_a.profile.escola = self.escola_a
        self.coord_a.profile.save()

    def test_coordenador_com_escola_passa_independente_do_valor_de_sistema(self):
        """
        CoordenadorRequiredMixin não faz checagem por objeto nem por
        'sistema' para um Coordenador comum (isso é responsabilidade do
        get_queryset de cada view / do AdminContextMiddleware, que corrige
        'sistema' para bater com profile.escola.tipo). O que a regressão
        aqui precisa garantir é que ter uma escola vinculada NÃO faz este
        usuário cair no bloco de "admin de segmento" (que já dependia do
        valor de nivel_acesso, mesmo antes do fix) — ele deve sempre passar
        pelo bloco de Coordenador local.
        """
        for sistema in ('cp', 'uditech'):
            request = _make_request(self.coord_a, sistema=sistema)
            self.assertTrue(_DummyCoordenadorView(request).test_func())
