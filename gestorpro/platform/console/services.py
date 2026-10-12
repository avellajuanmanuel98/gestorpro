"""
Operaciones de la consola de plataforma (personal de GestorPro).

Reglas:
- Todo cambio queda en la bitácora de plataforma (PlatformEvent) y, si afecta
  a una empresa, también en la auditoría de ESA empresa (la ve el dueño).
- Las métricas globales son de USO (cuántas empresas, usuarios, ventas): nunca
  montos ni datos de negocio de los clientes. Para ver datos de una empresa
  hace falta una sesión de soporte de solo lectura, con motivo y auditada.
- Nada se borra: las empresas se suspenden.
"""
import datetime
from collections import Counter
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Max, OuterRef, Q, Subquery
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.tokens import AccessToken

from gestorpro.core import entitlements
from gestorpro.core.access import support
from gestorpro.core.access.models import Membership, SupportSession
from gestorpro.core.access.services import invite_owner, provision_tenant
from gestorpro.core.audit import services as audit
from gestorpro.core.audit.models import AuditLog
from gestorpro.core.catalog.models import Item
from gestorpro.core.identity.authentication import TENANT_CLAIM
from gestorpro.core.sales.models import Sale
from gestorpro.core.tenancy.context import tenant_context
from gestorpro.core.tenancy.models import Location, Tenant
from gestorpro.core.usage import current_usage
from gestorpro.platform.subscriptions.models import Plan, PlanFeature, PlanLimit, Subscription

from .models import PlatformEvent

TRIAL_EXPIRED = 'trial_expired'


def record(actor, action: str, summary: str, *, tenant=None, details: dict | None = None, ip=None):
    return PlatformEvent.objects.create(actor=actor, actor_label=actor.email, action=action, tenant=tenant,
                                        summary=summary[:300], details=details or {}, ip=ip)


def _tenant_audit(tenant, action: str, summary: str):
    """La empresa también ve en su auditoría lo que la plataforma hizo sobre ella."""
    with tenant_context(tenant):
        audit.record(action, summary=summary)


def effective_status(sub: Subscription | None, now=None) -> str | None:
    if sub is None:
        return None
    now = now or timezone.now()
    if sub.status == Subscription.Status.TRIALING and sub.trial_ends_at and sub.trial_ends_at <= now:
        return TRIAL_EXPIRED
    return sub.status


# ── Métricas globales ───────────────────────────────────────────────────────

def overview() -> dict:
    now = timezone.now()
    week, month = now - datetime.timedelta(days=7), now - datetime.timedelta(days=30)
    tenants = list(Tenant.objects.select_related('subscription__plan'))
    subs = {t.id: getattr(t, 'subscription', None) for t in tenants}
    sold = set(Sale.all_tenants.filter(created_at__gte=week, status=Sale.Status.COMPLETED)
               .values_list('tenant_id', flat=True).distinct())
    acted = set(AuditLog.all_tenants.filter(created_at__gte=week).values_list('tenant_id', flat=True).distinct())
    sub_status = Counter(effective_status(s, now) or 'none' for s in subs.values())
    plan_counts = Counter((s.plan.code, s.plan.name) for s in subs.values() if s)
    paying = [s for s in subs.values() if s and s.status == Subscription.Status.ACTIVE]
    priced = [s.plan.price_monthly for s in paying if s.plan.price_monthly is not None]
    soon = [t for t in tenants if subs[t.id] and subs[t.id].status == Subscription.Status.TRIALING
            and subs[t.id].trial_ends_at and now < subs[t.id].trial_ends_at <= now + datetime.timedelta(days=7)]
    months = []
    first = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    for i in range(5, -1, -1):
        y, m = divmod(first.year * 12 + first.month - 1 - i, 12)
        start = first.replace(year=y, month=m + 1)
        y2, m2 = divmod(y * 12 + m + 1, 12)
        end = first.replace(year=y2, month=m2 + 1)
        months.append({'month': start.strftime('%Y-%m'),
                       'new_tenants': sum(1 for t in tenants if start <= t.created_at < end)})
    return {
        'tenants': {
            'total': len(tenants),
            'active': sum(1 for t in tenants if t.status == Tenant.Status.ACTIVE),
            'suspended': sum(1 for t in tenants if t.status == Tenant.Status.SUSPENDED),
            'new_30d': sum(1 for t in tenants if t.created_at >= month),
            'in_use_7d': len({t.id for t in tenants} & (sold | acted)),
            'by_vertical': dict(Counter(t.vertical for t in tenants)),
        },
        'subscriptions': {
            'by_status': dict(sub_status),
            'by_plan': [{'code': c, 'name': n, 'count': k} for (c, n), k in sorted(plan_counts.items())],
            'mrr': str(sum(priced, Decimal('0'))),
            'active_without_price': len(paying) - len(priced),
        },
        'users': Membership.all_tenants.filter(status=Membership.Status.ACTIVE).values('user').distinct().count(),
        'sales_30d': Sale.all_tenants.filter(created_at__gte=month, status=Sale.Status.COMPLETED).count(),
        'signups': months,
        'trials_ending': [{'id': t.id, 'name': t.name, 'trial_ends_at': subs[t.id].trial_ends_at.isoformat()}
                          for t in sorted(soon, key=lambda t: subs[t.id].trial_ends_at)],
        'attention': [
            {'id': t.id, 'name': t.name, 'kind': effective_status(subs[t.id], now)}
            for t in tenants
            if effective_status(subs[t.id], now) in (TRIAL_EXPIRED, Subscription.Status.PAST_DUE)
        ],
    }


