#!/usr/bin/env python3
"""
Nyrakai Word Generator
Generates word suggestions using AI, inspired by Māori, Sangam Tamil, Navi, and Dothraki.
Auto-validates against Nyrakai phonotactic rules.
Now with Sound Map integration for domain-aware generation!
"""

import os
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path
from validator import validate_word, normalize, word_exists_in_dictionary, check_english_similarity

# Import sound map for domain-aware generation
try:
    from sound_map import get_onset, get_domain, suggest_onset, SOUND_MAP, DOMAINS
    SOUND_MAP_AVAILABLE = True
except ImportError:
    SOUND_MAP_AVAILABLE = False

# Dictionary path for related word lookup
DICTIONARY_PATH = Path(__file__).parent / "nyrakai-dictionary.json"

def load_dictionary():
    """Load the Nyrakai dictionary."""
    try:
        with open(DICTIONARY_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"words": []}

# ============================================
# RELATED WORDS & DERIVATION SYSTEM
# ============================================

# Semantic categories for finding related words
SEMANTIC_CATEGORIES = {
    'people': ['person', 'man', 'woman', 'child', 'citizen', 'subject', 'servant', 'slave', 'stranger', 'neighbor', 'friend', 'enemy', 'guest', 'hero', 'traitor', 'spy', 'messenger', 'guide', 'prisoner', 'king', 'queen', 'leader', 'ruler', 'master', 'warrior', 'soldier'],
    'body': ['head', 'hand', 'foot', 'eye', 'ear', 'mouth', 'heart', 'blood', 'bone', 'skin', 'tongue', 'nose', 'hair', 'flesh', 'tooth', 'knee', 'liver', 'belly', 'neck', 'breast', 'leg', 'arm'],
    'nature': ['water', 'fire', 'earth', 'air', 'wind', 'rain', 'cloud', 'stone', 'tree', 'river', 'mountain', 'forest', 'sea', 'lake', 'sand', 'ash', 'ember', 'smoke'],
    'celestial': ['sun', 'moon', 'star', 'sky', 'light', 'day', 'night', 'bright', 'dark'],
    'action': ['give', 'take', 'come', 'go', 'walk', 'run', 'see', 'hear', 'speak', 'eat', 'drink', 'sleep', 'die', 'kill', 'fight', 'make', 'create'],
    'quality': ['good', 'bad', 'big', 'small', 'long', 'short', 'hot', 'cold', 'new', 'old', 'true', 'false', 'free'],
    'kinship': ['mother', 'father', 'son', 'daughter', 'brother', 'sister', 'wife', 'husband', 'family'],
    'animals': ['dog', 'bird', 'fish', 'snake', 'horse', 'wolf', 'deer', 'bear', 'louse', 'worm'],
    'abstract': ['truth', 'death', 'life', 'soul', 'fate', 'dream', 'fear', 'love', 'hate', 'wisdom', 'name', 'voice'],
}

# Nyrakai derivation patterns
DERIVATION_PATTERNS = {
    'masculine': {'suffix': 'æn', 'description': 'masculine gender marker'},
    'feminine': {'suffix': 'ñī', 'bridge': 'a', 'description': 'feminine gender marker (with bridge vowel if needed)'},
    'plural_m': {'suffix': 'œ', 'description': 'masculine/mixed plural (attaches after gender)'},
    'plural_f': {'suffix': 'ā', 'description': 'feminine plural (attaches after gender)'},
    'agent': {'suffix': 'ar', 'description': 'one who does X (agent noun)'},
    'abstract': {'prefix': "n'", 'description': 'abstract/truth quality'},
    'negation': {'prefix': 'za', 'description': 'negation/opposite'},
    'diminutive': {'suffix': 'ek', 'description': 'small/diminutive'},
    'augmentative': {'suffix': 'ñor', 'description': 'great/augmentative'},
}


