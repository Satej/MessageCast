import json
from datetime import datetime

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from api.models import APIProduct
from chat.models import Chat
from chat.serializers import ChatSerializer


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = 'chat_%s' % self.room_name
        self.user = self.scope["user"]

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        chat_room = text_data_json['roomName']
        user = self.user

        if message.rstrip() != '':

            try:
                api_product = await sync_to_async(APIProduct.objects.get, thread_sensitive=True)(name=chat_room)
                results = await sync_to_async(Chat.objects.create, thread_sensitive=True)(user=user, message=message,
                                                                                          chat_room=api_product)
                # Send message to WebSocket
            except APIProduct.DoesNotExist as e:
                # This chat-room does not exist
                pass

            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'room_name': self.room_name,
                    'username': user.username,
                    'created_at': f"{datetime.now().strftime('%Y-%m-%d %H:%M')}",
                }
            )

    # Receive message from room group
    async def chat_message(self, event):
        message = event['message']
        username = event['username']
        created_at = event['created_at']
        # user = self.user.username

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': f"{message} - {username} - {created_at}"
        }))