# ── Empresas ────────────────────────────────────────────────────────────────

def tenant_queryset(params) -> list:
    members = (Membership.all_tenants.filter(tenant=OuterRef('pk'), status=Membership.Status.ACTIVE)
               .values('tenant').annotate(n=Count('id')).values('n'))
    last_activity = (AuditLog.all_tenants.filter(tenant=OuterRef('pk')).values('tenant')
                     .annotate(m=Max('created_at')).values('m'))
    last_sale = (Sale.all_tenants.filter(tenant=OuterRef('pk')).values('tenant')
                 .annotate(m=Max('created_at')).values('m'))
    qs = (Tenant.objects.select_related('subscription__plan')
          .annotate(members=Subquery(members), last_activity=Subquery(last_activity),
                    last_sale=Subquery(last_sale))
          .order_by('-created_at'))
    if params.get('q'):
        q = params['q'].strip()
        by_user = Membership.all_tenants.filter(user__email__icontains=q).values('tenant_id')
        qs = qs.filter(Q(name__icontains=q) | Q(slug__icontains=q) | Q(tax_id__icontains=q) | Q(email__icontains=q)
                       | Q(pk__in=by_user))
    if params.get('status'):
        qs = qs.filter(status=params['status'])
    if params.get('vertical'):
        qs = qs.filter(vertical=params['vertical'])
    if params.get('plan'):
        qs = qs.filter(subscription__plan__code=params['plan'])
    if params.get('subscription'):
        now = timezone.now()
        value = params['subscription']
        if value == TRIAL_EXPIRED:
            qs = qs.filter(subscription__status=Subscription.Status.TRIALING, subscription__trial_ends_at__lte=now)
        elif value == Subscription.Status.TRIALING:
            qs = qs.filter(Q(subscription__trial_ends_at__gt=now) | Q(subscription__trial_ends_at__isnull=True),
                           subscription__status=value)
        else:
            qs = qs.filter(subscription__status=value)
    return qs


def tenant_detail(tenant: Tenant) -> dict:
    sub = getattr(tenant, 'subscription', None)
    ent = entitlements.for_tenant(tenant.id)
    with tenant_context(tenant):
        usage = current_usage()
        members = [{'email': m.user.email, 'name': m.user.full_name, 'role': m.role.name, 'status': m.status,
                    'last_login': m.user.last_login.isoformat() if m.user.last_login else None}
                   for m in Membership.objects.select_related('user', 'role').order_by('role__name', 'user__email')]
        locations = Location.objects.filter(is_active=True).count()
        products = Item.objects.filter(kind__in=Item.PRODUCT_KINDS, is_active=True).count()
    supports = SupportSession.objects.filter(tenant=tenant).select_related('agent')[:10]
    return {
        'usage': [{'key': k, 'label': label, 'used': usage.get(k, 0), 'limit': ent.limit(k)}
                  for k, label in entitlements.LIMITS.items()],
        'features': sorted(ent.features),
        'members': members,
        'locations': locations,
        'products': products,
        'subscription_status': effective_status(sub),
        'support_sessions': [{'id': s.id, 'agent': s.agent.email, 'reason': s.reason,
                              'started_at': s.started_at.isoformat(), 'expires_at': s.expires_at.isoformat(),
                              'ended_at': s.ended_at.isoformat() if s.ended_at else None,
                              'requests': s.request_count} for s in supports],
        'events': [{'id': e.id, 'action': e.action, 'summary': e.summary, 'actor': e.actor_label,
                    'created_at': e.created_at.isoformat()}
                   for e in PlatformEvent.objects.filter(tenant=tenant)[:20]],
    }


