"""Admin activity logging helper."""
from flask import request
from flask_login import current_user

from app.extensions import db
from app.models.business import ActivityLog


def log_action(action, entity=None, entity_id=None, description=None):
    """Record an action in the activity log table.

    Args:
        action: short verb, e.g. 'create', 'update', 'delete', 'login'
        entity: model/entity name, e.g. 'product', 'order', 'user'
        entity_id: primary key of the affected record
        description: human-readable description of the action
    """
    user = current_user if current_user.is_authenticated else None
    log = ActivityLog(
        user_id=user.id if user else None,
        user_name=user.full_name if user else 'Anonymous',
        action=action,
        entity=entity,
        entity_id=entity_id,
        description=description,
        ip_address=request.remote_addr if request else None,
    )
    db.session.add(log)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
