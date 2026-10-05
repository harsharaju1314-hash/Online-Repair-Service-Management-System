"""SLA Calculation and Monitoring Module.

Provides helper functions to calculate SLA deadlines, elapsed time,
remaining hours, and SLA compliance status based on ticket priority and creation time.
"""

from datetime import datetime, timezone

SLA_TARGET_HOURS = {
    "HIGH": 8,
    "MEDIUM": 24,
    "LOW": 48
}

def parse_iso_or_sql_timestamp(ts_str):
    """Parse SQLite or ISO timestamp string to a datetime object."""
    if not ts_str:
        return None
    if isinstance(ts_str, datetime):
        return ts_str
    
    # Try common SQLite formats
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S.%f"):
        try:
            return datetime.strptime(ts_str, fmt)
        except ValueError:
            continue
    # Fallback to string slicing if with timezone
    try:
        clean_str = ts_str.split(".")[0].replace("T", " ")
        return datetime.strptime(clean_str, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return datetime.utcnow()

def calculate_sla_status(created_at_str, priority="MEDIUM", resolved_at_str=None, current_time=None):
    """
    Calculate the SLA status for a given repair request.

    Returns a dict containing:
    - priority: str
    - sla_target_hours: int
    - elapsed_hours: float
    - remaining_hours: float
    - status: 'Within SLA' | 'Approaching SLA' | 'SLA Breached'
    - is_breached: bool
    - is_approaching: bool
    """
    target_hours = SLA_TARGET_HOURS.get(priority.upper(), 24)
    created_dt = parse_iso_or_sql_timestamp(created_at_str)
    
    if not created_dt:
        return {
            "priority": priority,
            "sla_target_hours": target_hours,
            "elapsed_hours": 0.0,
            "remaining_hours": float(target_hours),
            "status": "Within SLA",
            "is_breached": False,
            "is_approaching": False,
            "badge_class": "badge-success"
        }

    # Reference end time is either the resolution time (if resolved) or current time
    if resolved_at_str:
        end_dt = parse_iso_or_sql_timestamp(resolved_at_str)
    elif current_time:
        end_dt = current_time
    else:
        end_dt = datetime.now(timezone.utc).replace(tzinfo=None)

    elapsed_seconds = max(0, (end_dt - created_dt).total_seconds())
    elapsed_hours = round(elapsed_seconds / 3600.0, 2)
    remaining_hours = round(target_hours - elapsed_hours, 2)

    # 75% threshold for approaching SLA
    warning_threshold_hours = target_hours * 0.75

    if elapsed_hours > target_hours:
        sla_status = "SLA Breached"
        is_breached = True
        is_approaching = False
        badge_class = "badge-danger"
    elif elapsed_hours >= warning_threshold_hours:
        sla_status = "Approaching SLA"
        is_breached = False
        is_approaching = True
        badge_class = "badge-warning"
    else:
        sla_status = "Within SLA"
        is_breached = False
        is_approaching = False
        badge_class = "badge-success"

    return {
        "priority": priority,
        "sla_target_hours": target_hours,
        "elapsed_hours": elapsed_hours,
        "remaining_hours": remaining_hours,
        "status": sla_status,
        "is_breached": is_breached,
        "is_approaching": is_approaching,
        "badge_class": badge_class
    }
