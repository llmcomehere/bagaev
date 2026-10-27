import { validateAge, AgeError } from "./main";
import { Result } from "./result";
const r: Result<number, AgeError> = validateAge(3);
void r;
