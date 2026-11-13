import { describe, expect, it } from 'vitest'
import { escapeHtml, inlineMarkdown } from './markdown'

describe('inlineMarkdown', () => {
  it('aplica el formato permitido', () => {
    expect(inlineMarkdown('**Total** de *hoy*')).toBe('<strong>Total</strong> de <em>hoy</em>')
  })

  it('nunca deja pasar HTML del texto de la IA (XSS)', () => {
    const payload = 'Cliente <img src=x onerror="alert(1)"> y <script>robar()</script>'
    const html = inlineMarkdown(payload)
    expect(html).not.toContain('<img')
    expect(html).not.toContain('<script')
    expect(html).toContain('&lt;img src=x onerror=&quot;alert(1)&quot;&gt;')
  })

  it('escapa HTML dentro de negritas y código', () => {
    expect(inlineMarkdown('**<b>x</b>**')).toBe('<strong>&lt;b&gt;x&lt;/b&gt;</strong>')
    expect(inlineMarkdown('`<svg onload=1>`')).toContain('&lt;svg onload=1&gt;')
  })

  it('escapa comillas para no romper atributos', () => {
    expect(escapeHtml(`"'&`)).toBe('&quot;&#39;&amp;')
  })
})
