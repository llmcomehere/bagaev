export interface CatalogDb { readonly discounts: Map<string, number> }
export function finalPrice(name: string, base: number): number {
  return base;
}
export function quote(name: string, base: number): number {
  return finalPrice(name, base);
}
