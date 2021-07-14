import json
from operator import itemgetter
from pprint import pprint

from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async

class ChatConsumer (AsyncWebsocketConsumer):
    # ! all functions should be async
    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"{self.room_name}"

        # Add this channel instance to a group named with the room name
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        # accept connection
        await self.accept()

    async def disconnect(self, close_code):
        # Leave Room
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from web socket
    async def receive(self, text_data):
        data = json.loads(text_data)
        username, room_name, message =  itemgetter("username", "room_name", "message") (data)

        # send message to channel layer  
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': "chat_message",
                "username": username,
                "message": message
            }
        )

    # Receive message from room group
    async def chat_message(self, event):
        username = event["username"]
        message = event["message"]

        await self.send(text_data=json.dumps({
            'username': username,
            'message': message
        }))
        