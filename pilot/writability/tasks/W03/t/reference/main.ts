export interface Size { readonly w: number; readonly h: number }
export type Shape = { readonly kind: "circle"; readonly r: number } | { readonly kind: "rect"; readonly size: Size };
export function area(s: Shape): number {
  switch (s.kind) {
    case "circle": return 3 * s.r * s.r;
    case "rect": return s.size.w * s.size.h;
  }
}
