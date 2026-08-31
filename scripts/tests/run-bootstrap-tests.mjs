import { spawnSync } from 'node:child_process';

const tests = process.platform === 'win32'
  ? [['powershell.exe', ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', 'scripts/tests/bootstrap.test.ps1']]]
  : [
      ['bash', ['scripts/tests/bootstrap.test.sh']],
      ['bash', ['scripts/tests/run-crew-ticket.test.sh']],
      ['bash', ['scripts/tests/ralph.test.sh']],
      [process.execPath, ['scripts/tests/powershell-bootstrap.test.mjs']],
    ];

for (const [command, args] of tests) {
  const result = spawnSync(command, args, { stdio: 'inherit' });
  if (result.error) {
    throw result.error;
  }
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}
