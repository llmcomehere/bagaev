export interface Item { readonly price: number; readonly stock: number }
export interface PriceChanged { readonly name: string; readonly old: number; readonly new: number }
export interface ShopDb { readonly items: Map<string, Item>; readonly history: Map<string, readonly number[]> }
export interface Outbox { emit(ev: PriceChanged): void }