@transaction.atomic
def onboard(actor, *, name: str, owner_email: str, vertical: str, plan_code: str, city: str = '',
            tax_id: str = '', ip=None) -> tuple[Tenant, str]:
    if not Plan.objects.filter(code=plan_code, is_active=True).exists():
        raise ValidationError({'plan': 'Plan desconocido o inactivo.'})
    if Tenant.objects.filter(name__iexact=name.strip()).exists():
        raise ValidationError({'name': 'Ya existe una empresa con ese nombre.'})
    tenant = provision_tenant(name=name.strip(), vertical=vertical, plan_code=plan_code, city=city, tax_id=tax_id)
    with tenant_context(tenant):
        _, token = invite_owner(email=owner_email)
    record(actor, 'tenant.created', f'Creó la empresa {tenant.name} ({plan_code}) e invitó a {owner_email}',
           tenant=tenant, details={'vertical': vertical, 'plan': plan_code, 'owner': owner_email}, ip=ip)
    return tenant, invitation_url(token)


def invitation_url(token: str) -> str:
    return f"{settings.FRONTEND_URL.rstrip('/')}/invitation/{token}"


@transaction.atomic
def reinvite_owner(actor, tenant: Tenant, email: str, ip=None) -> str:
    with tenant_context(tenant):
        if Membership.objects.filter(role__grants_all=True, user__email__iexact=email,
                                     status=Membership.Status.ACTIVE).exists():
            raise ValidationError({'email': 'Esa persona ya es propietaria activa de la empresa.'})
        _, token = invite_owner(email=email)
    record(actor, 'tenant.owner_invited', f'Generó una invitación de propietario para {email}', tenant=tenant,
           details={'email': email}, ip=ip)
    return invitation_url(token)


@transaction.atomic
def set_tenant_status(actor, tenant: Tenant, status: str, reason: str, ip=None) -> Tenant:
    if status not in Tenant.Status.values:
        raise ValidationError({'status': 'Estado inválido.'})
    if status == tenant.status:
        return tenant
    if status == Tenant.Status.SUSPENDED and not reason.strip():
        raise ValidationError({'reason': 'Indica el motivo de la suspensión.'})
    before = tenant.status
    Tenant.objects.filter(pk=tenant.pk).update(status=status)
    tenant.status = status
    verb = 'Suspendió' if status == Tenant.Status.SUSPENDED else 'Reactivó'
    record(actor, f'tenant.{status}', f'{verb} la empresa {tenant.name}' + (f': {reason}' if reason else ''),
           tenant=tenant, details={'from': before, 'to': status, 'reason': reason}, ip=ip)
    _tenant_audit(tenant, f'platform.tenant.{status}', f'GestorPro {verb.lower()} la empresa'
                  + (f'. Motivo: {reason}' if reason else ''))
    if status == Tenant.Status.SUSPENDED:
        # Cierra de inmediato cualquier acceso de soporte abierto
        SupportSession.objects.filter(tenant=tenant, ended_at__isnull=True).update(ended_at=timezone.now())
    return tenant


@transaction.atomic
def change_subscription(actor, tenant: Tenant, data: dict, ip=None) -> Subscription:
    sub = Subscription.objects.select_for_update().select_related('plan').get(tenant=tenant)
    changes = {}
    if 'plan' in data and data['plan'] != sub.plan.code:
        plan = Plan.objects.filter(code=data['plan'], is_active=True).first()
        if plan is None:
            raise ValidationError({'plan': 'Plan desconocido o inactivo.'})
        changes['plan'] = [sub.plan.code, plan.code]
        sub.plan = plan
    if 'status' in data and data['status'] != sub.status:
        changes['status'] = [sub.status, data['status']]
        sub.status = data['status']
        if sub.status == Subscription.Status.CANCELED:
            sub.canceled_at = timezone.now()
    for field in ('trial_ends_at', 'current_period_end'):
        if field in data and data[field] != getattr(sub, field):
            old = getattr(sub, field)
            changes[field] = [old.isoformat() if old else None, data[field].isoformat() if data[field] else None]
            setattr(sub, field, data[field])
    if not changes:
        return sub
    sub.save()
    note = (data.get('note') or '').strip()
    labels = {'plan': 'plan', 'status': 'estado', 'trial_ends_at': 'fin de la prueba',
              'current_period_end': 'fin del período'}
    summary = 'Suscripción: ' + ', '.join(labels[k] for k in changes) + (f' ({note})' if note else '')
    record(actor, 'subscription.changed', f'{tenant.name}. {summary}', tenant=tenant,
           details={'changes': changes, 'note': note}, ip=ip)
    _tenant_audit(tenant, 'platform.subscription.changed', f'GestorPro cambió tu {summary.lower()}')
    return sub


