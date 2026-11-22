import pytest
from app.services.audit_service import AuditLogService


def test_audit_service_non_blocking_without_mongodb():
    # When MongoDB is unconfigured, audit logging succeeds safely and logs locally
    success = AuditLogService.log_event(
        event_type="TEST_EVENT",
        actor_id=1,
        entity_type="test_entity",
        entity_id=999,
        details={"action": "test", "password": "supersecretpassword123"},
    )
    assert success is True
