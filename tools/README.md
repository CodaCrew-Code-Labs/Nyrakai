# Nyrakai Tools

Command-line utilities for working with the Nyrakai conlang.

## Scripts

### translator.py ⭐ NEW
Translates English sentences to Nyrakai following all grammatical rules.

```bash
# Translate a sentence
python3 translator.py "I see the star"
python3 translator.py "She does not drink water"
python3 translator.py "Do you know the truth?"

# Interactive mode
python3 translator.py --interactive
```

**Features:**
- OVSV word order transformation
- Case suffixes (accusative, dative, etc.)
- Aspect markers (completed, ongoing, habitual, potential)
- Negation with za- prefix
- Question particle ka
- Interfix rules (-w-, -a-)
- **Refuses to hallucinate** — reports missing vocabulary

**Example output:**
```
📝 English: I see the star
✅ Nyrakai: hīnaš yɛniræn fā

📖 Breakdown:
   star → hīnaš (object, accusative)
   see → yɛn (verb stem)
   I → fā (subject)
   [ongoing] → iræn (aspect)
```

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
