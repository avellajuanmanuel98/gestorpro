import { AxiosError, AxiosHeaders } from 'axios'
import { describe, expect, it } from 'vitest'
import { getErrorMessage } from './errors'

const apiError = (status: number, data: unknown) =>
  new AxiosError('fail', 'ERR', undefined, undefined,
    { status, data, statusText: '', headers: {}, config: { headers: new AxiosHeaders() } })

describe('Mensajes de error para el usuario', () => {
  it('muestra el detalle que manda el servidor', () => {
    expect(getErrorMessage(apiError(403, { detail: 'No tienes permiso para anular ventas.' })))
      .toBe('No tienes permiso para anular ventas.')
  })

  it('junta los errores de validación por campo', () => {
    expect(getErrorMessage(apiError(400, { payments: ['Faltan $2000.00 por pagar.'] })))
      .toBe('Faltan $2000.00 por pagar.')
  })

  it('sin respuesta del servidor habla de conexión, no de un error genérico', () => {
    expect(getErrorMessage(new AxiosError('Network Error'))).toMatch(/conectar con el servidor/)
  })

  it('una página de error del servidor no se muestra en pantalla ni en inglés', () => {
    expect(getErrorMessage(apiError(502, '<html>'.padEnd(400, 'x')))).toMatch(/servidor tuvo un problema/)
    expect(getErrorMessage(apiError(404, ''), 'No encontrado')).toBe('No encontrado')
  })
})
