#!/usr/bin/env node
/**
 * Test runner for the JS notecalc engine against shared tests/*.nc files.
 * Extracts the engine from index.html and validates against expected results.
 */
import { readFileSync, readdirSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const htmlPath = join(__dirname, "index.html");
const testsDir = join(__dirname, "..", "tests");

// Extract JS engine from index.html between markers
const html = readFileSync(htmlPath, "utf-8");
const startMarker = "// --- SI Prefixes ---";
const endMarker = "// END NOTECALC ENGINE";
const startIdx = html.indexOf(startMarker);
const endIdx = html.indexOf(endMarker);
if (startIdx === -1 || endIdx === -1) {
  console.error("Could not find engine markers in index.html");
  process.exit(1);
}
const engineCode = html.slice(startIdx, endIdx);

// Evaluate the engine code in a function scope and extract processText
const ns = {};
const wrappedCode = engineCode + "\nreturn { processText, tokenize, evaluateLine, formatResult };";
const factory = new Function(wrappedCode);
const engine = factory();
const { processText } = engine;

const RESULT_RE = /\s{2,}# => .*$/;

let totalTests = 0;
let totalPassed = 0;
let totalFailed = 0;
let failedFiles = [];

const files = readdirSync(testsDir).filter(f => f.endsWith(".nc")).sort();

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
      const expStr = m[0].replace(/^\s+# => /, "");
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
