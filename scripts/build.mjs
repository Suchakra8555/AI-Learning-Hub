// Zero-dependency static site builder.
// Reads content/course.json + content/<track>/*.md and writes dist/.
import { readFileSync, writeFileSync, mkdirSync, readdirSync, cpSync, rmSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const CONTENT = join(ROOT, 'content');
const UI = join(ROOT, 'ui');
const DIST = join(ROOT, 'dist');
const CHECK_ONLY = process.argv.includes('--check');

const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const slugify = (s) =>
  s.toLowerCase().replace(/<[^>]+>/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');

const problems = [];
const warn = (m) => problems.push(m);

// ---------- Syntax highlighting (small, good enough for lesson code) ----------
const KEYWORDS = {
  python: 'def class import from return if elif else for while in not and or is with as try except finally raise None True False yield lambda async await pass break continue global',
  js: 'const let var function return if else for while of in new class import from export default async await try catch throw null true false undefined this',
  bash: 'if then else fi for do done while in echo export cd mkdir pip npm npx git python node source',
  yaml: 'true false null',
  json: 'true false null',
};
const ALIAS = { py: 'python', ts: 'js', typescript: 'js', javascript: 'js', sh: 'bash', shell: 'bash', yml: 'yaml' };

function highlight(code, langRaw) {
  const lang = ALIAS[langRaw] || langRaw;
  if (!KEYWORDS[lang]) return esc(code);
  const comment = lang === 'js' ? '\\/\\/.*$' : '#.*$';
  const kw = KEYWORDS[lang].split(' ').join('|');
  const re = new RegExp(
    `(${comment})|("""[\\s\\S]*?"""|'''[\\s\\S]*?'''|[fr]?"(?:\\\\.|[^"\\\\\\n])*"|[fr]?'(?:\\\\.|[^'\\\\\\n])*'|\`(?:\\\\.|[^\`\\\\])*\`)|\\b(${kw})\\b|\\b(\\d+(?:\\.\\d+)?)\\b`,
    'gm'
  );
  let out = '', last = 0, m;
  while ((m = re.exec(code))) {
    out += esc(code.slice(last, m.index));
    const cls = m[1] ? 'c' : m[2] ? 's' : m[3] ? 'k' : 'n';
    out += `<span class="tok-${cls}">${esc(m[0])}</span>`;
    last = m.index + m[0].length;
    if (m[0].length === 0) re.lastIndex++;
  }
  return out + esc(code.slice(last));
}

// ---------- Markdown ----------
function makeRenderer(ctx) {
  const link = (u) => {
    if (u.startsWith('lesson:')) {
      const target = u.slice(7);
      const [path, hash] = target.split('#');
      if (!ctx.lessonSet.has(path)) warn(`${ctx.file}: broken lesson link "${u}"`);
      return `${ctx.prefix}${path}.html${hash ? '#' + hash : ''}`;
    }
    if (u.startsWith('code:')) return `${ctx.repoUrlBase}${u.slice(5)}`;
    return u;
  };

  function inline(s) {
    const codes = [];
    s = s.replace(/`([^`]+)`/g, (_, c) => { codes.push(c); return `\u0000${codes.length - 1}\u0000`; });
    s = esc(s);
    s = s.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img alt="$1" src="$2" loading="lazy">');
    s = s.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, t, u) => {
      const href = link(u.replace(/&amp;/g, '&'));
      const ext = /^https?:/.test(href) ? ' rel="noopener" target="_blank"' : '';
      return `<a href="${href}"${ext}>${t}</a>`;
    });
    s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    s = s.replace(/(^|[^*\w])\*([^*\s][^*]*?)\*(?!\w)/g, '$1<em>$2</em>');
    s = s.replace(/\u0000(\d+)\u0000/g, (_, i) => `<code>${esc(codes[i])}</code>`);
    return s;
  }

  const CALLOUT_TITLES = { tip: 'Tip', warn: 'Careful', note: 'Note', try: 'Try it', say: 'In one sentence', check: 'Check yourself' };

  function blocks(lines) {
    const out = [];
    let i = 0;
    while (i < lines.length) {
      const l = lines[i];
      if (!l.trim()) { i++; continue; }

      let m = l.match(/^```(\w*)\s*(.*)$/);
      if (m) {
        const body = [];
        i++;
        while (i < lines.length && !lines[i].startsWith('```')) body.push(lines[i++]);
        i++;
        const lang = m[1] || 'text';
        const label = m[2] ? `<span class="code-label">${esc(m[2])}</span>` : `<span class="code-label">${esc(lang === 'text' ? '' : lang)}</span>`;
        out.push(
          `<div class="code"><div class="code-bar">${label}<button class="copy" type="button" aria-label="Copy code">Copy</button></div><pre><code>${highlight(body.join('\n'), lang)}</code></pre></div>`
        );
        continue;
      }

      m = l.match(/^:::(\w+)\s*(.*)$/);
      if (m) {
        const type = m[1];
        const title = m[2];
        const body = [];
        i++;
        while (i < lines.length && lines[i].trim() !== ':::') body.push(lines[i++]);
        i++;
        const inner = blocks(body).join('\n');
        if (type === 'check') {
          out.push(`<details class="callout check"><summary>${inline(title || 'Check yourself')}</summary><div class="callout-body">${inner}</div></details>`);
        } else {
          out.push(`<aside class="callout ${type}"><p class="callout-title">${esc(title || CALLOUT_TITLES[type] || type)}</p><div class="callout-body">${inner}</div></aside>`);
        }
        continue;
      }

      m = l.match(/^(#{2,4})\s+(.*)$/);
      if (m) {
        const level = m[1].length;
        const text = m[2].trim();
        const id = slugify(text);
        if (level <= 3) ctx.toc.push({ level, id, text: text.replace(/`/g, '') });
        out.push(`<h${level} id="${id}"><a class="anchor" href="#${id}" aria-label="Link to this section">#</a>${inline(text)}</h${level}>`);
        i++;
        continue;
      }

      if (/^(-{3,}|\*{3,})$/.test(l.trim())) { out.push('<hr>'); i++; continue; }

      if (l.trim().startsWith('<figure')) {
        const html = [];
        while (i < lines.length) {
          html.push(lines[i]);
          if (lines[i].includes('</figure>')) { i++; break; }
          i++;
        }
        out.push(html.join('\n'));
        continue;
      }

      if (l.includes('|') && i + 1 < lines.length && /^\s*\|?\s*:?-{2,}/.test(lines[i + 1])) {
        const cells = (row) => row.trim().replace(/^\||\|$/g, '').split('|').map((c) => c.trim());
        const head = cells(l);
        i += 2;
        const rows = [];
        while (i < lines.length && lines[i].includes('|') && lines[i].trim()) rows.push(cells(lines[i++]));
        out.push(
          `<div class="table-wrap"><table><thead><tr>${head.map((h) => `<th>${inline(h)}</th>`).join('')}</tr></thead><tbody>${rows
            .map((r) => `<tr>${r.map((c) => `<td>${inline(c)}</td>`).join('')}</tr>`)
            .join('')}</tbody></table></div>`
        );
        continue;
      }

      if (l.startsWith('>')) {
        const body = [];
        while (i < lines.length && lines[i].startsWith('>')) body.push(lines[i++].replace(/^>\s?/, ''));
        out.push(`<blockquote>${blocks(body).join('\n')}</blockquote>`);
        continue;
      }

      m = l.match(/^(\s*)([-*]|\d+\.)\s+(.*)$/);
      if (m && m[1].length === 0) {
        const ordered = /\d/.test(m[2]);
        const items = [];
        while (i < lines.length) {
          const mm = lines[i].match(/^([-*]|\d+\.)\s+(.*)$/);
          if (mm) {
            const width = mm[1].length + 1;
            const item = [mm[2]];
            i++;
            while (i < lines.length && (/^\s{2,}\S/.test(lines[i]) || (!lines[i].trim() && i + 1 < lines.length && /^\s{2,}\S/.test(lines[i + 1])))) {
              item.push(lines[i].slice(Math.min(width, lines[i].length - lines[i].trimStart().length)));
              i++;
            }
            items.push(item);
          } else break;
        }
        const tag = ordered ? 'ol' : 'ul';
        out.push(
          `<${tag}>${items
            .map((it) => {
              const html = blocks(it).join('\n');
              return `<li>${html.replace(/^<p>([\s\S]*?)<\/p>$/, '$1')}</li>`;
            })
            .join('')}</${tag}>`
        );
        continue;
      }

      const para = [];
      while (
        i < lines.length &&
        lines[i].trim() &&
        !/^(```|:::|#{2,4}\s|>|<figure)/.test(lines[i]) &&
        !/^([-*]|\d+\.)\s/.test(lines[i])
      ) para.push(lines[i++]);
      if (!para.length) { para.push(lines[i++]); }
      out.push(`<p>${inline(para.join(' '))}</p>`);
    }
    return out;
  }

  return { render: (md) => blocks(md.split(/\r?\n/)).join('\n'), inline };
}

function parseFrontmatter(src) {
  const m = src.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?/);
  if (!m) return { meta: {}, body: src };
  const meta = {};
  for (const line of m[1].split(/\r?\n/)) {
    const kv = line.match(/^(\w+):\s*(.*)$/);
    if (kv) meta[kv[1]] = kv[2].replace(/^["']|["']$/g, '');
  }
  return { meta, body: src.slice(m[0].length) };
}

// ---------- Load course ----------
const course = JSON.parse(readFileSync(join(CONTENT, 'course.json'), 'utf8'));
const lessons = []; // flat ordered list of ready lessons
const lessonSet = new Set();

for (const track of course.tracks) {
  track.lessons = [];
  const dir = join(CONTENT, track.id);
  if (track.status === 'ready') {
    const files = existsSync(dir) ? readdirSync(dir).filter((f) => f.endsWith('.md')).sort() : [];
    for (const f of files) {
      const slug = f.replace(/^\d+-/, '').replace(/\.md$/, '');
      const { meta, body } = parseFrontmatter(readFileSync(join(dir, f), 'utf8'));
      if (!meta.title) warn(`${track.id}/${f}: missing title`);
      const lesson = {
        track: track.id,
        slug,
        path: `${track.id}/${slug}`,
        title: meta.title || slug,
        summary: meta.summary || '',
        time: meta.time || '',
        stage: meta.stage || '',
        body,
        file: `${track.id}/${f}`,
      };
      track.lessons.push(lesson);
      lessons.push(lesson);
      lessonSet.add(lesson.path);
    }
  }
}

// ---------- Templates ----------
const template = readFileSync(join(UI, 'template.html'), 'utf8');

function sidebarHtml(prefix, current) {
  return course.tracks
    .map((t) => {
      const open = current && current.track === t.id ? ' open' : '';
      if (t.status !== 'ready') {
        return `<details class="track planned"><summary><span class="track-name">${esc(t.title)}</span><span class="pill">Planned</span></summary><ul>${(t.planned || [])
          .map((p) => `<li><span class="soon">${esc(p)}</span></li>`)
          .join('')}</ul></details>`;
      }
      return `<details class="track"${open}><summary><span class="track-name">${esc(t.title)}</span><span class="track-count" data-track="${t.id}"></span></summary><ul>${t.lessons
        .map(
          (l) =>
            `<li><a href="${prefix}${l.path}.html" data-lesson="${l.path}"${current && current.path === l.path ? ' aria-current="page"' : ''}><span class="tick" aria-hidden="true"></span><span>${esc(l.title)}</span></a></li>`
        )
        .join('')}</ul></details>`;
    })
    .join('\n');
}

function page({ title, description, prefix, bodyHtml, current, tocHtml, pageClass }) {
  return template
    .replaceAll('{{title}}', esc(title))
    .replaceAll('{{description}}', esc(description || course.tagline))
    .replaceAll('{{prefix}}', prefix)
    .replaceAll('{{sidebar}}', sidebarHtml(prefix, current))
    .replaceAll('{{toc}}', tocHtml || '')
    .replaceAll('{{pageClass}}', pageClass || '')
    .replaceAll('{{current}}', current ? current.path : '')
    .replaceAll('{{body}}', bodyHtml)
    .replaceAll('{{siteName}}', esc(course.siteName));
}

// ---------- Build ----------
if (!CHECK_ONLY) {
  rmSync(DIST, { recursive: true, force: true });
  mkdirSync(DIST, { recursive: true });
  cpSync(join(UI, 'style.css'), join(DIST, 'style.css'));
  cpSync(join(UI, 'app.js'), join(DIST, 'app.js'));
  if (existsSync(join(UI, 'assets'))) cpSync(join(UI, 'assets'), join(DIST, 'assets'), { recursive: true });
}

const searchIndex = [];
const glossary = [];

lessons.forEach((lesson, idx) => {
  const prefix = '../';
  const ctx = { prefix, lessonSet, toc: [], file: lesson.file, repoUrlBase: course.repoUrlBase || '' };
  const r = makeRenderer(ctx);
  const html = r.render(lesson.body);
  const prev = lessons[idx - 1];
  const next = lessons[idx + 1];
  const trackObj = course.tracks.find((t) => t.id === lesson.track);
  const posInTrack = trackObj.lessons.indexOf(lesson) + 1;

  const tail = lesson.body.split('\n').slice(-15);
  if (tail.some((l) => l.startsWith('Next:') && l.includes('lesson:'))) {
    warn(`${lesson.file}: hand-typed "Next:" line; the build adds the Up next card from folder order, so remove it`);
  }

  const nextTrackObj = next ? course.tracks.find((t) => t.id === next.track) : null;
  const crossNext = !!next && next.track !== lesson.track;
  const crossPrev = !!prev && prev.track !== lesson.track;
  let upNext;
  if (next) {
    const label = crossNext
      ? `You finished <em>${esc(trackObj.title)}</em>. Next track: <em>${esc(nextTrackObj.title)}</em>`
      : `Up next &middot; Lesson ${posInTrack + 1} of ${trackObj.lessons.length}`;
    upNext = `<aside class="up-next${crossNext ? ' is-track' : ''}" aria-label="Up next">
    <p class="up-next-label">${label}</p>
    <a class="up-next-title" href="${prefix}${next.path}.html">${esc(next.title)}</a>
    ${next.summary ? `<p class="up-next-summary">${esc(next.summary)}</p>` : ''}
    ${next.time ? `<p class="up-next-time">${esc(next.time)}</p>` : ''}
  </aside>`;
  } else {
    upNext = `<aside class="up-next is-track" aria-label="Course finished">
    <p class="up-next-label">You finished the course</p>
    <p class="up-next-summary">That was the last lesson. Pick any track again from the course map, or look up a word in the glossary.</p>
    <p class="up-next-links"><a href="${prefix}index.html#tracks">Course map</a> <a href="${prefix}glossary.html">Glossary</a></p>
  </aside>`;
  }

  const toc = ctx.toc.length
    ? `<nav class="toc" aria-label="On this page"><p class="toc-title">On this page</p><ul>${ctx.toc
        .map((t) => `<li class="l${t.level}"><a href="#${t.id}">${esc(t.text)}</a></li>`)
        .join('')}</ul></nav>`
    : '';

  const bodyHtml = `
<article class="lesson" data-lesson="${lesson.path}">
  <header class="lesson-head">
    <p class="crumb"><a href="${prefix}index.html">Course</a> / ${esc(trackObj.title)} / Lesson ${posInTrack} of ${trackObj.lessons.length}${lesson.time ? ` / ${esc(lesson.time)}` : ''}</p>
    <h1>${esc(lesson.title)}</h1>
    ${lesson.summary ? `<p class="lede">${esc(lesson.summary)}</p>` : ''}
  </header>
  <div class="prose">${html}</div>
  <div class="finish">
    <button type="button" class="mark-done" data-done="${lesson.path}"><span class="mark-off">Mark this lesson done</span><span class="mark-on">Done. Click to undo</span></button>
  </div>
  ${upNext}
  <nav class="pager" aria-label="Lesson navigation">
    ${prev ? `<a class="prev" href="${prefix}${prev.path}.html"><span>${crossPrev ? 'Previous track' : 'Previous'}</span>${esc(prev.title)}</a>` : '<span></span>'}
    ${next ? `<a class="next" href="${prefix}${next.path}.html"><span>${crossNext ? 'Next track' : 'Next'}</span>${esc(next.title)}</a>` : '<span></span>'}
  </nav>
</article>`;

  const out = page({
    title: `${lesson.title} · ${course.siteName}`,
    description: lesson.summary,
    prefix,
    bodyHtml,
    current: lesson,
    tocHtml: toc,
    pageClass: 'is-lesson',
  });
  if (!CHECK_ONLY) {
    mkdirSync(join(DIST, lesson.track), { recursive: true });
    writeFileSync(join(DIST, `${lesson.path}.html`), out);
  }

  const plain = html.replace(/<pre[\s\S]*?<\/pre>/g, ' ').replace(/<[^>]+>/g, ' ').replace(/&[a-z#0-9]+;/g, ' ').replace(/\s+/g, ' ');
  searchIndex.push({
    path: lesson.path,
    title: lesson.title,
    track: trackObj.title,
    summary: lesson.summary,
    heads: ctx.toc.map((t) => t.text).join(' · '),
    text: plain.slice(0, 6000),
  });
  for (const m of lesson.body.matchAll(/^\*\*([^*]+)\*\*\s*:\s*(.+)$/gm)) {
    if (lesson.body.includes('<!-- glossary -->')) glossary.push({ term: m[1], def: m[2], path: lesson.path, title: lesson.title });
  }
});

// Glossary page from content/glossary.md (definition list: "**Term**: meaning")
let glossaryHtml = '';
const glossaryFile = join(CONTENT, 'glossary.md');
if (existsSync(glossaryFile)) {
  const { meta, body } = parseFrontmatter(readFileSync(glossaryFile, 'utf8'));
  const items = [...body.matchAll(/^\*\*([^*]+)\*\*\s*:\s*(.+)$/gm)]
    .map((m) => ({ term: m[1], def: m[2] }))
    .sort((a, b) => a.term.localeCompare(b.term));
  const ctx = { prefix: '', lessonSet, toc: [], file: 'glossary.md', repoUrlBase: '' };
  const r = makeRenderer(ctx);
  glossaryHtml = `<article class="lesson"><header class="lesson-head"><h1>${esc(meta.title || 'Plain-words glossary')}</h1><p class="lede">${esc(meta.summary || '')}</p></header><div class="prose"><input id="gloss-filter" class="gloss-filter" type="search" placeholder="Filter words" aria-label="Filter glossary"><dl class="glossary">${items
    .map((it) => `<div class="gloss-item"><dt>${esc(it.term)}</dt><dd>${r.inline(it.def)}</dd></div>`)
    .join('')}</dl></div></article>`;
  glossaryHtml = glossaryHtml.replace(/href="(lesson:[^"]+)"/g, (_, u) => `href="${u}"`);
  searchIndex.push({ path: 'glossary', title: meta.title || 'Glossary', track: 'Reference', summary: meta.summary || '', heads: '', text: items.map((i) => i.term + ' ' + i.def).join(' ').slice(0, 6000) });
}

if (!CHECK_ONLY) {
  // Home
  const ready = course.tracks.filter((t) => t.status === 'ready');
  const first = lessons[0];
  const ladder = course.ladder
    .map(
      (s, n) =>
        `<li class="rung"><div class="rung-mark" aria-hidden="true">${n + 1}</div><div><h3>${esc(s.title)}</h3><p>${esc(s.text)}</p>${
          s.lesson && lessonSet.has(s.lesson) ? `<a href="${s.lesson}.html">Read this stage</a>` : ''
        }</div></li>`
    )
    .join('');
  const trackCards = course.tracks
    .map((t) => {
      const isReady = t.status === 'ready';
      const head = isReady && t.lessons[0] ? `<a class="track-link" href="${t.lessons[0].path}.html">${esc(t.title)}</a>` : `<span class="track-link off">${esc(t.title)}</span>`;
      return `<li class="track-row${isReady ? '' : ' is-planned'}"><div>${head}<p>${esc(t.blurb)}</p></div><div class="track-meta">${
        isReady ? `<span class="track-count" data-track="${t.id}">${t.lessons.length} lessons</span>` : '<span class="pill">Planned</span>'
      }</div></li>`;
    })
    .join('');
  const home = `
<section class="home-hero">
  <h1>${esc(course.headline)}</h1>
  <p class="lede">${esc(course.tagline)}</p>
  <p class="cta-row"><a class="btn primary" href="${first.path}.html" id="start-btn">Start the first lesson</a><a class="btn" href="#tracks">See the whole course</a></p>
</section>
<section class="home-section" id="ladder">
  <h2>The RAG ladder: from a script on your laptop to a system people rely on</h2>
  <p class="section-lede">Each rung fixes the problem the last one left behind. You climb in order, and you run code at every step.</p>
  <ol class="ladder">${ladder}</ol>
</section>
<section class="home-section" id="tracks">
  <h2>The course map</h2>
  <p class="section-lede">Every track is written. Go in order, or jump to the one you need.</p>
  <ul class="track-list">${trackCards}</ul>
</section>
<section class="home-section">
  <h2>How to learn from this</h2>
  <ul class="how">
    ${course.howTo.map((h) => `<li><strong>${esc(h.title)}</strong> ${esc(h.text)}</li>`).join('')}
  </ul>
</section>`;
  writeFileSync(join(DIST, 'index.html'), page({ title: course.siteName, description: course.tagline, prefix: '', bodyHtml: home, current: null, pageClass: 'is-home' }));

  if (glossaryHtml) {
    writeFileSync(join(DIST, 'glossary.html'), page({ title: `Glossary · ${course.siteName}`, description: 'Hard words, said simply.', prefix: '', bodyHtml: glossaryHtml, current: null, pageClass: 'is-glossary' }));
  }

  writeFileSync(join(DIST, 'search-index.js'), `window.__SEARCH__=${JSON.stringify(searchIndex)};window.__LESSONS__=${JSON.stringify(lessons.map((l) => l.path))};`);
}

const planned = course.tracks.filter((t) => t.status !== 'ready').length;
console.log(`Built ${lessons.length} lessons across ${course.tracks.length - planned} ready tracks (${planned} planned).`);
if (problems.length) {
  console.error('\nProblems:\n - ' + problems.join('\n - '));
  process.exit(1);
}
