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
import logging

logger = logging.getLogger(__name__)


def is_rate_limit_error(e):
    """Check if an exception is a Google API Rate Limit / quota error."""
    error_str = str(e).upper()
    return "RESOURCE_EXHAUSTED" in error_str or "429" in error_str or "QUOTA" in error_str


def extract_agent_answer(result):
    """
    Extract text answer from a LangGraph agent result.
    LangGraph returns: {"messages": [HumanMessage(...), AIMessage(...), ...]}
    The last AIMessage that has real text content is the answer.
    """
    messages = result.get("messages", [])
    if not messages:
        return "I'm sorry, I couldn't find an answer for that."

    # Walk backwards to find the last AI message with content
    for msg in reversed(messages):
        msg_type = getattr(msg, 'type', None) or type(msg).__name__.lower()
        content = getattr(msg, 'content', None)
        if 'ai' in msg_type.lower() and content:
            if isinstance(content, str) and content.strip():
                return content.strip()
            if isinstance(content, list):
                texts = [
                    block.get("text", "") if isinstance(block, dict) else str(block)
                    for block in content
                    if block
                ]
                text = " ".join(t for t in texts if t).strip()
                if text:
                    return text

    # Fallback: last message whatever it is
    last = messages[-1]
    content = getattr(last, 'content', '')
    if isinstance(content, str):
        return content.strip() or "I'm sorry, I couldn't find an answer for that."
    return "I'm sorry, I couldn't find an answer for that."


def run_agent(agent, message_text):
    """Invoke a LangGraph compiled graph and return clean text answer."""
    result = agent.invoke({"messages": [{"role": "user", "content": message_text}]})
    return extract_agent_answer(result)


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

        message_text = request.data.get("message", "").strip()
        if not message_text:
            return Response({"error": "Message is required"}, status=status.HTTP_400_BAD_REQUEST)

        session, _ = ChatSession.objects.get_or_create(user=user, is_active=True)
        ChatMessage.objects.create(session=session, role='user', content=message_text)
        student_profile = get_object_or_404(StudentProfile, user=user)

        answer = ""
        try:
            agent = get_student_agent(student_profile.id)
            answer = run_agent(agent, message_text)

        except Exception as e:
            if is_rate_limit_error(e):
                logger.warning(f"Rate limit hit for student chat. Rotating key. Error: {e}")
                if key_rotator.rotate():
                    try:
                        agent = get_student_agent(student_profile.id)
                        answer = run_agent(agent, message_text)
                    except Exception as retry_e:
                        logger.error(f"Retry failed after key rotation: {retry_e}")
                        answer = "I'm experiencing high traffic right now. Please try again in a moment."
                else:
                    answer = "The system is currently at its API limit. Please try again later."
            else:
                logger.error(f"Student chat error: {e}", exc_info=True)
                answer = f"An error occurred: {str(e)}"

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

        message_text = request.data.get("message", "").strip()
        if not message_text:
            return Response({"error": "Message is required"}, status=status.HTTP_400_BAD_REQUEST)

        session, _ = ChatSession.objects.get_or_create(user=user, is_active=True)
        ChatMessage.objects.create(session=session, role='user', content=message_text)
        faculty_profile = get_object_or_404(FacultyProfile, user=user)

        answer = ""
        try:
            agent = get_faculty_agent(faculty_profile.id)
            answer = run_agent(agent, message_text)

        except Exception as e:
            if is_rate_limit_error(e):
                logger.warning(f"Rate limit hit for faculty chat. Rotating key. Error: {e}")
                if key_rotator.rotate():
                    try:
                        agent = get_faculty_agent(faculty_profile.id)
                        answer = run_agent(agent, message_text)
                    except Exception as retry_e:
                        logger.error(f"Retry failed after key rotation: {retry_e}")
                        answer = "High traffic detected. Please try again shortly."
                else:
                    answer = "The system has reached its API limit. Please try again later."
            else:
                logger.error(f"Faculty chat error: {e}", exc_info=True)
                answer = f"An error occurred: {str(e)}"

        ChatMessage.objects.create(session=session, role='assistant', content=str(answer))
        return Response({"response": str(answer)})