def find_related_words(english_word: str) -> dict:
    """Find related words from the dictionary based on semantic similarity."""
    dictionary = load_dictionary()
    words = dictionary.get("words", [])
    word_lower = english_word.lower()
    
    results = {
        "exact_match": None,
        "same_category": [],
        "partial_matches": [],
        "root_family": [],
    }
    
    # Find which category this word belongs to
    word_category = None
    for category, members in SEMANTIC_CATEGORIES.items():
        if word_lower in members:
            word_category = category
            break
    
    for entry in words:
        eng = entry.get("english", "").lower()
        nyr = entry.get("nyrakai", "")
        
        # Exact match
        if eng == word_lower:
            results["exact_match"] = entry
            continue
        
        # Same semantic category
        if word_category:
            for cat, members in SEMANTIC_CATEGORIES.items():
                if cat == word_category and eng in members:
                    results["same_category"].append(entry)
                    break
        
        # Partial string match in English meaning
        if word_lower in eng or eng in word_lower:
            results["partial_matches"].append(entry)
        
        # Root family (shared Nyrakai root - first 2-3 chars)
        if results["exact_match"]:
            exact_nyr = results["exact_match"].get("nyrakai", "")
            if len(exact_nyr) >= 2 and len(nyr) >= 2:
                if nyr[:2] == exact_nyr[:2] and nyr != exact_nyr:
                    results["root_family"].append(entry)
    
    return results


def suggest_derivations(base_word: dict) -> list:
    """Suggest possible derived forms from a base word."""
    if not base_word:
        return []
    
    nyr = base_word.get("nyrakai", "")
    eng = base_word.get("english", "")
    pos = base_word.get("pos", "noun")
    gender = base_word.get("inherent_gender", "flexible")
    
    suggestions = []
    
    # Check if word ends in consonant (for bridge vowel)
    vowels = set('aeiouāēīōūæɒɛəœ')
    ends_in_consonant = nyr and nyr[-1] not in vowels
    
    # Gender derivations (for flexible nouns)
    if pos == "noun" and gender == "flexible":
        # Masculine
        masc = nyr + DERIVATION_PATTERNS['masculine']['suffix']
        suggestions.append({
            "derived": masc,
            "base": nyr,
            "english": f"{eng} (masculine)",
            "pattern": "masculine",
            "description": DERIVATION_PATTERNS['masculine']['description']
        })
        
        # Feminine (with bridge vowel if needed)
        if ends_in_consonant:
            fem = nyr + DERIVATION_PATTERNS['feminine']['bridge'] + DERIVATION_PATTERNS['feminine']['suffix']
        else:
            fem = nyr + DERIVATION_PATTERNS['feminine']['suffix']
        suggestions.append({
            "derived": fem,
            "base": nyr,
            "english": f"{eng} (feminine)",
            "pattern": "feminine",
            "description": DERIVATION_PATTERNS['feminine']['description']
        })
        
        # Plural forms
        masc_plural = masc + DERIVATION_PATTERNS['plural_m']['suffix']
        fem_plural = fem + DERIVATION_PATTERNS['plural_f']['suffix']
        suggestions.append({
            "derived": masc_plural,
            "base": nyr,
            "english": f"{eng}s (masculine plural)",
            "pattern": "plural_m",
            "description": "masculine/mixed plural"
        })
        suggestions.append({
            "derived": fem_plural,
            "base": nyr,
            "english": f"{eng}s (feminine plural)",
            "pattern": "plural_f",
            "description": "feminine plural"
        })
    
    # Negation (for adjectives/qualities)
    if pos in ["adjective", "noun"] and eng in ['good', 'true', 'free', 'hot', 'cold', 'big', 'small', 'new', 'old', 'friend', 'life']:
        neg = DERIVATION_PATTERNS['negation']['prefix'] + nyr
        opposite = {
            'good': 'bad', 'true': 'false', 'free': 'bound', 'hot': 'cold', 
            'cold': 'hot', 'big': 'small', 'small': 'big', 'new': 'old', 
            'old': 'new', 'friend': 'enemy', 'life': 'death'
        }.get(eng, f"not-{eng}")
        suggestions.append({
            "derived": neg,
            "base": nyr,
            "english": opposite,
            "pattern": "negation",
            "description": DERIVATION_PATTERNS['negation']['description']
        })
    
    # Augmentative (great X)
    if pos == "noun":
        aug = nyr + DERIVATION_PATTERNS['augmentative']['suffix']
        suggestions.append({
            "derived": aug,
            "base": nyr,
            "english": f"great {eng}",
            "pattern": "augmentative",
            "description": DERIVATION_PATTERNS['augmentative']['description']
        })
    
    # Diminutive (small X)
    if pos == "noun":
        dim = nyr + DERIVATION_PATTERNS['diminutive']['suffix']
        suggestions.append({
            "derived": dim,
            "base": nyr,
            "english": f"little {eng}",
            "pattern": "diminutive",
            "description": DERIVATION_PATTERNS['diminutive']['description']
        })
    
    return suggestions


