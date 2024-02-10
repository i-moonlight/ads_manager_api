import json

from channels.generic.websocket import AsyncWebsocketConsumer

class AdAccountsConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        await self.channel_layer.group_add('ad-accounts', self.channel_name)

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard('ad-accounts', self.channel_name)

    async def send_notification(self, event):
        await self.send(text_data=json.dumps({
            'message': event.get('message'),
            'ad_platform': event.get('ad_platform'),
            'is_importing': event.get('is_importing'),
            'task_id': event.get('task_id')
        }))
