#!/usr/bin/env python3
"""Deterministic, inert offline views of an explicit public-source allowlist.

This is a deliberately small Markdown subset, not a browser or source executor.
It makes no network request and does not configure hosting.
"""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import html
import json
import posixpath
import re
from urllib.parse import urlsplit, quote, unquote

SOURCES = ('README.md', 'docs/choose-and-start.md', 'docs/pure-filter.md',
           'docs/example-queue-change.md', 'docs/beta.md', 'docs/toolchain.md',
           'docs/l2.md', 'docs/filter-saved-workflow.md', 'docs/store.md',
           'docs/stateful-components.md', 'docs/probe-component-outcomes.md',
           'docs/probe-outcome-composition.md', 'docs/probe-outcome-persistence.md',
           'docs/component-text-cli.md', 'docs/component-arithmetic-form.md', 'docs/component-arithmetic-edits.md', 'docs/component-diagnostics.md', 'docs/readable-authoring.md', 'docs/component-match-form.md', 'docs/component-match-edits.md', 'docs/stock-adjustment.md', 'docs/component-expression-locations.md', 'docs/component-text-list-form.md', 'docs/tag-box.md', 'docs/component-fold-form.md', 'docs/tag-box-budget.md', 'docs/component-record-list-form.md', 'docs/pure-record-form.md', 'docs/pure-reindex-entry.md', 'docs/pure-batch-reindex.md', 'docs/record-diagnostics.md', 'docs/pure-record-drafts.md', 'docs/pure-change-workflow.md', 'docs/pure-option-form.md', 'docs/pure-optional-fields.md', 'docs/pure-json-form.md', 'docs/catalog-edit-workflow.md', 'docs/focused-function-edits.md', 'docs/function-context.md', 'docs/record-formatting.md', 'docs/record-wide-profile.md', 'docs/catalog-wide.md', 'docs/wide-function-editing.md', 'docs/wide-authoring.md', 'docs/record-draft-export.md', 'docs/record-capabilities.md', 'docs/pure-inventory-reservation.md', 'docs/inventory-focused-change.md', 'docs/offline-documentation.md', 'docs/application.md', 'docs/probe-native-wide-emitter.md', 'docs/probe-native-wide-wire.md', 'docs/probe-native-wide-adapter.md', 'docs/probe-native-wide-qualification.md', 'docs/probe-native-wide-followthrough.md', 'docs/inventory-json.md', 'docs/json-argument-prepare.md', 'docs/inventory-json-focused-change.md', 'docs/native-source-locations.md', 'docs/record-source-map.md', 'docs/inventory-batch.md', 'LICENSE')
REPOSITORY = 'https://github.com/llmcomehere/bagaev'
LIMIT = 1048576
STYLE = '''body{margin:0;background:#f7f9fa;color:#202830;font:16px/1.6 system-ui,sans-serif}main{max-width:1050px;margin:auto;padding:28px}nav{display:flex;flex-wrap:wrap;gap:6px 18px;padding:12px 0;border-bottom:1px solid #d6dfe3}a{color:#006d63}article{background:white;padding:24px;border:1px solid #dce3e6;border-radius:8px;margin-top:20px}h1,h2,h3{line-height:1.25;scroll-margin-top:16px}h1{font-size:2rem}h2{margin-top:2rem}pre{overflow:auto;background:#f1f4f5;padding:16px;border-radius:5px}code{font:0.9em ui-monospace,monospace;overflow-wrap:anywhere}.table{overflow:auto}table{border-collapse:collapse;width:100%}th,td{border:1px solid #dce3e6;text-align:left;vertical-align:top;padding:8px}small,.notice{color:#52646c}.notice{border-left:3px solid #00796b;padding-left:12px}footer{font-size:12px;overflow-wrap:anywhere;margin-top:24px}a:focus-visible{outline:3px solid #008b7b;outline-offset:3px}@media(max-width:650px){main{padding:16px}article{padding:16px}h1{font-size:1.65rem}pre{padding:10px}}'''

class BuildError(ValueError):
    pass


def page_path(source):
    return source[:-3] + '.html' if source.endswith('.md') else source + '.html'


def source_url(source, revision):
    return REPOSITORY + '/blob/' + revision + '/' + quote(source, safe='/')


