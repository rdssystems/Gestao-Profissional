from datetime import date, timedelta

from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User, Group
from django.urls import reverse

from core.mixins import StaffRequiredMixin, CoordenadorRequiredMixin
from core.models import AuditLog
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


class AuditLogChamadaTest(TestCase):
    """
    Regressão de 2026-08-01: fecha as maiores lacunas do log de auditoria
    encontradas na auditoria do sistema (RegistroAula/Chamada não tinham
    nenhum rastro, e ExcluirRegistroAulaView gravava DOIS logs por exclusão
    porque chamava self.save_log() manualmente sem suprimir o post_delete
    automático de core/audit_signals.py, que também cobre RegistroAula).
    """

    def setUp(self):
        from cursos.models import Curso, TipoCurso, Inscricao

        self.escola = Escola.objects.create(
            nome='Escola Chamada', endereco='Rua X', email='chamada@example.com',
            telefone='3333-3333', tipo='CP',
        )
        self.superuser = User.objects.create_superuser(
            username='admin_chamada', password='x', email='admin_chamada@example.com'
        )
        self.tipo_curso = TipoCurso.objects.create(escola=self.escola, nome='Informática')
        self.curso = Curso.objects.create(
            escola=self.escola, tipo_curso=self.tipo_curso, nome='Curso Teste',
            carga_horaria=40, vagas=20,
            data_inicio=date.today(), data_fim=date.today() + timedelta(days=30),
            status='Em Andamento', nome_professor='Professor Teste',
        )
        self.aluno = Aluno.objects.create(
            escola=self.escola, nome_completo='Aluno Chamada', cpf='33333333333',
            data_nascimento='2000-01-01',
        )
        self.inscricao = Inscricao.objects.create(aluno=self.aluno, curso=self.curso, status='cursando')

    def test_excluir_registro_aula_grava_apenas_um_log(self):
        from cursos.models import RegistroAula

        registro = RegistroAula.objects.create(curso=self.curso, data_aula=date.today())
        self.client.login(username='admin_chamada', password='x')
        url = reverse('cursos:excluir_registro_aula', kwargs={'pk': registro.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)

        ct = ContentType.objects.get_for_model(RegistroAula)
        count = AuditLog.objects.filter(content_type=ct, object_id=str(registro.pk), acao='DELETE').count()
        self.assertEqual(count, 1)

    def test_fazer_chamada_post_grava_log(self):
        from cursos.models import RegistroAula

        self.client.login(username='admin_chamada', password='x')
        url = reverse('cursos:fazer_chamada', kwargs={'curso_pk': self.curso.pk})
        data = {
            'data_aula': date.today().strftime('%Y-%m-%d'),
            'observacoes': '',
            'chamada-TOTAL_FORMS': '1',
            'chamada-INITIAL_FORMS': '0',
            'chamada-MIN_NUM_FORMS': '0',
            'chamada-MAX_NUM_FORMS': '1000',
            'chamada-0-inscricao': str(self.inscricao.pk),
            'chamada-0-status_presenca': 'P',
        }
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 302)

        registro = RegistroAula.objects.get(curso=self.curso, data_aula=date.today())
        ct = ContentType.objects.get_for_model(RegistroAula)
        self.assertEqual(
            AuditLog.objects.filter(content_type=ct, object_id=str(registro.pk)).count(), 1
        )

    def test_chamada_publica_post_grava_log_sem_usuario(self):
        """POST anônimo (link compartilhado com professor externo, sem
        login de usuário do sistema) — antes desta correção, não deixava
        nenhum rastro no log de auditoria."""
        from cursos.models import RegistroAula

        login_url = reverse('cursos:chamada_publica', kwargs={'token': self.curso.token_acesso})
        self.client.post(login_url, data={'action': 'login', 'nome_professor': 'Professor Teste'})

        response = self.client.post(login_url, data={
            'action': 'salvar_chamada',
            'presencas': [str(self.inscricao.pk)],
        })
        self.assertEqual(response.status_code, 302)

        registro = RegistroAula.objects.get(curso=self.curso, data_aula=date.today())
        ct = ContentType.objects.get_for_model(RegistroAula)
        log = AuditLog.objects.filter(content_type=ct, object_id=str(registro.pk)).first()
        self.assertIsNotNone(log)
        self.assertIsNone(log.usuario)
        self.assertIn('Professor Teste', log.detalhes)


