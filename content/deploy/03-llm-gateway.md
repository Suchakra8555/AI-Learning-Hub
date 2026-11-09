---
title: The LLM gateway, one door for many models
summary: What a gateway is, why teams use one, and what LangSmith's beta version documents.
time: 10 min
---

Imagine five teams, each with their own keys for three model providers. Nobody can see total spend, and a key leak is a mess. A **gateway** is one endpoint all calls go through. It holds the provider keys, applies rules, and records every call.

## LangSmith's LLM Gateway

From the quickstart ([source](https://docs.langchain.com/langsmith/llm-gateway-quickstart.md)): you call models from several providers through one endpoint with one LangSmith API key. To switch provider, change the model ID. Every call is traced, and your team's spend rules apply. The docs list pages on API formats (Chat Completions, Messages, Responses), fallbacks, spend, rate limits, model access, and data policies.

The setup it shows:

```bash
export LANGSMITH_GATEWAY_BASE_URL="https://gateway.smith.langchain.com/v1"
curl "$LANGSMITH_GATEWAY_BASE_URL/models"
```

Then you send a chat request to `/chat/completions` with a model ID from that list. We did not see a full request body, and we did not run it.

## Status and cost

- **Beta.** The quickstart says beta and needs a paid-plan organization. One search result called it "private beta" with a waitlist. We could not reconcile the two, so confirm access with LangChain.
- Errors: 401 and 403 mean authentication, 424 means a provider credential problem.
- We did not read the spend, rate limit, or data policy pages. Read them before giving it to a team.

## Why use any gateway

| Benefit | Example |
|---|---|
| One place for keys | Rotate a key once |
| Spend control | Cap a team's monthly cost |
| Fallbacks | Switch provider if one is down |
| Central logs | Every call traced in one place |

The price is one more system that can fail, and one more place your prompts pass through. Check its data policy like you would a provider's. Open-source gateways exist too. The Awesome-RAG list names LiteLLM in its frameworks section ([research notes](lesson:research/awesome-rag)), and we did not test it.

:::check What is the main risk of routing everything through one gateway?
It becomes a single point of failure and a place where all your prompts pass, so it needs the same care as a core service.
:::
