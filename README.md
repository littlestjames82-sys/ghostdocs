# GhostDocs

**Get your business documents ready for an AI assistant, without sending them anywhere.**

If your shop or office has years of help pages, policy documents, manuals,
and standard procedures, an AI assistant can only use them well if it is
fed the right pages. Feed it everything and it gets slow, expensive, and
confused by old versions. Feed it a hand-picked few pages and nobody can
show later exactly what it was given.

GhostDocs looks through a folder of your documents on your own computer
and prepares a clean, tidy set:

- It lists every document and roughly how big each one is.
- It finds copies and near-copies, and picks the newest dated one as the
  probable current version.
- It holds back any page that looks like it contains personal details
  such as card numbers, and tells you it did.
- It names any file it cannot read instead of quietly skipping it.
- It produces an export folder you can hand to an assistant, plus a list
  (a manifest) of exactly what went in, so the set can be checked later.

By Ghost Developer Studio. GhostDocs is the document companion to
GhostSlice, which does the same job for computer code.

## What GhostDocs does not do

- It does not answer questions. It prepares the reading material. The
  assistant does the answering.
- It does not change, fix, or delete your original documents. Ever.
- It does not send anything over the internet. There are no accounts,
  no uploads, and no tracking. Your documents stay on your machine.
- It does not read handwriting or scanned pages. If a PDF is just a
  picture of a page, GhostDocs will list it as not covered.
- It does not rewrite or summarise your documents with AI. What goes
  into an export is your own words, cut at heading boundaries.

## What it can read

| Format | Covered? |
|---|---|
| Markdown (.md) | Yes |
| Plain text (.txt) | Yes |
| Web pages saved as HTML (.html) | Yes, text only |
| PDF (.pdf) | Only if the PDF has a real text layer |
| Word documents (.docx, .doc) | Not in this version |
| Spreadsheets and slides | Not in this version |
| Scanned or photo PDFs | Not in this version (no OCR) |

Anything not covered is named in the scan and in the report. It is never
silently skipped, and it never appears in an export.

## The three everyday commands

You need Python 3.10 or newer. From the GhostDocs folder:

```bash
# 1. Look at a folder of documents
PYTHONPATH=src python3 -m ghostdocs scan path/to/your-documents

# 2. Make an export folder for an assistant
PYTHONPATH=src python3 -m ghostdocs export path/to/your-documents -o path/to/export

# 3. Make a plain-words report you can open in a browser
PYTHONPATH=src python3 -m ghostdocs report path/to/your-documents -o report.html
```

There is also a `check` command that confirms an export matches its
manifest list. A worked example with a sample document set is in
`examples/WALKTHROUGH.md`.

The export folder contains:

- `PROMPT.md` and `files/` - the documents, ready to hand over.
- `manifest.json` - the list of what went in, with a fingerprint of
  each file so the set can be verified later.
- `chunks.jsonl` - the same material in section-sized pieces, for
  tools that load knowledge a piece at a time. Pieces are cut at
  headings, not at random lengths.

## Two things to know before you trust it

**"Probable current" is a guess.** When GhostDocs finds near-identical
pages it treats the newest dated one as the current version. Usually
that is right. Sometimes the older page is the one you still use. The
report shows its working, so check the picks that matter, especially
for policy and safety documents. If one folder is always the official
source, you can declare it in the settings file and its version wins.

**Sizes are estimates.** GhostDocs counts document size in tokens,
which is how AI assistants measure text. Its token numbers are careful
estimates, labelled as estimates in every output, not exact counts from
any one AI provider.

## Personal details are held back by default

Support documents often contain things customers pasted in: card
numbers, ID numbers, and similar. If a page contains shapes like
those, GhostDocs holds the whole page out of exports by default and
lists it in the report by file name and type of finding only. The
actual values are never printed in a scan, a report, or an export.

Including a held-back page is possible only with an explicit
`--allow-sensitive` flag on export, and the manifest records that you
did. Think carefully before using it.

## Settings (optional)

A file named `.ghostdocs.json` in your document folder can:

- Include or exclude files by pattern.
- Mark a folder as the authoritative source for duplicates.
- Set how each document is included: in full, headings only, or
  excluded.
- Choose whether older duplicate versions stay out of exports (the
  default) while still showing in reports.

No settings file is needed to get started.

## Your responsibility

Only run GhostDocs on documents you have the right to process, for
example your own business documents or a client's documents they have
asked you to prepare. Prepared for Ghost Developer Studio, October
2026. Pricing and any public release are not decided yet.
