name: Phoenix-Shift-B

on:
  schedule:
    # 🕒 Starts at 06:00 and 18:00 UTC
    - cron: '0 6,18 * * *'
  workflow_dispatch:

jobs:
  ultra-strike:
    strategy:
      matrix:
        machine_id: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    runs-on: ubuntu-latest
    timeout-minutes: 355 # Runs for 6 hours
    steps:
      - uses: actions/checkout@v4
      - run: pip install selenium==4.21.0 selenium-stealth
      - name: 🔥 Run Shift B
        env:
          INSTA_COOKIE: ${{ secrets.INSTA_COOKIE }}
          TARGET_THREAD_ID: ${{ secrets.TARGET_THREAD_ID }}
          MESSAGES: ${{ secrets.MESSAGES }}
        run: python -u main.py
