from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Escola

@receiver(post_save, sender=Escola)
def criar_ou_atualizar_usuario_coordenador(sender, instance, created, **kwargs):
    """
    Cria um novo usuário para o coordenador quando uma nova Escola é criada,
    ou atualiza o usuário existente se o email do coordenador for alterado.
    """
    escola = instance
    email = escola.email
    # nome_coordenador = escola.coordenador

    # Tenta encontrar um usuário com o email fornecido
    user = User.objects.filter(email=email).first()

    if user:
        # Se o usuário existe, mas não está ligado a esta escola, não faz nada para evitar roubar o usuário de outra escola.
        # A lógica de negócio pode ser mais complexa aqui, mas por segurança, vamos parar.
        if hasattr(user, 'escola_coordenada') and user.escola_coordenada != escola:
            return 
        
        # Garante que o usuário esteja ligado a esta escola
        if not hasattr(user, 'escola_coordenada') or user.escola_coordenada != escola:
             escola.coordenador_user = user
             escola.save()

    else:
        # Se o usuário não existe, cria um novo
        # Usa o email como username para garantir unicidade
        username = email
        # Evita erro se o username já existir (embora a checagem de email já deva prevenir isso)
        if User.objects.filter(username=username).exists():
            # Em um caso real, poderíamos adicionar um sufixo aleatório
            return 

        # Cria o usuário com uma senha inutilizável. O usuário precisará usar o fluxo de "reset de senha".
        user = User.objects.create_user(username=username, email=email)
        user.set_unusable_password()
        user.save()
        
        # Associa o novo usuário à escola
        escola.coordenador_user = user
        # O .save() aqui vai disparar o sinal de novo, então precisamos evitar um loop infinito.
        # A forma mais simples é desconectar o sinal temporariamente, mas uma checagem no início da função
        # (se o coordenador_user já é o usuário correto) também funciona.
        # No nosso caso, a checagem 'if user:' no início previne o loop.
        post_save.disconnect(criar_ou_atualizar_usuario_coordenador, sender=Escola)
        escola.save()
        post_save.connect(criar_ou_atualizar_usuario_coordenador, sender=Escola)
