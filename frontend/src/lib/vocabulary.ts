import { useAuthStore } from '@/store/authStore'

/**
 * Cómo habla cada negocio. Una panadería tiene "ingredientes", "horno" y vende pan de bono;
 * el resto de negocios ve términos y ejemplos generales ("insumos", "producto").
 * Todo texto de ejemplo que dependa del tipo de negocio vive aquí, no en las pantallas.
 */
const BAKERY = {
  ingredient: 'ingrediente', ingredients: 'ingredientes', Ingredient: 'Ingrediente', Ingredients: 'Ingredientes',
  productionTagline: 'Registra lo que sale del horno: descuenta ingredientes y suma producto',
  recipeTagline: 'Con la receta, el sistema calcula el costo real de cada pan y descuenta los ingredientes al producir.',
  preparedExamples: 'tinto, café con leche, jugos',
  kindHints: {
    finished_good: 'Lo produces tú: panes, tortas, bebidas preparadas',
    resale: 'Lo compras listo y lo revendes: gaseosas, agua, leche',
    service: 'No tiene existencias: domicilio, decoración',
  } as Record<string, string>,
  examples: {
    productName: 'Pan de bono',
    ingredientName: 'Harina de trigo',
    productCategory: 'Panes rellenos',
    ingredientCategory: 'Harinas',
    productsEmpty: 'Agrega lo que vendes: panes, bebidas, tortas por porción…',
    jobTitle: 'Panadero, cajera…',
    team: 'panaderos, cajeros, domiciliarios…',
    suppliers: 'Registra a quienes te venden harina, lácteos, empaques y demás insumos.',
    expense: 'Ej.: compra de huevos',
    purchaseItem: 'Harina, huevos, gaseosa…',
    wasteItem: 'Pan de bono, harina…',
    wasteNote: 'Ej.: tanda de las 6 a. m.',
    recipeProduct: 'Pan de bono, almojábana…',
  },
}

const GENERIC: typeof BAKERY = {
  ingredient: 'insumo', ingredients: 'insumos', Ingredient: 'Insumo', Ingredients: 'Insumos',
  productionTagline: 'Registra lo que produces: descuenta insumos y suma producto terminado',
  recipeTagline: 'Con la receta (o fórmula), el sistema calcula el costo real de cada producto y descuenta los insumos al producir.',
  preparedExamples: 'p. ej. bebidas o platos preparados',
  kindHints: {
    finished_good: 'Lo produces o transformas tú a partir de insumos',
    resale: 'Lo compras listo y lo vendes tal cual',
    service: 'No tiene existencias: mano de obra, instalación, domicilio',
  },
  examples: {
    productName: 'Nombre del producto',
    ingredientName: 'Nombre del insumo',
    productCategory: 'Ej.: Línea principal',
    ingredientCategory: 'Ej.: Materias primas',
    productsEmpty: 'Agrega lo que vendes, con su precio y su IVA.',
    jobTitle: 'Ej.: Vendedor, cajera…',
    team: 'vendedores, cajeros, domiciliarios…',
    suppliers: 'Registra a quienes te venden mercancía, materias primas e insumos.',
    expense: 'Ej.: compra de bolsas o papelería',
    purchaseItem: 'Buscar producto o insumo…',
    wasteItem: 'Buscar producto o insumo…',
    wasteNote: 'Ej.: lote dañado en bodega',
    recipeProduct: 'Producto que fabricas…',
  },
}

export type Vocabulary = typeof BAKERY

export function useVocabulary(): Vocabulary {
  return useAuthStore((s) => s.session?.tenant?.vertical) === 'bakery' ? BAKERY : GENERIC
}
