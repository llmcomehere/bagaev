export type Status = "draft" | "published";
export function label(s: Status): string {
  switch (s) {
    case "draft": return "черновик";
    case "published": return "опубликовано";
  }
}
export function isVisible(s: Status): boolean {
  switch (s) {
    case "draft": return false;
    case "published": return true;
  }
}
