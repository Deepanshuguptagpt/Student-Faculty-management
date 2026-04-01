# Academiq: Student-Faculty Management System
**Project Architecture & Implementation Guide (Jury Documentation)**

> [!NOTE]
> This document is designed to guide a technical or non-technical jury through the architecture, technologies, and data flow of the Academiq platform. It explains how different components scale and communicate with each other.

---

## 1. Project Overview & Objective
Academiq is a centralized web portal designed to bridge the communication gap between students, faculty members, and college administration. It modernizes the academic workflow by providing dashboards for assignment tracking, attendance, resource sharing, and features deeply integrated **Agentic AI assistants** that can read database records and intelligently answer complex student and faculty queries.

## 2. Technology Stack
* **Backend Framework:** Python with Django (v4.2)
* **Frontend:** HTML5, CSS3, Vanilla JavaScript (No heavy frameworks, for maximum speed)
* **Database:** SQLite (Relational Database)
* **Artificial Intelligence:** Google Gemini (`gemini-2.5-flash`), orchestrated using LangChain & LangGraph.
* **Security:** Django Session Middleware, Password Hashing (`check_password`, `make_password`), CSRF Protection.

---

## 3. The Core Architecture & File Structure
The project follows Django's standard Application (App) architecture. If the jury asks to see specific code, navigate to these critical directories:

### A. The Routing Brain (`core/`)
* **`settings.py`**: The neural center of the project. Contains the database connection, timezone configurations, installed apps, and static/media file routing.
* **`urls.py`**: The master traffic controller that delegates incoming web requests to the specific sub-applications.

### B. The Application Logic (`backend/` & `authentication/`)
* **`authentication/views.py`**: Contains the `login_view` and `logout_view`. Demonstrates secure password hashing comparisons and session flushes.
* **`backend/student/views.py`**: Code for student functionalities (e.g., viewing assignments, tracking attendance).
* **`backend/faculty/views.py`**: Code for faculty functionalities (creating assignments, grading, uploading notes).
* **`backend/administration/views.py`**: Code for admin controls (creating accounts, defining courses).

### C. The AI Brain (`ai_assistant/`)
* **`assistant/student.py` & `assistant/faculty.py`**: *Show this to the jury!* Contains the custom LangChain AI Agents that convert human text into SQL queries and internal data fetchers.
* **`views.py`**: Acts as the bridge that connects the JavaScript frontend chat window to the LangChain backend.

### D. The User Interface (`templates/`)
* Contains the visual HTML structures. Separated cleanly into `dashboards/student/`, `dashboards/faculty/`, and `dashboards/admin/`.

---

## 4. How Data Flows: GET vs. POST Requests
Web applications communicate using HTTP Methods. Here is how we utilize them throughout Academiq to keep data secure:

### GET Requests (Reading Data)
A `GET` request is used whenever a user simply wants to *look* at a page without changing anything in the database. 
* **Example:** When a student clicks "View Assignments," the browser sends a `GET` request. Django intercepts this, reads the `Assignment` table in the SQLite database, filters it for that student's course, and injects that data into the HTML template before sending it back to the screen.

### POST Requests (Writing/Modifying Data)
A `POST` request is used whenever a user submits a form, uploads a file, or permanently alters the database. `POST` requests are strictly protected by a CSRF (Cross-Site Request Forgery) token to prevent hackers from submitting forms on behalf of the user.
* **Example 1 (Assignment Submission):** When a student uploads a PDF for an assignment and clicks "Submit," a `POST` request is fired. Django securely saves the PDF to the server's `/media/` folder, marks the assignment as "Submitted" in the database, and reloads the page.
* **Example 2 (Security):** Deleting a student or faculty member is *only* allowed via `POST` requests. This prevents accidental deletions from someone just copying and pasting a URL link.

---

## 5. How Features Interlink (The Ecosystem)

The strength of Academiq lies in its connected relational database setup (`models.py`). 

1. **Authentication to Dashboards:** When a user logs in (POST), Django creates a secure Session ID cookie. When the user navigates to their dashboard (GET), Django checks this cookie against custom decorators like `@student_login_required`. If the cookie is missing or belongs to a different role, access is explicitly denied.
2. **Faculty to Student Data Flow:** When a Faculty member creates an Assignment (POST), it is tagged with a specific `Year` and `Branch`. The Student dashboard automatically queries and filters (GET) for assignments matching *their* specific Year and Branch profile. 
3. **The AI Chatbot Integration:**
   * A student types a question: *"How many lectures was I absent for in March?"*
   * The frontend sends an asynchronous `POST` (AJAX) request containing the text to the `ai_assistant` view.
   * The Django View passes the text and the Student's unique ID to the LangChain Agent.
   * The Agent realizes it needs attendance data, calls the internal `get_absent_lectures` Python tool to query the SQLite database, formats the answer, and sends it back to the frontend as a JSON response.

## 6. Highlighted Technical Achievements for the Jury
When presenting, be sure to highlight these advanced engineering decisions:
* **The "Agentic" AI:** The AI doesn't just chat; it uses "Tools" to read live database schema. It knows precisely who is logged in and tailors the answers specifically to their data.
* **Enterprise Security:** Passwords are never stored in plaintext. They are mathematically hashed using advanced Django algorithms. Destructive workflows are strictly protected by server-side POST validations.
* **Deployment Ready:** Strict separation of Static Files (CSS/JS) and Media Files (Uploads), making the application ready to be hosted on production cloud servers like AWS, PythonAnywhere, or DigitalOcean without architecture rewrites.
