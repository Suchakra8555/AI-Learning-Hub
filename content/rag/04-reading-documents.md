---
title: Reading documents without losing the good parts
summary: Real documents are PDFs with headers, tables, and scans. Bad text in means bad answers out.
time: 12 min
---

Our practice files are tidy Markdown. Yours will not be. This lesson covers what happens between "a file exists" and "clean text is ready to cut".

There is an old saying: **garbage in, garbage out**. In RAG it is the most reliable rule you will meet. If the text is scrambled, no search trick or model can rescue the answer.

## Look at the text before you trust it

The first habit: print the text your reader extracted from a few real files, and read it with your own eyes.

```python
from pathlib import Path
text = Path("some-extracted-file.txt").read_text(encoding="utf-8")
print(text[:2000])
```

Things people find when they finally look:

- Every page starts with "Confidential, Page 3 of 40". That junk lands in every chunk.
- A two-column PDF comes out with lines from both columns mixed together.
- A table becomes a stream of numbers with no column names.
- A scanned PDF gives empty text. It is a picture, not text.
- Words split across lines: "return-\nable".

## A reading checklist

| File type | What goes wrong | What to do |
|---|---|---|
| Text-based PDF | Headers, footers, columns | Use a layout-aware extractor. Strip lines that repeat on every page. |
| Scanned PDF or image | No text at all | Run OCR (a tool that reads text from pictures). Check the output by eye. |
| Word / Google Docs | Comments and tracked changes sneak in | Export a clean version. Decide if comments belong. |
| HTML / web pages | Menus, cookie banners, ads | Keep only the main content area. |
| Spreadsheets | Meaning lives in column names | Turn each row into a sentence: "Plan: Pro. Price: 20 dollars." |
| Slides | Fragments with no sentences | Include speaker notes. Keep slide titles with their content. |

You do not need to solve all of these on day one. You do need to know which ones *your* documents have.

## How a serious PDF reader works

Simple extractors read the text layer of a PDF and stop. Tools built for messy documents do more, one page at a time:

1. **Read the text layer.** A PDF made by Word or a browser already contains the characters. Take them. This is fast and exact.
2. **Decide if the page needs OCR.** If the text layer is empty or garbage, the page is probably a scan. Render the page as an image and read it with **OCR** (optical character recognition: software that reads text from a picture).
3. **OCR in two steps.** A **detector** finds boxes around each line of text. A **recognizer** reads the letters inside each box. PaddleOCR, a popular open-source OCR kit, is built this way ([repo](https://github.com/PaddlePaddle/PaddleOCR)).
4. **Layout analysis.** A vision model labels each region of the page: title, body text, table, figure, caption, header, footer. Those labels give you reading order (left column before right), headings for chunking, and junk to drop.
5. **Table structure.** For each region marked as a table, a second model finds rows, columns and merged cells, so the table comes out as a real table (HTML or Markdown) and not a soup of numbers.

You rarely build this yourself. Open-source options include Docling ([repo](https://github.com/docling-project/docling)) and MinerU ([repo](https://github.com/opendatalab/MinerU)). Cloud services include AWS Textract, Google Document AI and Azure AI Document Intelligence. They differ in cost, speed, languages, and whether your files leave your network. Test two or three on your ugliest files before you pick.

:::note See one up close
RAGFlow, an open-source RAG product, runs all five steps locally with small models on the CPU. The [RAGFlow ingestion lesson](lesson:ragflow/ingestion) walks through it.
:::

## Keep the labels

While you read, collect **metadata**. That is information about the text rather than the text itself.

- Where it came from (file name, link).
- Its title and section headings.
- A date or version.
- Who may see it.

You will use this metadata for sources in answers, for filtering ("only the 2025 policy"), and for access control. It is far easier to save it now than to reconstruct it later.

```python
doc = {
    "source": "returns.md",
    "title": "Returns and refunds",
    "updated": "2025-03-01",
    "audience": "public",
    "text": "...",
}
```

## Clean in small, visible steps

Write each cleaning step as its own tiny function, and print before and after. It keeps cleaning honest.

```python
import re

def remove_repeated_lines(pages):
    """Drop lines that appear on most pages, like running headers."""
    from collections import Counter
    counts = Counter(line.strip() for page in pages for line in set(page.splitlines()))
    common = {line for line, n in counts.items() if n > len(pages) * 0.6 and line}
    return ["\n".join(l for l in page.splitlines() if l.strip() not in common) for page in pages]

def fix_hyphenation(text):
    return re.sub(r"(\w)-\n(\w)", r"\1\2", text)
```

:::tip
Keep the original file untouched and save the cleaned text beside it. When something looks wrong later, you can tell whether the reader or the cleaner caused it.
:::

## Tables deserve special care

Tables hold the facts people ask about most: prices, limits, dates. A table flattened into a line of numbers is useless.

A reliable approach is to convert each row into a full sentence that carries its column names.

Before:

```text
Standard 4-6 days 6
Express 2 days 15
```

After:

```text
Shipping speed: Standard. Delivery time: 4 to 6 business days. Cost: 6 dollars.
Shipping speed: Express. Delivery time: 2 business days. Cost: 15 dollars.
```

Now a search for "how much is express" has words to match.

## Decide what you will not index

More documents is not always better. Old versions, drafts, and duplicate files all produce confident answers from stale text. Ask for each source:

- Is this the current version?
- Would we be comfortable if the bot quoted it word for word to a customer?
- Does anyone have to be kept from seeing it?

:::warn
If two documents disagree (an old and a new policy), the bot will sometimes quote the old one. Remove old versions or tag them so search can skip them.
:::

:::try
Take one real PDF from your own work and extract its text. Read the first page of output. Write down three things that look wrong. That list is your cleaning plan.
:::

:::check Why save the title and file name alongside the text?
So answers can cite sources, search can filter by date or audience, and you can trace a bad answer back to the file it came from.
:::

:::check A spreadsheet row reads "Pro 20 yes". What would you do before indexing it?
Turn it into a sentence with the column names, such as "Plan: Pro. Monthly price: 20 dollars. Includes support: yes."
:::
