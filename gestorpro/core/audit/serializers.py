from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = ['id', 'created_at', 'actor', 'actor_label', 'action', 'entity_type', 'entity_id',
                  'summary', 'changes', 'ip']
        read_only_fields = fields
