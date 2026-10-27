import { addDecimal, AddError } from "./main";
import { Result } from "./result";
const r: Result<number, AddError> = addDecimal("1", "2");
void r;