def display_related_words(english_word: str):
    """Display related words and derivation suggestions."""
    related = find_related_words(english_word)
    
    print("\n" + "=" * 50)
    print("📚 DICTIONARY LOOKUP")
    print("=" * 50)
    
    # Exact match
    if related["exact_match"]:
        entry = related["exact_match"]
        print(f"\n✅ FOUND IN DICTIONARY:")
        print(f"   {entry['nyrakai']} = {entry['english']} ({entry.get('pos', 'noun')})")
        if entry.get('notes'):
            print(f"   Notes: {entry['notes']}")
        
        # Show derivations
        derivations = suggest_derivations(entry)
        if derivations:
            print(f"\n🔄 POSSIBLE DERIVATIONS:")
            for d in derivations[:6]:  # Limit to 6
                print(f"   {d['derived']} → {d['english']}")
                print(f"      Pattern: {d['pattern']} ({d['description']})")
    else:
        print(f"\n❌ '{english_word}' not in dictionary yet")
    
    # Same category words
    if related["same_category"]:
        print(f"\n📂 SAME CATEGORY ({len(related['same_category'])} words):")
        for entry in related["same_category"][:8]:  # Limit display
            print(f"   {entry['nyrakai']} = {entry['english']}")
    
    # Partial matches
    if related["partial_matches"]:
        print(f"\n🔍 PARTIAL MATCHES:")
        for entry in related["partial_matches"][:5]:
            print(f"   {entry['nyrakai']} = {entry['english']}")
    
    # Root family
    if related["root_family"]:
        print(f"\n🌿 SAME ROOT FAMILY:")
        for entry in related["root_family"][:5]:
            print(f"   {entry['nyrakai']} = {entry['english']}")
    
    return related

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
EJECTIVES: k^, p^, t^ (with caret)
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
- Ejectives (k^, p^, t^) count as single consonants

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

# ============================================
# NEW FEATURES: Borrowing & Onomatopoeia
# ============================================

BORROWING_REFERENCE = """
BORROWING SYSTEM:
When generating words, occasionally draw from these source languages:

1. TAMIL (~60% of borrowings) - For everyday concepts:
   - Transform Tamil roots with Nyrakai phonotactics
   - Add ejectives, glottal markers, affricates
   - Examples: ஆறு (āṟu) "river" → nærŧ, கனவு (kaṉavu) "dream" → k^æn'œ

2. SANSKRIT - For sacred/abstract concepts:
   - Philosophy, ritual, fate, soul
   - Examples: आत्मा (ātmā) "soul" → ræțm, ज्ञान (jñāna) "wisdom" → ñ'ān

3. GREEK - For celestial concepts:
   - Sun, moon, stars, thunder
   - Examples: ἥλιος (hḗlios) "sun" → hīra, ἀστήρ (astḗr) "star" → hīn

4. ARAMAIC - For sacred/ritual words
5. ARABIC - For numerals, trade terms

TRANSFORMATION RULES:
- Drop syllables, harden vowels
- Add ejectives (k^, p^, t^) or glottal (')
- Use affricates (ƨ, ƶ, ŧ, ț) 
- Always follow Nyrakai syllable rules
"""

ONOMATOPOEIA_REFERENCE = """
ONOMATOPOEIA SYSTEM:
Sound-words use these exotic consonants heavily:

| Sound | IPA | Use For |
|-------|-----|---------|
| k^ | /k'/ | Thunder, cracks, sharp sounds |
| p^ | /p'/ | Impacts, pops, drops |
| t^ | /t'/ | Snaps, breaks |
| ƨ (ts) | /ts/ | Fire, hissing, steam |
| ƶ (dz) | /dz/ | Fire roar, buzzing |
| ŧ (tr) | /tr/ | Rumbles, tremors |
| ț (th) | /θ/ | Wind, whispers |
| ' | /əʔ/ | Cosmic breaks, forbidden sounds |

EXAMPLES:
- ŧ'ōm (thunder rumble)
- ƨræk (fire crackle) 
- ƶōr (fire roar)
- ț'ūs (whisper)
- pl'æš (splash)
- ƶūr (growl)

Reduplication (once only) for sustained sounds: ŧ'ōm-ŧ'ōm
"""

