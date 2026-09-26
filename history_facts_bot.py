name: History Facts Bot

on:
  workflow_dispatch:
    inputs:
      topic:
        description: "Topic (khaali chhodein to AI khud chunega)"
        required: false
        type: string
      video_format:
        description: "Video format"
        required: true
        type: choice
        options: [long, shorts]
        default: long

permissions:
  contents: write

jobs:
  run-automation:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: ffmpeg install
        run: sudo apt-get update && sudo apt-get install -y ffmpeg

      - name: Python deps install
        run: pip install -r requirements.txt

      - name: YouTube credentials taiyaar karo
        env:
          CLIENT_SECRETS_JSON: ${{ secrets.YT_CLIENT_SECRETS_JSON }}
          TOKEN_JSON: ${{ secrets.YT_TOKEN_JSON }}
        run: |
          printf '%s' "$CLIENT_SECRETS_JSON" > client_secrets.json
          printf '%s' "$TOKEN_JSON" > token.json

      - name: History Facts video banao aur upload karo
        env:
          TOPIC: ${{ inputs.topic }}
          VIDEO_FORMAT: ${{ inputs.video_format }}
          GEMINI_API_KEY_1: ${{ secrets.GEMINI_API_KEY_1 }}
          GEMINI_API_KEY_2: ${{ secrets.GEMINI_API_KEY_2 }}
          GEMINI_API_KEY_3: ${{ secrets.GEMINI_API_KEY_3 }}
          GEMINI_MODEL_NAME: "gemini-3.6-flash"
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: python history_facts_bot.py

      - name: Used topics file commit karo
        run: |
          git config user.name "history-facts-bot"
          git config user.email "history-facts-bot@users.noreply.github.com"
          git add used_topics.txt || true
          git diff --cached --quiet || git commit -m "chore: log used topic [skip ci]"
          git push || true