@transaction.atomic
def update_plan(actor, plan: Plan, data: dict, ip=None) -> Plan:
    changes = {}
    for field in ('name', 'description', 'price_monthly', 'is_public', 'is_active'):
        if field in data and data[field] != getattr(plan, field):
            old = getattr(plan, field)
            changes[field] = [str(old) if old is not None else None,
                              str(data[field]) if data[field] is not None else None]
            setattr(plan, field, data[field])
    if 'is_active' in data and not data['is_active'] and plan.subscriptions.exists():
        raise ValidationError({'is_active': 'Hay empresas con este plan: cámbialas de plan antes de desactivarlo.'})
    plan.save()
    if 'features' in data:
        wanted = set(data['features'])
        unknown = wanted - set(entitlements.FEATURES)
        if unknown:
            raise ValidationError({'features': f'Funcionalidad desconocida: {", ".join(sorted(unknown))}'})
        current = set(plan.features.values_list('key', flat=True))
        if wanted != current:
            changes['features'] = [sorted(current), sorted(wanted)]
            plan.features.exclude(key__in=wanted).delete()
            PlanFeature.objects.bulk_create([PlanFeature(plan=plan, key=k) for k in wanted - current])
    if 'limits' in data:
        unknown = set(data['limits']) - set(entitlements.LIMITS)
        if unknown:
            raise ValidationError({'limits': f'Límite desconocido: {", ".join(sorted(unknown))}'})
        current = {lim.key: lim.value for lim in plan.limits.all()}
        for key, value in data['limits'].items():
            if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 0):
                raise ValidationError({'limits': f'{key}: debe ser un entero ≥ 0 o vacío (ilimitado).'})
            if current.get(key, 0) != value or key not in current:
                changes[f'limit.{key}'] = [current.get(key), value]
                PlanLimit.objects.update_or_create(plan=plan, key=key, defaults={'value': value})
    if changes:
        record(actor, 'plan.updated', f'Modificó el plan {plan.name}: {", ".join(changes)}',
               details={'plan': plan.code, 'changes': changes}, ip=ip)
    return plan


# ── Soporte (solo lectura) ──────────────────────────────────────────────────

@transaction.atomic
def start_support(actor, tenant: Tenant, reason: str, ip=None) -> dict:
    reason = (reason or '').strip()
    if len(reason) < 10:
        raise ValidationError({'reason': 'Explica el motivo (mínimo 10 caracteres): la empresa lo verá.'})
    if tenant.status != Tenant.Status.ACTIVE:
        raise ValidationError({'tenant': 'La empresa está suspendida.'})
    SupportSession.objects.filter(agent=actor, ended_at__isnull=True).update(ended_at=timezone.now())
    session = SupportSession.objects.create(tenant=tenant, agent=actor, reason=reason, expires_at=support.expiry(),
                                            ip=ip)
    token = AccessToken.for_user(actor)
    token[TENANT_CLAIM] = tenant.id
    token[support.SUPPORT_CLAIM] = session.id
    token.set_exp(from_time=timezone.now(), lifetime=session.expires_at - timezone.now())
    record(actor, 'support.started', f'Abrió soporte de solo lectura en {tenant.name}: {reason}', tenant=tenant,
           details={'session': session.id, 'reason': reason}, ip=ip)
    _tenant_audit(tenant, 'platform.support.started',
                  f'Soporte de GestorPro ({actor.email}) entró en modo solo lectura por '
                  f'{support.SUPPORT_MINUTES} minutos. Motivo: {reason}')
    return {'access': str(token), 'expires_at': session.expires_at.isoformat(), 'session': session.id,
            'tenant': {'id': tenant.id, 'name': tenant.name}}


@transaction.atomic
def end_support(actor, session_id: int, ip=None) -> bool:
    session = SupportSession.objects.select_for_update().select_related('tenant').filter(
        pk=session_id, agent=actor, ended_at__isnull=True).first()
    if session is None:
        return False
    session.ended_at = timezone.now()
    session.save(update_fields=['ended_at'])
    record(actor, 'support.ended', f'Cerró el soporte en {session.tenant.name} ({session.request_count} consultas)',
           tenant=session.tenant, details={'session': session.id, 'requests': session.request_count}, ip=ip)
    _tenant_audit(session.tenant, 'platform.support.ended',
                  f'Soporte de GestorPro ({actor.email}) salió ({session.request_count} consultas)')
    return True
