from .models import Customer

# Identificación que usa la DIAN para el "consumidor final" en Colombia
FINAL_CONSUMER_DOCUMENT = '222222222222'


def ensure_final_consumer() -> Customer:
    """Cliente genérico para ventas de mostrador. Requiere el tenant activo; idempotente."""
    customer, _ = Customer.objects.get_or_create(
        document_type=Customer.DocumentType.CC, document_number=FINAL_CONSUMER_DOCUMENT,
        defaults={'first_name': 'Consumidor', 'last_name': 'final'},
    )
    return customer
