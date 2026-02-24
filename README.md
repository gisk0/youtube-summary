# 📺 YouTube Summary

**Drop a YouTube link in chat → get an instant, structured summary.**

An [OpenClaw](https://openclaw.com) skill that extracts video transcripts and generates concise summaries with key points and notable quotes. Supports custom prompts — just add your instructions after the URL.

## ✨ Features

- **Any YouTube URL** — `youtube.com/watch`, `youtu.be`, `/shorts/`, `/live/`, `m.youtube.com`
- **Custom prompts** — "focus on the technical details", "list action items", "explain like I'm 5"
- **Long video support** — handles videos of any length with smart truncation for very long transcripts
- **Multi-language** — summaries match the transcript language automatically
- **Telegram-optimized** — output fits Telegram's formatting and character limits

## 🚀 Quick Example

You:
> https://www.youtube.com/watch?v=dQw4w9WgXcQ summarize the key arguments

Giskard:
> 📺 **Never Gonna Give You Up** — Rick Astley (3min)
>
> **TL;DR:** Rick makes an impassioned case for commitment and loyalty...
>
> **Key Points:**
> • Never going to give you up
> • Never going to let you down
> ...

## 📦 Setup

### 1. Get a TranscriptAPI key

Sign up at [transcriptapi.com](https://transcriptapi.com) — $5/mo for 1,000 transcripts.

### 2. Store the key in `pass`

```bash
pass insert transcriptapi/api-key
# Paste your API key when prompted
```

> **Note:** If you use GPG with multiple keys, init the path first:
> ```bash
> pass init --path transcriptapi <YOUR_GPG_KEY_IDS>
> ```

### 3. Install Python dependencies

```bash
pip install -r skills/youtube-summary/requirements.txt
```

That's it. Drop a YouTube link in chat and the skill kicks in automatically.

## 🔧 Why TranscriptAPI? (And the fallback)

### The problem

YouTube aggressively blocks transcript requests from datacenter IP ranges. If your OpenClaw instance runs on a VPS (Hetzner, DigitalOcean, AWS, Linode, etc.), the popular `youtube-transcript-api` Python library will fail silently for most videos — returning "Could not find a transcript" even when captions exist.

This affects the vast majority of self-hosted setups.

### The solution

[TranscriptAPI.com](https://transcriptapi.com) proxies requests through residential IPs, making transcript extraction reliable from any host. At $5/mo for 1,000 transcripts, it's the default and recommended approach.

### Local fallback

If you run OpenClaw on a residential IP (home server, local machine), the skill automatically falls back to the `youtube-transcript-api` library when no API key is configured — no cost, no signup needed. It also supports proxy configuration via the `YT_PROXY_URL` environment variable for `youtube-transcript-api`.

## 🎨 Custom Prompt Examples

| You type | You get |
|---|---|
| `<url>` | Default structured summary with TL;DR + key points |
| `<url> focus on the technical details` | Technical deep-dive |
| `<url> list all action items` | Actionable takeaways |
| `<url> what are the main arguments for and against?` | Balanced pro/con analysis |
| `<url> explain like I'm 5` | Simplified summary |
| `<url> auf Deutsch zusammenfassen` | Summary in German |

## 🔍 Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `Invalid API key` | TranscriptAPI key is wrong or expired | Check `pass transcriptapi/api-key` |
| `No transcript available` | Video has no captions | Nothing to do — video has no transcript |
| `Video not found` | Bad URL or private video | Double-check the URL |
| `Rate limited` | Too many requests | Wait a moment, try again |
| `SETUP_NEEDED` | No API key and library fallback failed (likely VPS IP block) | Sign up at transcriptapi.com |

## 📁 Files

```
youtube-summary/
├── SKILL.md              # Agent instructions (how the AI uses this skill)
├── README.md             # This file (for humans)
├── requirements.txt      # Python dependencies
├── scripts/
│   ├── extract.py        # Transcript extraction + metadata
│   ├── utils.py          # URL parsing, token counting, text helpers
│   └── prompts.py        # Summary prompt templates (reference)
└── LICENSE               # MIT
```

## 📄 License

MIT — see [LICENSE](LICENSE).
