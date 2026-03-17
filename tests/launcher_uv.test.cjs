const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');

const { __internal } = require('../bin/ds.js');

test('createPythonRuntimePlan prefers a valid active conda interpreter', () => {
  const plan = __internal.createPythonRuntimePlan({
    condaProbes: [
      {
        ok: true,
        executable: '/opt/conda/envs/ds311/bin/python',
        realExecutable: '/opt/conda/envs/ds311/bin/python',
        version: '3.11.9',
        major: 3,
        minor: 11,
        patch: 9,
        source: 'conda',
        sourceLabel: 'conda:ds311',
      },
    ],
    pathProbes: [
      {
        ok: true,
        executable: '/usr/bin/python3',
        realExecutable: '/usr/bin/python3',
        version: '3.12.2',
        major: 3,
        minor: 12,
        patch: 2,
        source: 'path',
        sourceLabel: 'path',
      },
    ],
    minimumVersionRequest: '3.11',
  });

  assert.equal(plan.runtimeKind, 'system');
  assert.equal(plan.source, 'conda');
  assert.equal(plan.selectedProbe.executable, '/opt/conda/envs/ds311/bin/python');
});

test('createPythonRuntimePlan falls back to uv-managed python when active conda is too old', () => {
  const plan = __internal.createPythonRuntimePlan({
    condaProbes: [
      {
        ok: true,
        executable: '/opt/conda/envs/legacy/bin/python',
        realExecutable: '/opt/conda/envs/legacy/bin/python',
        version: '3.10.14',
        major: 3,
        minor: 10,
        patch: 14,
        source: 'conda',
        sourceLabel: 'conda:legacy',
      },
    ],
    pathProbes: [
      {
        ok: true,
        executable: '/usr/bin/python3',
        realExecutable: '/usr/bin/python3',
        version: '3.12.2',
        major: 3,
        minor: 12,
        patch: 2,
        source: 'path',
        sourceLabel: 'path',
      },
    ],
    minimumVersionRequest: '3.11',
  });

  assert.equal(plan.runtimeKind, 'managed');
  assert.equal(plan.source, 'conda');
  assert.equal(plan.rejectedProbe.version, '3.10.14');
  assert.equal(plan.minimumVersionRequest, '3.11');
});

test('buildUvRuntimeEnv pins uv state inside the DeepScientist runtime tree', () => {
  const home = path.join(path.sep, 'tmp', 'DeepScientistHome');
  const env = __internal.buildUvRuntimeEnv(home, { EXTRA_MARKER: '1' });

  assert.equal(env.EXTRA_MARKER, '1');
  assert.equal(env.UV_PROJECT_ENVIRONMENT, path.join(home, 'runtime', 'python-env'));
  assert.equal(env.UV_CACHE_DIR, path.join(home, 'runtime', 'uv-cache'));
  assert.equal(env.UV_PYTHON_INSTALL_DIR, path.join(home, 'runtime', 'python'));
});

test('runtimePythonPath resolves to the managed uv environment interpreter', () => {
  const home = path.join(path.sep, 'tmp', 'DeepScientistHome');
  const interpreter = __internal.runtimePythonPath(home);

  assert.ok(interpreter.includes(path.join('runtime', 'python-env')));
  assert.ok(
    interpreter.endsWith(path.join('bin', 'python'))
      || interpreter.endsWith(path.join('Scripts', 'python.exe'))
  );
});

test('compareVersions follows semantic numeric ordering', () => {
  assert.equal(__internal.compareVersions('1.5.2', '1.5.2'), 0);
  assert.equal(__internal.compareVersions('1.5.3', '1.5.2'), 1);
  assert.equal(__internal.compareVersions('1.6.0', '1.12.0'), -1);
});

test('detectInstallMode distinguishes npm packages from source checkouts', () => {
  assert.equal(
    __internal.detectInstallMode(path.join(path.sep, 'usr', 'lib', 'node_modules', '@researai', 'deepscientist')),
    'npm-package'
  );
  assert.equal(
    __internal.detectInstallMode(path.join(path.sep, 'ssdwork', 'deepscientist', 'DeepScientist')),
    'source-checkout'
  );
});
