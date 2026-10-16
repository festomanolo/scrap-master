# Scrap Master — Capability Benchmark, Limitations, Scribd API Extraction & Parallel Speedup Architecture

Based on our live benchmark scraping **Tanzania Form Two National Assessment (FTNA — Subject Code `036`: Information and Computer Studies / Computer Science)** examination papers and marking schemes—and inspecting the architecture of **Scrap Master**—this document provides:

1. **Where Scrap Master Succeeds (Core Abilities)**
2. **Where Scrap Master Fails (Limitations & Blind Spots)**
3. **Summary Verdict Matrix**
4. **How Scribd API / Embed Extraction Works (Bypassing the Web UI & Paywall Blur)**
5. **How to Make Scrap Master Significantly Faster (Parallel Execution & Async Batch Downloading)**

---

## 1. Where It Succeeds (Its Core Abilities)

1. **Instant HTML-to-Markdown Conversion (`web` channel via Jina Reader)**
   - **What we saw:** With zero configuration, `curl -s https://r.jina.ai/https://maktaba.tetea.org/resources/form-1-2/` stripped away all complex HTML/CSS clutter and returned a clean Markdown table with `[2025](url.pdf)[(Solutions)](url-solutions.pdf)`.
   - **Why it's powerful:** You don't need to write brittle BeautifulSoup/XPath/CSS selectors for every new website. Any static or server-rendered web page is immediately readable by an LLM or a 3-line regex script.

2. **Multi-Platform Routing & Fallback Architecture (16+ Platforms)**
   - Instead of being a single scraper, it is a **capability router** (`scrap_master/channels/`) that knows the best upstream tool for supported platforms (Web, YouTube, GitHub, Twitter/X, Reddit, Facebook, Instagram, LinkedIn, Bilibili, XiaoHongShu, RSS, Exa Search, Scribd, etc.) and falls back when one breaks.
   - **`scrap-master doctor` Health Checks:** It probes your machine and tells an agent in JSON (`--json`) which backends are actually working right now and how to fix missing ones.
