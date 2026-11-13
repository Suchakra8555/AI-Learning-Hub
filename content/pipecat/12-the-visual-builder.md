---
title: The visual builder: one component for every node
summary: How Dograh's canvas works. The backend publishes a spec for each node type, one React component renders them all, a zustand store holds the graph, and layout and validation run on the server.
time: 30 min
---

The builder is the part of Dograh people remember. It looks like a diagram tool, but its design is stricter than that: **the backend owns what a node is, and the frontend renders whatever it is told.**

:::warn What we read
UI code at Dograh commit `5dfa84c`: `ui/src/app/workflow/[workflowId]/`, `ui/src/components/flow/`. We did not run it in a browser and did not capture a real saved payload, so the JSON shown is from a test fixture and the TypeScript types. Line numbers move quickly in this repo.
:::

## The stack

From `ui/package.json`: Next.js 15 (App Router), React 19, `@xyflow/react` 12 (the library, formerly React Flow, that draws nodes and edges), zustand 5 for state, Tailwind 4 with shadcn/ui, and a generated API client from `@hey-api/openapi-ts`. `ui/AGENTS.md` says the client in `src/client/` "is auto-generated from the backend OpenAPI spec". You regenerate it with `npm run generate-client`, against a running backend.

There is no layout library in the UI. Auto-layout runs on the server. More below.

## One component for every node type

`RenderWorkflow.tsx` (952 lines) holds the only `<ReactFlow>`. Its node types are built like this:

```tsx
// Single generic component for every node type. Seed with core node types
// so the initial render is stable before specs load, then merge in any
// spec-defined or already-present node types so plugin integrations like
// Tuner render without extra React registrations.
const nodeTypes = useMemo(() => {
    const typeNames = new Set<string>([
        ...Object.values(NodeType), ...specs.map((spec) => spec.name),
        ...nodes.map((node) => node.type), ...(initialFlow?.nodes ?? []).map((node) => node.type),
    ]);
    return Object.fromEntries(Array.from(typeNames).map((typeName) => [typeName, GenericNode]));
}, [initialFlow?.nodes, nodes, specs]);
```

Every type maps to `GenericNode`. Where does the difference between a Start node and a Webhook node come from? From a **spec** the backend serves at `GET /api/v1/node-types`.

<figure>
<svg viewBox="0 0 900 340" role="img" aria-labelledby="t12 d12">
  <title id="t12">How a node gets its form</title>
  <desc>Backend Python classes with node_spec decorators produce a catalog of specs. The API serves it at node-types. The UI caches it. GenericNode and NodeEditForm render any node type from its spec. Saving a node writes into the zustand store, and the whole workflow is sent to the backend, which validates it and returns errors that the store marks on nodes and edges.</desc>
  <defs><marker id="ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g font-size="13" text-anchor="middle">
    <rect class="box hot" x="10" y="40" width="190" height="70" rx="10"/><text x="105" y="68">Python data classes</text><text x="105" y="88" font-size="11" class="small">@node_spec in dto.py</text>
    <rect class="box" x="250" y="40" width="170" height="70" rx="10"/><text x="335" y="68">GET /node-types</text><text x="335" y="88" font-size="11" class="small">spec catalog</text>
    <rect class="box" x="470" y="40" width="190" height="70" rx="10"/><text x="565" y="68">useNodeSpecs</text><text x="565" y="88" font-size="11" class="small">cached once per page</text>
    <rect class="box hot" x="710" y="40" width="180" height="70" rx="10"/><text x="800" y="68">GenericNode +</text><text x="800" y="88">NodeEditForm</text>
    <rect class="box" x="710" y="170" width="180" height="60" rx="10"/><text x="800" y="196">zustand store</text><text x="800" y="214" font-size="11" class="small">nodes, edges, history</text>
    <rect class="box" x="450" y="170" width="210" height="60" rx="10"/><text x="555" y="196">PUT /workflow/{id}</text><text x="555" y="214" font-size="11" class="small">whole graph + viewport</text>
    <rect class="box hot" x="190" y="170" width="230" height="60" rx="10"/><text x="305" y="196">Server validation</text><text x="305" y="214" font-size="11" class="small">WorkflowError list</text>
    <rect class="box" x="190" y="266" width="230" height="52" rx="10"/><text x="305" y="290">data.invalid on nodes</text><text x="305" y="306" font-size="11" class="small">red border + message</text>
  </g>
  <path class="arrow" d="M200 75 H246" marker-end="url(#ah)"/>
  <path class="arrow" d="M420 75 H466" marker-end="url(#ah)"/>
  <path class="arrow" d="M660 75 H706" marker-end="url(#ah)"/>
  <path class="arrow" d="M800 110 V166" marker-end="url(#ah)"/>
  <path class="arrow" d="M710 200 H664" marker-end="url(#ah)"/>
  <path class="arrow" d="M450 200 H424" marker-end="url(#ah)"/>
  <path class="arrow" d="M305 230 V262" marker-end="url(#ah)"/>
