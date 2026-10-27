export type Status = "draft" | "published" | "archived";
export function label(s: Status): string {
  switch (s) {
    case "draft": return "черновик";
    case "published": return "опубликовано";
    case "archived": return "архив";
  }
}
export function isVisible(s: Status): boolean {
  switch (s) {
    case "draft": return false;
    case "published": return true;
    case "archived": return false;
  }
}
