#!/usr/bin/env node
const pdf2md = require("@opendocsg/pdf2md");
const fs = require("fs");
const path = require("path");

const input = process.argv[2];
const output = process.argv[3];

if (!input) {
  console.error("Usage: convert.js <input.pdf> [output.md]");
  process.exit(1);
}

const buf = fs.readFileSync(path.resolve(input));
pdf2md(new Uint8Array(buf))
  .then((text) => {
    if (output) {
      fs.writeFileSync(path.resolve(output), text);
      console.log(`Wrote ${output}`);
    } else {
      process.stdout.write(text);
    }
  })
  .catch((err) => {
    console.error("Conversion failed:", err.message);
    process.exit(1);
  });
