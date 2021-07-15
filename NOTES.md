## Requirements

### Packages
- django
- channels
- channels_redis

### Others
- a redis server, use docker or:
install a native redis server
```
sudo apt-get install redis-server
redis-server
``` 

## First Steps
**1. Create project and apps**

I prefer creating my applications within a directory called `apps` so that
everything seems more organized.

Make sure to include an empty `__init__.py` module in the `apps` directory for python to recognize
it.

```bash
django_chat \ 
    # directory for all applications
    apps\
        __init__.py

        # chat application
        chat\
            admin.py.py
            apps.py
            models.py
            views.py
            ...
    # project module
    django_chat\
        settings.py
        urls.py
        asgi.py
        wsgi.py
        ...
```

**2. Add apps and `channels` to `INSTALLED_APPS`.**

For the app to be recognized, change its name in the `AppConfig` class in its `apps.py` module.
Use the full path to the application directory:
```py
# apps.chat.apps
from django.apps import AppConfig


class ChatConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.chat'
```

And then in INSTALLED_APPS:

```py
# django_chat.settings

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'channels',
    'apps.chat',
]
```

**3. Configure ASIG_APPLICATION setting**

```py
ASGI_APPLICATION = 'django_chat.asgi.application'
```

**4. setup channel layers for redis**
   
```py
CHANNEL_LAYERS = {
    {
        'default': {
            'BACKEND': "channels_redis.core.RedisChannelLayer",
            'CONFIG': {
                'hosts': [('127.0.0.1', 5000)] # redis port
            }
        }
    }
}

```

## Create the Front Page
In the front page, the user enters a username and room name to be used to create a 'chat room' where users
can chat. On form submit, the room name is passed as a kwarg, part of a new url. The new URL is going to be the 
URL to visit in order to chat in a 'chat room' with that particular name the user entered. This url's view also accepts
a username URL parameter which is passed in the context data of template for the chat room. 
```py
# apps.chat.views
# TemplateView for chat room page

class RoomView(TemplateView):
    template_name = "chat/room.html"
    
    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["room_name"] = self.kwargs.get("room_name") # Django urlpattern parameter
        context_data["username"] = self.request.GET.get("username", "Anonymous") # URL parameter

        print(context_data)

        return context_data

# apps.chat.urls

from django.urls import path

from .views import IndexView, RoomView

urlpatterns = [
    path('', IndexView.as_view(), name="index"),
    path('<str:room_name>/', RoomView.as_view(), name='room'),
]
```


## Creating the Room Page and Establishing Communication with Django
The room page is where the websockets are implemented.
Here, there is a text input field and a div that represents a chat area.
The username and room name are received as template variables from the URL through the view.

### Workflow
**- Create Web Socket in JS**

A web socket that connects to the Django backend is created with a URL present in the backend

**- Add Event Handlers**
onmessage
: defines actions to be performed when some data is received via the socket 

onclose
: defines actions to be performed when the socket connection is closed
```js
// event handler for when socket connection closes
chatSocket.addEventListener("close", e => {
    alert("connection closed unexpectedly");
})
``` 

The form submit event handler is what causes a message to be sent via the websocket to the Django backend.
It adds the room name and username to the message text that is sent.
```js
// Form event handler to send chat message via socket
document.getElementById("send-message-form").addEventListener("submit", e => {
    e.preventDefault();
    
    const message = e.target.message.value.trim();
    
    chatSocket.send(JSON.stringify({
        username: username,
        room_name: roomName,
        message: message
    }))
    
    e.target.reset();
})

``` 
**- Creating the Connection with The Django Server**
After the message is sent, Django needs to handle it.
Two new modules are created in the app for this:
- consumers.py (analogous to views.py)
- routing.py (analogous to urls.py)

The web socket that the message from the frontend is sent through has a corresponding route
created in the routing module to enable Django handle the request.
```py
from django.urls import path 

from .consumers import ChatConsumer

websocket_urlpatterns = [
    path('ws/<str:room_name>/', ChatConsumer.as_asgi())
]
```

As evident above, the web socket route matches the socket request to a `consumer` - like a normal
url route is matched to a `view` in the `urls` module.

The consumer module defines how the Django server deals with matched web socket requests

A consumer that subclasses `channels.generic.websocket.AsyncWebsocketConsumer` is created. We call it
`ChatConsumer`.

The `connect` method of the consumer is called when a connection is established. In this case,
the room name is retrieved from the URL using `self.scope["url_route"]["kwargs][<url_parameter>]`
`self.scope` is analogous to `request` in a Django view.

```py
# apps.chat.consumers

class ChatConsumer (AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        # ...
```

Next, a group is created in the channel layer.
> Channel layers allow you to talk between different instances of an application. They’re a useful part of making a distributed realtime application if you don’t want to have to shuttle all of your messages or events through a database. **~ Official Docs**

