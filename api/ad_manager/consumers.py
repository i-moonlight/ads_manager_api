import json

from channels.generic.websocket import AsyncWebsocketConsumer

class AdManagerConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        await self.channel_layer.group_add('ad-manager', self.channel_name)

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard('ad-manager', self.channel_name)

    async def send_notification(self, event):
        await self.send(text_data=json.dumps({
            'message': event.get('message'),
        }))
