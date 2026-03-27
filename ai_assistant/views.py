from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from authentication.models import User
from .models import ChatSession, ChatMessage
from .assistant.student import get_student_agent
from .assistant.faculty import get_faculty_agent
from backend.student.models import StudentProfile
from backend.faculty.models import FacultyProfile
from ai_assistant.utils import key_rotator
import google.api_core.exceptions
from langchain_google_genai.chat_models import ChatGoogleGenerativeAIError

def extract_answer(content):
    """Robustly extract text from various LangChain/Gemini content formats."""
    if not content:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = []
        for block in content:
            if isinstance(block, str):
                texts.append(block)
            elif isinstance(block, dict):
                text = block.get("text") or block.get("content") or ""
                if text:
                    texts.append(str(text))
        return " ".join(texts).strip()
    return str(content)

def is_rate_limit_error(e):
    """Check if an exception is a Google API Rate Limit error."""
    error_str = str(e).upper()
    return "RESOURCE_EXHAUSTED" in error_str or "429" in error_str

class StudentChatAPI(APIView):
    authentication_classes = [] 
    permission_classes = []

    def post(self, request):
        student_email = request.session.get('student_email')
        if not student_email:
            return Response({"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)
        
        user = User.objects.filter(email=student_email).first()
        if not user:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        message_text = request.data.get("message")
        if not message_text:
            return Response({"error": "Message is required"}, status=status.HTTP_400_BAD_REQUEST)

        session, _ = ChatSession.objects.get_or_create(user=user, is_active=True)
        ChatMessage.objects.create(session=session, role='user', content=message_text)
        student_profile = get_object_or_404(StudentProfile, user=user)
        
        try:
            agent = get_student_agent(student_profile.id)
            inputs = {"messages": [{"role": "user", "content": message_text}]}
            res = agent.invoke(inputs)
            
            messages = res.get("messages", [])
            answer = ""
            for msg in reversed(messages):
                if msg.type == 'ai' and msg.content:
                    extracted = extract_answer(msg.content)
                    if extracted.strip():
                        answer = extracted
                        break
            
            if not answer and messages:
                answer = extract_answer(messages[-1].content)
            
            if not answer:
                answer = "I'm sorry, I couldn't find an answer for that."

        except Exception as e:
            if is_rate_limit_error(e):
                if key_rotator.rotate():
                    try:
                        agent = get_student_agent(student_profile.id)
                        res = agent.invoke({"messages": [{"role": "user", "content": message_text}]})
                        answer = extract_answer(res["messages"][-1].content)
                    except Exception as retry_e:
                        answer = "I'm experiencing high traffic. Please try again in a moment."
                else:
                    answer = "The system is currently at its limit. Please try again later."
            else:
                answer = f"Error: {str(e)}"

        ChatMessage.objects.create(session=session, role='assistant', content=str(answer))
        return Response({"response": str(answer)})

class FacultyChatAPI(APIView):
    authentication_classes = [] 
    permission_classes = []

    def post(self, request):
        faculty_email = request.session.get('faculty_email')
        if not faculty_email:
            return Response({"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)
        
        user = User.objects.filter(email=faculty_email).first()
        if not user:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        message_text = request.data.get("message")
        if not message_text:
            return Response({"error": "Message is required"}, status=status.HTTP_400_BAD_REQUEST)

        session, _ = ChatSession.objects.get_or_create(user=user, is_active=True)
        ChatMessage.objects.create(session=session, role='user', content=message_text)
        faculty_profile = get_object_or_404(FacultyProfile, user=user)
        
        try:
            agent = get_faculty_agent(faculty_profile.id)
            inputs = {"messages": [{"role": "user", "content": message_text}]}
            res = agent.invoke(inputs)
            
            messages = res.get("messages", [])
            answer = ""
            for msg in reversed(messages):
                if msg.type == 'ai' and msg.content:
                    extracted = extract_answer(msg.content)
                    if extracted.strip():
                        answer = extracted
                        break
            if not answer and messages:
                answer = extract_answer(messages[-1].content)
            
        except Exception as e:
            if is_rate_limit_error(e):
                if key_rotator.rotate():
                    try:
                        agent = get_faculty_agent(faculty_profile.id)
                        res = agent.invoke({"messages": [{"role": "user", "content": message_text}]})
                        answer = extract_answer(res["messages"][-1].content)
                    except:
                        answer = "High traffic. Please try again."
                else:
                    answer = "System at limit."
            else:
                answer = f"Error: {str(e)}"

        ChatMessage.objects.create(session=session, role='assistant', content=str(answer))
        return Response({"response": str(answer)})