class AuditLogDocumentosPublicoTest(TestCase):
    """Regressão de 2026-08-01: documentos/publico ficaram totalmente fora
    do log de auditoria (nem AuditLogMixin, nem allow-list de signals)."""

    def setUp(self):
        self.escola = Escola.objects.create(
            nome='Escola Doc', endereco='Rua Y', email='doc@example.com',
            telefone='4444-4444', tipo='CP',
        )
        self.superuser = User.objects.create_superuser(
            username='admin_doc', password='x', email='admin_doc@example.com'
        )
        self.client.login(username='admin_doc', password='x')

    def test_documento_upload_e_delete_geram_log(self):
        from documentos.models import DocumentoUnidade

        upload_url = reverse('documentos:documento_upload')
        arquivo = SimpleUploadedFile('teste.pdf', b'conteudo-fake', content_type='application/pdf')
        response = self.client.post(upload_url, data={
            'arquivo': arquivo, 'nome': 'Documento Teste',
            'categoria': 'outros', 'escola': self.escola.pk,
        })
        self.assertEqual(response.status_code, 302)

        doc = DocumentoUnidade.objects.get(nome='Documento Teste')
        ct = ContentType.objects.get_for_model(DocumentoUnidade)
        self.assertEqual(
            AuditLog.objects.filter(content_type=ct, object_id=str(doc.pk), acao='CREATE').count(), 1
        )

        delete_url = reverse('documentos:documento_excluir', kwargs={'pk': doc.pk})
        response = self.client.post(delete_url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            AuditLog.objects.filter(content_type=ct, object_id=str(doc.pk), acao='DELETE').count(), 1
        )

    def test_bloco_conteudo_create_gera_log(self):
        from publico.models import BlocoConteudo

        create_url = reverse('publico:bloco_create', kwargs={'escola_id': self.escola.pk})
        response = self.client.post(create_url, data={
            'tipo': 'texto', 'titulo': 'Bloco Teste', 'texto': 'Conteúdo de teste',
            'dias_semana': '', 'ordem': '0', 'ativo': 'on',
        })
        self.assertEqual(response.status_code, 302)

        bloco = BlocoConteudo.objects.get(titulo='Bloco Teste')
        ct = ContentType.objects.get_for_model(BlocoConteudo)
        self.assertEqual(
            AuditLog.objects.filter(content_type=ct, object_id=str(bloco.pk), acao='CREATE').count(), 1
        )


class AuditLogLimparAgendaTest(TestCase):
    """Regressão de 2026-08-01: limpar_agenda_cursos_view faz um .update()
    em massa (Django não dispara post_save nesse caso), então essa ação
    explícita do usuário não deixava nenhum rastro no log de auditoria."""

    def setUp(self):
        from cursos.models import Curso, TipoCurso

        self.escola = Escola.objects.create(
            nome='Escola Agenda', endereco='Rua Z', email='agenda@example.com',
            telefone='5555-5555', tipo='CP',
        )
        self.superuser = User.objects.create_superuser(
            username='admin_agenda', password='x', email='admin_agenda@example.com'
        )
        tipo_curso = TipoCurso.objects.create(escola=self.escola, nome='Informática')
        # Curso "Aberta" sem nenhuma inscrição — candidato ao arquivamento automático.
        self.curso = Curso.objects.create(
            escola=self.escola, tipo_curso=tipo_curso, nome='Curso Vazio',
            carga_horaria=40, vagas=20,
            data_inicio=date.today(), data_fim=date.today() + timedelta(days=30),
            status='Aberta',
        )

    def test_limpar_agenda_gera_log_com_quantidade(self):
        self.client.login(username='admin_agenda', password='x')
        response = self.client.post(reverse('core:limpar_agenda_cursos'))
        self.assertEqual(response.status_code, 302)

        log = AuditLog.objects.filter(acao='UPDATE', usuario=self.superuser).order_by('-data_hora').first()
        self.assertIsNotNone(log)
        self.assertIn('"quantidade": 1', log.detalhes)