def link(target, source, revision):
    if any(ord(c) < 32 for c in target) or '\\' in target:
        raise BuildError('invalid link characters')
    parsed = urlsplit(target)
    if parsed.scheme:
        if parsed.scheme not in ('https', 'http') or not parsed.netloc:
            raise BuildError('unsupported link scheme')
        return target
    if parsed.netloc or target.startswith('/') or parsed.query:
        raise BuildError('unsupported repository link')
    if not parsed.path:
        return '#' + parsed.fragment if parsed.fragment else '#'
    path = posixpath.normpath(posixpath.join(posixpath.dirname(source), unquote(parsed.path)))
    if path == '..' or path.startswith('../') or path.startswith('/'):
        raise BuildError('repository link escapes root')
    suffix = '#' + quote(unquote(parsed.fragment), safe='-._~') if parsed.fragment else ''
    if path in SOURCES:
        return posixpath.relpath(page_path(path), posixpath.dirname(page_path(source)) or '.') + suffix
    return source_url(path, revision) + suffix


TOKEN = re.compile(r'`([^`\n]+)`|\[([^\]\n]+)\]\(([^)\n]+)\)|\*\*([^*\n]+)\*\*')

def inline(text, source, revision):
    out = []; start = 0
    for m in TOKEN.finditer(text):
        out.append(html.escape(text[start:m.start()]))
        if m[1] is not None:
            out.append('<code>' + html.escape(m[1]) + '</code>')
        elif m[2] is not None:
            out.append('<a href="' + html.escape(link(m[3], source, revision), quote=True) + '">' + html.escape(m[2]) + '</a>')
        else:
            out.append('<strong>' + html.escape(m[4]) + '</strong>')
        start = m.end()
    return ''.join(out) + html.escape(text[start:])


def cells(line):
    out = []; current = []; code = False
    for c in line.strip().strip('|'):
        if c == '`': code = not code
        if c == '|' and not code:
            out.append(''.join(current).strip()); current = []
        else: current.append(c)
    out.append(''.join(current).strip())
    return out


def list_marker(line):
    m = re.match(r'^( *)(?:([-*]) |(\d+)\. )(.+)$', line.rstrip('\r\n'))
    return (len(m[1]), 'ul' if m[2] else 'ol', m[4], m[3]) if m else None


def render_list(lines, start, fmt, depth=0):
    if depth > 32: raise BuildError('list nesting too deep')
    base, tag, _, _ = list_marker(lines[start]); out = ['<' + tag + '>']; i = start
    while i < len(lines):
        marker = list_marker(lines[i])
        if marker is None or marker[0] != base or marker[1] != tag: break
        attribute = ' value="' + marker[3] + '"' if tag == 'ol' else ''
        out.append('<li' + attribute + '>' + fmt(marker[2])); i += 1
        while i < len(lines):
            child = list_marker(lines[i])
            if child and child[0] > base:
                nested, i = render_list(lines, i, fmt, depth + 1); out.append(nested)
            elif not child and lines[i].strip() and len(lines[i]) - len(lines[i].lstrip(' ')) > base:
                out.append(' ' + fmt(lines[i].strip())); i += 1
            else: break
        out.append('</li>')
    out.append('</' + tag + '>'); return ''.join(out), i


