export interface Item { readonly price: number; readonly stock: number }
export interface ShopDb { readonly items: Map<string, Item> }
