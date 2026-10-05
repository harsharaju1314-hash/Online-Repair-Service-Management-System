# System Architecture & Flowchart

## 1. High-Level Architecture

The **Online Repair Service Management System** follows a clean monolithic MVC pattern built on Python Flask with an embedded SQLite database engine.

```mermaid
graph TD
    Client["Client (Browser / REST Client)"]
    
    subgraph Flask_Application ["Flask Application Core"]
        AuthLayer["Authentication & Role Middleware (Session-Based)"]
        Routes["Web UI Routes & Templates (Jinja2)"]
        APILayer["REST API Endpoints (JSON)"]
        SLAMonitor["SLA Engine & State Machine Validator"]
        DBLayer["Data Access Layer (Parameterized SQLite Queries)"]
    end
    
    Database[("SQLite Database (app.db)")]
    Logs["Application Logs (app.log / stdout)"]

    Client --> AuthLayer
    AuthLayer --> Routes
    AuthLayer --> APILayer
    Routes --> SLAMonitor
    APILayer --> SLAMonitor
    SLAMonitor --> DBLayer
    DBLayer --> Database
    Routes --> Logs
    APILayer --> Logs
```

---

## 2. Request Lifecycle Workflow

```mermaid
stateDiagram-v2
    [*] --> REQUESTED: Customer Submits Request
    REQUESTED --> ASSIGNED: Staff Assigns Technician
    REQUESTED --> CANCELLED: Customer / Staff Cancels
    ASSIGNED --> SCHEDULED: Appointment Booked
    ASSIGNED --> CANCELLED: Request Cancelled
    SCHEDULED --> IN_PROGRESS: Technician Starts Work
    SCHEDULED --> CANCELLED: Appointment Cancelled
    IN_PROGRESS --> RESOLVED: Technician / Staff Marks Resolved
    RESOLVED --> CLOSED: Final Verification & Closure
    CLOSED --> [*]
    CANCELLED --> [*]
```

---

## 3. SLA Calculation Flow

```mermaid
flowchart TD
    Req["Incoming / Open Request"] --> TimeCalc["Compute Elapsed Time: (Current Time - Created Time)"]
    TimeCalc --> WindowCheck{"Elapsed Time vs SLA Target Window"}
    WindowCheck -- "Elapsed <= 75% Target" --> Within["Status: Within SLA (Normal)"]
    WindowCheck -- "Elapsed > 75% and <= 100% Target" --> Warning["Status: Approaching SLA (Warning)"]
    WindowCheck -- "Elapsed > 100% Target" --> Breached["Status: SLA Breached (Critical Escalation)"]
```

---

## 4. Deployment Pipeline Flow

```mermaid
flowchart LR
    Dev["Local Development"] --> GitPush["Git Push to GitHub"]
    GitPush --> CI["GitHub Actions CI"]
    CI --> Lint["Flake8 / Code Quality"]
    Lint --> Tests["Pytest (Unit & Integration)"]
    Tests --> DockerBuild["Docker Image Build"]
    DockerBuild --> Staging["Staging Container Launch"]
    Staging --> Health["GET /health Automated Verification"]
```
