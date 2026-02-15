#!/usr/bin/env node
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const here = __dirname;

// Extract engine script from index.html (first <script> block, up to END CALCED ENGINE)
const html = fs.readFileSync(path.join(here, "..", "web", "index.html"), "utf8");
const scriptStart = html.indexOf("<script>") + "<script>".length;
const engineEnd = html.indexOf("// END CALCED ENGINE");
const engineSrc = html.slice(scriptStart, engineEnd);

// Run engine in a context that exposes the functions
const ctx = { exports: {} };
vm.createContext(ctx);
vm.runInContext(engineSrc, ctx);
const { classifyLine, evaluateLine } = ctx;

let failures = 0;

// --- classify vectors ---
const classifyVectors = JSON.parse(fs.readFileSync(path.join(here, "classify_vectors.json"), "utf8"));
for (let i = 0; i < classifyVectors.length; i++) {
  const v = classifyVectors[i];
  const result = classifyLine(v.text, v.variables);
  const expected = v.expected;
  if (JSON.stringify(result) !== JSON.stringify(expected)) {
    console.log(`FAIL classify vector ${i}: ${JSON.stringify(v.text)}`);
    if (v.note) console.log(`  note: ${v.note}`);
    console.log(`  expected: ${JSON.stringify(expected)}`);
    console.log(`  got:      ${JSON.stringify(result)}`);
    failures++;
  }
}

// --- evaluate vectors ---
const evaluateVectors = JSON.parse(fs.readFileSync(path.join(here, "evaluate_vectors.json"), "utf8"));
for (let i = 0; i < evaluateVectors.length; i++) {
  const v = evaluateVectors[i];
  const [result] = evaluateLine(v.text, v.variables);
  const expected = v.expected;
  if (result !== expected) {
    console.log(`FAIL evaluate vector ${i}: ${JSON.stringify(v.text)}`);
    console.log(`  expected: ${JSON.stringify(expected)}`);
    console.log(`  got:      ${JSON.stringify(result)}`);
    failures++;
  }
}

const total = classifyVectors.length + evaluateVectors.length;
if (failures) {
  console.log(`\n${failures}/${total} vectors failed`);
  process.exit(1);
} else {
  console.log(`All ${total} vectors passed`);
}
