"""Read-only admin audit feed. No mutation or historical backfill endpoint."""

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.pagination import paginate
from apps.inventory.models import InventoryAudit
from apps.inventory.permissions import IsInventoryAdmin


def record_inventory_change(user, entity, entity_id, after, before=None):
    # Ignore no-op edits. Actor comes from the authenticated request, never payload.
    if before == after:
        return
    InventoryAudit.objects.create(
        actor_id=str(user.pk),
        actor_name=user.get_username(),
        entity=entity,
        entity_id=entity_id,
        action="create" if before is None else "update",
        before=before,
        after=after,
    )


def serialize_audit(row):
    return {
        "id": str(row.id),
        "at": row.at.isoformat(),
        "actor_id": row.actor_id,
        "actor_name": row.actor_name,
        "entity": row.entity,
        "entity_id": str(row.entity_id),
        "action": row.action,
        "before": row.before,
        "after": row.after,
    }


class InventoryAuditListView(APIView):
    permission_classes = [IsAuthenticated, IsInventoryAdmin]

    def get(self, request):
        rows = InventoryAudit.objects.all()
        return Response(paginate(request.query_params, rows, serialize_audit))