</svg>
<figcaption>The round trip. The spec contract is <code>api/services/workflow/node_specs/_base.py</code> (<code>SPEC_VERSION = "1.0.0"</code>). Comments in the code say "adding a new node type is now zero frontend code: declare the spec on the backend" (<code>useWorkflowState.ts:58</code>).</figcaption>
</figure>

A spec lists a node's properties, their types, their order, graph constraints and an icon name. The property types are a fixed set: `string`, `number`, `boolean`, `options`, `multi_options`, `fixed_collection`, `json`, `tool_refs`, `document_refs`, `recording_ref`, `credential_ref`, `mention_textarea` and `url`. The frontend `PropertyInput` has a `switch` over them with an exhaustive `never` guard, so adding a type on the backend without a widget fails type-checking.

Conditional fields work through `DisplayOptions(show={"extraction_enabled": [True]})`. The rule is implemented twice, in Python and TypeScript, and both are locked to one shared fixture file (`display_options_fixtures.json`) with a test on each side. That is a neat way to keep two implementations in step.

What stays in the frontend: per-type look and handles. `GenericNode.tsx` lines 45 to 73 hold `STYLE_VARIANT_BY_SPEC`, `HANDLES_BY_SPEC` and `DOC_URL_BY_SPEC`. The comment says keeping them there "avoids leaking UI concerns into the backend schema". Start has a source handle only, Agent has both, End has a target only, and Global, Trigger, Webhook and QA have none.

### The node types

| Type | Handles | Constraint | What the editor shows (not all) |
|---|---|---|---|
| Start Call | out | exactly 1 instance, no incoming | greeting (text or audio), allow interrupt, delayed start, pre-call fetch URL |
| Agent Node | in, out | at least 1 incoming | prompt, allow interrupt, variable extraction, tools, documents |
| End Call | in | no outgoing | closing prompt, extraction |
| Global Node | none | at most 1 | the persona prompt |
| API Trigger | none | at most 1 | endpoint path |
| Webhook | none | | method, URL, credential, headers, payload template |
| QA Analysis | none | | enable, sample rate, minimum call length, which model |

Integration packages (BigQuery, Noveum, Paygent, Tuner) add their own node types the same way, and appear under "Integrations" in the add-node panel without UI changes.

## State and undo

One zustand store (`stores/workflowStore.ts`, 466 lines) holds nodes, edges, name, a history array, `isDirty`, validation errors, template variables and the `ReactFlowInstance`. Undo is hand-written. `zundo` is in `package.json` but nothing uses it. History is a list of snapshots capped at 50:

```ts
const MAX_HISTORY_SIZE = 50;
const commitHistory = (state, snapshot) => {
  const history = [...state.history.slice(0, state.historyIndex + 1), snapshot];
  if (history.length > MAX_HISTORY_SIZE) { history.shift(); }
  return { ...snapshot, history, historyIndex: history.length - 1, isDirty: true };
};
```

