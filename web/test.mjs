#!/usr/bin/env node
/**
 * Test runner for the JS calced engine.
 * Extracts the engine from index.html and runs:
 *   1. Unit vectors from tests/classify_vectors.json and tests/evaluate_vectors.json
 *   2. Integration tests from tests/*.md
 */
import { readFileSync, readdirSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const htmlPath = join(__dirname, "index.html");
const testsDir = join(__dirname, "..", "tests");

// Extract JS engine from index.html between markers
const html = readFileSync(htmlPath, "utf-8");
const startMarker = "// -- CALCED ENGINE BEGIN --";
const endMarker = "// END CALCED ENGINE";
const startIdx = html.indexOf(startMarker);
const endIdx = html.indexOf(endMarker);
if (startIdx === -1 || endIdx === -1) {
  console.error("Could not find engine markers in index.html");
  process.exit(1);
}
const engineCode = html.slice(startIdx, endIdx);

// Evaluate the engine code in a function scope and extract exports
const wrappedCode = engineCode + "\nreturn { processText, evaluateLine, classifyLine, formatResult };";
const engine = new Function(wrappedCode)();
const { processText, evaluateLine, classifyLine } = engine;

// --- Unit vector tests ---
let unitFailures = 0;

const classifyVectors = JSON.parse(readFileSync(join(testsDir, "classify_vectors.json"), "utf8"));
for (let i = 0; i < classifyVectors.length; i++) {
  const v = classifyVectors[i];
  const result = classifyLine(v.text, v.variables);
  if (JSON.stringify(result) !== JSON.stringify(v.expected)) {
    console.error(`FAIL classify vector ${i}: ${JSON.stringify(v.text)}`);
    if (v.note) console.error(`  note: ${v.note}`);
    console.error(`  expected: ${JSON.stringify(v.expected)}`);
    console.error(`  got:      ${JSON.stringify(result)}`);
    unitFailures++;
  }
}

const evaluateVectors = JSON.parse(readFileSync(join(testsDir, "evaluate_vectors.json"), "utf8"));
for (let i = 0; i < evaluateVectors.length; i++) {
  const v = evaluateVectors[i];
  const [result] = evaluateLine(v.text, v.variables);
  const resultVal = result !== null && result !== "TOTAL"
    ? (result._isDate ? `${result.y}-${String(result.m).padStart(2,"0")}-${String(result.d).padStart(2,"0")}` : result.toNumber())
    : result;
  if (resultVal !== v.expected) {
    console.error(`FAIL evaluate vector ${i}: ${JSON.stringify(v.text)}`);
    console.error(`  expected: ${JSON.stringify(v.expected)}`);
    console.error(`  got:      ${JSON.stringify(resultVal)}`);
    unitFailures++;
  }
}

const unitTotal = classifyVectors.length + evaluateVectors.length;
if (unitFailures) {
  console.log(`FAIL unit vectors (${unitTotal - unitFailures}/${unitTotal} passed)`);
} else {
  console.log(`PASS unit vectors (${unitTotal}/${unitTotal} passed)`);
}


const RESULT_RE = /\s+# => .*$/;
const INDICATOR_RE = / [│┘]$/;

let totalTests = 0;
let totalPassed = 0;
let totalFailed = 0;
let failedFiles = [];

const files = readdirSync(testsDir).filter(f => f.endsWith(".md")).sort();

for (const file of files) {
  const content = readFileSync(join(testsDir, file), "utf-8");
  const lines = content.split("\n");
  // Remove trailing empty line from split
  if (lines.length > 0 && lines[lines.length - 1] === "") lines.pop();

  // Build pure input (strip # => results) and collect expected results
  const inputLines = [];
  const expected = []; // {lineNum, expected} or null
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const m = line.match(RESULT_RE);
    if (m) {
      const clean = line.replace(RESULT_RE, "").trimEnd();
      inputLines.push(clean);
      const expStr = m[0].replace(/^\s+# => /, "").replace(INDICATOR_RE, "").trimEnd();
      expected.push({ lineNum: i + 1, expected: expStr });
    } else {
      inputLines.push(line);
      expected.push(null);
    }
  }

  const pureInput = inputLines.join("\n");
  const results = processText(pureInput);

  let filePassed = 0;
  let fileFailed = 0;

  for (let i = 0; i < expected.length; i++) {
    if (expected[i] === null) continue;
    totalTests++;
    const exp = expected[i].expected;
    const got = results[i] && results[i].result !== null ? results[i].result : null;
    if (got === exp) {
      filePassed++;
      totalPassed++;
    } else {
      fileFailed++;
      totalFailed++;
      const lineNum = expected[i].lineNum;
      console.error(`  FAIL ${file}:${lineNum}: expected "${exp}", got "${got}"`);
    }
  }

  const status = fileFailed === 0 ? "PASS" : "FAIL";
  const counts = `${filePassed + fileFailed} tests, ${filePassed} passed`;
  console.log(`${status} ${file} (${counts})`);
  if (fileFailed > 0) failedFiles.push(file);
}

console.log();
console.log(`Total: ${totalTests} tests, ${totalPassed} passed, ${totalFailed} failed`);

if (totalFailed > 0) {
  process.exit(1);
}
