from django.urls import path
from . import views

# making separate urls.py for rooms
app_name = "rooms"

# receiving "localhost/rooms/110230" to use it as primary key for database
urlpatterns = [path("<int:pk>", views.room_detail, name="detail")]