def render(text, source, revision):
    if source == 'LICENSE':
        return '<h1>License</h1><pre>' + html.escape(text) + '</pre>', 'License'
    lines = text.splitlines(keepends=True); out = []; i = 0; slugs = {}; title = source
    fmt = lambda s: inline(s, source, revision)
    while i < len(lines):
        line = lines[i].rstrip('\r\n')
        if not line.strip(): i += 1; continue
        if line.startswith('```'):
            code = []; i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                code.append(lines[i]); i += 1
            if i == len(lines): raise BuildError('unclosed code fence')
            out.append('<pre><code>' + html.escape(''.join(code)) + '</code></pre>'); i += 1; continue
        heading = re.match(r'^(#{1,6}) (.+)$', line)
        if heading:
            level = len(heading[1]); name = heading[2]
            slug = re.sub(r'[^\w\- ]', '', name.lower()).replace(' ', '-')
            count = slugs.get(slug, 0); slugs[slug] = count + 1
            if count: slug += '-' + str(count)
            if level == 1 and title == source: title = name
            out.append(f'<h{level} id="{html.escape(slug, quote=True)}">{fmt(name)}</h{level}>'); i += 1; continue
        if line.startswith('|') and i + 1 < len(lines) and re.fullmatch(r'[| :\-\r\n]+', lines[i + 1]):
            headers = cells(line); out.append('<div class="table"><table><thead><tr>' + ''.join('<th>' + fmt(c) + '</th>' for c in headers) + '</tr></thead><tbody>'); i += 2
            while i < len(lines) and lines[i].startswith('|'):
                row = cells(lines[i]); out.append('<tr>' + ''.join('<td>' + fmt(c) + '</td>' for c in row) + '</tr>'); i += 1
            out.append('</tbody></table></div>'); continue
        if list_marker(line):
            rendered, i = render_list(lines, i, fmt); out.append(rendered); continue
        paragraph = [line]; i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r'^(?:#|```|\||\s*[-*] |\s*\d+\. )', lines[i]):
            paragraph.append(lines[i].strip()); i += 1
        out.append('<p>' + fmt(' '.join(paragraph)) + '</p>')
    return '\n'.join(out), title


def document(body, title, source, revision, digest, nav):
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="color-scheme" content="light"><title>' + html.escape(title) + ' · bagaev</title><style>' + STYLE + '</style></head><body><main>'
            '<nav aria-label="Documentation">' + nav + '</nav><p class="notice">Offline documentation preview. No deployment or live execution is established by this build.</p><article>' + body + '</article><footer>Source reference: <a href="' + html.escape(source_url(source, revision), quote=True) + '">' + html.escape(source) + '</a><br>Revision: ' + revision + '<br>Source SHA-256: ' + digest + '</footer></main></body></html>\n')


def build(root, output, revision):
    if not re.fullmatch(r'[0-9a-f]{40}', revision): raise BuildError('invalid source revision')
    if root.is_symlink() or not root.is_dir(): raise BuildError('invalid source root')
    root = root.resolve()
    if not output.is_absolute() or output.exists() or not output.parent.is_dir(): raise BuildError('output must be a new absolute directory')
    captured = {}
    for name in SOURCES:
        path = root / name
        if any(p.is_symlink() for p in (path, *path.parents) if p != root.parent): raise BuildError('source symlink refused')
        if not path.is_file() or not path.resolve().is_relative_to(root): raise BuildError('missing or nonregular source')
        data = path.read_bytes()
        if len(data) > LIMIT: raise BuildError('source too large')
        try: text = data.decode('utf-8')
        except UnicodeError as e: raise BuildError('source is not UTF-8') from e
        captured[name] = (text, hashlib.sha256(data).hexdigest())
    pages = {}; records = []
    for name, (text, digest) in captured.items():
        body, title = render(text, name, revision)
        nav = ' '.join('<a href="' + html.escape(posixpath.relpath(page_path(n), posixpath.dirname(page_path(name)) or '.'), quote=True) + '">' + html.escape(n) + '</a>' for n in SOURCES)
        pages[page_path(name)] = document(body, title, name, revision, digest, nav)
        records.append({'source':name, 'page':page_path(name), 'title':title, 'sha256':digest, 'source_url':source_url(name, revision)})
    pages['index.html'] = pages['README.html']
    pages['index.json'] = json.dumps({'schema':'bagaev-offline-docs/1', 'revision':revision, 'deployment':'not-configured', 'sources':records}, ensure_ascii=False, sort_keys=True, indent=2) + '\n'
    output.mkdir()
    for name, text in pages.items():
        target = output / PurePosixPath(name); target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('x', encoding='utf-8', newline='') as f: f.write(text)
    return {'files':len(pages), 'sources':len(records), 'revision':revision}


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--source-root',type=Path,default=Path(__file__).resolve().parents[1]); p.add_argument('--output',type=Path,required=True); p.add_argument('--revision',required=True); a=p.parse_args()
    try: result=build(a.source_root,a.output,a.revision)
    except (BuildError,OSError) as e: p.exit(2,'offline documentation build refused: '+str(e)+'\n')
    print(json.dumps(result,sort_keys=True))

if __name__=='__main__': main()
