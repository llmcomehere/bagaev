import { makeEmail, emailText } from "./main";
const e = makeEmail("a@b");
const s: string = e === undefined ? "" : emailText(e);
void s;
