# Online Repair Service Management System

A web-based service management application built with Python Flask and SQLite, designed to streamline repair request tracking, technician dispatching, and SLA compliance monitoring.

---

## Overview

The **Online Repair Service Management System** provides a centralized platform for managing end-to-end repair operations. Customers can submit service requests, specify convenient time windows, and track progress in real time. Service staff and administrators can triage incoming tickets, assign qualified technicians, schedule appointments, and monitor Service Level Agreement (SLA) deadlines.

This project was built as a practical portfolio application for an **Associate DevOps Engineer** role, demonstrating core backend development, relational database modeling, automated testing with pytest, containerization with Docker, and CI/CD automation with GitHub Actions.

---

## Problem Statement

Small-to-medium repair service providers often face operational inefficiencies caused by:
1. **Unstructured Request Intake**: Requests submitted via phone calls or emails lack standardized issue descriptions and categorization.
2. **Scheduling Conflicts**: Manual dispatching frequently leads to double-booked technicians and missed appointments.
3. **Lack of SLA Visibility**: Without automated deadline tracking, high-priority issues breach target resolution times unnoticed.
4. **Poor Status Transparency**: Customers have no direct mechanism to track the lifecycle of their repair jobs.

This application resolves these issues by enforcing a strict state-machine workflow, conflict-checked scheduling, automated SLA tracking, and role-based access control.

---

## Key Features

- **Role-Based Access Control (RBAC)**:
  - **Customer**: Submit requests, select service category, choose preferred dates, track live request status, view service history, and cancel eligible requests.
  - **Service Staff**: Triage incoming tickets, assign available technicians, set ticket priority, schedule appointments with conflict prevention, update lifecycle states, and record diagnostic notes.
  - **Administrator**: Manage service categories, provision and manage user accounts, inspect system audit logs, and monitor SLA compliance metrics.
- **Controlled Request Lifecycle**:
  - Enforced transitions: `REQUESTED` &rarr; `ASSIGNED` &rarr; `SCHEDULED` &rarr; `IN_PROGRESS` &rarr; `RESOLVED` &rarr; `CLOSED`.
  - Safeguards prevent invalid state jumps (e.g., jumping from `REQUESTED` directly to `RESOLVED` or modifying `CLOSED` tickets).
- **Automated SLA Tracking Engine**:
  - Priority-based SLA resolution windows:
    - **High Priority**: 8 hours
    - **Medium Priority**: 24 hours
    - **Low Priority**: 48 hours
  - Real-time status indicators: `Within SLA`, `Approaching SLA` (when &ge;75% of target time has elapsed), and `SLA Breached`.
- **Technician & Appointment Scheduling**:
  - Technician registry with specialization mapping.
  - Conflict-prevention validation that prevents double-booking a technician for overlapping time slots.
- **RESTful API**:
  - JSON endpoints for creating, retrieving, updating, assigning, and resolving repair requests.
- **Audit Logging & Troubleshooting**:
  - Structured event logging for user authentication, ticket creation, technician assignments, status transitions, and cancellations.
- **Health Check Endpoint**:
  - Dedicated `GET /health` endpoint verifying database connectivity and service availability for container orchestration and uptime checks.

---

## Tech Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Backend** | Python 3.12, Flask 3.0.3, Werkzeug | Web application framework, routing, and session management |
| **Frontend** | HTML5, CSS3, JavaScript (ES6), Jinja2 | Responsive user interface, dashboards, and dynamic views |
| **Database** | SQLite 3 | Relational database with foreign key constraints and indexing |
| **Testing** | pytest 8.2.2 | Automated unit and integration test suite |
| **Linting** | flake8 7.1.0 | Code quality and syntax validation |
| **Containerization** | Docker | Containerized packaging, layer caching, and healthcheck |
| **CI/CD** | GitHub Actions | Automated build, lint, test, and Docker build pipeline |
| **Automation** | Bash | Deployment, health checking, and process lifecycle scripts |

---

## System Architecture & Workflow

### 1. Data Flow

$$\text{User / REST Client} \longrightarrow \text{Flask Router} \longrightarrow \text{Auth \& RBAC} \longrightarrow \text{Business Logic \& SLA Engine} \longrightarrow \text{Parameterized SQLite DB} \longrightarrow \text{Response}$$

### 2. Request Lifecycle State Machine

```
   [ Customer Submits ]
           │
           ▼
     ┌───────────┐
     │ REQUESTED │ ───────────────┐
     └───────────┘                │
           │                      │
           ▼ (Staff assigns tech) │
     ┌───────────┐                │
     │ ASSIGNED  │ ───────────────┤
     └───────────┘                │
           │                      │
           ▼ (Schedule appointment)
     ┌───────────┐                │
     │ SCHEDULED │ ───────────────┼───► [ CANCELLED ]
     └───────────┘                │
           │                      │
           ▼ (Work begins)        │
     ┌─────────────┐              │
     │ IN_PROGRESS │ ─────────────┘
     └─────────────┘
           │
           ▼ (Work completed)
     ┌───────────┐
     │ RESOLVED  │
     └───────────┘
           │
           ▼ (Staff verification)
     ┌───────────┐
     │  CLOSED   │
     └───────────┘
```

