import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const PLUGIN_ROOT = __dirname;
const STATE_ROOT = path.resolve(__dirname, "..", "..", "..", "..");

const DEFAULT_CONFIG = {
  enabled: true,
  backend: "jsonl",
  limit: 4,
  recentWindow: 8,
  minQueryLength: 2,
  heading: "[Brain Recall]",
  cliPath: null,
  projectRoot: null,
};

function normalizeConfig(pluginConfig) {
  return {
    ...DEFAULT_CONFIG,
    ...(pluginConfig || {}),
  };
}

function resolvePythonBin() {
  return process.env.OPENCLAW_BRAIN_PYTHON || process.env.PYTHON || "python";
}

function resolveProjectRoot(cfg = {}) {
  const explicit = cfg.projectRoot || process.env.OPENCLAW_BRAIN_PROJECT_ROOT;
  if (explicit) return path.resolve(String(explicit));
  return PLUGIN_ROOT;
}

function resolveCliPath(cfg = {}) {
  const projectRoot = resolveProjectRoot(cfg);
  const candidates = [
    cfg.cliPath,
    process.env.OPENCLAW_BRAIN_CLI_PATH,
    path.join(PLUGIN_ROOT, "hooks", "brain_cli.py"),
    path.join(projectRoot, "hooks", "brain_cli.py"),
    path.join(STATE_ROOT, "workspace", "projects", "openclaw-brain", "hooks", "brain_cli.py"),
    path.join(STATE_ROOT, "projects", "openclaw-brain", "hooks", "brain_cli.py"),
    path.join(STATE_ROOT, "hooks", "brain_cli.py"),
  ].filter(Boolean).map((value) => path.resolve(String(value)));

  for (const candidate of candidates) {
    if (existsSync(candidate)) return candidate;
  }
  return candidates[0];
}

function resolveStoreRoot(ctx = {}, cfg = {}) {
  const workspaceDir = ctx?.cfg?.workspace?.dir || process.env.OPENCLAW_WORKSPACE_DIR;
  if (workspaceDir) {
    return path.join(workspaceDir, "data", "openclaw-brain");
  }
  const projectRoot = resolveProjectRoot(cfg);
  return path.join(projectRoot, "data", "openclaw-brain");
}

async function callBrainCli(payload, cfg = {}) {
  return await new Promise((resolve, reject) => {
    const cliPath = resolveCliPath(cfg);
    const child = spawn(resolvePythonBin(), [cliPath], {
      cwd: path.dirname(cliPath),
      stdio: ["pipe", "pipe", "pipe"],
      env: {
        ...process.env,
        PYTHONIOENCODING: process.env.PYTHONIOENCODING || 'utf-8',
        OPENCLAW_BRAIN_PROJECT_ROOT: resolveProjectRoot(cfg),
      },
    });

    let stdout = "";
    let stderr = "";

    child.stdout.on("data", (chunk) => {
      stdout += String(chunk);
    });

    child.stderr.on("data", (chunk) => {
      stderr += String(chunk);
    });

    child.on("error", reject);
    child.on("close", (code) => {
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

function extractTextParts(value) {
  if (!value) return [];
  if (typeof value === "string") return [value];
  if (Array.isArray(value)) {
    return value.flatMap((item) => extractTextParts(item));
  }
  if (typeof value === "object") {
    if (typeof value.text === "string") return [value.text];
    if (typeof value.content === "string") return [value.content];
    if (Array.isArray(value.content)) return extractTextParts(value.content);
    if (typeof value.value === "string") return [value.value];
  }
  return [];
}

function getMessageText(message) {
  const parts = [];
  if (typeof message === "string") return message.trim();
  if (message?.content) parts.push(...extractTextParts(message.content));
  if (message?.text) parts.push(...extractTextParts(message.text));
  if (message?.message?.content) parts.push(...extractTextParts(message.message.content));
  return parts.join("\n").trim();
}

function getMessageId(message) {
  return message?.id || message?.message_id || message?.message?.id || message?.message?.message_id || null;
}

function getRole(message) {
  return message?.role || message?.message?.role || null;
}

function collectRecentMessages(messages, limit) {
  const recent = [];
  for (let i = messages.length - 1; i >= 0 && recent.length < limit; i -= 1) {
    const msg = messages[i];
    const role = getRole(msg);
    if (role !== "user" && role !== "assistant") continue;
    const text = getMessageText(msg);
    if (!text) continue;
    recent.push({
      role,
      text,
      id: getMessageId(msg),
    });
  }
  return recent.reverse();
}

function findLatestUserQuery(messages, minQueryLength) {
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    const msg = messages[i];
    if (getRole(msg) !== "user") continue;
    const text = getMessageText(msg);
    if (text && text.trim().length >= minQueryLength) {
      return text.trim();
    }
  }
  return "";
}

function normalizeHeading(text, fallback) {
  if (!text) return fallback;
  const trimmed = String(text).trim();
  if (!trimmed) return fallback;
  return trimmed.startsWith("[") ? trimmed : `[${trimmed}]`;
}

const plugin = {
  id: "brain-prompt",
  name: "Brain Prompt Injector",
  description: "Injects compact recalled memory context before prompt build.",
  register(api) {
    api.on("before_prompt_build", async (params, ctx) => {
      const cfg = normalizeConfig(api.pluginConfig);
      if (!cfg.enabled) return {};

      const messages = Array.isArray(params?.messages) ? params.messages : [];
      const query = findLatestUserQuery(messages, cfg.minQueryLength);
      if (!query) return {};

      const recent = collectRecentMessages(messages, cfg.recentWindow);
      const recentMessages = recent.map((item) => item.text);
      const recentMessageIds = recent.map((item) => item.id).filter(Boolean);

      try {
        const result = await callBrainCli({
          action: "build-context",
          store_root: resolveStoreRoot(ctx, cfg),
          backend: cfg.backend,
          query,
          recent_messages: recentMessages,
          recent_message_ids: recentMessageIds,
          limit: cfg.limit,
          context: {
            sessionKey: ctx?.sessionKey,
            channel: ctx?.channel,
          },
        }, cfg);

        if (!result?.context_text) {
          return {};
        }

        const heading = normalizeHeading(cfg.heading, DEFAULT_CONFIG.heading);
        const contextText = String(result.context_text);
        const finalText = contextText.startsWith(heading)
          ? contextText
          : contextText.replace(/^\[Brain Recall\]/, heading);

        api.logger?.debug?.(
          `brain-prompt injected ${result.count || 0} recall items from ${result.resolved_store_root || "brain store"}`,
        );
        return {
          prependSystemContext: finalText,
        };
      } catch (error) {
        api.logger?.warn?.(`brain-prompt injection failed: ${error.message}`);
        return {};
      }
    });
  },
};

export default plugin;
export {
  getMessageText,
  getMessageId,
  getRole,
  collectRecentMessages,
  findLatestUserQuery,
};
