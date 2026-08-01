from datetime import date, timedelta

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

        from django.contrib.auth.models import Group
        # Criar um usuário coordenador
        self.coordenador_user = User.objects.create_user(
            username='coordenador', 
            password='password123', 
            email='coordenador@escola1.com'
        )
        group_coordenador, _ = Group.objects.get_or_create(name='Coordenador')
        self.coordenador_user.groups.add(group_coordenador)

        # Criar duas escolas
        self.escola1 = Escola.objects.create(
            nome='Escola Teste 1', 
            email='coordenador@escola1.com', 
            coordenador_user=self.coordenador_user
        )
        self.coordenador_user.profile.escola = self.escola1
        self.coordenador_user.profile.save()
        
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
        form_data = {'nome': 'Nova Escola Via Teste', 'email': 'nova@teste.com', 'endereco': 'Rua Teste', 'telefone': '11999999999'}
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


class AlunosCursosPorEscolaListViewTest(TestCase):
    """
    Regressão do bug crítico de 2026-08-01: AlunosPorEscolaListView e
    CursosPorEscolaListView não tinham NENHUM mixin de autenticação —
    qualquer visitante anônimo via internet via nome completo/CPF/telefone
    de alunos reais, só sabendo o escola_id.
    """
    def setUp(self):
        from django.contrib.auth.models import Group
        from alunos.models import Aluno

        self.escola_a = Escola.objects.create(nome='Escola A', email='a@escola-a.com', tipo='CP')
        self.escola_b = Escola.objects.create(nome='Escola B', email='b@escola-b.com', tipo='CP')

        self.coord_a = User.objects.create_user(username='coord_a', password='password123')
        self.coord_a.groups.add(Group.objects.get_or_create(name='Coordenador')[0])
        self.coord_a.profile.escola = self.escola_a
        self.coord_a.profile.save()

        self.aluno_b = Aluno.objects.create(
            escola=self.escola_b, nome_completo='Fulano da Escola B',
            cpf='99999999999', data_nascimento='2000-01-01',
        )

        self.url_alunos_escola_b = reverse('escolas:alunos_da_escola', args=[self.escola_b.pk])
        self.url_cursos_escola_b = reverse('escolas:cursos_da_escola', args=[self.escola_b.pk])

    def test_visitante_anonimo_nao_acessa_lista_de_alunos(self):
        response = self.client.get(self.url_alunos_escola_b)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response, f"{reverse('login')}?next={self.url_alunos_escola_b}"
        )

    def test_visitante_anonimo_nao_acessa_lista_de_cursos(self):
        response = self.client.get(self.url_cursos_escola_b)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response, f"{reverse('login')}?next={self.url_cursos_escola_b}"
        )

    def test_coordenador_de_uma_escola_nao_acessa_alunos_de_outra_escola(self):
        """
        Também fecha o IDOR: mesmo autenticado, um Coordenador da Escola A
        não pode ver a lista de alunos da Escola B trocando o escola_id na URL.
        """
        self.client.login(username='coord_a', password='password123')
        response = self.client.get(self.url_alunos_escola_b)
        self.assertEqual(response.status_code, 404)

    def test_coordenador_acessa_alunos_da_propria_escola(self):
        self.client.login(username='coord_a', password='password123')
        url = reverse('escolas:alunos_da_escola', args=[self.escola_a.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class DashboardCarrosselEscopoTest(TestCase):
    """
    Regressão do bug de 2026-08-01: um admin geral que selecionava uma
    escola específica pelo trocador de contexto da navbar ainda via o
    carrossel do Dashboard com TODAS as escolas da rede, porque a ausência
    do parâmetro ?escola_id= na URL (todo carregamento normal da página)
    era tratada como se fosse um clique explícito em "Todas as Unidades",
    sobrescrevendo a escola ativa da sessão.
    """
    def setUp(self):
        self.escola_a = Escola.objects.create(nome='Escola A', email='a@escola-a.com', tipo='CP')
        self.escola_b = Escola.objects.create(nome='Escola B', email='b@escola-b.com', tipo='CP')

        self.superuser = User.objects.create_superuser(
            username='admin_dash', password='password123', email='admin_dash@example.com'
        )

        self.client.login(username='admin_dash', password='password123')
        self.client.post(
            reverse('escolas:trocar_contexto'),
            data={'escola_id': self.escola_a.pk},
        )

    def test_dashboard_respeita_escola_ativa_sem_query_param(self):
        """Sem ?escola_id= na URL, deve mostrar só a escola ativa da sessão."""
        response = self.client.get(reverse('escolas:dashboard'))
        self.assertEqual(response.status_code, 200)
        nomes = [e['nome'] for e in response.context['escolas_dados']]
        self.assertEqual(nomes, [self.escola_a.nome])

    def test_dashboard_ver_global_explicito_ainda_funciona(self):
        """?escola_id=all explícito continua ativando a visão agregada da
        rede (card "Visão Geral da Rede", só aparece quando há mais de uma
        escola no escopo) — em vez de ficar preso na escola ativa da sessão."""
        response = self.client.get(reverse('escolas:dashboard'), {'escola_id': 'all'})
        self.assertEqual(response.status_code, 200)
        nomes = {e['nome'] for e in response.context['escolas_dados']}
        self.assertIn('🌐 Visão Geral da Rede', nomes)


class DashboardQueryOptimizationTest(TestCase):
    """
    Regressão de 2026-08-01: DashboardView.get_context_data disparava ~2
    queries de Chamada por CURSO ATIVO por ESCOLA (loop de assiduidade) —
    com muitas escolas/cursos isso vira centenas de queries numa unica
    carga de pagina. Numeros aqui sao calculados a mao a partir do fixture
    (nao apenas "nao mudou"), pra garantir que o batching das queries nao
    alterou o resultado, so a forma de calcular.
    """

    def setUp(self):
        from cursos.models import Curso, TipoCurso, Inscricao, RegistroAula, Chamada
        from alunos.models import Aluno

        self.escola_a = Escola.objects.create(nome='Escola Dash A', email='dasha@example.com', tipo='CP')
        self.escola_b = Escola.objects.create(nome='Escola Dash B', email='dashb@example.com', tipo='CP')
        self.superuser = User.objects.create_superuser(
            username='admin_dash_opt', password='x', email='admin_dash_opt@example.com'
        )

        tipo_a = TipoCurso.objects.create(escola=self.escola_a, nome='Informática A')
        tipo_b = TipoCurso.objects.create(escola=self.escola_b, nome='Informática B')

        self.curso_a = Curso.objects.create(
            escola=self.escola_a, tipo_curso=tipo_a, nome='Curso A1', carga_horaria=40, vagas=10,
            data_inicio=date.today() - timedelta(days=10), data_fim=date.today() + timedelta(days=10),
            status='Em Andamento',
        )
        self.curso_b = Curso.objects.create(
            escola=self.escola_b, tipo_curso=tipo_b, nome='Curso B1', carga_horaria=40, vagas=5,
            data_inicio=date.today() - timedelta(days=10), data_fim=date.today() + timedelta(days=10),
            status='Em Andamento',
        )

        # Escola A: 3 alunos cursando + 1 concluido = 4 alunos no total.
        # Chamada: 2 presentes, 1 ausente -> 66% de assiduidade.
        alunos_a = [
            Aluno.objects.create(escola=self.escola_a, nome_completo=f'Aluno A{i}', cpf=f'1111111111{i}', data_nascimento='2000-01-01')
            for i in range(3)
        ]
        aluno_a4 = Aluno.objects.create(escola=self.escola_a, nome_completo='Aluno A concluido', cpf='11111111119', data_nascimento='2000-01-01')
        inscricoes_a = [Inscricao.objects.create(aluno=al, curso=self.curso_a, status='cursando') for al in alunos_a]
        Inscricao.objects.create(aluno=aluno_a4, curso=self.curso_a, status='concluido')

        ra_a = RegistroAula.objects.create(curso=self.curso_a, data_aula=date.today())
        Chamada.objects.create(registro_aula=ra_a, inscricao=inscricoes_a[0], status_presenca='P')
        Chamada.objects.create(registro_aula=ra_a, inscricao=inscricoes_a[1], status_presenca='P')
        Chamada.objects.create(registro_aula=ra_a, inscricao=inscricoes_a[2], status_presenca='A')

        # Escola B: 2 alunos cursando. Chamada: 2 presentes -> 100%.
        alunos_b = [
            Aluno.objects.create(escola=self.escola_b, nome_completo=f'Aluno B{i}', cpf=f'2222222222{i}', data_nascimento='2000-01-01')
            for i in range(2)
        ]
        inscricoes_b = [Inscricao.objects.create(aluno=al, curso=self.curso_b, status='cursando') for al in alunos_b]
        ra_b = RegistroAula.objects.create(curso=self.curso_b, data_aula=date.today())
        for insc in inscricoes_b:
            Chamada.objects.create(registro_aula=ra_b, inscricao=insc, status_presenca='P')

        self.client.login(username='admin_dash_opt', password='x')

    def test_kpis_e_assiduidade_por_escola_batem_com_calculo_manual(self):
        response = self.client.get(reverse('escolas:dashboard'), {'escola_id': 'all'})
        self.assertEqual(response.status_code, 200)
        por_nome = {e['nome']: e for e in response.context['escolas_dados']}

        dados_a = por_nome['Escola Dash A']
        self.assertEqual(dados_a['kpis']['total_alunos'], 4)
        self.assertEqual(dados_a['kpis']['cursos_ativos'], 1)
        self.assertEqual(dados_a['kpis']['alunos_cursando'], 3)
        self.assertEqual(dados_a['assiduidade']['labels'], ['Curso A1'])
        self.assertEqual(dados_a['assiduidade']['series'], [66])

        dados_b = por_nome['Escola Dash B']
        self.assertEqual(dados_b['kpis']['total_alunos'], 2)
        self.assertEqual(dados_b['kpis']['cursos_ativos'], 1)
        self.assertEqual(dados_b['kpis']['alunos_cursando'], 2)
        self.assertEqual(dados_b['assiduidade']['labels'], ['Curso B1'])
        self.assertEqual(dados_b['assiduidade']['series'], [100])

    def test_query_count_nao_escala_linearmente_com_numero_de_escolas(self):
        """Antes da otimizacao, cada escola com curso ativo somava ~2 queries
        de Chamada extras (uma por curso). Com 2 escolas/2 cursos isso ja da
        pra flagrar se a query de assiduidade voltou a rodar por curso em
        vez de uma vez só."""
        from django.test.utils import CaptureQueriesContext
        from django.db import connection

        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(reverse('escolas:dashboard'), {'escola_id': 'all'})
        self.assertEqual(response.status_code, 200)

        chamada_queries = [q for q in ctx.captured_queries if 'chamada' in q['sql'].lower()]
        # Antes: 2 escolas x 1 curso ativo cada x 2 queries (presentes/total) = 4,
        # mais o card global (mais 2). Depois da otimizacao deve ser O(1),
        # nao O(numero de cursos). Regressao: falha se voltar a crescer por curso.
        self.assertLessEqual(len(chamada_queries), 4, f"queries de Chamada: {len(chamada_queries)}")