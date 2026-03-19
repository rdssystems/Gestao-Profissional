import json
from channels.generic.websocket import AsyncWebsocketConsumer

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get('user')
        self.groups_to_join = ["global_notifications"]

        # Se o usuário estiver logado e tiver uma escola associada, entra no grupo da escola
        if self.user and self.user.is_authenticated:
            try:
                # Tentamos pegar a escola do perfil
                if hasattr(self.user, 'profile') and self.user.profile.escola:
                    escola_id = self.user.profile.escola.id
                    self.groups_to_join.append(f"school_notifications_{escola_id}")
            except Exception:
                pass

        # Entra em todos os grupos necessários
        for group in self.groups_to_join:
            await self.channel_layer.group_add(
                group,
                self.channel_name
            )

        await self.accept()

    async def disconnect(self, close_code):
        # Sai de todos os grupos
        for group in getattr(self, 'groups_to_join', []):
            await self.channel_layer.group_discard(
                group,
                self.channel_name
            )

    # Recebe mensagem do WebSocket (do cliente) - não usado neste caso, mas bom ter
    async def receive(self, text_data):
        pass

    # Recebe mensagem do grupo (do backend/signals) e envia para o WebSocket
    async def send_notification(self, event):
        message = event['message']
        notification_type = event.get('notification_type', 'info')
        
        # Envia mensagem para o WebSocket
        await self.send(text_data=json.dumps({
            'message': message,
            'type': notification_type
        }))
