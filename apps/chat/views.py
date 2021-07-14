from django.shortcuts import render

from django.views.generic import TemplateView

# Create your views here.
class IndexView(TemplateView):
    template_name = "chat/index.html"

class RoomView(TemplateView):
    template_name = "chat/room.html"
    
    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["room_name"] = self.kwargs.get("room_name") # Django urlpattern parameter
        context_data["username"] = self.request.GET.get("username", "Anonymous") # URL parameter

        return context_data
