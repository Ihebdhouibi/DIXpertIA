# DIXpertIA – Enterprise IT Solutions Portal

## 📖 Overview

DIXpertIA is a full‑stack employee portal and admin dashboard for an IT services company.  
It features:

- Public corporate homepage with **Services**, **About**, and a full **Contact** page (with form + FAQ).
- Authentication (login/register) with role‑based views:
  - **Employee**: view payslips, submit leave requests, see team directory.
  - **Admin (HR)**: manage invoices, approve/reject leave requests, manage team members.
- Dynamic **notifications** (in English) that respect user roles:
  - Leave requests trigger a notification **only for admins**.
  - Approval/rejection triggers a notification **only for the employee**.
- Fully responsive UI with a persistent sidebar, mobile drawer, and notification bell.

---

## 🧰 Tech Stack

### Frontend
- **React 18** with **TypeScript**
- **Vite** – fast dev server and build tool
- **Tailwind CSS** – utility‑first styling (custom design tokens)
- **Lucide React** – icon library
- **Motion (Framer Motion)** – animations
- **LocalStorage** – client‑side data persistence (prototype/demo)

### Backend (FastAPI – Python)
- **FastAPI** – REST API framework
- **Uvicorn** – ASGI server
- **Pydantic** – data validation
- **SQLAlchemy** (optional – present in `app/` structure) – ORM
- **Alembic** – database migrations
- **JSON file** (`db.json`) – current storage (mock data)

### Gateway & Proxy
- **Node.js** + **Express** – serves the React build and proxies `/api` calls to the FastAPI backend.
- **Vite middleware** – serves the frontend in development.

### Database (future / optional)
- The `app/` folder contains SQLAlchemy models and Alembic migrations for PostgreSQL/MySQL, but the current active backend uses `main.py` with JSON storage.

---

## 📁 Project Structure
├── app/ # Modular FastAPI backend (SQLAlchemy, models, routers)
│ ├── core/ # config, database, security
│ ├── models/ # SQLAlchemy models
│ ├── routers/ # API endpoints
│ └── schemas/ # Pydantic schemas
├── alembic/ # Database migrations
├── src/ # React frontend
│ ├── components/ # All UI components (PayslipsView, LeaveRequestsView, TeamView, InvoicesView, Homepage, Registration, Sidebar)
│ ├── App.tsx # Main app with state & notifications
│ ├── data.ts # Initial seed data
│ └── types.ts # TypeScript types
├── main.py # Single‑file FastAPI entry point (used in production)
├── server.ts # Node.js gateway (Express + Vite middleware)
├── package.json # Node dependencies
├── requirements.txt # Python dependencies
├── .env.example # (removed) template for environment variables
└── README.md # Short intro

---

## 🔧 Setup & Running

### Prerequisites
- Node.js (v18+)
- Python 3.12+ (with pip)
- (Optional) PostgreSQL if you want to use the `app/` backend.

### 1. Clone the repository
```bash
git clone https://github.com/Ihebduhobi/DIXpertIA.git
cd DIXpertIA




### 2. Install frontend dependencies
'''bash
npm install  

### 3. Install Python dependencies
'''bash
pip install -r requirements.txt
##4. Run the full stack (development)
''bash
npm run dev


### 🌐 Public Homepage & Navigation
Unauthenticated users see the corporate homepage (Homepage.tsx).

Click "Employee Login" to enter the authentication flow (register / login).

After login, the user is redirected to their role‑appropriate dashboard:

Employee → Payslips

Admin → Invoices

The sidebar includes a "Home" button (without logging out) that returns to the public homepage while keeping the session active.

The homepage shows a "Go to Dashboard" button for logged‑in users.

### 🔔 Notifications System
Notifications are stored in localStorage and persist across sessions.

Each notification has a targetRole ('admin' or 'employee') to control visibility.

Leave request creation → notification targetRole: 'admin' (only admins see it).

Leave approval/rejection → notification targetRole: 'employee' (only the employee sees it).

The bell icon shows an unread count.

The popover displays the last 10 notifications with timestamps.

Clicking a notification with link: 'team' switches to the Team tab (for quick approval).

