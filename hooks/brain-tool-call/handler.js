/**
 * Brain Tool Call Hook Handler
 * 
 * Records tool calls to episodic memory and extracts semantic knowledge
 * from tool results.
 */

import { createSubsystemLogger } from "../../subsystem-CDcEQtQK.js";

const log = createSubsystemLogger("hooks/brain-tool-call");

// Configuration defaults
const DEFAULT_CONFIG = {
  enabled: true,
  extract_knowledge: true,
  max_history: 100,
  knowledge_threshold: 0.5,
};

// Storage
let episodicMemory = [];
let semanticKnowledge = [];

/**
 * Summarize tool result for storage
 */
function summarizeResult(result, maxLen = 100) {
  if (result === null || result === undefined) {
    return 'null';
  }
  
  try {
    if (typeof result === 'object') {
      if (Array.isArray(result)) {
        return `list[${result.length}]`;
      }
      const keys = Object.keys(result).slice(0, 3);
      const summary = keys.map(k => `${k}=${typeof result[k]}`).join(', ');
      return `dict(${summary})`;
    }
    return String(result).slice(0, maxLen);
  } catch {
    return String(typeof result);
  }
}

/**
 * Extract knowledge from tool result
 */
function extractKnowledge(toolName, result) {
  const knowledgeItems = [];
  
  if (!result) return knowledgeItems;
  
  try {
    // Process dict results
    if (typeof result === 'object' && !Array.isArray(result)) {
      const ignoreKeys = ['status', 'success', 'error', 'message', 'code'];
      
      for (const [key, value] of Object.entries(result)) {
        if (ignoreKeys.includes(key.toLowerCase())) continue;
        if (value === null || value === undefined) continue;
        if (typeof value === 'object' && !value) continue;
        
        const summary = typeof value === 'string' 
          ? value.slice(0, 200) 
          : JSON.stringify(value).slice(0, 200);
        
        knowledgeItems.push({
          type: 'fact',
          key,
          value: summary,
          source: `tool:${toolName}`,
          timestamp: new Date().toISOString(),
        });
      }
    }
    
    // Process string results
    else if (typeof result === 'string' && result.length > 20) {
      knowledgeItems.push({
        type: 'result',
        content: result.slice(0, 500),
        source: `tool:${toolName}`,
        timestamp: new Date().toISOString(),
      });
    }
    
    // Process array results
    else if (Array.isArray(result)) {
      for (let i = 0; i < Math.min(result.length, 10); i++) {
        if (typeof result[i] === 'object') {
          knowledgeItems.push({
            type: 'item',
            index: i,
            data: JSON.stringify(result[i]).slice(0, 200),
            source: `tool:${toolName}`,
            timestamp: new Date().toISOString(),
          });
        }
      }
    }
  } catch (e) {
    log.error(`Knowledge extraction failed: ${e.message}`);
  }
  
  return knowledgeItems;
}

/**
 * Handle tool call event
 */
const handleToolCall = async (event) => {
  // Get configuration
  const cfg = event.context?.cfg || {};
  const hookConfig = cfg['hooks?.brain-tool-call'] || cfg.hooks?.['brain-tool-call'] || DEFAULT_CONFIG;
  
  if (!hookConfig.enabled) {
    return;
  }
  
  // Extract tool call data from event
  const toolCall = event.tool_call || event.data?.tool_call || event;
  const toolName = toolCall.name || toolCall.tool || 'unknown';
  const arguments_ = toolCall.arguments || toolCall.args || {};
  const result = toolCall.result;
  const timestamp = toolCall.timestamp || new Date().toISOString();
  const success = toolCall.success ?? true;
  
  // Record to episodic memory
  const episode = {
    tool_name: toolName,
    arguments: arguments_,
    result_summary: summarizeResult(result),
    timestamp,
    success,
  };
  
  episodicMemory.push(episode);
  
  // Enforce history limit
  const maxHistory = hookConfig.max_history ?? DEFAULT_CONFIG.max_history;
  if (episodicMemory.length > maxHistory) {
    episodicMemory = episodicMemory.slice(-maxHistory);
  }
  
  const resultObj = {
    tool_name: toolName,
    episodic_recorded: true,
    knowledge_extracted: false,
  };
  
  // Extract knowledge if enabled
  if (hookConfig.extract_knowledge && result) {
    const knowledge = extractKnowledge(toolName, result);
    if (knowledge.length > 0) {
      semanticKnowledge.push(...knowledge);
      resultObj.knowledge_extracted = true;
      resultObj.knowledge_count = knowledge.length;
      log.info(`Extracted ${knowledge.length} knowledge items from ${toolName}`);
    }
  }
  
  return resultObj;
};

/**
 * Get episodic memory
 */
function getEpisodicMemory() {
  return episodicMemory;
}

/**
 * Get semantic knowledge
 */
function getSemanticKnowledge() {
  return semanticKnowledge;
}

/**
 * Find similar tool calls
 */
function findSimilarCalls(toolName, limit = 5) {
  const similar = episodicMemory.filter(ep => ep.tool_name === toolName);
  return similar.slice(-limit);
}

export default handleToolCall;
export { getEpisodicMemory, getSemanticKnowledge, findSimilarCalls };
