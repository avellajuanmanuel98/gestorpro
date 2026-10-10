from django.db.models import Count, Sum
from rest_framework import serializers

from gestorpro.kernel.money import ZERO, money_str

from . import services
from .models import CashMovement, CashRegister, CashSession


class CashRegisterSerializer(serializers.ModelSerializer):
    location_name = serializers.CharField(source='location.name', read_only=True)
    open_session_by = serializers.SerializerMethodField()

    class Meta:
        model = CashRegister
        fields = ['id', 'name', 'location', 'location_name', 'is_active', 'open_session_by']

    def get_open_session_by(self, obj):
        session = obj.sessions.filter(status=CashSession.Status.OPEN).select_related('opened_by').first()
        return _user_name(session.opened_by) if session else None


class CashMovementSerializer(serializers.ModelSerializer):
    type_label = serializers.CharField(source='get_type_display', read_only=True)
    created_by_name = serializers.SerializerMethodField()
    sale_number = serializers.CharField(source='sale.number', read_only=True, default=None)

    class Meta:
        model = CashMovement
        fields = ['id', 'type', 'type_label', 'amount', 'reason', 'sale_number', 'created_by_name', 'created_at']

    def get_created_by_name(self, obj):
        return obj.created_by.full_name or obj.created_by.email


def _user_name(user):
    return (user.full_name or user.email) if user else None


class CashSessionSerializer(serializers.ModelSerializer):
    register_name = serializers.CharField(source='register.name', read_only=True)
    opened_by_name = serializers.SerializerMethodField()
    closed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = CashSession
        fields = ['id', 'register', 'register_name', 'status', 'opened_by_name', 'opened_at', 'opening_amount',
                  'closed_by_name', 'closed_at', 'expected_amount', 'counted_amount', 'difference', 'closing_note']
        read_only_fields = fields

    def get_opened_by_name(self, obj):
        return _user_name(obj.opened_by)

    def get_closed_by_name(self, obj):
        return _user_name(obj.closed_by)


class CashSessionDetailSerializer(CashSessionSerializer):
    """Turno con su resumen: lo que debería haber en el cajón y las ventas por medio de pago."""
    summary = serializers.SerializerMethodField()
    movements = CashMovementSerializer(many=True, read_only=True)

    class Meta(CashSessionSerializer.Meta):
        fields = CashSessionSerializer.Meta.fields + ['denominations', 'summary', 'movements']
        read_only_fields = fields

    def get_summary(self, obj):
        from gestorpro.core.sales.models import Payment, Sale

        by_type = {r['type']: r['t'] for r in obj.movements.values('type').annotate(t=Sum('amount'))}
        completed = obj.sales.filter(status=Sale.Status.COMPLETED)
        totals = completed.aggregate(count=Count('id'), total=Sum('total'))
        by_method = (Payment.objects.filter(sale__cash_session=obj, sale__status=Sale.Status.COMPLETED)
                     .values('method__name', 'method__kind').annotate(total=Sum('amount')).order_by('-total'))
        return {
            'opening': money_str(obj.opening_amount),
            'cash_sales': money_str(by_type.get('sale', ZERO)),
            'voids': money_str(by_type.get('void', ZERO)),
            'income': money_str(by_type.get('income', ZERO)),
            'expenses': money_str(by_type.get('expense', ZERO)),
            'withdrawals': money_str(by_type.get('withdrawal', ZERO)),
            'expected': money_str(services.expected_amount(obj) if obj.is_open else obj.expected_amount),
            'sales_count': totals['count'],
            'sales_total': money_str(totals['total'] or ZERO),
            'voided_count': obj.sales.filter(status=Sale.Status.VOIDED).count(),
            'by_method': [{'method': r['method__name'], 'kind': r['method__kind'], 'total': money_str(r['total'])}
                          for r in by_method],
            'tolerance': money_str(services.tolerance()),
        }


class OpenSessionSerializer(serializers.Serializer):
    register = serializers.PrimaryKeyRelatedField(queryset=CashRegister.objects)
    opening_amount = serializers.DecimalField(max_digits=14, decimal_places=2)


class MovementInputSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=[(t, t) for t in CashMovement.MANUAL_TYPES])
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    reason = serializers.CharField(max_length=200)


class CloseSessionSerializer(serializers.Serializer):
    counted_amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    denominations = serializers.DictField(child=serializers.IntegerField(min_value=0), required=False)
    note = serializers.CharField(max_length=500, required=False, allow_blank=True)