---

## Project Structure

```
Online-Repair-Service-Management-System/
├── .github/
│   └── workflows/
│       └── ci.yml               # GitHub Actions CI pipeline configuration
├── app/
│   ├── __init__.py              # Application factory, logging, and health endpoint
│   ├── api.py                   # REST API endpoints
│   ├── auth.py                  # Authentication, RBAC decorators, and audit logging
│   ├── config.py                # Environment configurations (Dev, Test, Prod)
│   ├── db.py                    # Database connection manager, schema runner, seeds
│   ├── routes.py                # Web UI route handlers for Customer, Staff, Admin
│   ├── sla.py                   # SLA calculation and threshold monitoring engine
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css        # Application UI stylesheet
│   │   └── js/
│   │       └── main.js          # Client-side form helpers
│   └── templates/
│       ├── base.html            # Master Jinja2 layout template
│       ├── auth/
│       │   ├── login.html       # Login page
│       │   └── register.html    # Customer registration page
│       ├── customer/
│       │   ├── dashboard.html   # Customer ticket dashboard
│       │   ├── new_request.html # Request submission form
│       │   └── view_request.html# Request detail & timeline view
│       ├── staff/
│       │   ├── dashboard.html   # Staff triage dashboard with SLA metrics
│       │   └── manage_request.html # Triage, dispatch, and lifecycle management
│       └── admin/
│           ├── dashboard.html   # Admin system metrics and SLA overview
│           ├── categories.html  # Service categories management
│           ├── users.html       # User provisioning and roles
│           └── logs.html        # System activity audit logs
├── docs/
│   ├── requirements.md          # System Requirements Specification (SRS)
│   ├── architecture.md          # Architecture and workflow documentation
│   ├── scrum_backlog.md         # Agile Scrum product backlog & user stories
│   └── api_spec.md              # REST API specification
├── scripts/
│   ├── start.sh                 # Linux startup script
│   ├── stop.sh                  # Graceful stop script
│   ├── health_check.sh          # Automated health check script with retries
│   └── deploy.sh                # Staging deployment script
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Pytest fixtures and mock authentication helper
│   ├── test_api.py              # REST API integration tests
│   ├── test_auth.py             # User authentication and registration tests
│   ├── test_health.py           # Health check endpoint test
│   ├── test_requests.py         # Request lifecycle, dispatch, and conflict tests
│   └── test_sla.py              # SLA calculation unit tests
├── .dockerignore
├── .env.example                 # Template for environment variables
├── .gitattributes
├── .gitignore
├── Dockerfile                   # Multi-stage production container configuration
├── pytest.ini                   # Pytest test discovery configuration
├── requirements.txt             # Pinned project dependencies
├── run.py                       # Local development entry point
└── schema.sql                   # SQLite relational database schema
```

---

## Database Schema

The database schema utilizes relational integrity, primary keys, foreign keys with cascading where appropriate, and check constraints:

1. **`users`**: Account credentials, email, hashed passwords, and assigned roles (`customer`, `staff`, `admin`).
2. **`service_categories`**: Available repair categories (`Appliance Repair`, `Electrical Repair`, `Plumbing`, `AC Service`).
3. **`technicians`**: Technician contact info, specializations, and availability flags.
4. **`repair_requests`**: Core ticket record including customer reference, category, priority, status, preferred schedule, assigned technician, and SLA targets.
5. **`appointments`**: Scheduled service time slots and technician booking records.
6. **`request_updates`**: Immutable audit timeline tracking every status change, note, and actor.
7. **`activity_logs`**: System-level audit events (logins, registrations, dispatching).

---

## REST API Endpoints

All API endpoints return and accept JSON payloads (`Content-Type: application/json`).

| Method | Endpoint | Purpose | Access Control |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Verify application and database health status | Public |
| `GET` | `/api/categories` | Retrieve list of active service categories | Public |
| `GET` | `/api/technicians` | Retrieve list of registered technicians | `staff`, `admin` |
| `GET` | `/api/requests` | List repair requests (filtered by user role) | Authenticated |
| `POST` | `/api/requests` | Submit a new repair request | `customer`, `admin` |
| `GET` | `/api/requests/<id>` | Get full details and history of a specific request | Owner / `staff` / `admin` |
| `PUT` | `/api/requests/<id>` | Update request priority, title, or description | `staff`, `admin` |
| `POST` | `/api/requests/<id>/assign` | Assign technician and set SLA priority | `staff`, `admin` |
| `POST` | `/api/requests/<id>/status` | Advance request status along valid lifecycle path | `staff`, `admin` |
| `POST` | `/api/requests/<id>/resolve` | Mark repair request as `RESOLVED` | `staff`, `admin` |
| `POST` | `/api/requests/<id>/cancel` | Cancel an eligible repair request | Owner / `admin` |

