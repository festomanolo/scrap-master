# Groq Whisper Setup Guide

## What it does

## Steps the Agent can do automatically

1. Check whether it's already configured:
```bash
scrap-master doctor | grep -i "groq\|whisper"
```

2. If the user provides a key, write it to config:
```python
from scrap_master.config import Config
c = Config()
c.set("groq_api_key", "USER_PROVIDED_KEY")
```

3. Test (optional):
```bash
curl -s https://api.groq.com/openai/v1/models \
  -H "Authorization: Bearer USER_PROVIDED_KEY" \
  -o /dev/null -w "%{http_code}"
```
Returns 200 = working

## Steps the user must do manually

Tell the user:

> Audio transcription from videos requires a Groq API key (free).
>
> Steps:
> 1. Go to https://console.groq.com
> 2. Sign up with a Google account or email
> 3. Click "API Keys" in the left menu
> 4. Click "Create API Key"
> 5. Copy the generated key and paste it to me
>
> Groq provides a free tier that is more than enough for everyday use.

## What the Agent does after receiving the key

1. Write to config: `config.set("groq_api_key", key)`
2. Test API availability
3. Respond: "✅ Audio transcription is enabled! Now I can extract content even from videos without subtitles."
