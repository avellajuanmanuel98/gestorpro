from django.db import transaction

from .models import Sequence


def next_number(*, location, doc_type: str, prefix: str = '', width: int = 6) -> str:
    """
    Reserva el siguiente consecutivo. DEBE llamarse dentro de la transacción del
    documento (transaction.atomic): el bloqueo se libera al confirmar o revertir.
    """
    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError('next_number() requiere una transacción activa.')
    seq, _ = Sequence.objects.get_or_create(location=location, doc_type=doc_type, defaults={'prefix': prefix})
    seq = Sequence.objects.select_for_update().get(pk=seq.pk)
    value = seq.next_value
    seq.next_value = value + 1
    seq.save(update_fields=['next_value', 'updated_at'])
    return f'{seq.prefix}{value:0{width}d}'
