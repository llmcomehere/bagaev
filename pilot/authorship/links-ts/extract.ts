/**
 * Извлекатель связей варианта B: проект TypeScript → граф в общей схеме (spec/links/graph.schema.json).
 *
 *   node --no-warnings pilot/authorship/links-ts/extract.ts <корень проекта>   → JSON на stdout
 *
 * Правила (фиксируются до измерения, protocol.md):
 * - узлы: модуль (файл без каталога src/ и расширения; test/app.test.ts → test.app), функции верхнего уровня
 *   и переменные вызываемого типа (fn, включая arrow/function expression и алиасы),
 *   типы (type), события (event — интерфейс модуля events с полем `type: "<Имя>"`), таблицы (table — объекты
 *   репозитория модуля db), прочие константы (value), тесты (test — вызов `test("имя", …)` в test/), смысловые
 *   сущности, контракты и правила из JSDoc (`@entity`, `@contract … about …`, `@rule`);
 * - ID — имя: идентичность кода в TypeScript — имя (переименование — новая сущность);
 * - calls — по типчекеру; references — функция как значение; uses_type — ссылки на типы проекта;
 * - reads/writes — вызовы методов таблиц репозитория (get/all/for…/has — чтение; put/replace…/set/delete — запись);
 * - emits — `emit(db, { type: "<Имя>", … })`; consumes — регистрация обработчика в HANDLERS под именем события;
 * - declared — `@implements`, `@requires`, `@checks`, `@derived_from` в JSDoc, `about` контракта;
 * - PARTIAL: вызов без разрешения (any, динамика), emit без литерала типа, сырой SQL (`db.prepare`, `db.exec`) вне
 *   слоя инфраструктуры (db, bus, migrations);
 * - пробел EXTERNAL_CONSUMERS — функции, которые вызывает CLI (`cli.ts`): их вызывают извне программы.
 * Места (`span`, `head`) — байты UTF-8, как у bagaev. Числа в выводе — десятичные строки (BAG-CJSON-1).
 */
