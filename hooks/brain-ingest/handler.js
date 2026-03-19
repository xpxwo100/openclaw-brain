/**
 * Brain Ingest Hook Handler
 *
 * Unified ingress hook for both message events and tool events.
 * Keeps one config surface, one persistence path, and one Python bridge.
 */

const { callBrainCli, resolveStoreRoot } = require('../_lib/brain-bridge.js');
const fs = require('node:fs');
const path = require('node:path');

const log = {
  info: (...args) => console.info('[brain-ingest]', ...args),
  warn: (...args) => console.warn('[brain-ingest]', ...args),
  error: (...args) => console.error('[brain-ingest]', ...args),
};

function writeDebug() {}

const DEFAULT_CONFIG = {
  enabled: true,
  backend: 'jsonl',
  attention_threshold: 0.7,
  working_memory_limit: 10,
  auto_consolidate: true,
  consolidation_interval: 12,
  consolidation_stale_minutes: 30,
  extract_knowledge: true,
  max_history: 100,
  knowledge_threshold: 0.5,
  persist_all_messages: true,
};

const KEYWORDS = {
  remember: 0.8,
  important: 0.9,
  task: 0.7,
  deadline: 0.9,
  meeting: 0.6,
  note: 0.7,
  '记住': 0.8,
  '重要': 0.9,
  '任务': 0.7,
  '截止': 0.9,
  '会议': 0.6,
  '开会': 0.7,
  '有会': 0.7,
  '喜欢': 0.6,
};

