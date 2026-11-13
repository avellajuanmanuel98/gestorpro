from django.conf import settings
from django.db import models

from gestorpro.core.tenancy.db import TenantModel


class Permission(models.Model):
    """Permiso atómico. El catálogo se define en código (ver registry.py)."""
    code = models.CharField(max_length=80, primary_key=True)
    module = models.CharField(max_length=50)
    description = models.CharField(max_length=200)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return self.code


class Role(TenantModel):
    """Rol por empresa: OWNER, ADMIN, CASHIER... o personalizados."""
    code = models.CharField(max_length=40)
    name = models.CharField(max_length=80)
    is_system = models.BooleanField(default=False)
    grants_all = models.BooleanField(default=False)
    permissions = models.ManyToManyField(Permission, blank=True, related_name='roles')

    class Meta(TenantModel.Meta):
        ordering = ['name']
        constraints = [models.UniqueConstraint(fields=['tenant', 'code'], name='role_unique_code_per_tenant')]

    def __str__(self):
        return self.name

    def permission_codes(self) -> frozenset[str]:
        if self.grants_all:
            return frozenset(Permission.objects.values_list('code', flat=True))
        return frozenset(self.permissions.values_list('code', flat=True))


class Membership(TenantModel):
    """
    Vínculo usuario ↔ empresa. Un usuario puede pertenecer a varias empresas
    (dueño de dos panaderías, contador externo) con un rol distinto en cada una.
    """

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Activa'
        INVITED = 'invited', 'Invitada'
        SUSPENDED = 'suspended', 'Suspendida'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='memberships')
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name='memberships')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    default_location = models.ForeignKey(
        'tenancy.Location', on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
    )

    class Meta(TenantModel.Meta):
        constraints = [models.UniqueConstraint(fields=['tenant', 'user'], name='membership_unique_user_per_tenant')]

    def __str__(self):
        return f'{self.user} @ {self.tenant_id} ({self.role.code})'

    @property
    def permission_codes(self) -> frozenset[str]:
        if not hasattr(self, '_permission_codes'):
            self._permission_codes = self.role.permission_codes()
        return self._permission_codes

    def has_perm(self, code: str) -> bool:
        return code in self.permission_codes


class Invitation(TenantModel):
    """
    Invitación a unirse a la empresa con un rol. El enlace contiene un token
    aleatorio; en BD solo se guarda su hash (SHA-256), así que una filtración
    de la base de datos no permite aceptar invitaciones.
    """
    email = models.EmailField()
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='invitations')
    token_hash = models.CharField(max_length=64, unique=True, editable=False)
    expires_at = models.DateTimeField()
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                   related_name='+')
    accepted_at = models.DateTimeField(null=True, blank=True)
    accepted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='+')
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta(TenantModel.Meta):
        ordering = ['-created_at']
        indexes = [models.Index(fields=['tenant', 'email'])]

    def __str__(self):
        return f'{self.email} → {self.role}'

    @property
    def status(self) -> str:
        from django.utils import timezone
        if self.accepted_at:
            return 'accepted'
        if self.revoked_at:
            return 'revoked'
        if self.expires_at <= timezone.now():
            return 'expired'
        return 'pending'


class SupportSession(models.Model):
    """
    Acceso de SOPORTE de la plataforma a una empresa: solo lectura, con motivo,
    con vencimiento y visible para la empresa en su auditoría. Lo crea la capa
    Platform; aquí vive porque la autenticación (Core) debe poder validarlo.
    No es TenantModel: la plataforma lo consulta por empresa de forma explícita.
    """
    tenant = models.ForeignKey('tenancy.Tenant', on_delete=models.CASCADE, related_name='support_sessions')
    agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    reason = models.CharField('motivo', max_length=300)
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    request_count = models.PositiveIntegerField(default=0)
    ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-started_at']
        indexes = [models.Index(fields=['tenant', '-started_at'])]

    def __str__(self):
        return f'Soporte {self.agent} → {self.tenant} ({self.started_at:%Y-%m-%d %H:%M})'
