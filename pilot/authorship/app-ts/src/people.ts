/** Люди: идентификатор, отображаемое имя, адрес почты. */
export type PersonId = string;

export interface Person {
  id: PersonId;
  displayName: string;
  email: string;
}

export function displayName(people: Map<PersonId, Person>, p: PersonId): string {
  return people.get(p)?.displayName ?? p;
}

export function emailOf(people: Map<PersonId, Person>, p: PersonId): string | undefined {
  return people.get(p)?.email;
}