PRONUNCIATION_GUIDE = """
PRONUNCIATION OUTPUT RULES:
When the word contains ' (schwa marker):
- The ' adds "uh" (schwa) + glottal stop before the vowel
- ALWAYS show this in pronunciation!

Examples:
- n'æ → "nuh-ai" (NOT "nai")  
- r'ōk → "ruh-ohk" (NOT "rohk")
- ŧ'ōm → "tr-uh-ohm" (NOT "trohm")
- k^æn'œ → "kain-uh-oi" (NOT "kain-oi")

The "uh" must appear in every pronunciation where ' exists!
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


def get_domain_hint(english_word: str) -> str:
    """Get domain and onset hints based on the English word's semantic category."""
    if not SOUND_MAP_AVAILABLE:
        return ""
    
    # Map common English words to Nyrakai domains
    domain_keywords = {
        'nature': ['water', 'fire', 'earth', 'air', 'wind', 'rain', 'cloud', 'stone', 'rock', 'tree', 'plant', 'river', 'mountain', 'forest', 'sea', 'lake'],
        'body': ['hand', 'foot', 'eye', 'ear', 'mouth', 'heart', 'blood', 'bone', 'skin', 'head', 'tongue', 'nose', 'hair', 'flesh', 'tooth', 'knee', 'liver', 'belly', 'neck', 'breast'],
        'action': ['give', 'walk', 'stand', 'come', 'go', 'run', 'take', 'make', 'do', 'see', 'hear', 'create', 'build', 'fight', 'swim', 'fly', 'sleep', 'eat', 'drink', 'kill', 'die', 'sit', 'lie'],
        'abstract': ['truth', 'death', 'soul', 'fate', 'wisdom', 'life', 'dream', 'fear', 'hope', 'love', 'hate', 'like'],
        'social': ['person', 'man', 'woman', 'child', 'village', 'family', 'tribe', 'king', 'queen', 'leader', 'voice', 'name'],
        'quantity': ['one', 'two', 'three', 'four', 'five', 'many', 'few', 'all', 'none', 'zero', 'pair'],
        'spatial': ['big', 'small', 'long', 'short', 'over', 'under', 'near', 'far', 'round', 'path', 'road'],
        'quality': ['good', 'bad', 'hot', 'cold', 'dry', 'wet', 'new', 'old', 'dark', 'light', 'true', 'false'],
        'celestial': ['sun', 'moon', 'star', 'sky', 'light', 'bright', 'white', 'day', 'night'],
        'mammal': ['dog', 'cat', 'deer', 'horse', 'cow', 'sheep', 'goat', 'wolf', 'bear', 'lion', 'tiger', 'pig', 'fox', 'rabbit', 'mouse', 'rat', 'elephant', 'monkey', 'ape', 'beast', 'animal', 'mammal', 'doe', 'buck', 'stag'],
        'bird': ['bird', 'eagle', 'hawk', 'owl', 'crow', 'raven', 'sparrow', 'dove', 'pigeon', 'chicken', 'duck', 'goose', 'swan', 'falcon'],
        'fish': ['fish', 'shark', 'whale', 'dolphin', 'salmon', 'trout', 'eel'],
        'insect': ['insect', 'bug', 'louse', 'ant', 'bee', 'wasp', 'fly', 'spider', 'worm', 'beetle'],
    }
    
    word_lower = english_word.lower()
    detected_domain = None
    
    for domain, keywords in domain_keywords.items():
        if word_lower in keywords:
            detected_domain = domain
            break
    
    # Special onset mappings for animal domains (from sound-map.md)
    animal_onsets = {
        'mammal': ['gw-'],  # gwōr (dog), beasts, livestock
        'bird': ['t-'],     # tūk (bird), flying creatures
        'fish': ['n-'],     # nūl (fish), aquatic creatures
        'insect': ['y-'],   # yīk (louse), small creatures
    }
    
    if detected_domain:
        # Use special animal onsets or fall back to sound_map
        if detected_domain in animal_onsets:
            onsets = animal_onsets[detected_domain]
            onset_str = ", ".join(onsets)
            return f"""
SOUND MAP GUIDANCE (MANDATORY):
The word "{english_word}" is a {detected_domain.upper()}.
YOU MUST START the word with one of these onsets: {onset_str}
This is NOT optional - words for {detected_domain}s MUST use these sounds.
Examples: gwōr (dog), tūk (bird), nūl (fish), yīk (louse)
"""
        else:
            onsets = suggest_onset(detected_domain)
            onset_str = ", ".join(onsets[:8])  # Limit to 8 examples
            return f"""
SOUND MAP GUIDANCE:
The word "{english_word}" belongs to the {detected_domain.upper()} domain.
Preferred onsets for this domain: {onset_str}
You SHOULD START the word with one of these sounds for phonosemantic consistency.
"""
    
    return ""


