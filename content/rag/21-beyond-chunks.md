---
title: Beyond plain chunks, graphs, trees, images and the database choice
summary: When top-k chunk search is not enough, and how to pick where to store vectors.
time: 20 min
---

Chunk search answers "find the paragraph about X". Some questions need more.

## Questions that chunks cannot answer

"What are the main themes across all 5,000 tickets?" No single chunk holds that. Two ideas try to help:

- **Graph RAG.** A model reads your text and builds a **graph**: things (people, products, places) joined by relationships. Questions are answered by walking the graph. Microsoft's open-source GraphRAG does this, and its own page warns that indexing "can be an expensive operation". It is research code in maintenance mode ([repo](https://github.com/microsoft/graphrag)).
- **Tree of summaries (RAPTOR).** Group similar chunks, have a model summarize each group, then group and summarize the summaries, until one summary sits at the top. Store every level. A detailed question matches a leaf chunk, and a "what is this about" question matches a summary near the top ([paper](https://arxiv.org/abs/2401.18059)). The paper reports a 20-point gain on one reading benchmark when paired with GPT-4. That is the authors' result on their test, not ours.
- **Tree RAG.** Build a table-of-contents tree of each document and let a model walk down to the right section, with no vectors at all. PageIndex does this ([repo](https://github.com/VectifyAI/PageIndex)). It claims strong results on one finance benchmark. That is the vendor's claim, which we did not check.

### How GraphRAG builds its graph

The GraphRAG paper ([paper](https://arxiv.org/abs/2404.16130)) goes in four steps:

1. **Extract.** A model reads each chunk and lists the things in it, then the relationships between those things. Things first, links second, so every link joins two known things.
2. **Group.** An algorithm called Leiden splits the graph into **communities**: clusters of things that link to each other far more than to the rest. It does this at several levels, from small clusters to large ones.
3. **Summarize.** A model writes a report for each community.
4. **Answer.** A *local* question ("who supplies the tent poles?") starts at the matching things and walks their links. A *global* question ("what are the main themes?") runs over the community reports: each one gives a partial answer, and a final call combines them.

Step 2 is what makes global questions work. [RAGFlow](lesson:ragflow/agents-trees-graphs-and-gaps) shows what happens when a product reads community reports but has no code that writes them.

Rule: use these only after plain hybrid search plus reranking fails on questions you have measured. They cost more to build and are harder to keep fresh.

## Tables, charts, scans

Documents contain more than text. NVIDIA describes three designs for **multimodal RAG** ([source](https://developer.nvidia.com/blog/an-easy-introduction-to-multimodal-retrieval-augmented-generation/)):

1. One shared search space for images and text.
2. Turn everything into text: a chart becomes a table, an image becomes a caption.
3. Keep separate stores per type and rerank the combined results.

Design 2 is the easiest to start with, since the rest of your pipeline stays the same.

## Where to store vectors

| Kind | Examples | Pick it when |
|---|---|---|
| Add-on to a database you have | pgvector for Postgres | You already run Postgres, and your data is small to medium |
| Dedicated vector database | Chroma, Qdrant, Weaviate, Milvus, Pinecone | You need scale, filters, and a service built for it |
| Search engine | Elasticsearch, OpenSearch | You also need strong keyword search and already run one |
| In-memory library | FAISS | A single machine, experiments, or a fixed collection |

The names come from the Awesome-RAG database list, which does not compare them. Our table is a starting rule, not a benchmark. Test with your data size and filters. Two questions decide most cases: how many chunks will you hold, and do you need to filter by user or date while searching? ([access rules](lesson:rag/fast-cheap-safe))

## Small to big

Search over **small** chunks, since they match precisely. Then return the **bigger** parent section to the model for context. LlamaIndex lists this as a production step ([guide](https://developers.llamaindex.ai/python/framework/optimizing/production_rag/)). [More ways to chunk](lesson:rag/more-ways-to-chunk) measures it against four other methods.

## Dig deeper

Our [research notes on Awesome-RAG](lesson:research/awesome-rag) list every source we read by topic, a beginner-to-advanced reading path, and which links we did not open. The upstream list is the [Awesome-RAG](https://github.com/Danielskry/Awesome-RAG) repo.

:::check A manager asks for "the main complaints across all support tickets". Why does top-5 chunk search fail?
The answer is spread over thousands of chunks, and top-5 shows only a handful. You need aggregation or a graph or summary approach.
:::
