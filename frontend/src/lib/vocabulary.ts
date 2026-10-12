import { useAuthStore } from '@/store/authStore'

/** Cómo habla cada negocio: una panadería tiene "ingredientes" y un "horno"; el resto, "insumos". */
const BAKERY = {
  ingredient: 'ingrediente', ingredients: 'ingredientes', Ingredient: 'Ingrediente', Ingredients: 'Ingredientes',
  productionTagline: 'Registra lo que sale del horno: descuenta ingredientes y suma producto',
  recipeTagline: 'Con la receta, el sistema calcula el costo real de cada pan y descuenta los ingredientes al producir.',
  preparedExamples: 'tinto, café con leche, jugos',
}
const GENERIC: typeof BAKERY = {
  ingredient: 'insumo', ingredients: 'insumos', Ingredient: 'Insumo', Ingredients: 'Insumos',
  productionTagline: 'Registra lo que produces: descuenta insumos y suma producto terminado',
  recipeTagline: 'Con la receta (o fórmula), el sistema calcula el costo real de cada producto y descuenta los insumos al producir.',
  preparedExamples: 'p. ej. bebidas o platos preparados',
}

export type Vocabulary = typeof BAKERY

export function useVocabulary(): Vocabulary {
  return useAuthStore((s) => s.session?.tenant?.vertical) === 'bakery' ? BAKERY : GENERIC
}
