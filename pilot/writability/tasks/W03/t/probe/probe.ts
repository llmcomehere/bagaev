import { area, Shape } from "./main";
const s: Shape = { kind: "rect", size: { w: 2, h: 3 } };
const n: number = area(s) + area({ kind: "circle", r: 2 });
void n;
