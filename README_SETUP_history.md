History Facts YouTube Bot — पूरी तरह ऑटोमैटिक (GitHub पर)

यह कैसे काम करता है





Topic तय होता है — या तो आप देते हैं (GitHub पेज पर या Telegram पर), या टॉपिक खाली छोड़ने पर AI खुद एक नया रोचक history topic चुन लेता है (पहले इस्तेमाल हो चुके टॉपिक used_topics.txt में लॉग रहते हैं, दोबारा नहीं आएंगे)।



Gemini उस टॉपिक पर facts लिखता है:





Shorts → ठीक 3 beats (Hook + Fact + Twist) — एक ही कहानी



Long → 7 अलग factsहर fact के साथ एक precise English image-search query भी आता है।



हर fact के लिए Wikimedia Commons पहले, फिर DuckDuckGo/Bing से असली history photo खोजी जाती है।



हर fact की आवाज़ बनती है (Edge TTS primary → OpenAI.fm → gTTS fallback)।



ffmpeg से smooth Ken-Burns zoom + fade वाला वीडियो बनता है (photo + आवाज़ + नीचे Hindi caption, Noto Sans Devanagari font)। Shorts = vertical, Long = horizontal।



YouTube पर अपलोड — Shorts में टाइटल में अपने आप #Shorts जुड़ जाता है।



सारे temp files (images, audio, intermediate clips) अंत में cleanup हो जाते हैं।

रिपो में डालनी हैं ये फाइलें

history_facts_bot.py
telegram_check_topic.py
requirements.txt
.github/workflows/history-facts-bot.yml

Secrets (Settings → Secrets and variables → Actions)







Secret Name



Value





GEMINI_API_KEY_1/2/3



आपकी Gemini keys





TELEGRAM_BOT_TOKEN



Telegram बॉट का token





TELEGRAM_CHAT_ID



आपकी chat id





YT_CLIENT_SECRETS_JSON



इस चैनल के client_secrets.json का raw कंटेंट





YT_TOKEN_JSON



इस चैनल के token.json का raw कंटेंट

⚠️ अगर यह नया YouTube चैनल है, तो client_secrets.json / token.json भी उसी नए चैनल के account से बनाने होंगे।

चलाने के 2 तरीके

GitHub पेज से:
Actions → "History Facts Bot" → Run workflow → topic में कुछ भी लिखें (जैसे "Mughal history" या खाली छोड़ दें) → video_format में long या shorts चुनें → Run।

Telegram से:





सिर्फ एक टॉपिक भेजें: Chandragupta Maurya → long वीडियो बनेगा



"shorts" शब्द जोड़ दें: World War 2 shorts → shorts वीडियो बनेगा उसी टॉपिक पर



सिर्फ auto या auto shorts भेजें → AI खुद टॉपिक चुनेगा

ध्यान रखने वाली बातें





हर 10 मिनट में GitHub check करता है कि Telegram पर कोई नया मैसेज आया — इसलिए थोड़ी देर लग सकती है।



अगर किसी fact के लिए सही photo ना मिले, तो generic history image / plain dark slide लग जाएगी (Telegram पर बता दिया जाएगा)।



Category ID "27" (Education) पर upload होता है।



Hindi captions के लिए workflow fonts-noto-core install करता है (Noto Sans Devanagari)।



Gemini model default: gemini-2.0-flash (workflow env में set)।

