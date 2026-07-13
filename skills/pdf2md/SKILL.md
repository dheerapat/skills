---
name: pdf2md
description: Convert PDF files to Markdown using @opendocsg/pdf2md. Use when asked to convert a PDF to Markdown or extract text from a PDF.
---

# pdf2md

Converts a single PDF file to Markdown.

## Setup

Dependencies installed automatically by pi when the package is installed.

## Usage

```bash
node <skill-dir>/scripts/convert.js <input.pdf> [output.md]
```

If `output.md` is omitted, prints to stdout.

### Examples

```bash
# Write to file
node <skill-dir>/scripts/convert.js ~/documents/report.pdf report.md

# Print to stdout
node <skill-dir>/scripts/convert.js ~/documents/report.pdf
```
