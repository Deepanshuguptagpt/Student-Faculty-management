"""
Assignment Evaluator Agent — AI-Powered Auto-Grading

Runs after assignment deadlines pass. For each eligible assignment:
1. Extracts content from student submissions (digital PDFs, handwritten/scanned PDFs, DOCX)
2. Evaluates using Gemini AI with a lenient, student-friendly grading policy
3. Saves grades to DB (AssignmentSubmission.grade, .feedback, .ai_confidence)
4. Generates an Excel report and emails it to the faculty

Grading Philosophy (LENIENT):
- If a student answers correctly and covers all points → FULL MARKS
- Diagrams are only required when explicitly asked; voluntary relevant diagrams are appreciated, never penalized
- Extra effort (additional explanations, examples) is rewarded, never penalized
- Benefit of the doubt always goes to the student
"""

import json
import os
import logging
import traceback
from io import BytesIO
from datetime import datetime

import pandas as pd
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import EmailMessage
from django.conf import settings

from backend.faculty.models import (
    Assignment, AssignmentSubmission, AssignmentEvaluationLog
)
from backend.student.models import StudentProfile, Enrollment
from ai_assistant.utils import key_rotator

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────────────
# Content Extraction Utilities
# ────────────────────────────────────────────────────────────────────────────────

def extract_text_from_pdf(file_path):
    """Extract text from a digital (non-scanned) PDF using pypdf."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text.strip())
        return "\n\n".join(text_parts)
    except Exception as e:
        logger.warning(f"pypdf text extraction failed: {e}")
        return ""


def extract_text_from_docx(file_path):
    """Extract text from a Word document."""
    try:
        from docx import Document
        doc = Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
    except Exception as e:
        logger.warning(f"python-docx extraction failed: {e}")
        return ""


def convert_pdf_to_images(file_path):
    """Convert PDF pages to PIL images for Gemini Vision analysis."""
    try:
        from pdf2image import convert_from_path
        images = convert_from_path(file_path, dpi=200, first_page=1, last_page=10)
        return images
    except Exception as e:
        logger.warning(f"pdf2image conversion failed (Poppler may not be installed): {e}")
        return []


def extract_content_from_file(file_path):
    """
    Smart content extraction:
    1. Try text extraction first (digital PDF / DOCX)
    2. If text is too short (likely scanned/handwritten), fall back to images
    Returns: (text_content: str, images: list[PIL.Image], is_handwritten: bool)
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext in ('.docx', '.doc'):
        text = extract_text_from_docx(file_path)
        return text, [], False

    if ext == '.pdf':
        text = extract_text_from_pdf(file_path)
        # If we got meaningful text (>50 chars), it's a digital PDF
        if len(text.strip()) > 50:
            return text, [], False
        # Otherwise, likely scanned/handwritten — try image conversion
        images = convert_pdf_to_images(file_path)
        if images:
            return text, images, True
        # If image conversion also fails, return whatever text we got
        return text, [], False

    # Fallback for other file types
    return "", [], False


# ────────────────────────────────────────────────────────────────────────────────
# AI Evaluation
# ────────────────────────────────────────────────────────────────────────────────

