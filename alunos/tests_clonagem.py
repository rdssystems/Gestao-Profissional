from django.test import TestCase
from django.contrib.auth.models import User, Group
from django.urls import reverse
from escolas.models import Escola
from .models import Aluno
from .forms import VerificarCPFForm

class AlunoClonagemTest(TestCase):
    def setUp(self):
        # Create Group
        self.group_coord, _ = Group.objects.get_or_create(name='Coordenador')

        # User & School A (Source)
        self.coord_a = User.objects.create_user(username='coord_a', password='password')
        self.coord_a.groups.add(self.group_coord)
        self.escola_a = Escola.objects.create(nome='Escola A', email='a@test.com', coordenador_user=self.coord_a)
        self.coord_a.profile.escola = self.escola_a
        self.coord_a.profile.save()

        # User & School B (Destination)
        self.coord_b = User.objects.create_user(username='coord_b', password='password')
        self.coord_b.groups.add(self.group_coord)
        self.escola_b = Escola.objects.create(nome='Escola B', email='b@test.com', coordenador_user=self.coord_b)
        self.coord_b.profile.escola = self.escola_b
        self.coord_b.profile.save()

        # Student in School A
        self.aluno_a = Aluno.objects.create(
            escola=self.escola_a,
            nome_completo='Aluno Original',
            cpf='123.456.789-00',
            data_nascimento='2000-01-01',
            sexo='M',
            estado_civil='Solteiro',
            email_principal='aluno@test.com',
            telefone_principal='123456789',
            endereco_rua='Rua Teste',
            endereco_numero='10',
            endereco_bairro='Centro',
            endereco_cidade='Cidade',
            endereco_estado='UF',
            endereco_cep='00000-000'
        )
        
        self.verify_url = reverse('alunos:verificar_cpf')
        self.clone_url = reverse('alunos:clonar_aluno', kwargs={'pk': self.aluno_a.pk})

    def test_verify_cpf_finds_existing_student(self):
        self.client.login(username='coord_b', password='password')
        response = self.client.post(self.verify_url, {'cpf': '123.456.789-00'})
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('aluno_existente', response.context)
        self.assertEqual(response.context['aluno_existente'], self.aluno_a)
        self.assertTrue(response.context['mostrar_opcao_clonar'])

    def test_clone_student_action(self):
        self.client.login(username='coord_b', password='password')
        response = self.client.post(self.clone_url)
        
        # Should redirect to edit view of NEW student
        self.assertEqual(response.status_code, 302)
        
        # Verify new student exists in School B
        aluno_b = Aluno.objects.filter(escola=self.escola_b, cpf='123.456.789-00').first()
        self.assertIsNotNone(aluno_b)
        self.assertNotEqual(aluno_b.pk, self.aluno_a.pk)
        self.assertEqual(aluno_b.nome_completo, 'Aluno Original')
        
        # Check redirect target
        expected_url = reverse('alunos:editar_aluno', kwargs={'pk': aluno_b.pk})
        self.assertRedirects(response, expected_url)

    def test_prevent_duplicate_clone_in_same_school(self):
        # Create the clone first
        self.client.login(username='coord_b', password='password')
        self.client.post(self.clone_url)
        
        # Try to clone again
        response = self.client.post(self.clone_url)
        
        # Should redirect to list (or safe place) and not create another one
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Aluno.objects.filter(escola=self.escola_b, cpf='123.456.789-00').count(), 1)

    def test_verify_cpf_blocks_if_already_in_school(self):
        # Clone first
        self.client.login(username='coord_b', password='password')
        self.client.post(self.clone_url)
        
        # Verify again
        response = self.client.post(self.verify_url, {'cpf': '123.456.789-00'})
        
        # Should show error message and NOT offer clone option
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn("já está cadastrado nesta escola", content)
        self.assertIsNone(response.context.get('mostrar_opcao_clonar'))

