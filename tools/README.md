# Nyrakai Tools

Command-line utilities for working with the Nyrakai conlang.

## Scripts

### validator.py
Validates Nyrakai words against phonotactic rules.

```bash
# Validate a single word
python3 validator.py kæ
python3 validator.py n'æra
python3 validator.py hro

# Validate entire dictionary
python3 validator.py --check-dict
```

### word-generator.py
AI-powered word generator using Claude or OpenAI.

```bash
# Generate 5 suggestions for "fire"
python3 word-generator.py fire

# Generate 10 suggestions for "mountain"
python3 word-generator.py mountain 10
```

Requires `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` in environment or `~/.clawdbot/clawdbot.json`.

### alphabet-stats.py
Analyze alphabet usage and statistics.

```bash
python3 alphabet-stats.py
```

## Dictionary

`nyrakai-dictionary.json` contains all validated Nyrakai words with:
- Nyrakai spelling
- English meaning
- Part of speech
- Phoneme breakdown
- Syllable structure

## Usage from Repo Root

```bash
cd tools
python3 validator.py <word>
```