def get_word_type_hint(english_word: str) -> tuple:
    """Determine if word should use borrowing or onomatopoeia approach."""
    import random
    
    # Onomatopoeia candidates
    sound_words = ['thunder', 'splash', 'crack', 'crash', 'bang', 'boom', 'hiss', 
                   'whisper', 'growl', 'roar', 'buzz', 'hum', 'snap', 'pop', 
                   'drip', 'sizzle', 'crackle', 'rumble', 'thud', 'clap']
    
    # Sacred/abstract words (Sanskrit borrowing)
    sacred_words = ['soul', 'fate', 'wisdom', 'divine', 'sacred', 'spirit', 
                    'eternal', 'truth', 'destiny', 'karma', 'dharma', 'meditation']
    
    # Celestial words (Greek borrowing)  
    celestial_words = ['sun', 'moon', 'star', 'sky', 'heaven', 'cosmos', 'thunder']
    
    word_lower = english_word.lower()
    
    if word_lower in sound_words:
        return ('onomatopoeia', ONOMATOPOEIA_REFERENCE)
    elif word_lower in sacred_words:
        return ('borrowing_sanskrit', BORROWING_REFERENCE)
    elif word_lower in celestial_words:
        return ('borrowing_greek', BORROWING_REFERENCE)
    elif random.random() < 0.3:  # 30% chance to use borrowing approach
        return ('borrowing_tamil', BORROWING_REFERENCE)
    else:
        return ('standard', '')


