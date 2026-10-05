"""SLA calculation logic unit tests."""

from datetime import datetime, timedelta
from app.sla import calculate_sla_status

def test_sla_within_target():
    """Verify that a newly created HIGH priority request is 'Within SLA'."""
    now = datetime(2026, 10, 5, 12, 0, 0)
    created_at = (now - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
    
    result = calculate_sla_status(created_at, priority="HIGH", current_time=now)
    assert result['status'] == 'Within SLA'
    assert result['is_breached'] is False
    assert result['is_approaching'] is False
    assert result['elapsed_hours'] == 2.0
    assert result['remaining_hours'] == 6.0

def test_sla_approaching_warning():
    """Verify that a request exceeding 75% of target window is 'Approaching SLA'."""
    now = datetime(2026, 10, 5, 12, 0, 0)
    # HIGH priority SLA = 8 hours. 7 hours elapsed is > 6 hours (75%)
    created_at = (now - timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S")
    
    result = calculate_sla_status(created_at, priority="HIGH", current_time=now)
    assert result['status'] == 'Approaching SLA'
    assert result['is_breached'] is False
    assert result['is_approaching'] is True
    assert result['badge_class'] == 'badge-warning'

def test_sla_breached():
    """Verify that a request exceeding target window is 'SLA Breached'."""
    now = datetime(2026, 10, 5, 12, 0, 0)
    # MEDIUM priority SLA = 24 hours. 26 hours elapsed -> Breached
    created_at = (now - timedelta(hours=26)).strftime("%Y-%m-%d %H:%M:%S")
    
    result = calculate_sla_status(created_at, priority="MEDIUM", current_time=now)
    assert result['status'] == 'SLA Breached'
    assert result['is_breached'] is True
    assert result['is_approaching'] is False
    assert result['badge_class'] == 'badge-danger'

def test_sla_resolved_request_uses_resolved_at_time():
    """Verify that once resolved, SLA elapsed time is fixed to resolved_at timestamp."""
    created_at = "2026-10-01 10:00:00"
    resolved_at = "2026-10-01 14:00:00"  # 4 hours later
    current_time = datetime(2026, 10, 10, 10, 0, 0) # Days later

    result = calculate_sla_status(created_at, priority="HIGH", resolved_at_str=resolved_at, current_time=current_time)
    assert result['elapsed_hours'] == 4.0
    assert result['status'] == 'Within SLA'
    assert result['is_breached'] is False
