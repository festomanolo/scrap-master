# Video & Podcasts

Subtitles and transcripts for YouTube, Bilibili, and Xiaoyuzhou Podcast.

## YouTube (yt-dlp)

### Get video metadata

```bash
yt-dlp --dump-json "URL"
```

### Download subtitles

```bash
# Download subtitles (without downloading the video)
yt-dlp --write-sub --write-auto-sub --sub-lang "zh-Hans,zh,en" --skip-download -o "/tmp/%(id)s" "URL"

# Then read the .vtt file
cat /tmp/VIDEO_ID.*.vtt
```

### Get comments

```bash
# Extract comments (best-effort — not guaranteed to be complete)
yt-dlp --write-comments --skip-download --write-info-json \
  --extractor-args "youtube:max_comments=20" \
  -o "/tmp/%(id)s" "URL"
# Comments are in the 'comments' field of the .info.json file
```

### Search videos

```bash
yt-dlp --dump-json "ytsearch5:query"
```

> **Subtitle note**: Manually uploaded subtitles extract reliably. Auto-generated subtitles
> may have repeated lines between segments and may need post-processing.
> **Comments note**: `--write-comments` scrapes the web page (not the YouTube Data API) —
> some comments may be missing.

### Subtitle retry chain (execute in order, stop at first non-empty result)

`doctor` only confirms yt-dlp itself and the JS runtime are executable — it does not make a
live request to a specific video. So `active_backend: yt-dlp` does not mean the target
video's subtitles have been verified in real time.

1. Try the `yt-dlp --write-sub --write-auto-sub` command above first.
2. If bot detection fires, the subtitle response is empty, or no subtitle file is generated,
   and OpenCLI is connected: `opencli youtube transcript "URL" -f yaml`.
3. If OpenCLI returns `Caption URL returned empty response`, retry up to 3 times — this is
   a transient failure of an expiring subtitle URL, not proof that the video has no subtitles.
4. Still failing, or the video genuinely has no subtitles: `scrap-master transcribe "URL"` to
   download audio and transcribe.

Success means getting actual non-empty subtitle/transcript content — not a zero exit code
or `doctor`'s version probe result.

### Fallback for videos with no subtitles: Whisper audio transcription

```bash
# When a video has no subtitles: download audio and transcribe via Whisper (free Groq key)
scrap-master transcribe "https://www.youtube.com/watch?v=VIDEO_ID"
scrap-master transcribe ./local_audio.mp3 -o /tmp/transcript.txt
```

> `scrap-master transcribe` accepts public http(s) URLs or local audio files only.
> For `ytsearch5:` search results, select a specific video URL from yt-dlp output first,
> then transcribe.
> Requires a configured key: `scrap-master configure groq-key` (hidden input; free, console.groq.com)
> or `scrap-master configure openai-key`. Default `auto` mode uses only the first configured
> provider (Groq preferred, then OpenAI) — fails without falling back to the other.
> `--allow-provider-fallback` explicitly authorizes cross-provider fallback; the same audio
> may be processed by both Groq and OpenAI (potentially incurring OpenAI costs). Use only
> when you have confirmed the content is safe to share with both providers.

## Bilibili (bili-cli primary, OpenCLI for subtitles)

> ⚠️ **Do not use yt-dlp for Bilibili**: Bilibili's rate-limiting blocks yt-dlp with 412
> across the board (verified with latest version, direct/proxy/with cookie — all fail).
> yt-dlp is for YouTube only.

### Video detail / search / trending / rankings (bili-cli, read-only, no login)

```bash
# Video detail (title / uploader / duration / view+engagement data / subtitle availability)
bili video BVxxx

# Search videos
bili search "query" --type video -n 5

# Trending / rankings
bili hot -n 10
bili rank -n 10

# Download audio and split into ASR-ready WAV (for use with scrap-master transcribe when no subtitles)
bili audio BVxxx
```

### Subtitles (OpenCLI — requires desktop Chrome)

```bash
# Subtitles with per-sentence timestamps
opencli bilibili subtitle BVxxx

# OpenCLI can also search / read video metadata (fallback)
opencli bilibili search "query" -f yaml
opencli bilibili video BVxxx -f yaml
```

### Zero-config fallback: direct search API

```bash
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
curl -s -c /tmp/bili_ck.txt -o /dev/null -A "$UA" "https://www.bilibili.com/"
curl -s -b /tmp/bili_ck.txt -A "$UA" -e "https://www.bilibili.com/" \
  "https://api.bilibili.com/x/web-interface/search/all/v2?keyword=QUERY&page=1"
```

> **Install bili-cli**: `pipx install bilibili-cli` (upstream unmaintained since March 2026
> but verified healthy; read-only use requires no login — `bili login` QR scan unlocks
> feeds, favorites, and personal features).

## Xiaoyuzhou Podcast

### Transcribe a single episode (optionally add --polish for improved punctuation)

```bash
# Output a Markdown file to /tmp/. --polish uses Llama 3.3 70B on Groq to add
# Chinese punctuation and sensible paragraph breaks.
~/.scrap-master/tools/xiaoyuzhou/transcribe.sh --polish "https://www.xiaoyuzhoufm.com/episode/EPISODE_ID"
```

> The transcription prompt already asks Whisper for Chinese punctuation. If punctuation
> still looks poor, add `--polish` to run a free Llama 3.3 70B pass on Groq (~7 extra
> seconds for a 9-minute episode). Use on demand — each transcription adds one extra LLM call.

### Prerequisites

1. **ffmpeg**: `brew install ffmpeg`
2. **Groq API key** (free): https://console.groq.com/keys
3. **Configure the key**: `scrap-master configure groq-key` (hidden input)
4. **First-time setup**: `scrap-master install --env=auto --system --channels=xiaoyuzhou` (requires explicit user approval)

### Check status

```bash
scrap-master doctor
```

> Output Markdown files are saved to `/tmp/` by default.

## Quick Reference

| Scenario | Recommended tool |
|----------|-----------------|
| YouTube subtitles | yt-dlp; on failure: OpenCLI (up to 3 retries) → scrap-master transcribe |
| Bilibili video detail / search | bili-cli |
| Bilibili subtitles | opencli bilibili subtitle |
| Podcast transcription | Xiaoyuzhou transcribe.sh |
| Audio/video without subtitles | scrap-master transcribe (Bilibili audio: `bili audio` first) |