def build_evaluation_prompt(assignment, extracted_text, max_marks, rubric_text):
    """Build the evaluation prompt with lenient grading philosophy."""
    rubric_section = f"""
FACULTY'S ANSWER KEY / RUBRIC (use this as reference for accuracy):
{rubric_text}
""" if rubric_text else "No rubric/answer key provided by faculty. Use your own subject knowledge to assess accuracy."

    return f"""You are a LENIENT and FAIR academic evaluator for a university assignment.

ASSIGNMENT DETAILS:
- Title: {assignment.title}
- Course: {assignment.course.name} ({assignment.course.code})
- Description/Instructions: {assignment.description or 'Not provided'}
- Maximum Marks: {max_marks}

{rubric_section}

STUDENT'S SUBMISSION:
{extracted_text}

GRADING PHILOSOPHY (VERY IMPORTANT — FOLLOW STRICTLY):
1. BE LENIENT. The faculty wants students to score well.
2. If the student has answered correctly and covered the key points → give FULL MARKS for that question.
3. Diagrams are ONLY required when EXPLICITLY asked in the question. If not asked, do NOT deduct marks for missing diagrams.
4. If the student voluntarily draws a RELEVANT diagram (even when not asked), DO NOT deduct marks. Appreciate the extra effort — give the same or slightly better marks.
5. Extra explanations, examples, or additional relevant information should NEVER be penalized. Reward effort.
6. Benefit of the doubt ALWAYS goes to the student.
7. Only deduct marks for: genuinely wrong/incorrect answers, completely missing answers, or clearly irrelevant content.
8. Partial answers that show understanding should get proportional marks, leaning generous.

EVALUATION CRITERIA (weighted):
1. Relevance (20%): Does the answer address the question asked?
2. Accuracy (25%): Are the facts, concepts, and explanations correct?
3. Completeness (25%): Are all parts of the question answered?
4. Depth & Understanding (20%): Does the student demonstrate genuine understanding?
5. Presentation (10%): Is the answer reasonably well-organized?

RESPOND ONLY WITH VALID JSON (no markdown, no code blocks, no extra text):
{{"marks": <integer from 0 to {max_marks}>, "feedback": "<constructive 2-3 sentence feedback>", "confidence": "<high or medium or low>"}}
"""


def evaluate_with_text(llm, assignment, text_content, max_marks, rubric_text):
    """Evaluate a text-based submission using Gemini."""
    from langchain_core.messages import SystemMessage, HumanMessage

    prompt = build_evaluation_prompt(assignment, text_content, max_marks, rubric_text)

    response = llm.invoke([
        SystemMessage(content="You are a lenient, fair academic evaluator. Always respond with valid JSON only."),
        HumanMessage(content=prompt)
    ])

    return parse_ai_response(response.content, max_marks)


def evaluate_with_vision(assignment, images, max_marks, rubric_text, text_hint=""):
    """Evaluate handwritten submissions using Gemini Vision API directly."""
    import google.genai as genai
    from PIL import Image

    api_key = key_rotator.get_current_key()
    if not api_key:
        return None, "No API key available", "low"

    client = genai.Client(api_key=api_key)

    rubric_section = f"""
FACULTY'S ANSWER KEY / RUBRIC:
{rubric_text}
""" if rubric_text else "No rubric provided. Use your subject knowledge."

    prompt = f"""You are a LENIENT and FAIR academic evaluator. Analyze the handwritten student submission shown in the images below.

ASSIGNMENT DETAILS:
- Title: {assignment.title}
- Course: {assignment.course.name} ({assignment.course.code})
- Description/Instructions: {assignment.description or 'Not provided'}
- Maximum Marks: {max_marks}

{rubric_section}

{f"Partial text extracted: {text_hint}" if text_hint else ""}

GRADING PHILOSOPHY (FOLLOW STRICTLY):
1. BE LENIENT. Give benefit of the doubt to the student.
2. If the answer is correct and covers key points → FULL MARKS.
3. Diagrams only required when explicitly asked. Voluntary relevant diagrams are appreciated, never penalized.
4. Extra effort is rewarded, never penalized.
5. Only deduct for genuinely wrong, missing, or irrelevant content.
6. If handwriting is unclear but you can infer the meaning, give benefit of the doubt.

First, READ the handwritten text in the images carefully. Then evaluate:
1. Relevance (20%): On-topic?
2. Accuracy (25%): Correct facts?
3. Completeness (25%): All parts answered?
4. Depth (20%): Shows understanding?
5. Presentation (10%): Reasonably organized?

RESPOND ONLY WITH VALID JSON:
{{"marks": <integer 0 to {max_marks}>, "feedback": "<2-3 sentences>", "confidence": "<high or medium or low>"}}
"""

    # Build content parts: text prompt + images (limit to first 5 pages)
    contents = [prompt]
    for img in images[:5]:
        contents.append(img)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents
    )

    return parse_ai_response(response.text, max_marks)