The interesting part is **when** a snapshot is taken (`setNodes`, lines 216 to 252). Adding a node commits one. Dragging commits only when the drag ends (`dragging === false`), not on every mouse move. Deleting commits once, from React Flow's `onDelete`. Selection and size changes touch nothing. Without those rules, one drag would fill the undo stack with 200 entries.

## Tidy Up runs on the server

The brush button posts only ids, types and edge endpoints to `POST /api/v1/workflow/layout`. The API shells out to a small Node program (`api/mcp_server/ts_validator/src/layout.ts`) that runs the **dagre** layout library and returns positions. The same code lays out agents the AI builder creates. Because positions can change while the request is in flight, `applyLayoutPositions` merges only the positions into the *current* nodes, keeping edits made meanwhile.

Why on the server? The AI builder writes graphs with no positions, since models place nodes badly. The server already needed a layout step. Reusing it for the button keeps one layout. The cost is that CI must install Node for Python tests.

## Edges

Every edge is type `custom` (`CustomEdge.tsx`, 374 lines). It draws a smooth-step path, offsets parallel edges between the same pair so they do not overlap, and draws an arc for self-loops. Double-click opens a dialog with three fields: **Condition Label** (max 64 chars), **Condition**, and **Transition Speech** (text or a recording). Hovering or selecting an edge sets `selected_through_edge` on both endpoint nodes, which draws rings on them. That is how you see where an edge goes in a crowded graph.

## Validation

1. On mount, and after every save, the UI calls `POST /workflow/{id}/validate`.
2. The server builds a `WorkflowGraph` and returns `WorkflowError{kind, id, field, message}` records.
3. The store writes `data.invalid` and `data.validationMessage` onto the named nodes and edges. `BaseNode` turns that into a red border. The edit dialog shows the message.
4. A failed save with structured errors highlights the same way.
5. The tester is blocked while errors exist: "Resolve the current validation errors before starting another test."

Before saving, the server **strips** unknown keys from `node.data` and `edge.data` (`sanitize_workflow_definition`, `dto.py:1185`). UI-only fields such as `invalid`, `validationMessage` and `runtime_active` never reach the database.

## Save, draft and published

Saving a node dialog saves the **whole** workflow with `PUT`, then reloads the server's copy into the canvas, because the backend may add fields (a trigger path, for one). Saving a published workflow makes a **draft**. The header reads `v3 (Draft)` or `v3 (Published)`. Publishing takes a version name and a change description. `?version=N` opens an older version read-only, and a diff dialog compares two versions. A campaign can split traffic across versions.

The rule, from `RenderWorkflow.tsx:361`: the "current" version is the draft if one exists, otherwise the published one. Anything else is historical and cannot be edited.

## The agent builder

Next to the canvas is a chat that builds and edits workflows with AI. It runs in the ARQ worker, not in the browser request. The browser stream is disposable and reconnects with a sequence cursor, so closing the tab does not lose the run. It has human approval steps for plans and tools, and while it works the canvas is inert. The same MCP tools are exposed to Claude Code and Cursor.

:::try
Open `api/tests/dto_fixtures/sample_branching_workflow.json` in the Dograh repo. Draw it on paper. Then find the one `<ReactFlow>` element in `RenderWorkflow.tsx` and list which props stop dragging when you view an old version.
:::

:::check Why does Dograh render every node type with one React component?
Each node's fields come from a spec the backend publishes. One generic renderer plus a form renderer handles any spec, so a new node type needs a backend declaration and no new React code.
:::

:::check Why does dragging a node commit one undo step, not hundreds?
`setNodes` snapshots only when React Flow reports `dragging === false`, the end of the drag. Position changes during the drag only mark the workflow dirty.
:::

:::check Why does the server, not the browser, strip fields like runtime_active before saving?
The browser puts UI-only state into node data. The server is the one place every writer passes through (UI, AI builder, API, MCP), so it is the right place to keep the stored shape clean.
:::