import { createRequire } from "node:module";
import { createHash } from "node:crypto";
import { readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";
import { argv, stdout } from "node:process";

const require = createRequire(import.meta.url);
const ts = require("../../writability/node_modules/typescript/lib/typescript.js");

const meaningsMode = argv.includes("--meanings");
const root: string = argv.filter((a) => !a.startsWith("--"))[2] ?? ".";
const EXTRACTOR = "links-ts@1";
const INFRA = new Set(["db", "bus", "migrations"]);
const READ = /^(get|all|for|has|list|find)/;
const WRITE = /^(put|replace|set|delete|remove|insert|update)/;

const sha = (s: string): string => createHash("sha256").update(s, "utf8").digest("hex");

function walk(dir: string): string[] {
  let out: string[] = [];
  for (const e of readdirSync(join(root, dir), { withFileTypes: true })) {
    const rel = join(dir, e.name);
    if (e.isDirectory()) out = out.concat(walk(rel));
    else if (rel.endsWith(".ts") && !rel.endsWith(".d.ts")) out.push(rel);
  }
  return out;
}

const files = ["src", "test"].flatMap((d) => { try { return walk(d); } catch { return []; } }).sort();
const program = ts.createProgram(files.map((f: string) => join(root, f)).concat([join(root, "node-env.d.ts")]), {
  strict: true, target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.NodeNext, moduleResolution: ts.ModuleResolutionKind.NodeNext,
  allowImportingTsExtensions: true, noEmit: true, types: [],
});
const checker = program.getTypeChecker();

function modName(rel: string): string {
  return rel.replace(/^src\//, "").replace(/\.test\.ts$|\.ts$/, "").replaceAll("/", ".");
}

interface Node { id: string; kind: string; name: string; file: string; span: [string, string]; rev: string; pub: boolean;
  sig?: string; head?: [string, string]; purpose?: string; terms?: string[]; not_about?: string[] }
interface Edge { kind: string; src: string; dst: string; site: { file: string; span: [string, string] };
  provenance: { origin: string; rule: string; extractor?: string } }

const nodes = new Map<string, Node>();
const edges: Edge[] = [];
const partial = new Map<string, Set<string>>();
const gaps: { entity: string; reason: string }[] = [];
const declOf = new Map<any, string>();          // декларация TS → ID узла
const eventByType = new Map<string, string>();   // литерал type события → ID узла
const ruleIds = new Map<string, string>();       // Контракт.правило → ID узла
const entityIds = new Map<string, string>();     // Имя сущности → ID узла
const pendingDeclared: { src: string; kind: string; target: string; file: string; span: [string, string] }[] = [];

function bytes(text: string, pos: number): string {
  return String(Buffer.byteLength(text.slice(0, pos), "utf8"));
}

function flag(kind: string, reason: string) {
  if (!partial.has(kind)) partial.set(kind, new Set());
  partial.get(kind)!.add(reason);
}

function comments(sf: any, node: any): string {
  const text = sf.getFullText();
  return (ts.getLeadingCommentRanges(text, node.getFullStart()) ?? []).map((r: any) => text.slice(r.pos, r.end)).join("\n");
}

function tagArgs(doc: string, tag: string): string[] {
  const out: string[] = [];
  const rx = new RegExp(`@${tag}\\s+([^@*\\n]+)`, "g");
  for (const m of doc.matchAll(rx)) out.push((m[1] ?? "").trim());
  return out;
}

function addNode(sf: any, node: any, id: string, kind: string, pub: boolean, headEnd?: number) {
  const text = sf.getFullText();
  const start = node.getStart(sf);
  const n: Node = { id, kind, name: id, file: relative(root, sf.fileName), span: [bytes(text, start), bytes(text, node.getEnd())],
    rev: sha(node.getText(sf)), pub };
  if (headEnd !== undefined) {
    n.head = [bytes(text, start), bytes(text, headEnd)];
    n.sig = sha(text.slice(start, headEnd));
  }
  nodes.set(id, n);
  return n;
}

function edge(kind: string, src: string, dst: string, sf: any, at: any, origin = "structural", rule = "ts-1") {
  const text = sf.getFullText();
  edges.push({ kind, src, dst, site: { file: relative(root, sf.fileName), span: [bytes(text, at.getStart(sf)), bytes(text, at.getEnd())] },
    provenance: { origin, rule } });
}

// ------------------------------------------------------------ 1. узлы
for (const sf of program.getSourceFiles()) {
  const rel = relative(root, sf.fileName);
  if (!files.includes(rel)) continue;
  const mod = modName(rel);
  addNode(sf, sf, mod, "module", false);
  // смысловые сущности и контракты — в JSDoc модуля
  const first = sf.statements[0];
  const header = first ? comments(sf, first) : "";
  let contract: string | undefined;
  for (const line of header.split("\n")) {
    const ent = line.match(/@entity\s+(\w+)\s*—\s*(.*)$/);
    const con = line.match(/@contract\s+(\w+)\s+about\s+(\w+)/);
    const rule = line.match(/@rule\s+(\w+)\s*—\s*(.*)$/);
    const terms = line.match(/Термины:\s*([^.]*)\./);
    const notAbout = line.match(/Не о:\s*([^.]*)\./);
    if (ent) {
      const id = `${mod}.${ent[1]}`;
      const n = addNode(sf, first, id, "entity", true);
      n.rev = sha(line);
      n.purpose = (ent[2] ?? "").trim();
      entityIds.set(ent[1] ?? "", id);
    }
    if (terms && contract === undefined) {
      const e = [...nodes.values()].find((x) => x.kind === "entity" && x.file === rel);
      if (e) e.terms = (terms[1] ?? "").split(",").map((t) => t.trim()).filter(Boolean);
    }
    if (notAbout && contract === undefined) {
      const e = [...nodes.values()].find((x) => x.kind === "entity" && x.file === rel);
      if (e) e.not_about = (notAbout[1] ?? "").split(",").map((t) => t.trim()).filter(Boolean);
    }
    if (con) {
      contract = `${mod}.${con[1]}`;
      const n = addNode(sf, first, contract, "contract", true);
      n.rev = sha(line);
      pendingDeclared.push({ src: contract, kind: "about", target: `entity:${con[2]}`, file: rel, span: n.span });
    }
    if (rule && contract) {
      const id = `${contract}.${rule[1]}`;
      const n = addNode(sf, first, id, "rule", false);
      n.rev = sha(line);
      ruleIds.set(`${contract.split(".").pop()}.${rule[1]}`, id);
      edges.push({ kind: "defines", src: contract, dst: id, site: { file: rel, span: n.span }, provenance: { origin: "declared", rule: "ts-1" } });
    }
  }
  for (const st of sf.statements) {
    const pub = !!st.modifiers?.some((m: any) => m.kind === ts.SyntaxKind.ExportKeyword);
    const doc = comments(sf, st);
    if (ts.isFunctionDeclaration(st) && st.name) {
      const id = `${mod}.${st.name.text}`;
      addNode(sf, st, id, "fn", pub, st.body ? st.body.getStart(sf) : st.getEnd());
      declOf.set(st, id);
      for (const k of ["implements", "requires", "checks"]) for (const arg of tagArgs(doc, k)) for (const t of arg.split(",")) {
        pendingDeclared.push({ src: id, kind: k, target: t.trim(), file: rel, span: nodes.get(id)!.span });
      }
    } else if (ts.isInterfaceDeclaration(st) || ts.isTypeAliasDeclaration(st)) {
      const id = `${mod}.${st.name.text}`;
      let kind = "type";
      if (mod === "events" && ts.isInterfaceDeclaration(st)) {
        for (const m of st.members) {
          if (ts.isPropertySignature(m) && m.name.getText(sf) === "type" && m.type && ts.isLiteralTypeNode(m.type)) {
            kind = "event";
            eventByType.set((m.type.literal as any).text, id);
          }
        }
      }
      addNode(sf, st, id, kind, pub);
      declOf.set(st, id);
    } else if (ts.isVariableStatement(st)) {
      for (const d of st.declarationList.declarations) {
        if (!ts.isIdentifier(d.name)) continue;
        const id = `${mod}.${d.name.text}`;
        const isTable = mod === "db" && d.initializer && ts.isObjectLiteralExpression(d.initializer);
        const isFn = checker.getTypeAtLocation(d.name).getCallSignatures().length > 0;
        const body = d.initializer && (ts.isArrowFunction(d.initializer) || ts.isFunctionExpression(d.initializer))
          ? d.initializer.body : undefined;
        addNode(sf, st, id, isTable ? "table" : isFn ? "fn" : "value", pub,
          isFn ? (body ? body.getStart(sf) : st.getEnd()) : undefined);
        declOf.set(d, id);
        if (isFn) for (const k of ["implements", "requires", "checks"]) for (const arg of tagArgs(doc, k)) for (const t of arg.split(",")) {
          pendingDeclared.push({ src: id, kind: k, target: t.trim(), file: rel, span: nodes.get(id)!.span });
        }
        for (const t of tagArgs(doc, "derived_from")) {
          pendingDeclared.push({ src: id, kind: "derived_from", target: `entity:${t.split(/\s/)[0]}`, file: rel, span: nodes.get(id)!.span });
        }
      }
    } else if (ts.isExpressionStatement(st) && ts.isCallExpression(st.expression) && st.expression.expression.getText(sf) === "test") {
      const arg = st.expression.arguments[0];
      if (arg && ts.isStringLiteral(arg)) {
        const id = `${mod}.${arg.text}`;
        addNode(sf, st, id, "test", false, (st.expression.arguments[1] ?? st).getStart(sf));
        declOf.set(st, id);
        for (const a of tagArgs(doc, "checks")) for (const t of a.split(",")) {
          pendingDeclared.push({ src: id, kind: "checks", target: t.trim(), file: rel, span: nodes.get(id)!.span });
        }
      }
    }
  }
  for (const n of [...nodes.values()]) {
    if (n.file === rel && n.id !== mod && n.kind !== "rule" && n.id.startsWith(mod + ".")) {
      edges.push({ kind: "defines", src: mod, dst: n.id, site: { file: rel, span: n.span }, provenance: { origin: "structural", rule: "ts-1" } });
    }
  }
}

// ------------------------------------------------------------ 2. рёбра тел
function target(sym: any): string | undefined {
  if (!sym) return undefined;
  const s = sym.flags & ts.SymbolFlags.Alias ? checker.getAliasedSymbol(sym) : sym;
  for (const d of s.declarations ?? []) {
    const id = declOf.get(d) ?? (d.parent ? declOf.get(d.parent) : undefined);
    if (id) return id;
  }
  return undefined;
}

function visit(sf: any, owner: string, node: any) {
  const mod = owner.split(".")[0] ?? "";
  if (ts.isCallExpression(node)) {
    const callee = node.expression;
    if (ts.isPropertyAccessExpression(callee)) {
      const obj = target(checker.getSymbolAtLocation(callee.expression));
      const method = callee.name.text;
      if (obj && nodes.get(obj)?.kind === "table") {
        if (READ.test(method) || !WRITE.test(method)) edge("reads", owner, obj, sf, node);
        if (WRITE.test(method) || !READ.test(method)) edge("writes", owner, obj, sf, node);
      } else if ((method === "prepare" || method === "exec") && /\bDb\b|DatabaseSync/.test(checker.typeToString(checker.getTypeAtLocation(callee.expression)))) {
        if (!INFRA.has(mod)) {
          flag("reads", `сырой SQL в ${owner}`);
          flag("writes", `сырой SQL в ${owner}`);
        }
      } else {
        const t = target(checker.getSymbolAtLocation(callee));
        if (t) edge("calls", owner, t, sf, callee);
      }
    } else {
      const t = target(checker.getSymbolAtLocation(callee));
      if (t && ["fn", "value"].includes(nodes.get(t)?.kind ?? "")) {
        edge("calls", owner, t, sf, callee);
        if (t === "bus.emit") {
          const ev = node.arguments[1];
          const typeProp = ev && ts.isObjectLiteralExpression(ev)
            ? ev.properties.find((p: any) => ts.isPropertyAssignment(p) && p.name.getText(sf) === "type") : undefined;
          const lit = typeProp && ts.isStringLiteral(typeProp.initializer) ? typeProp.initializer.text : undefined;
          const evId = lit ? eventByType.get(lit) : undefined;
          if (evId) edge("emits", owner, evId, sf, node);
          else flag("emits", `emit без литерала типа события в ${owner}`);
        }
      } else if (!t) {
        const type = checker.getTypeAtLocation(callee);
        if (type.flags & ts.TypeFlags.Any) flag("calls", `вызов значения типа any в ${owner}`);
      }
    }
  } else if (ts.isIdentifier(node) && !ts.isCallExpression(node.parent) || (ts.isIdentifier(node) && ts.isCallExpression(node.parent) && node.parent.expression !== node)) {
    const t = target(checker.getSymbolAtLocation(node));
    if (t && t !== owner && ["fn", "value", "table"].includes(nodes.get(t)?.kind ?? "") && !ts.isPropertyAccessExpression(node.parent)) {
      edge("references", owner, t, sf, node);
    }
  }
  if (ts.isTypeReferenceNode(node)) {
    const t = target(checker.getSymbolAtLocation(node.typeName));
    if (t && t !== owner) edge("uses_type", owner, t, sf, node);
  }
  if (ts.isPropertyAccessExpression(node)) {
    // `fn.bind(...)`, `fn.call(...)`, `fn.apply(...)` сохраняют зависимость от функции-получателя.
    const receiver = target(checker.getSymbolAtLocation(node.expression));
    if (receiver && receiver !== owner && nodes.get(receiver)?.kind === "fn") edge("references", owner, receiver, sf, node.expression);
    // тип выражения, у которого берётся поле, — тоже использование типа (как типы выражений у bagaev)
    const ty = checker.getTypeAtLocation(node.expression);
    const t = target(ty.aliasSymbol ?? ty.getSymbol());
    if (t && t !== owner && ["type", "event"].includes(nodes.get(t)?.kind ?? "")) edge("uses_type", owner, t, sf, node);
  }
  ts.forEachChild(node, (c: any) => visit(sf, owner, c));
}

for (const sf of program.getSourceFiles()) {
  const rel = relative(root, sf.fileName);
  if (!files.includes(rel)) continue;
  for (const st of sf.statements) {
    let owner: string | undefined;
    if (ts.isFunctionDeclaration(st) || ts.isInterfaceDeclaration(st) || ts.isTypeAliasDeclaration(st) || ts.isExpressionStatement(st)) {
      owner = declOf.get(st);
    }
    if (ts.isVariableStatement(st)) {
      // Каждая декларация владеет своим телом, в том числе `const a = ..., b = () => a()`.
      for (const d of st.declarationList.declarations) {
        const id = declOf.get(d);
        if (id) visit(sf, id, d);
      }
    }
    if (owner) visit(sf, owner, st);
  }
  // регистрация обработчиков: HANDLERS = { <Событие>: [{ name, run: fn }] }
  if (modName(rel) === "handlers") {
    for (const st of sf.statements) {
      if (!ts.isVariableStatement(st)) continue;
      for (const d of st.declarationList.declarations) {
        if (!d.initializer || !ts.isObjectLiteralExpression(d.initializer)) continue;
        for (const p of d.initializer.properties) {
          if (!ts.isPropertyAssignment(p)) continue;
          const evId = eventByType.get(p.name.getText(sf));
          ts.forEachChild(p.initializer, function find(c: any): void {
            if (ts.isPropertyAssignment(c) && c.name.getText(sf) === "run") {
              const fn = target(checker.getSymbolAtLocation(c.initializer));
              if (fn && evId) edge("consumes", fn, evId, sf, c);
              else flag("consumes", `обработчик без разрешения в ${modName(rel)}`);
            }
            ts.forEachChild(c, find);
          });
        }
      }
    }
  }
  if (modName(rel) === "cli") {
    for (const e of edges) if (e.src.startsWith("cli.") && !e.dst.startsWith("cli.") && (e.kind === "calls" || e.kind === "references")
      && nodes.get(e.dst)?.kind === "fn") {
      if (!gaps.some((g) => g.entity === e.dst)) gaps.push({ entity: e.dst, reason: "EXTERNAL_CONSUMERS" });
    }
  }
}

// ------------------------------------------------------------ 3. объявленные связи
for (const d of pendingDeclared) {
  let dst: string | undefined;
  if (d.target.startsWith("entity:")) dst = entityIds.get(d.target.slice(7));
  else dst = ruleIds.get(d.target);
  if (dst) edges.push({ kind: d.kind, src: d.src, dst, site: { file: d.file, span: d.span }, provenance: { origin: "declared", rule: "ts-1" } });
  else flag(d.kind, `неразрешённая ссылка ${d.target} в ${d.src}`);
}

// ------------------------------------------------------------ вывод
const kinds = ["calls", "references", "reads", "writes", "emits", "consumes", "uses_type", "defines", "implements", "requires",
  "checks", "about", "derived_from"];
const coverage: Record<string, unknown> = {};
for (const k of kinds) {
  const r = partial.get(k);
  coverage[k] = r ? { status: "PARTIAL", basis: [...r].sort().join("; ") } : { status: "COMPLETE", basis: "правила ts-1 (extract.ts)" };
}
const key = (e: Edge) => `${e.kind}\u0000${e.src}\u0000${e.dst}\u0000${e.site.file}\u0000${e.site.span.join(",")}`;
const unique = [...new Map(edges.map((e) => [key(e), e])).values()].sort((a, b) => key(a) < key(b) ? -1 : key(a) > key(b) ? 1 : 0)
  .map((e) => ({ ...e, provenance: { ...e.provenance, extractor: EXTRACTOR }, id: sha(key(e)).slice(0, 24) }));
const sorted = [...nodes.values()].sort((a, b) => a.id < b.id ? -1 : 1);
if (meaningsMode) {
  // смыслы сущностей для поиска (не часть графа общей схемы)
  stdout.write(JSON.stringify(Object.fromEntries(sorted.filter((n) => n.kind === "entity")
    .map((n) => [n.name, { purpose: n.purpose ?? "", terms: n.terms ?? [], not_about: n.not_about ?? [] }]))) + "\n");
} else {
  stdout.write(JSON.stringify({
    format: "bagaev-graph/1",
    extractor_rev: EXTRACTOR,
    source: "",
    nodes: sorted.map(({ purpose, terms, not_about, ...n }) => n),
    edges: unique,
    coverage: { kinds: coverage, scope: "проект целиком: src/ и test/; библиотеки Node вне графа",
      external_boundaries: ["вызывающие CLI вне программы (EXTERNAL_CONSUMERS)", "встроенные модули Node: вызовы без узлов"] },
    gaps: gaps.sort((a, b) => a.entity < b.entity ? -1 : 1),
    unused_atoms: [],
  }) + "\n");
}
