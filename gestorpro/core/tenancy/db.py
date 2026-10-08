"""
Modelo base para TODOS los datos que pertenecen a una empresa.

Capas de aislamiento implementadas aquí:

1. `objects` (manager por defecto) filtra SIEMPRE por el tenant activo y lanza
   TenantContextMissing si no hay uno. Como es el manager por defecto, también
   lo usan los serializers de DRF para resolver claves foráneas: un ID de otro
   tenant simplemente "no existe" (cierra las referencias cruzadas).
2. `save()`/`delete()` rechazan escribir sin tenant activo o en un tenant
   distinto al activo.
3. `save()` verifica que toda FK hacia otro TenantModel apunte al mismo tenant.

`all_tenants` es el único acceso sin filtro. Su uso está reservado a la capa de
plataforma y a la autenticación, y debe ser explícito y revisable en code review.
"""
from django.conf import settings
from django.db import models

from gestorpro.kernel.errors import CrossTenantViolation, TenantContextMissing

from .context import get_active_tenant_id


class TenantQuerySet(models.QuerySet):
    def bulk_create(self, objs, *args, **kwargs):
        tenant_id = get_active_tenant_id()
        for obj in objs:
            if obj.tenant_id is None:
                obj.tenant_id = tenant_id
            elif obj.tenant_id != tenant_id:
                raise CrossTenantViolation('bulk_create con objetos de otro tenant.')
            obj.check_tenant_relations()
        return super().bulk_create(objs, *args, **kwargs)


class TenantManager(models.Manager.from_queryset(TenantQuerySet)):
    """Manager fail-closed: sin tenant activo no hay consulta."""

    def get_queryset(self):
        tenant_id = get_active_tenant_id()
        return super().get_queryset().filter(tenant_id=tenant_id)


class UnscopedManager(models.Manager):
    """Acceso global explícito (plataforma/autenticación). Úsese con cuidado."""


class TenantModel(models.Model):
    tenant = models.ForeignKey(
        'tenancy.Tenant', on_delete=models.CASCADE, related_name='+', editable=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()
    all_tenants = UnscopedManager()

    class Meta:
        abstract = True
        # Las relaciones internas de Django (cascadas, FKs hacia delante) usan
        # el manager base sin filtro; el aislamiento de lectura se aplica en
        # `objects` y la integridad de escritura en save().
        base_manager_name = 'all_tenants'

    def save(self, *args, **kwargs):
        self._assert_writable()
        self.check_tenant_relations()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self._assert_writable()
        return super().delete(*args, **kwargs)

    def _assert_writable(self):
        active = get_active_tenant_id(required=False)
        if active is None:
            raise TenantContextMissing(f'Escritura de {type(self).__name__} sin empresa activa.')
        if self.tenant_id is None:
            self.tenant_id = active
        elif self.tenant_id != active:
            raise CrossTenantViolation(f'{type(self).__name__} pertenece a otra empresa.')

    def check_tenant_relations(self):
        """Toda FK hacia otro TenantModel debe apuntar a la misma empresa."""
        for field in self._meta.concrete_fields:
            if not field.is_relation or field.name == 'tenant':
                continue
            related = field.related_model
            if not (isinstance(related, type) and issubclass(related, TenantModel)):
                continue
            value = getattr(self, field.attname)
            if value is None:
                continue
            if field.is_cached(self):
                same = getattr(self, field.name).tenant_id == self.tenant_id
            else:
                same = related.all_tenants.filter(pk=value, tenant_id=self.tenant_id).exists()
            if not same:
                raise CrossTenantViolation(f'{type(self).__name__}.{field.name} apunta a otra empresa.')


class AuthoredTenantModel(TenantModel):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', editable=False,
    )

    class Meta(TenantModel.Meta):
        abstract = True
