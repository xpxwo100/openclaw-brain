# Architecture

[中文版本 / Chinese version](./architecture.zh-CN.md)

## Goals

OpenClaw Brain exists to solve a very specific engineering problem:

> an agent should not treat every message as equally important, and it should not rely on raw chat history alone to appear consistent, personalized, and reliable.

The architecture is therefore optimized for:

- selective ingestion
- layered memory storage
- prompt-oriented recall
- durable persistence
- real integration with OpenClaw hooks and plugins

---

## Design principles

### 1. One canonical memory model
All durable memory layers should be representable as `MemoryRecord`.

This avoids the classic mess where every subsystem invents its own memory shape and integration degenerates into `getattr(...)` soup.

### 2. Cognitive terms, engineering boundaries
Names such as *hippocampus* and *episodic memory* are useful, but they are not excuses for vague ownership.

Each module must map cleanly to an engineering responsibility.

### 3. Orchestrator first
`OpenClawBrain` is the composition root.

External systems should talk to the orchestrator instead of stitching submodules together ad hoc.

### 4. Prompt injection is a first-class concern
Memory that cannot improve an answer is just storage.

The system is designed not only to **store** memory, but to **retrieve and inject** the right memory into the model context.

### 5. Portability matters
The project is designed to remain deployable on Windows, Linux, and macOS with minimal path and runtime surprises.

---

## Layer model

```text
input / event
   │
   ▼
AttentionGate
   │
   ├── reject
   ▼
Hippocampus
   │
   ├── WorkingMemory
   ├── EpisodicStore
   └── SemanticStore
           │
           ▼
MemoryRetriever
           │
           ▼
BrainContextBuilder
           │
           ▼
OpenClaw before_prompt_build plugin injection
```

---

## Components

### 1. Attention Gate
**Purpose:** decide whether a piece of information deserves memory budget.

**Inputs:**
- raw text
- optional context
- optional memory hints

**Output:**
- `AttentionResult`

**Why it exists:**
Without gating, the system becomes a glorified transcript dump.

---

### 2. Working Memory
**Purpose:** hold active task state and short-lived important items.

**Properties:**
- bounded capacity
- TTL-based expiry
- rehearsal support
- optimized for current-task relevance

**Why it exists:**
Agents need a place for temporary focus that should not immediately pollute durable memory.

---

### 3. Hippocampus
**Purpose:** rapidly encode candidate memories before durable placement.

**Properties:**
- append-friendly
- bounded buffer
- recent-memory staging
- useful source/context associations

**Why it exists:**
Not every remembered event should instantly become long-term knowledge.

---

### 4. Episodic Store
**Purpose:** durable storage for timestamped events and experiences.

**Properties:**
- event-oriented
- time-aware retrieval
- recent-window access
- useful for “what happened” queries

**Why it exists:**
Agents often need specific past events, not just abstract facts.

---

### 5. Semantic Store
**Purpose:** durable storage for stable knowledge.

**Primary kinds:**
- fact
- rule
- preference
- general concept

**Why it exists:**
A preference such as “the user likes concise replies” should not compete with raw event logs forever.

---

### 6. Retrieval
**Purpose:** merge candidates across stores and rerank them.

**Signals may include:**
- lexical relevance
- recency
- importance
- context match
- access history
- memory strength

**Why it exists:**
Brute-force recall is noisy. Reranking is what turns storage into usable memory.

---

### 7. Context Builder
**Purpose:** transform recalled memories into a compact, prompt-ready recall block.

**Responsibilities:**
- deduplicate near-echoes from recent chat
- prioritize semantic/rule/preference memories
- keep the final recall block compact
- return stable text for prompt injection

**Why it exists:**
If the system just repeats the last user message, it is not memory. It is lazy paraphrase.

---

### 8. Consolidation
**Purpose:** convert repeated or important experience into more durable memory.

**Current responsibilities:**
- de-duplication
- promotion from episodic to semantic when appropriate
- strength adjustment
- basic forgetting/downweighting behavior

**Future direction:**
- richer semantic extraction
- stronger clustering and summarization
- optional vector-assisted consolidation

---

## OpenClaw integration model

The system integrates into OpenClaw through three surfaces:

### Message hook
Captures inbound messages and decides what to remember.

### Tool-call hook
Stores tool usage as episodic memory and extracts structured semantic knowledge when possible.

### Prompt plugin
Uses `before_prompt_build` to inject a compact recall block into system-prompt space.

It also gives special priority to assistant execution-state summaries, so progress questions can return a synthesized state snapshot instead of a pile of raw chat echoes.

This gives the project a full loop:

```text
message / tool event
  -> ingestion
  -> persistence
  -> recall
  -> context block
  -> prompt injection
  -> better answer
```

---

## Persistence model

### JSONL backend
Use when you want transparency, simple backups, and low-friction debugging.

### LanceDB backend
Use when you want a more scalable foundation for future semantic/vector retrieval.

The persistence contract is intentionally backend-switchable so the cognitive layer does not depend on one storage implementation forever.

---

## Cross-platform notes

The project is intended to be deployable on:

- **Windows** for local OpenClaw workspace development
- **Linux** for server and automation-friendly deployments
- **macOS** for local development and desktop-centric usage

Portability assumptions:

- Python paths should not be hardcoded to a single shell environment
- Node-based plugin code should avoid platform-specific path tricks
- stores should live in stable workspace paths, not temp-only locations

---

## What this architecture is intentionally not

This is **not**:
- a full cognitive science simulator
- a magical AGI memory engine
- a replacement for all existing memory tools

It is a practical memory subsystem for agents.

That is the point.
ory tools

It is a practical memory subsystem for agents.

That is the point.
