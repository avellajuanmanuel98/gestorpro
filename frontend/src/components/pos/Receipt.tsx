import { createPortal } from 'react-dom'
import { useQuery } from '@tanstack/react-query'
import { tenantApi } from '@/api/auth'
import type { Sale } from '@/api/pos'
import { formatQty } from '@/lib/catalog'
import { formatDateTime } from '@/lib/dates'
import { formatCOP } from '@/lib/money'
import { receiptPromo } from '@/lib/promo'

/**
 * Tamaños en px A PROPÓSITO: el papel mide 80 mm y no debe crecer con la letra grande de la pantalla.
 * Ticket de venta para impresora térmica de 80 mm (se imprime con window.print;
 * los estilos de impresión ocultan todo lo demás). No es una factura
 * electrónica: la integración con la DIAN es una fase posterior.
 */
export default function Receipt({ sale, printable = false }: { sale: Sale; printable?: boolean }) {
  const { data: tenant } = useQuery({ queryKey: ['tenant'], queryFn: tenantApi.current, staleTime: 300_000 })
  const promo = receiptPromo(tenant?.vertical)
  return (
    <div className={`${printable ? 'print-ticket ' : ''}font-mono text-[12px] leading-snug text-black bg-white p-3 w-[300px] mx-auto`}>
      <div className="text-center space-y-0.5">
        <p className="font-bold text-[14px]">{tenant?.legal_name || tenant?.name}</p>
        {tenant?.tax_id && <p>NIT {tenant.tax_id}</p>}
        {tenant?.address && <p>{tenant.address}{tenant.city ? `, ${tenant.city}` : ''}</p>}
        {tenant?.phone && <p>Tel. {tenant.phone}</p>}
      </div>
      <div className="my-2 border-t border-dashed border-black" />
      <p>Venta {sale.number}{sale.status === 'voided' && ' — ANULADA'}</p>
      <p>{formatDateTime(sale.created_at)} · {sale.register_name}</p>
      <p>Atendió: {sale.cashier_name}</p>
      <p>Cliente: {sale.customer_name}</p>
      <div className="my-2 border-t border-dashed border-black" />
      {sale.lines.map((l) => (
        <div key={l.id} className="mb-1">
          <p>{l.item_name}</p>
          {/* Precio unitario con IVA incluido: lo que el cliente ve en el mostrador */}
          <p className="flex justify-between"><span>{formatQty(l.quantity, l.unit_symbol)} × {formatCOP(Number(l.line_total) / Number(l.quantity))}</span>
            <span>{formatCOP(l.line_total)}</span></p>
        </div>
      ))}
      <div className="my-2 border-t border-dashed border-black" />
      <p className="flex justify-between"><span>{Number(sale.tax_total) > 0 ? "Base sin IVA" : "Subtotal"}</span><span>{formatCOP(sale.subtotal)}</span></p>
      {Number(sale.tax_total) > 0 && <p className="flex justify-between"><span>IVA</span><span>{formatCOP(sale.tax_total)}</span></p>}
      {Number(sale.discount) > 0 && <p className="flex justify-between"><span>Descuento</span><span>−{formatCOP(sale.discount)}</span></p>}
      <p className="flex justify-between font-bold text-[14px]"><span>TOTAL</span><span>{formatCOP(sale.total)}</span></p>
      {sale.payments.map((p) => (
        <p key={p.id} className="flex justify-between"><span>{p.method_name}</span><span>{formatCOP(p.tendered)}</span></p>
      ))}
      {Number(sale.change_given) > 0 && <p className="flex justify-between"><span>Cambio</span><span>{formatCOP(sale.change_given)}</span></p>}
      <div className="my-2 border-t border-dashed border-black" />
      <p className="text-center">¡Gracias por su compra!</p>
      <p className="text-center text-[10px] mt-1">Comprobante de venta. No es factura electrónica.</p>
      <div className="mt-2 pt-2 border-t border-dashed border-black text-center text-[10px] leading-tight">
        <p className="font-bold">{promo.system}</p>
        <p>{promo.question}</p>
        <p>{promo.contact}</p>
      </div>
    </div>
  )
}

/**
 * La copia que va al papel: se monta directo en <body>, fuera de cualquier ventana o tarjeta.
 * Dentro de un modal, "left: 0" se mide desde el modal y el ticket salía corrido a la derecha,
 * cortando los valores. En pantalla no se ve (print-only).
 */
export function PrintableReceipt({ sale }: { sale: Sale }) {
  return createPortal(<div className="print-only"><Receipt sale={sale} printable /></div>, document.body)
}
