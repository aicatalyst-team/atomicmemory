# Deploying AtomicMemory on OpenShift: Portable Semantic Memory for AI Agents

AI agents that forget everything between sessions are a liability. AtomicMemory solves this with an inspectable, portable memory engine that gives agents persistent context through semantic retrieval, memory mutation, and contradiction-safe claim versioning. We ran a Proof of Concept to validate that the AtomicMemory Core API can run on OpenShift using UBI-based container images.

## What is AtomicMemory?

AtomicMemory is an open-source memory layer for AI applications. Unlike black-box hosted memory services, it is designed to be self-hosted, auditable, and correction-aware. The core server exposes a REST API backed by PostgreSQL with pgvector for vector similarity search and provides:

- Semantic retrieval across conversation history
- Memory mutation with AUDN (Add, Update, Delete, No-op) decisions
- Contradiction-safe claim versioning when users change their mind
- Multiple integration surfaces: SDK, CLI, MCP server, and framework adapters for LangChain, LangGraph, Vercel AI, and OpenAI Agents

## The PoC Challenge

The upstream AtomicMemory Docker image is built on `pgvector/pgvector:pg17` with an embedded PostgreSQL instance, uses `gosu` for privilege management, and relies on a complex Turborepo + pnpm workspace build pipeline. None of this works directly on OpenShift, which enforces non-root execution, restricted security contexts, and arbitrary UID assignment.

Key technical hurdles we needed to solve:

1. **Monorepo build complexity**: The project uses pnpm workspaces with Turborepo, requiring careful module resolution in the container
2. **Node.js dependency weight**: `onnxruntime-node` downloads ~600MB of GPU binaries during postinstall, exceeding OpenShift build pod ephemeral storage limits
3. **pgvector requirement**: The database needs the `vector` extension, which requires superuser privileges to install -- incompatible with OpenShift's restricted SCC
4. **TypeScript runtime**: The project runs TypeScript source directly via `tsx` rather than pre-compiled JavaScript

## How We Solved It

**Container image**: We built a single-stage UBI Node.js 22 image that installs `tsx` globally, runs `pnpm install --ignore-scripts` to skip the onnxruntime binary download, and sets the working directory to `packages/core/` where pnpm correctly resolves the dependency tree.

**Database**: Instead of the embedded PostgreSQL mode, we deployed an `ankane/pgvector` sidecar container. This image includes the pgvector extension and runs with permissions compatible with OpenShift's security model. The application container waits for PostgreSQL readiness, runs database migrations, then starts the API server.

**Embedding provider**: We configured `EMBEDDING_PROVIDER=transformers` with the local `Xenova/all-MiniLM-L6-v2` model, avoiding the need for external API keys during the PoC while still exercising the full embedding pipeline.

## Results

All three test scenarios passed:

| Test | Result | Response Time |
|---|---|---|
| Health check (`GET /health`) | PASS | 0.02s |
| Memory health + config (`GET /v1/memories/health`) | PASS | <0.01s |
| Memory stats (`GET /v1/memories/stats`) | PASS | 0.02s |

The server correctly reported its configuration including the local transformer embedding provider, confirmed database connectivity, and served memory statistics queries.

## What This Means for OpenShift AI

AtomicMemory fills a gap in the agentic AI stack: persistent, inspectable agent memory. Combined with OpenShift AI's MCP support and agent runtime capabilities, it provides:

- **Stateful agents**: Agents deployed on OpenShift AI can maintain context across sessions
- **Memory inspection**: Operations teams can audit what agents remember and how memories evolve
- **Multi-framework support**: The same memory backend serves LangChain, LangGraph, and Vercel AI agents through SDK adapters

For production deployment, the PostgreSQL sidecar should be replaced with a managed PostgreSQL instance with pgvector enabled, and the embedding provider can be pointed at a KServe-hosted embedding model for better performance and scalability.

## Try It

The fork with all PoC artifacts is available at [github.com/aicatalyst-team/atomicmemory](https://github.com/aicatalyst-team/atomicmemory). The `autopoc-artifacts` branch contains the PoC plan, test script, and full report. The `Dockerfile.ubi` and `kubernetes/` manifests on `main` provide a starting point for your own deployment.
