import json
from channels.generic.websocket import AsyncWebsocketConsumer

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Entra no grupo "global_notifications"
        # Em um sistema mais complexo, poderia ser específico por escola ou usuário
        self.group_name = "global_notifications"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Sai do grupo
        await self.channel_layer.group_discard(
            self.group_name,
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
