# Contributing

Anyone can add a lesson or fix one. This page tells you how.

## The one rule

**Write the way you would explain it to a coworker at their desk.**

If a new engineer would stop at a word, explain it in one short line the first time it appears, or add it to `content/glossary.md`.

## Writing rules

1. **Short sentences.** One idea each. Cut any sentence you can.
2. **Plain words.** Say "use", not "utilize". Say "show", not "showcase". Say "fix", not "remediate".
3. **Explain a term once, where it first shows up.** Put it in bold, then say what it means in the same sentence or the next.
4. **Say what, then why, then how.** Start a lesson with the problem the reader has.
5. **Show a number or an example** whenever you can. "Slow" means little. "Takes 6 seconds" means something.
6. **Be honest about limits.** If you did not run it, say so. If a source is unclear, say so. If a tool is in preview, say so.
7. **Facts about other tools come from their own docs,** with a link. Do not fill gaps from memory.
8. **No filler.** Skip "it is important to note", "in today's landscape", "let's dive in", "in conclusion". Skip closing summaries that repeat the lesson.
9. **No hype.** Do not call anything powerful, seamless, robust, or cutting-edge. Say what it does.
10. **Sentence case headings.** "Why we cut text into chunks", not "Why We Cut Text Into Chunks".

### Run the humanizer pass

Before you open a pull request, run the `humanizer` skill on your lesson. It is enabled for this repo in `.claude/settings.json`. It strips patterns that make text read as machine-written (filler openers, inflated words, stacked lists of three, empty closers).

What the humanizer must **not** touch: code blocks, tables, front matter, and quoted text from other sources. Check the diff to make sure it kept your examples and numbers.

## Add a lesson

1. Create `content/<track>/NN-short-name.md`. `NN` sets the order. The file name after the number becomes the URL (`05-chunking.md` gives `rag/chunking`).
2. Start with front matter:

```markdown
---
title: Chunking: cutting text into pieces worth finding
summary: One or two sentences on what the reader gets from this lesson.
time: 15 min
---
```

3. Write the lesson. End with one or two **check questions**. Do not type a "Next" line: the build adds an Up next card from the folder order, and `npm run check` fails if a `Next:` line with a lesson link is added.
4. Run `npm run check`. It builds the site without writing files and fails on broken lesson links.
5. Run `npm run dev` and read your page in the browser, on a narrow window too.

## Markdown you can use

Standard Markdown works: headings (`##`, `###`), lists, tables, links, inline code, bold, italic, quotes, and fenced code blocks with a language (` ```python `).

**Links to other lessons** use `lesson:` and the path without `.html`:

```markdown
[chunking](lesson:rag/chunking)
[a heading in it](lesson:rag/chunking#why-headings-travel-with-the-chunk)
```

**Callout boxes** use `:::` fences:

```markdown
:::tip
A useful shortcut.
:::

:::warn Optional title
Something that can hurt.
:::

:::try
A small exercise for the reader.
:::

:::say
The idea of the lesson in one sentence.
:::

:::note
A side fact.
:::

:::check Your question goes here, on the first line?
The answer goes here. It stays hidden until the reader clicks.
:::
```

**Diagrams** are inline SVG inside `<figure>` tags. Copy the one in `content/rag/02-the-whole-picture.md`. Use the classes `box`, `box hot`, `arrow`, and `small` so colors follow light and dark themes. Always add a `<title>` and `<desc>`.

## Add code

- Put runnable code under `code/<track>/`.
- Prefer the standard library. If you need an install, say so at the top of the file and in the lesson.
- Run it before you write about it. Paste real output into the lesson, not output you expect.
- If you could not run something, say so in the lesson. The repo already does this in two places.

## Add a word to the glossary

Add one line to `content/glossary.md`:

```markdown
**Word**: What it means, in one or two short sentences.
```

The page sorts itself.

## Turn a planned track into a real one

1. In `content/course.json`, find the track and set `"status": "ready"`.
2. Remove its `planned` list.
3. Add lessons in `content/<track-id>/`.

## Before you open a pull request

- [ ] `npm run check` passes.
- [ ] I ran every code sample, or said in the lesson that I did not.
- [ ] I ran the humanizer and checked that code and numbers were not changed.
- [ ] Every new hard word is explained or in the glossary.
- [ ] I read the page on a narrow window.
