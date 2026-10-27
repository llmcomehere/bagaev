export interface Article { readonly title: string; readonly words: number }
export function headline(a: Article): string {
  return `${a.title} (${a.words})`;
}
export function retitle(a: Article, t: string): Article {
  return { ...a, title: t };
}
