export interface Article { readonly name: string; readonly words: number }
export function headline(a: Article): string {
  return `${a.name} (${a.words})`;
}
export function retitle(a: Article, t: string): Article {
  return { ...a, name: t };
}
