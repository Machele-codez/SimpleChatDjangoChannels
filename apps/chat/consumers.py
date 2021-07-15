import json
from operator import itemgetter
from pprint import pprint

from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async

from .models import ChatMessage

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

    # On receive message from web socket
    async def receive(self, text_data):
        data = json.loads(text_data)
        username, room_name, message =  itemgetter("username", "room_name", "message") (data)

        # add received message to DB
        await self.store_chat_messsage(username=username, room_name=room_name, message=message)

        # broadcast message to room group on the channel layer  
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': "chat_message",
                "username": username,
                "message": message
            }
        )

    # When message is received by a channel, send it to the client
    async def chat_message(self, event):
        username = event["username"]
        message = event["message"]

        await self.send(text_data=json.dumps({
            'username': username,
            'message': message
        }))
        
    
    @sync_to_async
    def store_chat_messsage(self, username, room_name, message):
        ChatMessage.objects.create(username=username, room_name=room_name, message_text=message)
