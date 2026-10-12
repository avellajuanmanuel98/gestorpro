from rest_framework import serializers

from gestorpro.core.tenancy.models import Tenant
from gestorpro.platform.subscriptions.models import Plan, Subscription

from .models import PlatformEvent
from .services import effective_status


class TenantRowSerializer(serializers.ModelSerializer):
    plan = serializers.SerializerMethodField()
    subscription_status = serializers.SerializerMethodField()
    trial_ends_at = serializers.SerializerMethodField()
    current_period_end = serializers.SerializerMethodField()
    members = serializers.IntegerField(read_only=True, default=0)
    last_activity = serializers.DateTimeField(read_only=True)
    last_sale = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Tenant
        fields = ['id', 'name', 'slug', 'vertical', 'status', 'city', 'tax_id', 'email', 'phone', 'modules',
                  'created_at', 'plan', 'subscription_status', 'trial_ends_at', 'current_period_end',
                  'members', 'last_activity', 'last_sale']

    def _sub(self, obj):
        return getattr(obj, 'subscription', None)

    def get_plan(self, obj):
        sub = self._sub(obj)
        return {'code': sub.plan.code, 'name': sub.plan.name} if sub else None

    def get_subscription_status(self, obj):
        return effective_status(self._sub(obj))

    def get_trial_ends_at(self, obj):
        sub = self._sub(obj)
        return sub.trial_ends_at.isoformat() if sub and sub.trial_ends_at else None

    def get_current_period_end(self, obj):
        sub = self._sub(obj)
        return sub.current_period_end.isoformat() if sub and sub.current_period_end else None


class OnboardSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    owner_email = serializers.EmailField()
    vertical = serializers.ChoiceField(choices=Tenant.Vertical.choices)
    plan = serializers.SlugField()
    city = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    tax_id = serializers.CharField(max_length=30, required=False, allow_blank=True, default='')


class TenantStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Tenant.Status.choices)
    reason = serializers.CharField(max_length=300, required=False, allow_blank=True, default='')


class SubscriptionChangeSerializer(serializers.Serializer):
    plan = serializers.SlugField(required=False)
    status = serializers.ChoiceField(choices=Subscription.Status.choices, required=False)
    trial_ends_at = serializers.DateTimeField(required=False, allow_null=True)
    current_period_end = serializers.DateTimeField(required=False, allow_null=True)
    note = serializers.CharField(max_length=200, required=False, allow_blank=True, default='')


class ReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=300)


class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PlanSerializer(serializers.ModelSerializer):
    features = serializers.SerializerMethodField()
    limits = serializers.SerializerMethodField()
    subscribers = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Plan
        fields = ['id', 'code', 'name', 'description', 'price_monthly', 'currency', 'is_public', 'is_active', 'sort',
                  'features', 'limits', 'subscribers']

    def get_features(self, obj):
        return sorted(f.key for f in obj.features.all())

    def get_limits(self, obj):
        return {lim.key: lim.value for lim in obj.limits.all()}


class PlanUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=60, required=False)
    description = serializers.CharField(max_length=200, required=False, allow_blank=True)
    price_monthly = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0, required=False,
                                             allow_null=True)
    is_public = serializers.BooleanField(required=False)
    is_active = serializers.BooleanField(required=False)
    features = serializers.ListField(child=serializers.CharField(max_length=60), required=False)
    limits = serializers.DictField(child=serializers.IntegerField(min_value=0, allow_null=True), required=False)


class PlatformEventSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source='tenant.name', default=None)

    class Meta:
        model = PlatformEvent
        fields = ['id', 'action', 'summary', 'actor_label', 'tenant', 'tenant_name', 'details', 'ip', 'created_at']
