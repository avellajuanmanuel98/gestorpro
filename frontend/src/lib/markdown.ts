/**
 * SEGURIDAD: el texto viene del modelo de IA, que a su vez repite datos de la
 * empresa (nombres de clientes, notas…) escritos por otros usuarios. Se escapa
 * TODO el HTML antes de aplicar el formato; las únicas etiquetas que llegan al
 * DOM son las que genera este mismo código. Sin esto, un cliente llamado
 * `<img src=x onerror=...>` ejecutaría código en el navegador de quien consulta.
 */
export function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

export function inlineMarkdown(text: string): string {
  return escapeHtml(text)
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g,   '<em>$1</em>')
    .replace(/`(.*?)`/g,     '<code class="bg-black/10 dark:bg-white/10 px-1 py-0.5 rounded text-xs font-mono">$1</code>')
}
