from django.test import TestCase
from django.contrib.auth.models import User, Group
from .forms import AuxiliarAlunoForm

class AuxiliarAlunoFormTest(TestCase):
    def test_init_with_user(self):
        """
        Test that AuxiliarAlunoForm can be initialized with a 'user' argument,
        which is passed by AlunoUpdateView.
        """
        user = User.objects.create_user(username='test_auxiliar', password='password')
        
        # This should not raise TypeError
        try:
            form = AuxiliarAlunoForm(user=user)
        except TypeError as e:
            self.fail(f"AuxiliarAlunoForm raised TypeError with 'user' argument: {e}")
        
        self.assertTrue(form.is_bound is False)
