from django.urls import path
from .views import StudentChatAPI, FacultyChatAPI

urlpatterns = [
    path('student/chat/', StudentChatAPI.as_view(), name='student_chat_api'),
    path('faculty/chat/', FacultyChatAPI.as_view(), name='faculty_chat_api'),
]
