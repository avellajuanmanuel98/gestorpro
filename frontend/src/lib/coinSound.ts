/**
 * Sonido de monedas al abrir el cajón (al cobrar o con "Abrir cajón").
 *
 * Se sintetiza en el navegador (Web Audio), sin archivos de audio ni derechos de terceros,
 * imitando la física real: una moneda es un disco de metal, y al golpear suena con varios
 * modos de vibración NO armónicos (por eso "tintinea" en vez de dar una nota), con un
 * golpecito de ruido al impacto. Varias monedas caen sobre la bandeja y rebotan cada vez
 * más rápido y más suave. Cada vez suena un poco distinto, como en la vida real.
 */
let context: AudioContext | null = null

// Modos de un disco metálico delgado: [múltiplo de la frecuencia base, volumen, duración relativa]
const MODES: [number, number, number][] = [
  [1, 1, 1], [1.59, 0.55, 0.8], [2.14, 0.45, 0.6], [2.65, 0.35, 0.5], [3.16, 0.3, 0.4], [3.65, 0.22, 0.3],
]

/** Un golpe de moneda: tintineo metálico + "clic" de impacto. */
function strike(ctx: BaseAudioContext, out: AudioNode, t: number, base: number, level: number, ring: number,
                noise: AudioBuffer) {
  for (const [ratio, volume, length] of MODES) {
    const freq = base * ratio * (1 + (Math.random() - 0.5) * 0.012)  // monedas nunca idénticas
    if (freq > 16000) continue
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.type = 'sine'
    osc.frequency.value = freq
    const decay = ring * length
    gain.gain.setValueAtTime(0.0001, t)
    gain.gain.exponentialRampToValueAtTime(level * volume, t + 0.0015)
    gain.gain.exponentialRampToValueAtTime(0.0001, t + decay)
    osc.connect(gain).connect(out)
    osc.start(t)
    osc.stop(t + decay + 0.02)
  }
  // El contacto metal contra metal: un chasquido muy corto y brillante
  const click = ctx.createBufferSource()
  click.buffer = noise
  const filter = ctx.createBiquadFilter()
  filter.type = 'highpass'
  filter.frequency.value = 5000
  const gain = ctx.createGain()
  gain.gain.setValueAtTime(level * 0.9, t)
  gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.012)
  click.connect(filter).connect(gain).connect(out)
  click.start(t)
  click.stop(t + 0.02)
}

/** Programa el sonido completo en un contexto de audio (también sirve para grabarlo sin parlantes). */
export function scheduleCoins(ctx: BaseAudioContext, destination: AudioNode, start: number) {
  const out = ctx.createGain()
  out.gain.value = 0.55
  out.connect(destination)

  const noise = ctx.createBuffer(1, Math.ceil(ctx.sampleRate * 0.02), ctx.sampleRate)
  const data = noise.getChannelData(0)
  for (let i = 0; i < data.length; i++) data[i] = Math.random() * 2 - 1

  // Cinco monedas que caen casi juntas; cada una rebota 2 a 4 veces, cada rebote más
  // rápido y más suave (como una moneda que se asienta en la bandeja)
  for (let coin = 0; coin < 5; coin++) {
    const base = 2100 + Math.random() * 1700        // monedas de distinto tamaño
    let t = start + coin * 0.045 + Math.random() * 0.035
    let gap = 0.07 + Math.random() * 0.05
    let level = 0.5 - coin * 0.05
    const bounces = 2 + Math.floor(Math.random() * 3)
    for (let b = 0; b <= bounces; b++) {
      strike(ctx, out, t, base, level, 0.35 - b * 0.06, noise)
      t += gap
      gap *= 0.62
      level *= 0.55
    }
  }
}

export function playCoins() {
  try {
    const Ctx = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
    if (!Ctx) return
    context ??= new Ctx()
    if (context.state === 'suspended') void context.resume()
    scheduleCoins(context, context.destination, context.currentTime + 0.02)
  } catch {
    // Sin audio disponible: no es motivo para fallar un cobro
  }
}