---

## Installation & Setup

### Prerequisites

- Python 3.10+ (Tested with Python 3.12)
- Git
- Docker (optional, for containerized execution)

### 1. Clone the Repository

```bash
git clone https://github.com/harsharaju1314-hash/Online-Repair-Service-Management-System.git
cd Online-Repair-Service-Management-System
```

### 2. Create and Activate Virtual Environment

```bash
# Linux / macOS
python3 -m venv venv
source venv/bin/activate

# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
# Copy template
cp .env.example .env
```

---

## Running the Application

### Running Locally with Python

```bash
python run.py
```
The application will start at `http://127.0.0.1:5000`. Default demo accounts will be initialized automatically:

| Role | Username | Password |
| :--- | :--- | :--- |
| **Administrator** | `admin` | `admin123` |
| **Service Staff** | `staff1` | `staff123` |
| **Customer** | `customer1` | `customer123` |

### Running with Docker

```bash
# Build the Docker image
docker build -t online-repair-service:latest .

# Run the container
docker run -d -p 5000:5000 --name repair-service online-repair-service:latest

# Verify health
curl http://127.0.0.1:5000/health
```

---

## Automated Testing

The project includes an automated test suite with **21 test cases** covering authentication, role-based views, request lifecycles, appointment scheduling conflict checks, SLA calculations, and REST API endpoints.

```bash
# Run pytest with standard output
pytest

# Run pytest with verbose details
pytest -v
```

### Test Coverage Summary

- `tests/test_health.py`: Verifies `/health` endpoint response and database ping.
- `tests/test_auth.py`: Tests user registration, input validation, duplicate handling, credential verification, session management, and protected route redirection.
- `tests/test_requests.py`: Tests ticket creation, technician assignment, appointment scheduling, double-booking prevention, valid state progression (`REQUESTED` &rarr; `ASSIGNED` &rarr; `IN_PROGRESS` &rarr; `RESOLVED` &rarr; `CLOSED`), and rejection of invalid transitions.
- `tests/test_sla.py`: Validates calculation of elapsed time, remaining SLA windows, and status flags across `HIGH`, `MEDIUM`, and `LOW` priorities.
- `tests/test_api.py`: Validates REST API responses, JSON schemas, authentication guards, and status code correctness (200, 201, 400, 401, 403, 404).

---

## CI/CD Pipeline (GitHub Actions)

The continuous integration pipeline is defined in `.github/workflows/ci.yml`. On every push and pull request to `master` and `main`:

1. **Environment Setup**: Provisions Python 3.12 on an Ubuntu runner with pip caching.
2. **Dependency Installation**: Installs all pinned dependencies from `requirements.txt`.
3. **Linting & Code Quality**: Executes `flake8` to enforce Python syntax and formatting standards.
4. **Test Suite Execution**: Runs `pytest -v` across all test modules (fails pipeline if any test fails).
5. **Docker Image Build**: Compiles the `Dockerfile` into a container image to ensure build reproducibility.
6. **Container Health Verification**: Launches the container in background mode and runs `curl --fail http://127.0.0.1:5000/health` to confirm liveness before passing.

---

## Deployment & Operational Scripts

The `scripts/` directory contains Bash scripts for Linux-based operational automation:

- **`scripts/start.sh`**: Exports environment configuration and starts the application server.
- **`scripts/stop.sh`**: Identifies running process PIDs and gracefully terminates the application.
- **`scripts/health_check.sh`**: Probes `GET /health` with configurable retries and delay intervals.
- **`scripts/deploy.sh`**: Automates the staging deployment cycle: runs tests &rarr; builds Docker image &rarr; stops previous container &rarr; starts new container &rarr; executes health check.

---

## Key Takeaways & What I Learned

1. **State Machine Design**: Enforcing request lifecycle transitions at both application and database levels prevents invalid workflows and inconsistent ticket states.
2. **Deterministic SLA Calculations**: Handling elapsed time comparisons with timezone-aware datetime objects ensures accurate SLA threshold tracking.
3. **Automated Test Design**: Writing isolated fixtures and integration tests in pytest catches regression bugs early and validates edge cases like appointment scheduling conflicts.
4. **Containerization Best Practices**: Using `.dockerignore`, dependency layer caching, and lightweight base images (`python:3.12-slim`) optimizes image build times and minimizes container footprints.
5. **CI/CD Reliability**: Integrating automated health check verification into the GitHub Actions pipeline guarantees that only functional container builds pass validation.

---

## Author

**Harsha Raju**  
Aspiring Associate DevOps Engineer  
GitHub: [@harsharaju1314-hash](https://github.com/harsharaju1314-hash)
