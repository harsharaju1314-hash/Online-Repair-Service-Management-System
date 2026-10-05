# REST API Specification

All API endpoints return JSON and accept JSON payloads (with `Content-Type: application/json`).
Session cookies or standard role permissions apply.

---

## Endpoints Overview

| Method | Endpoint | Description | Auth Required | Allowed Roles |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/health` | Application health and database connectivity | No | Public |
| `GET` | `/api/categories` | List active service categories | No | Public |
| `POST` | `/api/requests` | Submit a new repair request | Yes | `customer`, `admin` |
| `GET` | `/api/requests` | List repair requests (filtered by role) | Yes | `customer`, `staff`, `admin` |
| `GET` | `/api/requests/<id>` | Retrieve full details of a specific request | Yes | `customer` (owner), `staff`, `admin` |
| `PUT` | `/api/requests/<id>` | Update request details (priority, title, etc.) | Yes | `staff`, `admin` |
| `POST` | `/api/requests/<id>/assign` | Assign a technician to a request | Yes | `staff`, `admin` |
| `POST` | `/api/requests/<id>/schedule` | Schedule appointment for a request | Yes | `staff`, `admin` |
| `POST` | `/api/requests/<id>/status` | Advance status (`IN_PROGRESS`, `RESOLVED`, `CLOSED`) | Yes | `staff`, `admin` |
| `POST` | `/api/requests/<id>/cancel` | Cancel an eligible request | Yes | `customer` (owner), `admin` |
| `GET` | `/api/technicians` | List all technicians | Yes | `staff`, `admin` |

---

## Sample Request & Response Payloads

### 1. `GET /health`
**Response (200 OK):**
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2026-10-05T10:25:00Z"
}
```

### 2. `POST /api/requests`
**Request Body:**
```json
{
  "category_id": 1,
  "title": "Refrigerator Compressor Not Cooling",
  "description": "The fridge section is warm while freezer has frost buildup.",
  "preferred_date": "2026-10-10",
  "preferred_time_slot": "10:00 AM - 01:00 PM"
}
```
**Response (201 Created):**
```json
{
  "message": "Repair request created successfully",
  "request_id": 1,
  "status": "REQUESTED"
}
```

### 3. `POST /api/requests/1/assign`
**Request Body:**
```json
{
  "technician_id": 2,
  "priority": "HIGH"
}
```
**Response (200 OK):**
```json
{
  "message": "Technician assigned successfully",
  "request_id": 1,
  "assigned_technician_id": 2,
  "status": "ASSIGNED"
}
```
