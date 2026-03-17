const { spawn } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

const PROJECT_ROOT = path.resolve(__dirname, '..', '..');

function resolvePythonBin() {
  return process.env.OPENCLAW_BRAIN_PYTHON || process.env.PYTHON || 'python';
}

function inferWorkspaceRootFromProjectRoot(projectRoot) {
  const normalized = path.normalize(projectRoot);
  const marker = `${path.sep}projects${path.sep}`;
  const index = normalized.lastIndexOf(marker);
  if (index >= 0) {
    return normalized.slice(0, index);
  }
  return null;
}

function resolveStoreRoot(event = {}) {
  const workspaceDir = event?.context?.cfg?.workspace?.dir || event?.cfg?.workspace?.dir || process.env.OPENCLAW_WORKSPACE_DIR;
  if (workspaceDir) {
    return path.join(workspaceDir, 'data', 'openclaw-brain');
  }
  const inferredWorkspace = inferWorkspaceRootFromProjectRoot(PROJECT_ROOT);
  return inferredWorkspace
    ? path.join(inferredWorkspace, 'data', 'openclaw-brain')
    : path.join(PROJECT_ROOT, 'data', 'openclaw-brain');
}

function resolveCliPath() {
  const workspaceRoot = inferWorkspaceRootFromProjectRoot(PROJECT_ROOT) || PROJECT_ROOT;
  const candidates = [
    process.env.OPENCLAW_BRAIN_CLI_PATH,
    path.join(PROJECT_ROOT, 'hooks', 'brain_cli.py'),
    path.join(PROJECT_ROOT, 'projects', 'openclaw-brain', 'hooks', 'brain_cli.py'),
    path.join(workspaceRoot, 'projects', 'openclaw-brain', 'hooks', 'brain_cli.py'),
    path.join(workspaceRoot, 'hooks', 'brain_cli.py'),
  ].filter(Boolean).map((value) => path.resolve(String(value)));

  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) return candidate;
  }

  return candidates[0];
}

async function callBrainCli(payload) {
  return await new Promise((resolve, reject) => {
    const cliPath = resolveCliPath();
    const child = spawn(resolvePythonBin(), [cliPath], {
      cwd: path.dirname(cliPath),
      stdio: ['pipe', 'pipe', 'pipe'],
      env: {
        ...process.env,
        PYTHONIOENCODING: process.env.PYTHONIOENCODING || 'utf-8',
        OPENCLAW_WORKSPACE_DIR: inferWorkspaceRootFromProjectRoot(PROJECT_ROOT) || process.env.OPENCLAW_WORKSPACE_DIR,
      },
    });

    let stdout = '';
    let stderr = '';

    child.stdout.on('data', (chunk) => {
      stdout += String(chunk);
    });

    child.stderr.on('data', (chunk) => {
      stderr += String(chunk);
    });

    child.on('error', (error) => {
      reject(error);
    });

    child.on('close', (code) => {
      if (code !== 0) {
        reject(new Error(stderr || `brain_cli exited with code ${code}`));
        return;
      }
      try {
        resolve(stdout ? JSON.parse(stdout) : {});
      } catch (error) {
        reject(new Error(`Failed to parse brain_cli output: ${error.message}\n${stdout}`));
      }
    });

    child.stdin.write(JSON.stringify(payload));
    child.stdin.end();
  });
}

async function buildBrainContext(event, query, options = {}) {
  return await callBrainCli({
    action: 'build-context',
    store_root: resolveStoreRoot(event),
    backend: options.backend,
    query,
    recent_messages: options.recent_messages || [],
    recent_message_ids: options.recent_message_ids || [],
    limit: options.limit || 5,
    context: options.context || {},
    emotion: options.emotion,
  });
}

module.exports = {
  PROJECT_ROOT,
  resolveCliPath,
  resolveStoreRoot,
  callBrainCli,
  buildBrainContext,
};
