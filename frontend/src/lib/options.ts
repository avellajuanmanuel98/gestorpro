/** Opciones de formularios compartidas (antes repetidas en cada formulario). */
export const PERSON_DOCUMENTS = [
  { value: 'CC', label: 'Cédula de ciudadanía' },
  { value: 'NIT', label: 'NIT' },
  { value: 'CE', label: 'Cédula de extranjería' },
  { value: 'PP', label: 'Pasaporte' },
] as const

export const SUPPLIER_CATEGORIES = [
  { value: 'materials', label: 'Materiales e insumos' },
  { value: 'services', label: 'Servicios' },
  { value: 'technology', label: 'Tecnología' },
  { value: 'logistics', label: 'Logística y transporte' },
  { value: 'marketing', label: 'Marketing y publicidad' },
  { value: 'other', label: 'Otro' },
] as const

export const DEPARTMENTS = [
  { value: 'operations', label: 'Producción / operaciones' },
  { value: 'sales', label: 'Ventas' },
  { value: 'admin', label: 'Administración' },
  { value: 'finance', label: 'Finanzas' },
  { value: 'hr', label: 'Recursos humanos' },
  { value: 'it', label: 'Tecnología' },
  { value: 'other', label: 'Otro' },
] as const

export const label = <T extends { value: string; label: string }>(options: readonly T[], value: string) =>
  options.find((o) => o.value === value)?.label ?? value