A group enables a single message to be broadcasted to all channels in the group.
>You use groups by adding a channel to them during connection, and removing it during disconnection. **~ Official Docs**

The group needs a name so the room name from the URL is used set as an instance attribute and used for that.

Finally, the connection is accepted using `self.accept()`.

```py
# apps.chat.consumers
class ChatConsumer (AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"{self.room_name}"

        # Add this channel instance to a group named with the room name
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        self.accept()
```

When the connection closes:
```py
async def disconnect(self, close_code):
    # Leave Room
    await self.channel_layer.group_discard(
        self.room_group_name,
        self.channel_name
    )
```

**- Django Handles the Message via the Socket**
The method that is called when a message is received (i.e, when the client sends some chat message) is 
the `receive` method.

It accepts `text_data` and `bytes_data`.

Our case is some JSON from the client which contains the message and some extra details, so the only 
the `text_data` argument will be used in the method definition.

When data is received, the username, room name, and message is extracted from the JSON.
Then the same data is sent to the same group so that the frontend can display it.

To send a message to the group, first the `self.channel_layer.group_send` function is used to send the data
in a form called an `event` to all channels in the group. The group name and the `event` 
are passed as arguments to the function.
Notice that within the `event`, the function has a key called `type`. The `type` determines which 
handling function to use to handle the `event` once the channels in the group receive it. 
In this case, the `chat_message` method.

```py
# apps.chat.consumers
class ChatConsumer(AsyncWebsocketConsumer):

    # ...

    # Receive message from web socket
    async def receive(self, text_data):
        data = json.loads(text_data)
        username, room_name, message =  itemgetter("username", "room_name", "message") (data)

        # send message to channel layer  
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': "chat.message",
                "username": username,
                "message": message
            }
        )

```

The `chat_message` method then sends the message via the Web socket to each client.

```py
# apps.chat.consumers
class ChatConsumer(AsyncWebsocketConsumer):
    # ...
    def receive(self, text_data):
        # ...

    # When message is received by a channel, send it to the client
    async def chat_message(self, event):
        username = event["username"]
        message = event["message"]

        await self.send(text_data=json.dumps({
            'username': username,
            'message': message
        }))
```

**- Frontend Handles Echoed Message from Backend**
When the message is sent back to the frontend, the onmessage web socket event handler is invoked
and the message is appended to the HTML.

```js
// event handler for when socket receives a message
chatSocket.addEventListener("message", e => {
    const data = JSON.parse(e.data);

    // if the data Object contains a message
    // add the message to the HTML of the page
    if (data.message) {
        document.querySelector(".chat-messages").innerHTML += `
            <div class="chat_message">
                <p class="chat_message_username">${data.username}</p>
                <p class="chat_message_text">${data.message}</p>
            </div>
        `
        console.log(data);
    }
})
```

**- Persisting Messages**
All works fine now, except that messages aren't saved.
So when the page is reloaded, previous messages are lost, also,
users who join chat rooms don't see older messages.

How do we fix this? *A Database of course!*

1. So a model is created to keep each message in the DB.
```py
# apps.chat.models

class Message(models.Model):
    username = models.CharField(max_length=255)
    room_name = models.CharField(max_length=255)
    message_text = models.TextField()
    date_time_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('date_time_added',)
```

The instances of the model, the messages, are ordered from oldest to newest so that they are
displayed accordingly.

2. Save the message when received via the consumer.
- First create a method to store the message in the db.
- Make the method asynchronous since an asynchronous consumer is what is being used
```py
@sync_to_async
def store_chat_messsage(self, username, room_name, message):
    ChatMessage.objects.create(username=username, room_name=room_name, message_text=message)

```

- await the method and pass the message details as parameters when the message is received

```py
# apps.chat.consumers
class ChatConsumer(AsyncWebsocketConsumer):
    # ...
    def receive(self, text_data):
        data = json.loads(text_data)
        username, room_name, message =  itemgetter("username", "room_name", "message") (data)

        # add received message to DB
        await self.store_chat_messsage(username=username, room_name=room_name, message=message)

        # broadcast message to room group on the channel layer  
        await self.channel_layer.group_send(
         # ...
        )
```

3. Retrieve previous messages from DB when the chat room page is requested.
So the `RoomView` view is modified to include the previous messages for a particular room in its context data.
```py
class RoomView(ListView):
    template_name = "chat/room.html"
    model = ChatMessage
    context_object_name = "chat_messages"

    # return only messages that have room name equal to what is passed in URL kwarg
    # in context data
    def get_queryset(self):
        return self.model.objects.filter(room_name = self.kwargs.get("room_name"))


    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["room_name"] = self.kwargs.get("room_name") # Django urlpattern parameter
        context_data["username"] = self.request.GET.get("username", "Anonymous") # URL parameter
        print(context_data)
        return context_data
```

# I believe we are done here, Alhamdulillah!