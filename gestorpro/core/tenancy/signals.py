from django.dispatch import Signal

# Se emite dentro de la transacción de alta de una empresa, con el tenant ya
# activo en contexto. Kwargs: tenant, plan_code (opcional, opaco para el Core).
# Lo escuchan Platform (crea la suscripción) y los Verticals (configuración
# inicial del negocio). El Core no conoce a ninguno de los dos.
tenant_provisioned = Signal()
