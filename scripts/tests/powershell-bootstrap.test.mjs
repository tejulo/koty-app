import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const repositoryRoot = resolve(fileURLToPath(new URL('../..', import.meta.url)));

async function readScript(path) {
  return readFile(resolve(repositoryRoot, path), 'utf8');
}

const bootstrap = await readScript('scripts/bootstrap.ps1');
const doctor = await readScript('scripts/doctor.ps1');

assert.match(bootstrap, /install --id jdx\.mise --exact/);
assert.match(bootstrap, /\[string\]\$MisePath/);
assert.match(bootstrap, /\$misePath install/);
assert.match(bootstrap, /\$misePath exec -- pnpm install --frozen-lockfile/);
assert.match(bootstrap, /\$misePath exec -- uv sync --project crewai --frozen/);
assert.match(bootstrap, /doctor\.ps1/);
assert.match(bootstrap, /\$doctorPath -NoExit -MisePath \$misePath/);
assert.match(bootstrap, /mise activate pwsh/);
assert.match(doctor, /\[string\]\$MisePath/);
assert.match(doctor, /pnpm install --frozen-lockfile --lockfile-only/);
assert.match(doctor, /uv lock --project crewai --check/);
assert.match(doctor, /import crew; print\('crew import ok'\)/);

console.log('PASS: PowerShell bootstrap scripts');
