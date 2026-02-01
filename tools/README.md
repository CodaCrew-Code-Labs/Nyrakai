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

**Save approved translations:**
```bash
python3 translator.py --save "I see the star"
# Prompts for confirmation, category, and context
# Saves to sentences.json
```

### sentence-validator.py
Validates sentences in `sentences.json` against all grammatical rules.

```bash
# Validate all sentences
python3 sentence-validator.py

# Validate specific sentence by ID
python3 sentence-validator.py --id 1

# Verbose mode (detailed analysis)
python3 sentence-validator.py --verbose
```

**Checks:**
- All words exist in dictionary (or are valid derived forms)
- Case suffixes correctly applied
- Aspect/mood markers valid
- Question particle placement
- Negation prefix usage

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

**Validation checks include:**
- Valid phoneme inventory
- Syllable structure (C)(C)V(')(C)
- Onset cluster rules
- Coda constraints
- **Forbidden sequences:** `^'` (ejective + glottal), `'a` (glottal + 'a')
- English similarity check (avoids look-alike words)
- Dictionary duplicate detection

### word-generator.py
AI-powered word generator using Claude or OpenAI.

```bash
# Generate 5 suggestions for "fire"
python3 word-generator.py fire

# Generate 10 suggestions for "mountain"
python3 word-generator.py mountain 10

# Generate with domain constraint
python3 word-generator.py fire 5 --domain nature
python3 word-generator.py think 3 --domain cognition

# List available domains
python3 word-generator.py --domains
```

Requires `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` in environment or `~/.clawdbot/clawdbot.json`.

### batch-generator.py ⭐ NEW
**Parallel** word generation with collision detection. ~2x faster than sequential.

```bash
# Generate multiple words in parallel
python3 batch-generator.py --words "jump,climb,dance,run" --domain action

# Generate from file (one word per line)
python3 batch-generator.py words.txt --domain action

# Generate all missing Swadesh 207 words
python3 batch-generator.py --swadesh-missing

# Validate multiple words in parallel
python3 batch-generator.py --validate-batch words.txt

# Save output to JSON
python3 batch-generator.py --words "test,example" -o results.json

# Add valid words directly to dictionary
python3 batch-generator.py --words "test,example" --add-to-dict
```

**Features:**
- Parallel API calls (5 workers by default)
- Collision detection:
  - Exact matches with existing dictionary
  - Similar words (edit distance < 2)
  - Duplicates within the batch
- Progress indicator
- Timing stats

**Speed comparison:**
- Sequential (8 words): ~24 seconds
- Parallel (8 words): ~12 seconds (~2x faster)

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
