/** Статьи. Редакторы статьи — отдельный список: право правки не следует из авторства. */
import type { PersonId } from "./people.ts";
import type { ActorId } from "./actors.ts";

export type ArticleId = string;

export interface Article {
  id: ArticleId;
  title: string;
  author: PersonId;
  editors: ActorId[];
  revision: number;
}
