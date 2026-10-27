export interface CatalogDb { readonly discounts: Map<string, number> }
export function finalPrice(db: CatalogDb, name: string, base: number): number {
  return base - (db.discounts.get(name) ?? 0);
}
export function quote(db: CatalogDb, name: string, base: number): number {
  return finalPrice(db, name, base);
}
