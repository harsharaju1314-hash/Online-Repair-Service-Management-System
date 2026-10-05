# System Requirements Specification (SRS)
## Online Repair Service Management System

### 1. Business Problem
Customers seeking home and office appliance repairs face fragmented communication, unpredictable scheduling, and lack of visibility into service progress. Service centers struggle with manual technician dispatching, missed SLAs (Service Level Agreements), and disorganized repair records.

This application provides a centralized web-based platform to:
- Digitize customer repair submissions and appointment tracking.
- Streamline triage, priority assignment, and technician dispatching for service teams.
- Enforce clear SLA monitoring and status transition safeguards.

---

### 2. User Roles & Capabilities

| Role | Permissions & Actions |
| :--- | :--- |
| **Customer** | • Register and authenticate.<br>• Submit repair requests with service category, description, and preferred appointment time.<br>• View real-time status and lifecycle history of own requests.<br>• Cancel eligible requests before execution.<br>• View past service records. |
| **Service Staff** | • Login and view triage queues.<br>• Assign qualified technicians to requests.<br>• Schedule and manage service appointments.<br>• Advance request lifecycle (`ASSIGNED` → `SCHEDULED` → `IN_PROGRESS` → `RESOLVED`).<br>• Add diagnostic and repair notes. |
| **Administrator** | • Manage service categories (create/toggle active status).<br>• Manage user accounts and roles.<br>• Monitor SLA compliance, breached requests, and escalation metrics.<br>• Inspect system audit logs. |

---

### 3. Functional Requirements

1. **Authentication & Authorization**:
   - Secure registration with unique username and email.
   - Password hashing with salted PBKDF2/SHA256 via Werkzeug.
   - Session-based access control with role-based view and API protection.
2. **Request Lifecycle Engine**:
   - Defined states: `REQUESTED` → `ASSIGNED` → `SCHEDULED` → `IN_PROGRESS` → `RESOLVED` → `CLOSED` (or `CANCELLED`).
   - Validated state transitions preventing unauthorized or illogical jumps (e.g. `CLOSED` cannot jump straight to `IN_PROGRESS`).
3. **Technician & Appointment Management**:
   - Database-backed technician registry with specialization filters.
   - Conflict-aware appointment scheduling (prevents double-booking same technician in same time slot).
4. **SLA Monitoring**:
   - Priority-based SLA resolution windows:
     - `HIGH`: 8 hours
     - `MEDIUM`: 24 hours
     - `LOW`: 48 hours
   - Real-time SLA classification: `Within SLA`, `Approaching SLA` (within 25% of expiration), `SLA Breached`.
5. **REST API Interface**:
   - JSON endpoints for creating, listing, viewing, assigning, and resolving requests.
6. **Health Check**:
   - Standard `/health` endpoint returning database and application status.

---

### 4. Non-Functional Requirements

- **Maintainability**: Clear separation of concerns (Flask application factory, blueprints, database connection layer, services).
- **Security**: Parameterized SQL queries to eliminate SQL injection, secure session cookies, CSRF awareness, no credentials logged or committed.
- **Portability**: Standardized Docker container execution and dependency isolation.
- **Testability**: Comprehensive automated testing with pytest covering database models, authentication, business logic, SLA metrics, and HTTP responses.
- **Observability**: Structured application event logging (auth attempts, request status transitions, triage events, errors).