const ASSISTANT_MEMORY_RE = /(我会|我将|稍后|接下来|下一步|我先|我准备|已经|完成|修复|更新|处理|搞定|确认|验证|排查|结论是|决定|根因是|主因是|当前状态是|目前状态是|现在状态是|i will|i'll|let me|going to|done|fixed|updated|completed|verified|confirmed|checked|decision|root cause|current state|the conclusion)/i;
const PREFERENCE_RE = /(我喜欢被叫|叫我|称呼我|call me|nickname|偏好)/i;
const TIME_RE = /(今天|明天|后天|今晚|明早|明晚|周[一二三四五六日天]|星期[一二三四五六日天]|上午|下午|\d+点|\d+:\d+)/;
const TASK_RE = /(deadline|会议|开会|有会|meeting|todo|待办|任务)/i;

let messageCount = 0;
let toolEventCount = 0;
const recentMessageIds = new Map();
const RECENT_MESSAGE_WINDOW_MS = 5 * 60 * 1000;

function pruneRecentMessageIds(now = Date.now()) {
  for (const [key, ts] of recentMessageIds.entries()) {
    if (now - ts > RECENT_MESSAGE_WINDOW_MS) recentMessageIds.delete(key);
  }
}

function markMessageSeen(messageId, now = Date.now()) {
  if (!messageId || messageId === 'unknown') return false;
  pruneRecentMessageIds(now);
  if (recentMessageIds.has(messageId)) return true;
  recentMessageIds.set(messageId, now);
  return false;
}

function scoreMessage(content) {
  if (!content) return 0;

  const lowerContent = content.toLowerCase();
  let score = 0;

  const length = content.length;
  if (length > 30 && length < 500) score += 0.2;
  else if (length >= 500) score += 0.2;

  for (const [keyword, weight] of Object.entries(KEYWORDS)) {
    if (lowerContent.includes(keyword)) score += weight * 0.1;
  }

  if (/^(记住|remember)[:：]/i.test(content.trim())) score += 0.55;
  if (PREFERENCE_RE.test(content)) score += 0.25;
  if (TIME_RE.test(content)) score += 0.2;
  if (TASK_RE.test(content)) score += 0.2;
  if (content.includes('?') || content.includes('？')) score += 0.2;
  if (content.includes('!') || content.includes('！')) score += 0.1;

  return Math.min(score, 1.0);
}

function readHookConfig(cfg, name) {
  return (
    cfg?.[`hooks?.${name}`]
    || cfg?.hooks?.[name]
    || cfg?.hooks?.internal?.entries?.[name]?.config
    || cfg?.hooks?.internal?.entries?.[name]
    || cfg?.hooks?.entries?.[name]?.config
    || cfg?.hooks?.entries?.[name]
    || cfg?.[`hooks.internal.entries.${name}.config`]
    || cfg?.[`hooks.entries.${name}.config`]
    || {}
  );
}

function readDirectHookConfig(cfg) {
  if (!cfg || typeof cfg !== 'object' || Array.isArray(cfg)) return {};

  const keys = Object.keys(DEFAULT_CONFIG);
  const direct = {};

  for (const key of keys) {
    if (cfg[key] !== undefined) direct[key] = cfg[key];
  }

  return direct;
}

function findOpenClawConfigPath() {
  let current = __dirname;
  for (let i = 0; i < 8; i += 1) {
    const candidate = path.join(current, 'openclaw.json');
    if (fs.existsSync(candidate)) return candidate;
    const parent = path.dirname(current);
    if (parent === current) break;
    current = parent;
  }
  return null;
}

let cachedDiskConfig = null;

function readHookConfigFromDisk(name) {
  if (cachedDiskConfig) {
    return readHookConfig(cachedDiskConfig, name);
  }

  const configPath = findOpenClawConfigPath();
  if (!configPath) return {};

  try {
    cachedDiskConfig = JSON.parse(fs.readFileSync(configPath, 'utf8'));
    return readHookConfig(cachedDiskConfig, name);
  } catch (error) {
    log.warn(`Failed to read OpenClaw config from disk: ${error.message}`);
    return {};
  }
}

function resolveConfig(cfg) {
  const direct = readDirectHookConfig(cfg);
  const unified = readHookConfig(cfg, 'brain-ingest');
  const legacyMessage = readHookConfig(cfg, 'brain-message');
  const legacyTool = readHookConfig(cfg, 'brain-tool-call');
  const disk = readHookConfigFromDisk('brain-ingest');
  return {
    ...DEFAULT_CONFIG,
    ...disk,
    ...legacyMessage,
    ...legacyTool,
    ...unified,
    ...direct,
  };
}

function resolveRuntimeConfig(event = {}) {
  const candidates = [
    event?.hookConfig,
    event?.context?.hookConfig,
    event?.context?.hook?.config,
    event?.context?.config,
    event?.config,
    event?.context?.cfg,
    event?.cfg,
    {},
  ];

  for (const candidate of candidates) {
    const resolved = resolveConfig(candidate);
    if (resolved.backend !== DEFAULT_CONFIG.backend) return resolved;
    if (resolved.enabled !== DEFAULT_CONFIG.enabled) return resolved;
    if (Object.keys(readDirectHookConfig(candidate)).length > 0) return resolved;
    if (readHookConfig(candidate, 'brain-ingest') && Object.keys(readHookConfig(candidate, 'brain-ingest')).length > 0) return resolved;
  }

  return resolveConfig(candidates[0]);
}

function pickFirstString(...values) {
  for (const value of values) {
    if (typeof value === 'string' && value.trim()) return value.trim();
  }
  return '';
}

function normalizeMessageEvent(event = {}) {
  const ctx = event.context || {};
  const metadata = ctx.metadata || {};
  const message = event.message || event.data?.message || event.data || {};
  const action = event.action || '';
  const content = pickFirstString(
    message.content,
    message.text,
    message.body,
    ctx.content,
    ctx.text,
  );

  const role = pickFirstString(
    message.role,
    message.message?.role,
    ctx.role,
    action === 'received' ? 'user' : '',
    action === 'sent' ? 'assistant' : '',
  ) || 'user';

  const author = pickFirstString(
    message.author?.name,
    message.sender,
    ctx.from,
    metadata.senderName,
    metadata.senderUsername,
    metadata.senderId,
    role === 'assistant' ? 'assistant' : 'unknown',
  );

  const channel = pickFirstString(
    message.channel,
    ctx.channel,
    metadata.surface,
    metadata.provider,
    metadata.channelName,
    'unknown',
  );

  const messageId = pickFirstString(
    message.id,
    message.message_id,
    ctx.messageId,
    metadata.messageId,
    'unknown',
  );

  return { content, author, role, channel, messageId, action };
}

async function handleMessageEvent(event, hookConfig) {
  writeDebug(event, { stage: 'handleMessageEvent:start' });
  const threshold = hookConfig.attention_threshold ?? DEFAULT_CONFIG.attention_threshold;
  const memoryLimit = hookConfig.working_memory_limit ?? DEFAULT_CONFIG.working_memory_limit;
  const normalized = normalizeMessageEvent(event);
  const { content, author, role, channel, messageId, action } = normalized;
  const importance = scoreMessage(content);
  messageCount += 1;

  const result = {
    event_kind: 'message',
    action,
    message_id: messageId,
    importance,
    remembered: false,
    location: null,
  };

  if (action === 'preprocessed') {
    result.skipped = 'preprocessed';
    writeDebug(event, { stage: 'message:skip-preprocessed', result });
    return result;
  }

  if (!content) {
    result.skipped = 'empty-content';
    return result;
  }

  const persistAllMessages = hookConfig.persist_all_messages ?? DEFAULT_CONFIG.persist_all_messages;
  const looksLikeAssistantMemory = role === 'assistant' && ASSISTANT_MEMORY_RE.test(content);
  const forcePersist = Boolean(
    (persistAllMessages && action === 'received' && content)
    || (looksLikeAssistantMemory && action === 'sent' && content)
  );

  if (action === 'received' && markMessageSeen(messageId)) {
    result.skipped = 'duplicate-message-id';
    writeDebug(event, { stage: 'message:skip-duplicate', result });
    return result;
  }

  if (importance < threshold && !forcePersist) {
    result.skipped = 'below-threshold';
    return result;
  }

  if (forcePersist && importance < threshold) {
    result.forced = looksLikeAssistantMemory ? 'assistant_memory' : 'persist_all_messages';
  }

  const batchSize = hookConfig.consolidation_interval ?? DEFAULT_CONFIG.consolidation_interval;
  const staleMinutes = hookConfig.consolidation_stale_minutes ?? DEFAULT_CONFIG.consolidation_stale_minutes;

  const cliResult = await callBrainCli({
    action: 'remember-message',
    store_root: resolveStoreRoot(event),
    backend: hookConfig.backend ?? DEFAULT_CONFIG.backend,
    attention_threshold: threshold,
    working_memory_capacity: memoryLimit,
    message: {
      content,
      author,
      role,
      channel,
      message_id: messageId,
    },
    importance,
    mode: 'episodic',
    persist_raw_message: persistAllMessages,
    auto_consolidate: hookConfig.auto_consolidate ?? DEFAULT_CONFIG.auto_consolidate,
    auto_consolidate_batch_size: batchSize,
    auto_consolidate_stale_minutes: staleMinutes,
  });

  result.remembered = Boolean(cliResult.remembered);
  result.location = result.remembered ? 'brain' : null;
  if (cliResult.consolidation) result.consolidation = cliResult.consolidation;

  log.info(`Message persisted to brain store (backend: ${hookConfig.backend ?? DEFAULT_CONFIG.backend}, importance: ${importance.toFixed(2)}, action: ${action || 'unknown'}): ${messageId}`);
  writeDebug(event, { stage: 'message:remembered', result });
  return result;
}

async function handleToolEvent(event, hookConfig) {
  const toolCall = event.tool_call || event.tool_result || event.data?.tool_call || event.data?.tool_result || event;
  const toolName = toolCall.name || toolCall.tool || 'unknown';
  const arguments_ = toolCall.arguments || toolCall.args || {};
  const result = toolCall.result;
  const timestamp = toolCall.timestamp || new Date().toISOString();
  const success = toolCall.success ?? true;
  toolEventCount += 1;

  const cliResult = await callBrainCli({
    action: 'remember-tool',
    store_root: resolveStoreRoot(event),
    backend: hookConfig.backend ?? DEFAULT_CONFIG.backend,
    extract_knowledge: hookConfig.extract_knowledge ?? DEFAULT_CONFIG.extract_knowledge,
    auto_consolidate: hookConfig.auto_consolidate ?? DEFAULT_CONFIG.auto_consolidate,
    auto_consolidate_batch_size: Math.max(1, Math.floor((hookConfig.max_history ?? DEFAULT_CONFIG.max_history) / 10)),
    auto_consolidate_stale_minutes: hookConfig.consolidation_stale_minutes ?? DEFAULT_CONFIG.consolidation_stale_minutes,
    tool: {
      name: toolName,
      arguments: arguments_,
      result,
      timestamp,
      success,
    },
  });

  if (cliResult.knowledge_count) {
    log.info(`Extracted ${cliResult.knowledge_count} knowledge items from ${toolName}`);
  }

  log.info(`Tool persisted to brain store (backend: ${hookConfig.backend ?? DEFAULT_CONFIG.backend}): ${toolName}`);

  return {
    event_kind: 'tool',
    tool_name: toolName,
    episodic_recorded: true,
    knowledge_extracted: Boolean(cliResult.knowledge_count),
    knowledge_count: cliResult.knowledge_count || 0,
    consolidation: cliResult.consolidation,
  };
}

async function handleBrainIngest(event) {
  const hookConfig = resolveRuntimeConfig(event);
  if (!hookConfig.enabled) return;

  try {
    if (event?.type === 'message' || event?.type?.includes?.('message')) {
      return await handleMessageEvent(event, hookConfig);
    }

    if (event?.type === 'tool_call' || event?.type === 'tool_result') {
      return await handleToolEvent(event, hookConfig);
    }

    if (event?.tool_call || event?.tool_result || event?.data?.tool_call || event?.data?.tool_result) {
      return await handleToolEvent(event, hookConfig);
    }

    return;
  } catch (error) {
    log.error(`brain-ingest hook failed: ${error.message}`);
    return {
      event_kind: event?.type || 'unknown',
      error: error.message,
    };
  }
}

module.exports = handleBrainIngest;
