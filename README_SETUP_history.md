# History Facts YouTube Bot — पूरी तरह ऑटोमैटिक (GitHub पर)

## यह कैसे काम करता है
1. **Topic तय होता है** — या तो आप देते हैं (GitHub पेज पर या Telegram पर), या टॉपिक खाली छोड़ने पर AI खुद एक नया रोचक history topic चुन लेता है (पहले इस्तेमाल हो चुके टॉपिक `used_topics.txt` में लॉग रहते हैं, दोबारा नहीं आएंगे)।
2. Gemini उस टॉपिक पर facts (Shorts के लिए 1, Long वीडियो के लिए 7) हिंदी में लिखता है — साथ में हर fact के लिए एक image-search query भी देता है।
3. हर fact के लिए DuckDuckGo से **असली history photo** खोजी जाती है।
4. हर fact की अलग आवाज़ बनती है (OpenAI.fm → Edge TTS → gTTS, तीन fallback)।
5. ffmpeg से Ken-Burns zoom इफ़ेक्ट वाला वीडियो बनता है (photo + आवाज़ + नीचे caption)। Shorts = vertical, Long = horizontal, सारे facts के clips जोड़कर एक वीडियो।
6. YouTube पर अपलोड — Shorts में टाइटल में अपने आप `#Shorts` जुड़ जाता है।

## रिपो में डालनी हैं ये फाइलें
```
history_facts_bot.py
telegram_check_topic.py
requirements.txt
.github/workflows/history-facts-bot.yml
```

## Secrets (Settings → Secrets and variables → Actions)

| Secret Name              | Value                                       |
|---------------------------|------------------------------------------------|
| `GEMINI_API_KEY_1/2/3`     | आपकी Gemini keys (news bot जैसी ही इस्तेमाल कर सकते हैं) |
| `TELEGRAM_BOT_TOKEN`       | Telegram बॉट का token                          |
| `TELEGRAM_CHAT_ID`         | आपकी chat id                                   |
| `YT_CLIENT_SECRETS_JSON`   | इस चैनल के `client_secrets.json` का raw कंटेंट |
| `YT_TOKEN_JSON`            | इस चैनल के `token.json` का raw कंटेंट          |

⚠️ अगर यह **नया** YouTube चैनल है (history facts वाला, अलग से product-review चैनल से), तो `client_secrets.json`/`token.json` भी उसी नए चैनल के account से बनाने होंगे — पुराने चैनल का token काम नहीं करेगा।

## चलाने के 2 तरीके

**GitHub पेज से:**
Actions → "History Facts Bot" → Run workflow → `topic` में कुछ भी लिखें (जैसे "Mughal history" या खाली छोड़ दें) → `video_format` में **long** या **shorts** चुनें → Run।

**Telegram से:**
- सिर्फ एक टॉपिक भेजें: `Chandragupta Maurya` → long वीडियो बनेगा
- "shorts" शब्द जोड़ दें: `World War 2 shorts` → shorts वीडियो बनेगा उसी टॉपिक पर
- सिर्फ `auto` या `auto shorts` भेजें → AI खुद टॉपिक चुनेगा

## ध्यान रखने वाली बातें
- हर 10 मिनट में GitHub check करता है कि Telegram पर कोई नया मैसेज आया — इसलिए थोड़ी देर लग सकती है।
- अगर किसी fact के लिए सही photo ना मिले, तो generic history image लग जाएगी (Telegram पर बता दिया जाएगा)।
- Categoy ID "27" (Education) पर upload होता है — चाहें तो बदलवा सकते हैं।
