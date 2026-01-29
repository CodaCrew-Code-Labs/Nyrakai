#!/usr/bin/env python3
"""
Nyrakai Word Generator
Generates word suggestions using AI, inspired by Māori, Sangam Tamil, Navi, and Dothraki.
Auto-validates against Nyrakai phonotactic rules.
"""

import os
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path
from validator import validate_word, normalize

# Load API keys from clawdbot config
CONFIG_PATH = Path.home() / ".clawdbot" / "clawdbot.json"

def load_config():
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except:
        return {}

config = load_config()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY") or config.get("env", {}).get("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY") or config.get("env", {}).get("ANTHROPIC_API_KEY")

# Nyrakai phonology reference for the prompt
NYRAKAI_REFERENCE = """
NYRAKAI PHONOLOGY:

CONSONANTS: d, f, g, h, k, l, m, n, ñ (ng), p, r, s, t, ț (th), z
VOWELS: a, e, i, o, u (short) | ā, ē, ī, ō, ū (long, written as aa, ee, ii, oo, uu)
GLIDES: w, y
EJECTIVES: k', p', t' (with apostrophe)
AFFRICATES: ƨ (ts), š (tch), ƶ (dz), ŧ (tr)
DIPHTHONGS: æ (ai), ɒ (au), ɛ (ei), ə (eu), œ (oi)

SPECIAL MARKER:
' (apostrophe between consonant and vowel) = schwa + glottal stop (əʔ)
  - Can ONLY appear between a consonant and a vowel (C'V pattern)
  - CANNOT start or end a word
  - Example: n'æ (true), kre'net (cold)

SYLLABLE STRUCTURE: (C)(C)V(C) — up to 2 onset consonants, required vowel, optional coda

VALID PATTERNS: V, CV, CCV, VC, CVC, CCVC

RULES:
- Every syllable must have a vowel
- ' cannot start or end a syllable
- Ejectives (k', p', t') count as single consonants

When writing words, use digraphs that will be auto-converted:
- ai→æ, au→ɒ, ei→ɛ, eu→ə, oi→œ
- aa→ā, ee→ē, ii→ī, oo→ō, uu→ū
- th→ț, ts→ƨ, tch→š, dz→ƶ, tr→ŧ
"""

INSPIRATION_NOTE = """
INSPIRATION SOURCES:
Draw phonetic and aesthetic inspiration from these languages:
1. MĀORI - Polynesian flow, vowel-rich, soft consonants
2. SANGAM TAMIL - Ancient Dravidian roots, retroflex sounds, classical feel
3. NAVI (Avatar) - Ejectives, unique consonant clusters, alien beauty
4. DOTHRAKI - Harsh gutturals balanced with flowing vowels, warrior aesthetic

Create words that feel ancient, mysterious, and distinctly NOT like any existing language.
The word should sound like it could be from a lost civilization.
"""


def call_anthropic(prompt: str, system: str) -> str:
    """Call Anthropic Claude API."""
    request_body = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 1000,
        "system": system,
        "messages": [{"role": "user", "content": prompt}]
    }).encode('utf-8')
    
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=request_body,
        headers={
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01"
        }
    )
    
    with urllib.request.urlopen(req, timeout=60) as response:
        result = json.loads(response.read().decode('utf-8'))
    
    return result["content"][0]["text"].strip()


def call_openai(prompt: str, system: str) -> str:
    """Call OpenAI API."""
    request_body = json.dumps({
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.9,
        "max_tokens": 1000
    }).encode('utf-8')
    
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=request_body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        }
    )
    
    with urllib.request.urlopen(req, timeout=30) as response:
        result = json.loads(response.read().decode('utf-8'))
    
    return result["choices"][0]["message"]["content"].strip()


def generate_words(english_word: str, count: int = 5) -> list:
    """Generate Nyrakai word suggestions for an English word."""
    
    prompt = f"""{NYRAKAI_REFERENCE}

{INSPIRATION_NOTE}

Generate exactly {count} unique Nyrakai word suggestions for the English word: "{english_word}"

Requirements:
1. Each word must follow Nyrakai phonotactic rules strictly
2. Use a MIX of plain syllables AND distinctive Nyrakai features (ejectives, schwa marker, affricates, long vowels, diphthongs)
3. Vary the complexity - some simple (1 syllable), some complex (2-3 syllables)
4. Make them feel ancient and mysterious
5. Use digraph forms (ai, ee, th, tr, etc.) - they will be auto-converted

Return ONLY a JSON array of objects with this format:
[
  {{"word": "suggested_word", "reasoning": "brief explanation of inspiration/meaning"}}
]

No markdown, no explanation outside the JSON."""

    system = "You are a constructed language expert specializing in creating words for the Nyrakai conlang. Return only valid JSON."
    
    result_text = None
    
    # Try Anthropic first (more reliable), then OpenAI
    if ANTHROPIC_API_KEY:
        try:
            print("Using Anthropic Claude...")
            result_text = call_anthropic(prompt, system)
        except Exception as e:
            print(f"Anthropic failed: {e}")
    
    if not result_text and OPENAI_API_KEY:
        try:
            print("Using OpenAI...")
            result_text = call_openai(prompt, system)
        except Exception as e:
            print(f"OpenAI failed: {e}")
    
    if not result_text:
        print("No API available or all failed.")
        return []
    
    try:
        # Clean up potential markdown
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        result_text = result_text.strip()
        
        suggestions = json.loads(result_text)
        return suggestions
        
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON: {e}")
        print(f"Raw response: {result_text[:500]}")
        return []


def validate_suggestions(suggestions: list) -> list:
    """Validate each suggestion against Nyrakai rules."""
    results = []
    
    for s in suggestions:
        word = s.get("word", "")
        reasoning = s.get("reasoning", "")
        
        validation = validate_word(word)
        
        results.append({
            "original": word,
            "normalized": validation["normalized"],
            "valid": validation["valid"],
            "errors": validation["errors"],
            "warnings": validation["warnings"],
            "phonemes": validation["phonemes"],
            "reasoning": reasoning
        })
    
    return results


def main():
    if len(sys.argv) < 2:
        print("Usage: python word-generator.py <english_word> [count]")
        print("Example: python word-generator.py 'fire' 5")
        sys.exit(1)
    
    english_word = sys.argv[1]
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    
    print(f"\n🗣️  Generating {count} Nyrakai words for: \"{english_word}\"\n")
    print("=" * 50)
    
    # Generate suggestions
    suggestions = generate_words(english_word, count)
    
    if not suggestions:
        print("Failed to generate suggestions.")
        sys.exit(1)
    
    # Validate each
    results = validate_suggestions(suggestions)
    
    # Display results
    valid_count = 0
    for i, r in enumerate(results, 1):
        status = "✓" if r["valid"] else "✗"
        if r["valid"]:
            valid_count += 1
        
        print(f"\n{i}. {status} {r['original']}", end="")
        if r["normalized"] != r["original"].lower():
            print(f" → {r['normalized']}", end="")
        print()
        
        print(f"   Phonemes: {r['phonemes']}")
        print(f"   Reasoning: {r['reasoning']}")
        
        if r["errors"]:
            print(f"   ❌ Errors: {r['errors']}")
        if r["warnings"]:
            print(f"   ⚠️  {r['warnings']}")
    
    print("\n" + "=" * 50)
    print(f"Valid: {valid_count}/{len(results)}")
    
    # Print valid words in simple format
    if valid_count > 0:
        print("\n📋 Valid suggestions:")
        for r in results:
            if r["valid"]:
                print(f"   {r['normalized']} - {english_word}")


if __name__ == "__main__":
    main()
