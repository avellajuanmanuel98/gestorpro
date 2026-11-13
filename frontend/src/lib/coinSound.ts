/**
 * Sonido de monedas al abrir el cajón (al cobrar o con "Abrir cajón").
 *
 * Se sintetiza en el navegador (Web Audio): sin archivos de audio ni derechos de terceros.
 * Son varios "tintineos" metálicos cortos, como monedas que caen en la bandeja.
 */
let context: AudioContext | null = null

// [segundos desde el inicio, frecuencia base en Hz, volumen]
const CLINKS: [number, number, number][] = [
  [0, 2600, 0.5], [0.06, 3400, 0.4], [0.13, 2900, 0.45], [0.2, 3900, 0.3], [0.29, 3100, 0.3], [0.4, 3600, 0.2],
]

export function playCoins() {
  try {
    const Ctx = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
    if (!Ctx) return
    context ??= new Ctx()
    if (context.state === 'suspended') void context.resume()
    const ctx = context
    const master = ctx.createGain()
    master.gain.value = 0.5
    master.connect(ctx.destination)
    const start = ctx.currentTime + 0.02
    for (const [at, freq, volume] of CLINKS) {
      // Un metal suena con parciales no armónicos: la base y uno a ×2,76
      for (const [ratio, share] of [[1, 1], [2.76, 0.5]]) {
        const osc = ctx.createOscillator()
        const gain = ctx.createGain()
        osc.type = 'sine'
        osc.frequency.value = freq * ratio
        const t = start + at
        gain.gain.setValueAtTime(0.0001, t)
        gain.gain.exponentialRampToValueAtTime(volume * share, t + 0.004)
        gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.22)
        osc.connect(gain).connect(master)
        osc.start(t)
        osc.stop(t + 0.25)
      }
    }
  } catch {
    // Sin audio disponible: no es motivo para fallar un cobro
  }
}
