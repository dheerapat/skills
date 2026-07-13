---
name: pdf2md
description: Convert PDF files to Markdown. Use when user mentioned .pdf file, asked to convert a PDF to Markdown, or you want to extract text from a PDF.
---

# pdf2md

Converts a single PDF file to Markdown.

## Setup

Install dependency first using npm

```bash
cd <skill-dir> && npm install
```

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
