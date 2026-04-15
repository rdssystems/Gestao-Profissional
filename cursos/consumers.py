import json
from channels.generic.websocket import AsyncWebsocketConsumer

class CursosConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.group_add("cursos_updates", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.group_discard("cursos_updates", self.channel_name)

    async def group_add(self, group, channel):
        await self.channel_layer.group_add(group, channel)

    async def group_discard(self, group, channel):
        await self.channel_layer.group_discard(group, channel)

    # Receive message from room group
    async def status_update(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps(event))