def parse_ai_response(raw_text, max_marks):
    """Parse the AI's JSON response, handling markdown formatting and edge cases."""
    text = raw_text.strip()

    # Strip markdown code blocks if present
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    try:
        data = json.loads(text)
        marks = int(data.get("marks", 0))
        marks = max(0, min(marks, max_marks))  # Clamp to valid range
        feedback = str(data.get("feedback", "No feedback provided."))
        confidence = str(data.get("confidence", "medium")).lower()
        if confidence not in ("high", "medium", "low"):
            confidence = "medium"
        return marks, feedback, confidence
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        logger.warning(f"Failed to parse AI response: {e}. Raw: {text[:200]}")
        return None, f"AI evaluation failed to parse. Raw response: {text[:200]}", "low"


# ────────────────────────────────────────────────────────────────────────────────
# Management Command
# ────────────────────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = 'AI-powered auto-grading agent: evaluates submissions after assignment deadlines pass and emails Excel reports to faculty.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force', action='store_true',
            help='Force evaluate ALL past-due assignments even if already evaluated (for testing)'
        )

    def handle(self, *args, **options):
        now = timezone.now()
        self.stdout.write(f"{'='*60}")
        self.stdout.write(f"Assignment Evaluator Agent started at {now}")
        self.stdout.write(f"{'='*60}")

        # Find eligible assignments:
        # - deadline has passed
        # - online submissions only
        # - AI evaluation enabled
        # - not yet evaluated (unless --force)
        eligible_assignments = Assignment.objects.filter(
            due_datetime__lt=now,
            submission_mode='online',
            enable_ai_evaluation=True,
        )

        if not options['force']:
            already_evaluated_ids = AssignmentEvaluationLog.objects.values_list(
                'assignment_id', flat=True
            )
            eligible_assignments = eligible_assignments.exclude(
                id__in=already_evaluated_ids
            )

        if not eligible_assignments.exists():
            self.stdout.write(self.style.WARNING("No assignments pending evaluation. Exiting."))
            return

        self.stdout.write(f"Found {eligible_assignments.count()} assignment(s) to evaluate.\n")

        for assignment in eligible_assignments:
            try:
                self.evaluate_assignment(assignment)
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f"FAILED to evaluate '{assignment.title}': {e}"
                ))
                logger.error(f"Evaluator error for assignment {assignment.id}: {traceback.format_exc()}")

        self.stdout.write(self.style.SUCCESS("\nAssignment Evaluator Agent completed."))

    def evaluate_assignment(self, assignment):
        """Evaluate all submissions for a single assignment."""
        self.stdout.write(f"\n{'─'*50}")
        self.stdout.write(f"Evaluating: {assignment.title}")
        self.stdout.write(f"Course: {assignment.course.code} | Max Marks: {assignment.max_marks}")
        self.stdout.write(f"{'─'*50}")

        submissions = AssignmentSubmission.objects.filter(
            assignment=assignment
        ).select_related('student__user')

        if not submissions.exists():
            self.stdout.write(self.style.WARNING("  No submissions found. Skipping."))
            return

        # Extract the faculty's question/rubric from their attachment
        faculty_instructions = self._extract_faculty_instructions(assignment)
        rubric_text = assignment.rubric or ""
        if faculty_instructions:
            rubric_text = f"{rubric_text}\n\nFACULTY ATTACHMENT CONTENT:\n{faculty_instructions}" if rubric_text else faculty_instructions

        max_marks = assignment.max_marks

        # Prepare LLM for text-based evaluations
        from langchain_google_genai import ChatGoogleGenerativeAI
        api_key = key_rotator.get_current_key()
        llm_kwargs = {"model": "gemini-2.5-flash", "temperature": 0.3}
        if api_key:
            llm_kwargs["google_api_key"] = api_key
        llm = ChatGoogleGenerativeAI(**llm_kwargs)

        results = []
        evaluated_count = 0

        for submission in submissions:
            self.stdout.write(f"\n  📄 Student: {submission.student.user.name} ({submission.student.enrollment_number})")

            # Extract content from student's submission
            text_content, images, is_handwritten = "", [], False

            if submission.attachment:
                file_path = submission.attachment.path
                if os.path.exists(file_path):
                    text_content, images, is_handwritten = extract_content_from_file(file_path)
                    self.stdout.write(f"     Content: {'Handwritten/Scanned' if is_handwritten else 'Digital'} | Text length: {len(text_content)} chars | Images: {len(images)}")
                else:
                    self.stdout.write(self.style.WARNING(f"     File not found: {file_path}"))

            # Also include any text content from the submission form
            if submission.content:
                text_content = f"{submission.content}\n\n{text_content}" if text_content else submission.content

            if not text_content and not images:
                self.stdout.write(self.style.WARNING("     No content to evaluate. Skipping."))
                results.append({
                    'Student Name': submission.student.user.name,
                    'Enrollment Number': submission.student.enrollment_number,
                    'Submission Date': submission.submitted_at.strftime('%Y-%m-%d %H:%M'),
                    'Marks': 'N/A',
                    'Out Of': max_marks,
                    'Feedback': 'No evaluable content found in submission.',
                    'AI Confidence': 'N/A',
                })
                continue

            # Evaluate using AI
            marks, feedback, confidence = None, "", "low"

            try:
                if is_handwritten and images:
                    # Use Gemini Vision for handwritten content
                    self.stdout.write("     Using Gemini Vision for handwritten evaluation...")
                    marks, feedback, confidence = evaluate_with_vision(
                        assignment, images, max_marks, rubric_text, text_hint=text_content
                    )
                else:
                    # Use text-based evaluation
                    self.stdout.write("     Using text-based AI evaluation...")
                    marks, feedback, confidence = evaluate_with_text(
                        llm, assignment, text_content, max_marks, rubric_text
                    )
            except Exception as e:
                error_msg = str(e)
                # Try key rotation on quota errors
                if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                    if key_rotator.rotate():
                        api_key = key_rotator.get_current_key()
                        llm_kwargs["google_api_key"] = api_key
                        llm = ChatGoogleGenerativeAI(**llm_kwargs)
                        try:
                            if is_handwritten and images:
                                marks, feedback, confidence = evaluate_with_vision(
                                    assignment, images, max_marks, rubric_text, text_hint=text_content
                                )
                            else:
                                marks, feedback, confidence = evaluate_with_text(
                                    llm, assignment, text_content, max_marks, rubric_text
                                )
                        except Exception as retry_err:
                            self.stdout.write(self.style.ERROR(f"     Retry failed: {retry_err}"))
                            feedback = f"AI evaluation error after retry: {retry_err}"
                else:
                    self.stdout.write(self.style.ERROR(f"     Evaluation error: {e}"))
                    feedback = f"AI evaluation error: {e}"

            # Save to database
            if marks is not None:
                submission.grade = str(marks)
                submission.feedback = feedback
                submission.ai_confidence = confidence
                submission.save()
                evaluated_count += 1
                self.stdout.write(self.style.SUCCESS(
                    f"     ✅ Grade: {marks}/{max_marks} | Confidence: {confidence}"
                ))
            else:
                self.stdout.write(self.style.WARNING(f"     ⚠️ Could not evaluate. Feedback: {feedback[:100]}"))

            results.append({
                'Student Name': submission.student.user.name,
                'Enrollment Number': submission.student.enrollment_number,
                'Submission Date': submission.submitted_at.strftime('%Y-%m-%d %H:%M'),
                'Marks': marks if marks is not None else 'Error',
                'Out Of': max_marks,
                'Feedback': feedback,
                'AI Confidence': confidence,
            })

        # Generate Excel and email to faculty
        if results:
            self._send_excel_report(assignment, results, evaluated_count)

        # Log evaluation
        AssignmentEvaluationLog.objects.update_or_create(
            assignment=assignment,
            defaults={
                'total_evaluated': evaluated_count,
                'report_sent': True,
            }
        )

        self.stdout.write(self.style.SUCCESS(
            f"\n  ✅ Completed: {evaluated_count}/{len(results)} submissions evaluated for '{assignment.title}'"
        ))

    def _extract_faculty_instructions(self, assignment):
        """Extract text from the faculty's assignment attachment (question paper)."""
        if not assignment.attachment:
            return ""

        file_path = assignment.attachment.path
        if not os.path.exists(file_path):
            return ""

        text, images, is_handwritten = extract_content_from_file(file_path)

        # For faculty attachments with images, try to get text via vision
        if is_handwritten and images and not text:
            try:
                import google.genai as genai
                api_key = key_rotator.get_current_key()
                if api_key:
                    client = genai.Client(api_key=api_key)
                    contents = [
                        "Extract all text from these assignment question/instruction pages. Return ONLY the extracted text, nothing else.",
                    ]
                    for img in images[:5]:
                        contents.append(img)

                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=contents
                    )
                    text = response.text
            except Exception as e:
                logger.warning(f"Vision extraction for faculty attachment failed: {e}")

        return text[:5000] if text else ""  # Cap at 5000 chars

    def _send_excel_report(self, assignment, results, evaluated_count):
        """Generate Excel report and email to faculty."""
        faculty_email = assignment.faculty.user.email
        faculty_name = assignment.faculty.user.name

        df = pd.DataFrame(results)
        excel_buffer = BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='AI Evaluation Results')

            # Auto-adjust column widths
            worksheet = writer.sheets['AI Evaluation Results']
            for column_cells in worksheet.columns:
                max_length = 0
                column_letter = column_cells[0].column_letter
                for cell in column_cells:
                    try:
                        if cell.value:
                            max_length = max(max_length, len(str(cell.value)))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 60)
                worksheet.column_dimensions[column_letter].width = adjusted_width

        excel_buffer.seek(0)

        # Compute stats
        valid_marks = [r['Marks'] for r in results if isinstance(r['Marks'], (int, float))]
        avg_marks = sum(valid_marks) / len(valid_marks) if valid_marks else 0
        max_achieved = max(valid_marks) if valid_marks else 0
        min_achieved = min(valid_marks) if valid_marks else 0

        email_body = f"""Dear {faculty_name},

The AI Evaluation Agent has completed automatic grading for your assignment:

📋 Assignment: {assignment.title}
📚 Course: {assignment.course.name} ({assignment.course.code})
📊 Max Marks: {assignment.max_marks}

Results Summary:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Total Submissions: {len(results)}
• Successfully Evaluated: {evaluated_count}
• Average Marks: {avg_marks:.1f}/{assignment.max_marks}
• Highest: {max_achieved}/{assignment.max_marks}
• Lowest: {min_achieved}/{assignment.max_marks}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The detailed evaluation report is attached as an Excel file. Each student's marks, feedback, and AI confidence level are included.

📌 Note: These marks have been automatically saved to the portal. You can review and override any grade from the Assignment Detail page on your dashboard.

Regards,
Academiq AI Evaluation Agent
"""

        email = EmailMessage(
            subject=f"AI Evaluation Report: {assignment.title} — {assignment.course.code}",
            body=email_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[faculty_email],
        )

        file_name = f"AI_Evaluation_{assignment.title.replace(' ', '_')[:40]}.xlsx"
        email.attach(file_name, excel_buffer.getvalue(),
                     'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

        try:
            email.send(fail_silently=False)
            self.stdout.write(self.style.SUCCESS(f"  📧 Excel report emailed to {faculty_email}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ❌ Failed to email report: {e}"))
            logger.error(f"Email send failed: {e}")
