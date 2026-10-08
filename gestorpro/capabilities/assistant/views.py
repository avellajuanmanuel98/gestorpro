"""
Asistente de IA para GestorPro.

Flujo:
1. El usuario envía un mensaje desde el frontend.
2. Recopilamos el contexto real del negocio (métricas, facturas, clientes).
3. Construimos un system prompt con ese contexto.
4. Llamamos al LLM (Groq) con streaming.
5. Hacemos stream de cada token al frontend vía Server-Sent Events (SSE).

Esto da la experiencia visual premium de "texto que aparece en tiempo real".
"""
import json
import logging
from decimal import Decimal

from django.conf import settings
from django.http import StreamingHttpResponse
from groq import Groq
from rest_framework.response import Response
from rest_framework.views import APIView

from gestorpro.core.access.permissions import HasTenantPermission

logger = logging.getLogger(__name__)



def _decimal_safe(val):
    """Normaliza importes a Decimal (se formatean al construir el texto)."""
    return val if isinstance(val, Decimal) else Decimal(str(val))


def _build_business_context(tenant) -> tuple[str, str]:
    """
    Recopila datos reales de la empresa del usuario autenticado
    y los formatea como contexto legible para el LLM.
    """
    from datetime import timedelta

    from django.db.models import Sum
    from django.utils import timezone

    from gestorpro.core.billing.models import Invoice
    from gestorpro.core.customers.models import Customer as Client

    company_name = tenant.name

    # ── Métricas de facturación (manager filtrado por la empresa activa) ──
    invoices = Invoice.objects.all()

    paid_total    = _decimal_safe(invoices.filter(status='paid')
                     .aggregate(t=Sum('total'))['t'] or Decimal('0'))
    pending_total = _decimal_safe(invoices.filter(status__in=['draft', 'sent'])
                     .aggregate(t=Sum('total'))['t'] or Decimal('0'))
    overdue_count = invoices.filter(status='overdue').count()
    total_inv     = invoices.filter(invoice_type='invoice').count()
    total_quotes  = invoices.filter(invoice_type='quote').count()

    # ── Clientes ─────────────────────────────────────────────
    client_qs = Client.objects.all()
    total_clients  = client_qs.count()
    active_clients = client_qs.filter(status='active').count()

    # ── Facturas recientes ────────────────────────────────────
    recent = invoices.select_related('customer').order_by('-created_at')[:5]
    recent_lines = []
    status_labels = {
        'draft': 'Borrador', 'sent': 'Enviada', 'paid': 'Pagada',
        'overdue': 'Vencida', 'cancelled': 'Cancelada',
    }
    for inv in recent:
        client_name = str(inv.customer)
        label = status_labels.get(inv.status, inv.status)
        recent_lines.append(
            f"  • {inv.number} | {client_name} | "
            f"${inv.total:,.0f} COP | {label}"
        )

    # ── Ingresos últimos 6 meses ──────────────────────────────
    since = timezone.now() - timedelta(days=180)
    from django.db.models.functions import TruncMonth
    monthly = (
        invoices.filter(status='paid', issue_date__gte=since)
        .annotate(month=TruncMonth('issue_date'))
        .values('month')
        .annotate(total=Sum('total'))
        .order_by('month')
    )
    MESES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
             'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    monthly_lines = [
        f"  • {MESES[r['month'].month - 1]} {r['month'].year}: "
        f"${(r['total'] or Decimal('0')):,.0f} COP"
        for r in monthly
    ] or ["  • Sin datos de ventas pagadas aún"]

    context = f"""
=== CONTEXTO DEL NEGOCIO: {company_name} ===

RESUMEN FINANCIERO (datos en COP):
  • Total recaudado (facturas pagadas): ${paid_total:,.0f}
  • Total pendiente de cobro:           ${pending_total:,.0f}
  • Facturas vencidas:                  {overdue_count}
  • Total facturas emitidas:            {total_inv}
  • Total cotizaciones:                 {total_quotes}

CLIENTES:
  • Total registrados: {total_clients}
  • Activos:           {active_clients}
  • Inactivos:         {total_clients - active_clients}

FACTURAS RECIENTES (últimas 5):
{chr(10).join(recent_lines) if recent_lines else '  • Sin facturas registradas aún'}

INGRESOS MENSUALES (últimos 6 meses, solo pagados):
{chr(10).join(monthly_lines)}

Fecha y hora actual: {timezone.now().strftime('%d de %B de %Y, %H:%M')}
""".strip()

    return context, company_name


def _sse_chunk(data: dict) -> str:
    """Formatea un dict como evento SSE."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


class AssistantChatView(APIView):
    """
    POST /api/assistant/chat/
    Body: { "message": "¿Cuánto vendí este mes?" }
    Response: Server-Sent Events (text/event-stream)

    Cada evento SSE tiene el formato:
        data: {"type": "delta", "text": "..."}
    Al finalizar:
        data: {"type": "done"}
    En caso de error:
        data: {"type": "error", "message": "..."}
    """
    permission_classes = [HasTenantPermission]
    required_permissions = {'POST': 'assistant.use'}

    def post(self, request):
        message = (request.data.get('message') or '').strip()
        if not message:
            return Response({'error': 'El mensaje no puede estar vacío.'}, status=400)
        if len(message) > 1000:
            return Response({'error': 'El mensaje es demasiado largo (máx 1000 caracteres).'}, status=400)

        # El contexto se arma ANTES de empezar el streaming: el generador corre
        # cuando la petición ya terminó y el tenant activo ya no existe.
        context, company_name = _build_business_context(request.tenant)

        api_key = getattr(settings, 'GROQ_API_KEY', None)
        if not api_key:
            return Response({'error': 'El asistente no está disponible en este momento.'}, status=503)

        def event_stream():
            try:
                client = Groq(api_key=api_key)

                system_prompt = f"""Eres el asistente de negocios de GestorPro para {company_name}.

Tu rol es ayudar al empresario a entender y gestionar su negocio a partir de los datos reales del sistema.

PRINCIPIOS:
- Responde siempre en español, de forma clara, concisa y profesional.
- Usa los datos del contexto para dar respuestas específicas y útiles.
- Cuando hagas cálculos financieros, usa los valores exactos del contexto.
- Si el usuario pregunta algo que no puedes responder con los datos disponibles, díselo honestamente.
- Formatea las cifras en pesos colombianos (COP) con separadores de miles.
- Usa bullets o listas cuando sea útil para la legibilidad.
- Sé directo al punto — el empresario tiene poco tiempo.
- Puedes dar recomendaciones de negocio cuando sean relevantes.
- No inventes datos que no estén en el contexto.

{context}"""

                stream = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    max_tokens=1024,
                    stream=True,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": message},
                    ],
                )

                for chunk in stream:
                    text = chunk.choices[0].delta.content or ''
                    if text:
                        yield _sse_chunk({"type": "delta", "text": text})

                yield _sse_chunk({"type": "done"})

            except Exception as e:
                err = str(e)
                if 'auth' in err.lower() or '401' in err:
                    yield _sse_chunk({"type": "error", "message": "API Key inválida. Verifica GROQ_API_KEY."})
                elif 'rate' in err.lower() or '429' in err:
                    yield _sse_chunk({"type": "error", "message": "Límite de uso alcanzado. Intenta en unos momentos."})
                else:
                    logger.exception('assistant_stream_error')
                    yield _sse_chunk({"type": "error", "message": "No pudimos generar la respuesta. Intenta de nuevo."})

        response = StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream',
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'  # Desactiva buffering en nginx
        return response
