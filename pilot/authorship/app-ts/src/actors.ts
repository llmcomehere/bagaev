/** Учётные записи, которые выполняют команды. Учётная запись может быть связана с человеком. */
import type { PersonId } from "./people.ts";

export type ActorId = string;

export interface Actor {
  id: ActorId;
  person: PersonId | null;
}
