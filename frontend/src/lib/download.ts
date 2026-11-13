import apiClient from '@/api/client'

/** Descarga un archivo que genera el servidor (con el token de la sesión) y lo guarda con su nombre. */
export async function downloadFile(url: string, params: object = {}, fallbackName = 'archivo') {
  const res = await apiClient.get<Blob>(url, { params, responseType: 'blob' })
  const match = /filename="?([^";]+)"?/.exec(String(res.headers['content-disposition'] ?? ''))
  const href = URL.createObjectURL(res.data)
  const a = Object.assign(document.createElement('a'), { href, download: match?.[1] ?? fallbackName })
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(href)
}
