from django.shortcuts import render

from django.views.generic import TemplateView, ListView

from .models import ChatMessage

# Create your views here.
class IndexView(TemplateView):
    template_name = "chat/index.html"

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
        context_data["room_name"] = self.kwargs.get("room_name") # from Django urlpattern parameter (kwarg)
        context_data["username"] = self.request.GET.get("username", "Anonymous") # from URL parameter
        
        return context_data