def generate_words(english_word: str, count: int = 5, domain: str = None) -> list:
    """Generate Nyrakai word suggestions for an English word."""
    
    # Get domain hint (use explicit domain if provided)
    if domain and SOUND_MAP_AVAILABLE:
        # Find valid onsets for this domain
        valid_onsets = [o for o, (p, s, _) in SOUND_MAP.items() if p == domain or s == domain]
        onset_list = ', '.join(sorted(valid_onsets)[:12])
        domain_hint = f"""
DOMAIN CONSTRAINT: The word MUST start with one of these onsets for the '{domain}' domain:
Valid onsets: {onset_list}

This is MANDATORY - do not use any other onset consonants!
"""
    else:
        domain_hint = get_domain_hint(english_word) if SOUND_MAP_AVAILABLE else ""
    
    # Get word type hint (borrowing or onomatopoeia)
    word_type, type_reference = get_word_type_hint(english_word)
    
    # Build type-specific instructions
    type_instructions = ""
    if word_type == 'onomatopoeia':
        type_instructions = """
SPECIAL: This is a SOUND WORD (onomatopoeia)!
- Use exotic consonants heavily: k^, p^, t^, ƨ, ƶ, ŧ, ț, '
- Make it sound like what it represents
- Can use reduplication (once only) for sustained sounds
"""
    elif word_type.startswith('borrowing'):
        source = word_type.split('_')[1].upper()
        type_instructions = f"""
SPECIAL: Consider {source} etymology for this word.
- Transform the source root using Nyrakai phonotactics
- Add ejectives, glottal markers, or affricates
- Drop syllables, shift vowels as needed
"""
    
    prompt = f"""{NYRAKAI_REFERENCE}

{PRONUNCIATION_GUIDE}

{INSPIRATION_NOTE}
{type_reference}
{domain_hint}
{type_instructions}

Generate exactly {count} unique Nyrakai word suggestions for the English word: "{english_word}"

Requirements:
1. Each word must follow Nyrakai phonotactic rules strictly
2. Use a MIX of plain syllables AND distinctive Nyrakai features (ejectives, schwa marker, affricates, long vowels, diphthongs)
3. Vary the complexity - some simple (1 syllable), some complex (2-3 syllables)
4. Make them feel ancient and mysterious
5. Use digraph forms (ai, ee, th, tr, etc.) - they will be auto-converted
6. If domain guidance is provided, prefer those onset sounds
7. IMPORTANT: If the word contains ' (schwa marker), the pronunciation MUST include "uh" before the vowel!

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


def validate_suggestions(suggestions: list, english_word: str = None) -> list:
    """Validate each suggestion against Nyrakai rules and show domain."""
    results = []
    
    for s in suggestions:
        word = s.get("word", "")
        reasoning = s.get("reasoning", "")
        
        validation = validate_word(word)
        
        result_entry = {
            "original": word,
            "normalized": validation["normalized"],
            "valid": validation["valid"],
            "errors": validation["errors"],
            "warnings": validation["warnings"],
            "phonemes": validation["phonemes"],
            "reasoning": reasoning
        }
        
        # Add domain info if available
        if SOUND_MAP_AVAILABLE:
            onset = get_onset(validation["normalized"])
            primary, secondary = get_domain(validation["normalized"])
            result_entry["onset"] = onset
            result_entry["domain"] = primary or "unmapped"
        
        # Check if word already exists in dictionary
        exists, eng_meaning = word_exists_in_dictionary(validation["normalized"])
        result_entry["exists_in_dictionary"] = exists
        if exists:
            result_entry["existing_meaning"] = eng_meaning
            result_entry["warnings"].append(f"⚠️  DUPLICATE: already means '{eng_meaning}'")
        
        # Check for English similarity (avoid look-alikes)
        if english_word and result_entry["valid"]:
            eng_valid, eng_warnings = check_english_similarity(
                validation["normalized"], english_word, threshold=0.5
            )
            if not eng_valid:
                result_entry["warnings"].extend([f"🚨 {w}" for w in eng_warnings])
                result_entry["english_similar"] = True
        
        results.append(result_entry)
    
    return results


def main():
    if len(sys.argv) < 2:
        print("Usage: python word-generator.py <english_word> [count] [--domain DOMAIN]")
        print("       python word-generator.py <english_word> --lookup")
        print("       python word-generator.py --domains (list available domains)")
        print("Example: python word-generator.py 'fire' 5 --domain nature")
        sys.exit(1)
    
    # Show available domains
    if sys.argv[1] == "--domains":
        if SOUND_MAP_AVAILABLE:
            from sound_map import DOMAINS
            print("Available domains and their onsets:")
            print("=" * 50)
            for domain, desc in DOMAINS.items():
                # Find onsets for this domain
                onsets = [o for o, (p, s, _) in SOUND_MAP.items() if p == domain or s == domain]
                print(f"  {domain:12}: {', '.join(sorted(onsets)[:8])}")
                print(f"               {desc}")
        else:
            print("Sound map not available")
        sys.exit(0)
    
    english_word = sys.argv[1]
    
    # Check for --lookup flag (only show related words, no generation)
    if len(sys.argv) > 2 and sys.argv[2] == "--lookup":
        display_related_words(english_word)
        sys.exit(0)
    
    # Parse --domain flag
    target_domain = None
    count = 5
    for i, arg in enumerate(sys.argv[2:], 2):
        if arg == "--domain" and i + 1 < len(sys.argv):
            target_domain = sys.argv[i + 1]
        elif arg.isdigit():
            count = int(arg)
    
    domain_msg = f" [domain: {target_domain}]" if target_domain else ""
    print(f"\n🗣️  Generating {count} Nyrakai words for: \"{english_word}\"{domain_msg}\n")
    
    # Show valid onsets for target domain
    if target_domain and SOUND_MAP_AVAILABLE:
        valid_onsets = [o for o, (p, s, _) in SOUND_MAP.items() if p == target_domain or s == target_domain]
        print(f"🎯 Target domain '{target_domain}' uses onsets: {', '.join(sorted(valid_onsets)[:10])}\n")
    
    # First, show related words from dictionary
    related = display_related_words(english_word)
    
    # If word exists, ask if they still want to generate
    if related["exact_match"]:
        print(f"\n💡 Word exists! Derivations shown above.")
        print("   Generating new alternatives anyway...\n")
    
    print("=" * 50)
    
    # Generate suggestions with domain constraint
    suggestions = generate_words(english_word, count, domain=target_domain)
    
    if not suggestions:
        print("Failed to generate suggestions.")
        sys.exit(1)
    
    # Validate each (including English similarity check)
    results = validate_suggestions(suggestions, english_word=english_word)
    
    # Filter by domain if specified
    if target_domain and SOUND_MAP_AVAILABLE:
        valid_onsets = set(o for o, (p, s, _) in SOUND_MAP.items() if p == target_domain or s == target_domain)
        for r in results:
            onset = r.get('onset', '')
            if onset and onset not in valid_onsets:
                r['valid'] = False
                r['errors'].append(f"Onset '{onset}' not valid for domain '{target_domain}'")
    
    # Display results
    print("\n🆕 AI-GENERATED SUGGESTIONS:")
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
        
        # Show domain info if available
        if 'onset' in r:
            print(f"   Onset: {r['onset']}- | Domain: {r['domain']}")
        
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
                domain_str = f" [{r.get('domain', '?')}]" if 'domain' in r else ""
                print(f"   {r['normalized']} - {english_word}{domain_str}")


if __name__ == "__main__":
    main()




# ============================================
# SMART WORD GENERATION SYSTEM
# ============================================

# Derivation rules: concept -> (base_word, affix, type)
DERIVATION_RULES = {
    # Negation patterns (za- prefix)
    'bad': ('good', 'za', 'prefix'),
    'dirty': ('clean', 'za', 'prefix'),
    'ugly': ('beautiful', 'za', 'prefix'),
    'wrong': ('correct', 'za', 'prefix'),
    'weak': ('strong', 'za', 'prefix'),
    'dull': ('sharp', 'za', 'prefix'),
    'wet': ('dry', 'za', 'prefix'),
    'cold': ('hot', 'za', 'prefix'),
    'dark': ('bright', 'za', 'prefix'),
    'enemy': ('friend', 'za', 'prefix'),
    'hate': ('love', 'za', 'prefix'),
    'die': ('live', 'za', 'prefix'),
    
    # Agentive (-ƨu suffix) - doer of action
    'hunter': ('hunt', 'ƨu', 'suffix'),
    'singer': ('sing', 'ƨu', 'suffix'),
    'fighter': ('fight', 'ƨu', 'suffix'),
    'speaker': ('speak', 'ƨu', 'suffix'),
    'killer': ('kill', 'ƨu', 'suffix'),
    'teacher': ('teach', 'ƨu', 'suffix'),
    'leader': ('lead', 'ƨu', 'suffix'),
    
    # Resultative (-țal suffix) - result of action
    'ash': ('burn', 'țal', 'suffix'),
    'death': ('die', 'țal', 'suffix'),
    'wound': ('cut', 'țal', 'suffix'),
    'creation': ('create', 'țal', 'suffix'),
    
    # Nominalizer (-ra suffix) - action to thing
    'fire': ('burn', 'ra', 'suffix'),
    'speech': ('speak', 'ra', 'suffix'),
    'thought': ('think', 'ra', 'suffix'),
    'breath': ('breathe', 'ra', 'suffix'),
    'dream': ('sleep', 'ra', 'suffix'),
    
    # Diminutive (-k^e suffix)
    'rain': ('water', 'k^e', 'suffix'),
    'sand': ('stone', 'k^e', 'suffix'),
    'ember': ('fire', 'k^e', 'suffix'),
    'pond': ('lake', 'k^e', 'suffix'),
    'hill': ('mountain', 'k^e', 'suffix'),
    
    # Augmentative (-ñor suffix)
    'wind': ('air', 'ñor', 'suffix'),
    'inferno': ('fire', 'ñor', 'suffix'),
    'ocean': ('sea', 'ñor', 'suffix'),
    'storm': ('rain', 'ñor', 'suffix'),
    
    # Place/Domain (-bren suffix)
    'forest': ('tree', 'bren', 'suffix'),
    'homeland': ('home', 'bren', 'suffix'),
    
    # Keeper/Guardian (-raš suffix)
    'shepherd': ('sheep', 'raš', 'suffix'),
    'guardian': ('guard', 'raš', 'suffix'),
}

# Onomatopoeia patterns - sound-symbolic words
ONOMATOPOEIA = {
    # Use ŧ'- onset for explosive/impact sounds
    'crash': ("ŧ'", ['æš', 'ōk', 'ūm']),
    'crack': ("ŧ'", ['æk', 'ōr', 'ūn']),
    'thunder': ("ŧ'", ['ōm', 'ūn', 'æl']),
    'bang': ("ŧ'", ['æñ', 'ōk', 'ūm']),
    'boom': ("ŧ'", ['ūm', 'ōn', 'æl']),
    
    # Use ƨ- onset for hissing/flowing sounds
    'splash': ('ƨ', ['læš', 'ōr', 'ūl']),
    'hiss': ('ƨ', ['īs', 'ær', 'ūn']),
    'sizzle': ('ƨ', ['īl', 'ōs', 'ær']),
    'flow': ('ƨ', ['ōr', 'æl', 'ūn']),
    'whistle': ('ƨ', ['īl', 'ōr', 'æn']),
    
    # Use gr- for growling/rumbling sounds
    'growl': ('gr', ['ōl', 'æn', 'ūr']),
    'rumble': ('gr', ['ūl', 'ōm', 'ær']),
    'roar': ('gr', ['ōr', 'æl', 'ūn']),
    
    # Use pl- for liquid/splashing sounds
    'plop': ('pl', ['ōp', 'æk', 'ūn']),
    'bubble': ('pl', ['ūl', 'ōk', 'ær']),
    'drip': ('pl', ['īk', 'ōr', 'ūl']),
    
    # Use š- for shushing/soft sounds
    'whisper': ('š', ['īr', 'ōl', 'ūn']),
    'shush': ('š', ['ūš', 'ōr', 'æl']),
    'rustle': ('š', ['ūl', 'ōr', 'æn']),
}

# Compound patterns for complex concepts
COMPOUND_RULES = {
    # body-part + quality compounds
    'blind': ('eye', 'dead'),
    'deaf': ('ear', 'dead'),
    'mute': ('mouth', 'dead'),
    
    # element + element compounds
    'mud': ('water', 'earth'),
    'steam': ('water', 'fire'),
    'lava': ('fire', 'stone'),
    
    # time compounds
    'midnight': ('night', 'middle'),
    'noon': ('day', 'middle'),
    'dawn': ('day', 'birth'),
    'dusk': ('day', 'death'),
}


def smart_generate(english_word: str, category: str = None) -> dict:
    """
    Smart word generation that tries:
    1. Derivation from existing root
    2. Onomatopoeia for sound-symbolic words
    3. Compound creation
    4. New root generation with proper onset
    
    Returns dict with word, method, and explanation.
    """
    word_lower = english_word.lower()
    dictionary = load_dictionary()
    
    # Build lookup
    eng_to_nyr = {}
    for entry in dictionary.get("words", []):
        eng = entry.get("english", "").lower()
        nyr = entry.get("nyrakai", "").split(" / ")[0]
        eng_to_nyr[eng] = nyr
    
    result = {
        "english": english_word,
        "method": None,
        "nyrakai": None,
        "base_word": None,
        "affix": None,
        "explanation": None,
    }
    
    # 1. Check for derivation
    if word_lower in DERIVATION_RULES:
        base_eng, affix, affix_type = DERIVATION_RULES[word_lower]
        if base_eng in eng_to_nyr:
            base_nyr = eng_to_nyr[base_eng]
            if affix_type == 'prefix':
                derived = affix + base_nyr
            else:
                derived = base_nyr + affix
            
            # Validate
            validation = validate_word(derived)
            if validation['valid']:
                result["method"] = "derivation"
                result["nyrakai"] = derived
                result["base_word"] = base_nyr
                result["affix"] = affix
                result["explanation"] = f"{affix}- + {base_nyr} ({base_eng})" if affix_type == 'prefix' else f"{base_nyr} ({base_eng}) + -{affix}"
                return result
    
    # 2. Check for onomatopoeia
    if word_lower in ONOMATOPOEIA:
        onset, templates = ONOMATOPOEIA[word_lower]
        for template in templates:
            word = onset + template
            if word.lower() not in [e.get("nyrakai", "").lower() for e in dictionary.get("words", [])]:
                validation = validate_word(word)
                if validation['valid']:
                    result["method"] = "onomatopoeia"
                    result["nyrakai"] = word
                    result["explanation"] = f"Sound-symbolic: {onset}- onset mimics the sound"
                    return result
    
    # 3. Check for compound
    if word_lower in COMPOUND_RULES:
        part1_eng, part2_eng = COMPOUND_RULES[word_lower]
        if part1_eng in eng_to_nyr and part2_eng in eng_to_nyr:
            part1_nyr = eng_to_nyr[part1_eng]
            part2_nyr = eng_to_nyr[part2_eng]
            compound = part1_nyr + "-" + part2_nyr
            result["method"] = "compound"
            result["nyrakai"] = compound
            result["explanation"] = f"{part1_nyr} ({part1_eng}) + {part2_nyr} ({part2_eng})"
            return result
    
    # 4. Fall back to new root with proper onset
    result["method"] = "new_root"
    result["explanation"] = "Generate new root with category-appropriate onset"
    
    return result


def print_smart_suggestion(english_word: str, category: str = None):
    """Print smart generation suggestion."""
    result = smart_generate(english_word, category)
    
    print(f"\n{'='*50}")
    print(f"Word: {result['english']}")
    print(f"{'='*50}")
    
    if result['method'] == 'derivation':
        print(f"✨ DERIVATION FOUND!")
        print(f"   Base: {result['base_word']}")
        print(f"   Affix: {result['affix']}")
        print(f"   Result: {result['nyrakai']}")
        print(f"   Formula: {result['explanation']}")
    elif result['method'] == 'onomatopoeia':
        print(f"🔊 ONOMATOPOEIA!")
        print(f"   Word: {result['nyrakai']}")
        print(f"   {result['explanation']}")
    elif result['method'] == 'compound':
        print(f"🔗 COMPOUND!")
        print(f"   Word: {result['nyrakai']}")
        print(f"   Formula: {result['explanation']}")
    else:
        print(f"📝 NEW ROOT NEEDED")
        print(f"   {result['explanation']}")
    
    return result

