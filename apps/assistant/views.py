"""
Asistente de IA para GestorPro.

Flujo:
1. El usuario envía un mensaje desde el frontend.
2. Recopilamos el contexto real del negocio (métricas, facturas, clientes).
3. Construimos un system prompt con ese contexto.
4. Llamamos a la API de Anthropic con streaming.
5. Hacemos stream de cada token al frontend vía Server-Sent Events (SSE).

Esto da la experiencia visual premium de "texto que aparece en tiempo real".
"""
import json
from decimal import Decimal
from django.http import StreamingHttpResponse
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from groq import Groq


def _decimal_safe(val):
    """Convierte Decimal a float de forma segura para JSON."""
    if isinstance(val, Decimal):
        return float(val)
    return val


def _build_business_context(user) -> str:
    """
    Recopila datos reales de la empresa del usuario autenticado
    y los formatea como contexto legible para el LLM.
    """
    from apps.billing.models import Invoice
    from apps.clients.models import Client
    from django.db.models import Sum
    from django.utils import timezone
    from datetime import timedelta

    company = getattr(user, 'company', None)
    company_name = company.name if company else 'tu empresa'

    # ── Métricas de facturación ──────────────────────────────
    invoices = Invoice.objects.filter(company=company)

    paid_total    = _decimal_safe(invoices.filter(status='paid')
                     .aggregate(t=Sum('total'))['t'] or Decimal('0'))
    pending_total = _decimal_safe(invoices.filter(status__in=['draft', 'sent'])
                     .aggregate(t=Sum('total'))['t'] or Decimal('0'))
    overdue_count = invoices.filter(status='overdue').count()
    total_inv     = invoices.filter(invoice_type='invoice').count()
    total_quotes  = invoices.filter(invoice_type='quote').count()

    # ── Clientes ─────────────────────────────────────────────
    client_qs = Client.objects.filter(company=company)
    total_clients  = client_qs.count()
    active_clients = client_qs.filter(status='active').count()

    # ── Facturas recientes ────────────────────────────────────
    recent = invoices.select_related('client').order_by('-created_at')[:5]
    recent_lines = []
    status_labels = {
        'draft': 'Borrador', 'sent': 'Enviada', 'paid': 'Pagada',
        'overdue': 'Vencida', 'cancelled': 'Cancelada',
    }
    for inv in recent:
        client_name = str(inv.client) if inv.client else '—'
        label = status_labels.get(inv.status, inv.status)
        recent_lines.append(
            f"  • {inv.number} | {client_name} | "
            f"${float(inv.total):,.0f} COP | {label}"
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
        f"${float(r['total'] or 0):,.0f} COP"
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
    permission_classes = [IsAuthenticated]

    def post(self, request):
        message = (request.data.get('message') or '').strip()
        if not message:
            return Response({'error': 'El mensaje no puede estar vacío.'}, status=400)
        if len(message) > 1000:
            return Response({'error': 'El mensaje es demasiado largo (máx 1000 caracteres).'}, status=400)

        try:
            context, company_name = _build_business_context(request.user)
        except Exception as e:
            context = "No se pudo obtener el contexto del negocio."
            company_name = "tu empresa"

        api_key = getattr(settings, 'GROQ_API_KEY', None)
        if not api_key:
            return Response({'error': 'GROQ_API_KEY no configurada.'}, status=500)

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
                    yield _sse_chunk({"type": "error", "message": f"Error inesperado: {err}"})

        response = StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream',
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'  # Desactiva buffering en nginx
        return response
