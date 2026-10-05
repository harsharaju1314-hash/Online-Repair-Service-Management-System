# Agile Scrum Backlog & Sprint Planning

This document tracks the product backlog, user stories, acceptance criteria, and sprint allocations for the **Online Repair Service Management System**.

---

## Product Backlog

| Story ID | Epic | User Story | Priority | Estimate |
| :--- | :--- | :--- | :--- | :--- |
| **US-01** | Authentication | As a user, I want to register and log in with role-based access so my account is secure. | High | 3 pts |
| **US-02** | Customer | As a customer, I want to submit a repair request specifying category, details, and preferred date. | High | 3 pts |
| **US-03** | Customer | As a customer, I want to view my request list and track lifecycle status in real time. | Medium | 2 pts |
| **US-04** | Customer | As a customer, I want to cancel an open request if I no longer need the repair. | Medium | 2 pts |
| **US-05** | Service Staff | As staff, I want to triage incoming requests and assign available technicians. | High | 3 pts |
| **US-06** | Service Staff | As staff, I want to schedule service appointments and prevent double-booking. | High | 3 pts |
| **US-07** | Service Staff | As staff, I want to update request progress and add diagnostic notes until resolution. | High | 2 pts |
| **US-08** | Admin | As an admin, I want to manage categories, view all tickets, and monitor SLA compliance. | Medium | 3 pts |
| **US-09** | SLA Engine | As staff/admin, I want visual indicators for tickets within, approaching, or breaching SLA. | High | 3 pts |
| **US-10** | REST API | As a developer, I want REST API endpoints for automated integrations and status updates. | Medium | 3 pts |
| **US-11** | Quality Assurance | As an engineer, I want automated unit and integration tests covering all critical paths. | High | 3 pts |
| **US-12** | DevOps | As a DevOps engineer, I want a GitHub Actions CI pipeline and Dockerized staging deployment. | High | 3 pts |

---

## Sprint Breakdown

### Sprint 1: Foundation, Authentication & Database (Phase 1 & 2)
- **Goal**: Implement database schema, Flask application structure, user registration, role-based login, and session handling.
- **Stories**: US-01, US-02

### Sprint 2: Core Workflow & SLA Monitoring (Phase 3 & 4)
- **Goal**: Build request lifecycle state engine, technician dispatching, appointment scheduling, SLA calculation, and structured logging.
- **Stories**: US-03, US-04, US-05, US-06, US-07, US-08, US-09, US-10

### Sprint 3: Test Automation & DevOps Pipeline (Phase 5, 6 & 7)
- **Goal**: Implement pytest suite with high coverage, build Dockerfile, create GitHub Actions CI workflow, and create staging deployment scripts.
- **Stories**: US-11, US-12
