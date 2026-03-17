/**
 * Brain Message Hook Handler
 * 
 * Processes messages through the Brain's attention gate to determine
 * if the message should be remembered.
 * 
 * This handler integrates with the Python brain modules via subprocess.
 */

import { createSubsystemLogger } from "../../subsystem-CDcEQtQK.js";
import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const log = createSubsystemLogger("hooks/brain-message");

// Configuration defaults
const DEFAULT_CONFIG = {
  enabled: true,
  attention_threshold: 0.7,
  working_memory_limit: 10,
  auto_consolidate: true,
  consolidation_interval: 100,
};

// Working memory storage (in-memory for the gateway lifetime)
let workingMemory = [];
let messageCount = 0;

/**
 * Calculate message importance score
 * Based on the Python AttentionGate implementation
 */
function scoreMessage(content) {
  if (!content) return 0;
  
  const lowerContent = content.toLowerCase();
  let score = 0;
  
  // Keyword weights
  const keywords = {
    'remember': 0.8,
    'important': 0.9,
    'task': 0.7,
    'deadline': 0.9,
    'meeting': 0.6,
    'note': 0.7,
    '记住': 0.8,
    '重要': 0.9,
    '任务': 0.7,
    '截止': 0.9,
    '会议': 0.6,
  };
  
  // Length scoring
  const length = content.length;
  if (length > 50 && length < 500) {
    score += 0.3;
  } else if (length >= 500) {
    score += 0.2;
  }
  
  // Keyword matching
  for (const [keyword, weight] of Object.entries(keywords)) {
    if (lowerContent.includes(keyword)) {
      score += weight * 0.1;
    }
  }
  
  // Question detection
  if (content.includes('?') || content.includes('？')) {
    score += 0.2;
  }
  
  // Exclamation detection
  if (content.includes('!') || content.includes('！')) {
    score += 0.1;
  }
  
  return Math.min(score, 1.0);
}

/**
 * Handle incoming message event
 */
const handleBrainMessage = async (event) => {
  // Only process message events
  if (!event.type || !event.type.includes('message')) {
    return;
  }
  
  // Get configuration
  const cfg = event.context?.cfg || {};
  const hookConfig = cfg['hooks?.brain-message'] || cfg.hooks?.['brain-message'] || DEFAULT_CONFIG;
  
  if (!hookConfig.enabled) {
    return;
  }
  
  const threshold = hookConfig.attention_threshold ?? DEFAULT_CONFIG.attention_threshold;
  const memoryLimit = hookConfig.working_memory_limit ?? DEFAULT_CONFIG.working_memory_limit;
  
  // Extract message content
  const message = event.message || event.data?.message || {};
  const content = message.content || message.text || '';
  const author = message.author?.name || message.sender || 'unknown';
  const channel = message.channel || 'unknown';
  const messageId = message.id || message.message_id || 'unknown';
  
  // Score the message
  const importance = scoreMessage(content);
  messageCount++;
  
  const result = {
    message_id: messageId,
    importance,
    remembered: false,
    location: null,
  };
  
  // Check if should remember
  if (importance >= threshold) {
    const memoryEntry = {
      content,
      author,
      channel,
      timestamp: new Date().toISOString(),
      importance,
      message_id: messageId,
    };
    
    // Add to working memory
    workingMemory.push(memoryEntry);
    result.remembered = true;
    result.location = 'working';
    
    // Enforce memory limit
    if (workingMemory.length > memoryLimit) {
      workingMemory.shift(); // Remove oldest
    }
    
    log.info(`Message remembered (importance: ${importance.toFixed(2)}): ${messageId}`);
  }
  
  // Check for consolidation trigger
  const consolidateInterval = hookConfig.consolidation_interval ?? DEFAULT_CONFIG.consolidation_interval;
  if (hookConfig.auto_consolidate && messageCount % consolidateInterval === 0) {
    result.trigger_consolidation = true;
    log.info(`Consolidation triggered at message ${messageCount}`);
  }
  
  // Return result (can be used by other hooks or logged)
  return result;
};

/**
 * Get current working memory contents
 */
function getWorkingMemory() {
  return workingMemory;
}

/**
 * Clear working memory
 */
function clearWorkingMemory() {
  const count = workingMemory.length;
  workingMemory = [];
  log.info(`Cleared ${count} working memory entries`);
  return count;
}

export default handleBrainMessage;
export { getWorkingMemory, clearWorkingMemory };
