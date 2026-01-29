#!/usr/bin/env python3
"""
Nyrakai Word Validator & Dictionary Manager
Checks if words follow Nyrakai phonotactic rules
Now with STRICT syllable structure validation!
"""

import json
import re
from pathlib import Path

# Nyrakai Alphabet
CONSONANTS = set('dfghklmnñprst') | {'ț', 'z'}
VOWELS_SHORT = set('aeiou')
VOWELS_LONG = {'ā', 'ē', 'ī', 'ō', 'ū'}
VOWELS = VOWELS_SHORT | VOWELS_LONG
GLIDES = {'w', 'y'}
EJECTIVES = {"k^", "p^", "t^"}
AFFRICATES = {'ƨ', 'š', 'ƶ', 'ŧ'}  # ts, tch, dz, tr
DIPHTHONGS_SHORT = {'æ', 'ɒ', 'ɛ', 'ə', 'œ'}  # ai, au, ei, eu, oi
DIPHTHONGS_LONG = {'ǣ'}  # āi (precomposed)
# These use combining macron (0x304) and need special handling:
DIPHTHONGS_LONG_COMBINING = {'ɒ̄', 'ɛ̄', 'ə̄', 'œ̄'}  # āu, ēi, ēu, ōi
DIPHTHONGS_LONG = DIPHTHONGS_LONG | DIPHTHONGS_LONG_COMBINING
DIPHTHONGS = DIPHTHONGS_SHORT | DIPHTHONGS_LONG

# Glottal marker (schwa + glottal stop)
# Special: C'V pattern - the ' adds schwa+glottal between consonant and vowel
# Treated as modifying the following vowel, not as a standalone consonant
GLOTTAL_MARKER = "'"

ALL_VOWELS = VOWELS | DIPHTHONGS
ALL_CONSONANTS = CONSONANTS | GLIDES | AFFRICATES | set(EJECTIVES)
# Note: ' is NOT in ALL_CONSONANTS - it's handled specially

# Exclusion rules
ONSET_C1_EXCLUDED = {GLOTTAL_MARKER}  # ' cannot start syllable
ONSET_C2_EXCLUDED = {"p'", "k'", "t'", 'š', 'ƨ', 'ñ'}  # these cannot be second consonant in cluster
CODA_EXCLUDED = {GLOTTAL_MARKER}  # ' cannot end syllable

# Valid consonant clusters for onset (C1 + C2)
# Common clusters: dr, gr, zw, kr, pr, tr, etc.
VALID_CLUSTERS = {
    'd': {'r', 'w'},
    'g': {'r', 'l', 'w'},
    'h': {'r'},  # for hro (white/bright)
    'k': {'r', 'l', 'w'},
    'p': {'r', 'l'},
    't': {'r', 'w'},
    's': {'r', 'l', 'w', 'n', 'm', 'k', 'p', 't'},
    'z': {'r', 'w', 'l'},
    'f': {'r', 'l'},
    'ŧ': {'r', 'w'},  # tr + r/w
    'ƶ': {'r', 'w'},  # dz + r/w
    'ț': {'r'},  # th + r (for țræn etc.)
}

DICT_PATH = Path(__file__).parent.parent / "memory" / "nyrakai-dictionary.json"

# Diphthong conversion map (digraph → single letter)
DIPHTHONG_MAP = {
    'ai': 'æ',
    'au': 'ɒ',
    'ei': 'ɛ',
    'eu': 'ə',
    'oi': 'œ',
    'āi': 'ǣ',
    'āu': 'ɒ̄',
    'ēi': 'ɛ̄',
    'ēu': 'ə̄',
    'ōi': 'œ̄',
}

# Long vowel conversion (double → macron)
LONG_VOWEL_MAP = {
    'aa': 'ā',
    'ee': 'ē',
    'ii': 'ī',
    'oo': 'ō',
    'uu': 'ū',
}

# Affricate/digraph conversion map (digraph → single letter)
AFFRICATE_MAP = {
    'ts': 'ƨ',
    'tch': 'š',
    'dz': 'ƶ',
    'tr': 'ŧ',
    'th': 'ț',  # voiceless dental fricative (like "think")
}


def normalize(word: str) -> str:
    """
    Normalize a word by converting digraphs to single letters.
    e.g., 'weilu' → 'wɛlu', 'kai' → 'kæ', 'tra' → 'ŧa', 'neer' → 'nēr'
    """
    result = word.lower()
    # Sort by length descending to match longer patterns first (tch before ts, āi before ai)
    for digraph, letter in sorted(AFFRICATE_MAP.items(), key=lambda x: -len(x[0])):
        result = result.replace(digraph, letter)
    # Long vowels (ee → ē) - must come BEFORE diphthongs to avoid conflicts
    for digraph, letter in sorted(LONG_VOWEL_MAP.items(), key=lambda x: -len(x[0])):
        result = result.replace(digraph, letter)
    for digraph, letter in sorted(DIPHTHONG_MAP.items(), key=lambda x: -len(x[0])):
        result = result.replace(digraph, letter)
    return result


def tokenize(word: str) -> list:
    """Break word into Nyrakai phonemes"""
    tokens = []
    i = 0
    word = word.lower()
    
    COMBINING_MACRON = '\u0304'  # ̄
    
    while i < len(word):
        # Check for ejectives (2-char: k', p', t')
        if i + 1 < len(word) and word[i:i+2] in EJECTIVES:
            tokens.append(word[i:i+2])
            i += 2
        # Check for long diphthongs with combining macron (2-char: base + ̄)
        elif i + 1 < len(word) and word[i+1] == COMBINING_MACRON:
            tokens.append(word[i:i+2])  # base + macron as single token
            i += 2
        # Check for glottal marker (')
        elif word[i] == GLOTTAL_MARKER:
            if i + 1 < len(word):
                next_char = word[i+1]
                # 'V pattern: glottal + vowel (onset/nucleus modifier)
                if next_char in ALL_VOWELS:
                    tokens.append("'" + next_char)  # 'V as single unit
                    i += 2
                else:
                    # V' pattern: the ' follows a vowel, adds schwa-glottal as coda
                    # Just add ' as a glottal coda marker
                    tokens.append("'")
                    i += 1
            else:
                # Word-final ' (rare but handle it)
                tokens.append("'")
                i += 1
        # Check for diphthongs
        elif word[i] in DIPHTHONGS_LONG or word[i] in DIPHTHONGS_SHORT:
            tokens.append(word[i])
            i += 1
        # Check for long vowels
        elif word[i] in VOWELS_LONG:
            tokens.append(word[i])
            i += 1
        # Single characters
        else:
            tokens.append(word[i])
            i += 1
    
    return tokens


def is_glottal_vowel(phoneme: str) -> bool:
    """Check if phoneme is a glottal-modified vowel ('V)"""
    return phoneme.startswith("'") and len(phoneme) == 2 and phoneme[1] in ALL_VOWELS


def is_glottal_coda(phoneme: str) -> bool:
    """Check if phoneme is a glottal coda marker (standalone ')"""
    return phoneme == "'"


def is_vowel(phoneme: str) -> bool:
    """Check if phoneme is a vowel (including glottal-modified vowels and long diphthongs)"""
    return phoneme in ALL_VOWELS or is_glottal_vowel(phoneme) or phoneme in DIPHTHONGS_LONG_COMBINING


def is_consonant(phoneme: str) -> bool:
    """Check if phoneme is a consonant (not including glottal coda)"""
    return phoneme in CONSONANTS or phoneme in GLIDES or phoneme in AFFRICATES or phoneme in EJECTIVES


def is_coda_valid(phoneme: str) -> bool:
    """Check if phoneme can be in coda position"""
    # Regular consonants and glottal coda (') are valid
    return is_consonant(phoneme) or is_glottal_coda(phoneme)


def syllabify(tokens: list) -> tuple:
    """
    Break tokens into syllables following (C)(C)V(')(C) pattern.
    Uses maximum onset principle (consonants prefer to attach to following vowel).
    The glottal coda (') can appear after vowel: V' pattern.
    Returns: (syllables: list of lists, errors: list)
    """
    if not tokens:
        return [], ["Empty word"]
    
    syllables = []
    errors = []
    current = []
    i = 0
    
    while i < len(tokens):
        token = tokens[i]
        
        if is_vowel(token):
            # Vowel found - this is the nucleus
            current.append(token)
            
            # Check for glottal coda (') immediately after vowel
            if i + 1 < len(tokens) and is_glottal_coda(tokens[i + 1]):
                current.append(tokens[i + 1])  # Add ' as coda
                i += 1
            
            # Check for consonant coda
            if i + 1 < len(tokens) and is_consonant(tokens[i + 1]):
                # Look ahead: is there another vowel after?
                if i + 2 < len(tokens) and is_vowel(tokens[i + 2]):
                    # Next consonant goes to next syllable (onset)
                    pass
                elif i + 2 < len(tokens) and is_consonant(tokens[i + 2]):
                    # Two consonants ahead - first is coda, second+ is next onset
                    # Check if they could be a valid cluster
                    c1, c2 = tokens[i + 1], tokens[i + 2]
                    if c1 in VALID_CLUSTERS and c2 in VALID_CLUSTERS.get(c1, set()):
                        # Valid cluster - both go to next syllable
                        pass
                    else:
                        # Not a valid cluster - first is coda
                        current.append(tokens[i + 1])
                        i += 1
                else:
                    # Last consonant is coda
                    current.append(tokens[i + 1])
                    i += 1
            
            # Complete syllable
            syllables.append(current)
            current = []
        
        elif is_consonant(token):
            # Consonant - add to current (onset)
            current.append(token)
        
        elif is_glottal_coda(token):
            # Orphan glottal (shouldn't happen if tokenizer works right)
            errors.append(f"Unexpected glottal marker position: {token}")
        
        else:
            errors.append(f"Unknown token: '{token}'")
        
        i += 1
    
    # Handle remaining consonants (shouldn't happen in valid word)
    if current:
        if any(is_consonant(t) or is_glottal_coda(t) for t in current) and not any(is_vowel(t) for t in current):
            errors.append(f"Syllable without vowel: {''.join(current)}")
        else:
            syllables.append(current)
    
    return syllables, errors


def validate_syllable(syllable: list) -> tuple:
    """
    Validate a single syllable follows (C)(C)V(')(C) pattern.
    The glottal marker (') can appear after vowel as V' pattern.
    Returns: (valid: bool, structure: str, errors: list)
    """
    errors = []
    structure = ""
    
    # Separate into onset, nucleus, glottal_coda, consonant_coda
    onset = []
    nucleus = None
    glottal_coda = False
    coda = []
    
    found_vowel = False
    for i, token in enumerate(syllable):
        if is_vowel(token):
            if found_vowel:
                errors.append(f"Multiple vowels in syllable: {syllable}")
            nucleus = token
            found_vowel = True
            # Rest is coda (glottal and/or consonant)
            for t in syllable[i+1:]:
                if is_glottal_coda(t):
                    glottal_coda = True
                elif is_consonant(t):
                    coda.append(t)
            break
        else:
            onset.append(token)
    
    if nucleus is None:
        errors.append(f"No vowel in syllable: {''.join(syllable)}")
        return False, "", errors
    
    # Build structure string
    # V' counts as V' (vowel + glottal)
    glottal_str = "'" if glottal_coda else ""
    structure = "C" * len(onset) + "V" + glottal_str + "C" * len(coda)
    
    # Validate: (C)(C)V(')(C) means max 2 onset, optional glottal, max 1 consonant coda
    if len(onset) > 2:
        errors.append(f"Too many onset consonants ({len(onset)}): {''.join(onset)}")
    
    if len(coda) > 1:
        errors.append(f"Too many coda consonants ({len(coda)}): {''.join(coda)}")
    
    # Check onset C1 exclusion
    if len(onset) >= 1 and onset[0] in ONSET_C1_EXCLUDED:
        errors.append(f"'{onset[0]}' cannot be first consonant in onset")
    
    # Check onset C2 exclusion (second consonant in cluster)
    if len(onset) >= 2 and onset[1] in ONSET_C2_EXCLUDED:
        errors.append(f"'{onset[1]}' cannot be second consonant in cluster")
    
    # Check valid cluster
    if len(onset) == 2:
        c1, c2 = onset[0], onset[1]
        if c1 not in VALID_CLUSTERS or c2 not in VALID_CLUSTERS.get(c1, set()):
            # Allow if c1 is ejective or affricate with common C2
            if c1 not in EJECTIVES and c1 not in AFFRICATES:
                errors.append(f"Invalid consonant cluster: {c1}{c2}")
    
    # Note: glottal coda (') is ALLOWED, only regular coda exclusions apply
    if len(coda) >= 1 and coda[0] in CODA_EXCLUDED:
        errors.append(f"'{coda[0]}' cannot be in coda")
    
    valid = len(errors) == 0
    return valid, structure, errors


def validate_word(word: str, auto_normalize: bool = True) -> dict:
    """
    Validate a Nyrakai word with STRICT syllable checking.
    Returns: {valid: bool, errors: [], syllables: [], warnings: [], normalized: str}
    """
    # Normalize diphthongs if enabled
    normalized = normalize(word) if auto_normalize else word.lower()
    
    result = {
        "word": word,
        "normalized": normalized,
        "valid": True,
        "errors": [],
        "warnings": [],
        "syllables": [],
        "syllable_structures": [],
        "phonemes": []
    }
    
    # Add warning if word was normalized
    if normalized != word.lower():
        result["warnings"].append(f"Auto-normalized: '{word}' → '{normalized}'")
    
    tokens = tokenize(normalized)
    result["phonemes"] = tokens
    
    # Check all phonemes are valid
    all_valid = CONSONANTS | VOWELS | GLIDES | AFFRICATES | DIPHTHONGS | set(EJECTIVES)
    for t in tokens:
        # Allow glottal-modified vowels ('V pattern)
        if is_glottal_vowel(t):
            continue
        # Allow glottal coda (')
        if is_glottal_coda(t):
            continue
        # Allow long diphthongs with combining macron
        if t in DIPHTHONGS_LONG_COMBINING:
            continue
        if t not in all_valid:
            result["errors"].append(f"Invalid phoneme: '{t}'")
            result["valid"] = False
    
    if not result["valid"]:
        return result
    
    # Syllabify
    syllables, syll_errors = syllabify(tokens)
    result["errors"].extend(syll_errors)
    
    if syll_errors:
        result["valid"] = False
        return result
    
    # Validate each syllable
    for syll in syllables:
        valid, structure, errors = validate_syllable(syll)
        result["syllables"].append("".join(syll))
        result["syllable_structures"].append(structure)
        
        if not valid:
            result["valid"] = False
            result["errors"].extend(errors)
    
    return result


def add_word(nyrakai: str, english: str, pos: str, is_root: bool = True, etymology: str = "") -> dict:
    """Add a word to the dictionary after validation"""
    
    validation = validate_word(nyrakai)
    
    if not validation["valid"]:
        return {
            "success": False,
            "error": f"Invalid word: {', '.join(validation['errors'])}"
        }
    
    # Load dictionary
    with open(DICT_PATH, 'r') as f:
        dictionary = json.load(f)
    
    # Check if Nyrakai word already exists
    for w in dictionary["words"]:
        if w["nyrakai"] == nyrakai or w["nyrakai"] == validation["normalized"]:
            return {
                "success": False,
                "error": f"Nyrakai word '{nyrakai}' already exists in dictionary"
            }
    
    # Check if English meaning already exists
    for w in dictionary["words"]:
        if w["english"].lower() == english.lower():
            return {
                "success": False,
                "error": f"English meaning '{english}' already has a Nyrakai word: '{w['nyrakai']}'"
            }
    
    # Add word
    entry = {
        "nyrakai": validation["normalized"],
        "english": english,
        "pos": pos,
        "is_root": is_root,
        "etymology": etymology,
        "phonemes": validation["phonemes"],
        "syllables": validation["syllables"],
        "structure": ".".join(validation["syllable_structures"])
    }
    
    dictionary["words"].append(entry)
    dictionary["meta"]["total_words"] = len(dictionary["words"])
    
    # Save
    with open(DICT_PATH, 'w') as f:
        json.dump(dictionary, f, indent=2, ensure_ascii=False)
    
    return {
        "success": True,
        "entry": entry
    }


def lookup(word: str) -> dict:
    """Look up a word in the dictionary (by Nyrakai or English)"""
    with open(DICT_PATH, 'r') as f:
        dictionary = json.load(f)
    
    for w in dictionary["words"]:
        if w["nyrakai"] == word or w["english"].lower() == word.lower():
            return w
    
    return None


def check_duplicate(nyrakai: str = None, english: str = None) -> dict:
    """Check if a word or meaning already exists"""
    with open(DICT_PATH, 'r') as f:
        dictionary = json.load(f)
    
    result = {"exists": False, "nyrakai_match": None, "english_match": None}
    
    normalized = normalize(nyrakai) if nyrakai else None
    
    for w in dictionary["words"]:
        if nyrakai and (w["nyrakai"] == nyrakai or w["nyrakai"] == normalized):
            result["exists"] = True
            result["nyrakai_match"] = w
        if english and w["english"].lower() == english.lower():
            result["exists"] = True
            result["english_match"] = w
    
    return result


def list_words() -> list:
    """List all words in dictionary"""
    with open(DICT_PATH, 'r') as f:
        dictionary = json.load(f)
    return dictionary["words"]


def validate_dictionary() -> dict:
    """Validate ALL words in dictionary against current rules"""
    with open(DICT_PATH, 'r') as f:
        dictionary = json.load(f)
    
    results = {
        "total": len(dictionary["words"]),
        "valid": 0,
        "invalid": 0,
        "invalid_words": []
    }
    
    for w in dictionary["words"]:
        validation = validate_word(w["nyrakai"])
        if validation["valid"]:
            results["valid"] += 1
        else:
            results["invalid"] += 1
            results["invalid_words"].append({
                "nyrakai": w["nyrakai"],
                "english": w["english"],
                "errors": validation["errors"]
            })
    
    return results


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--check-dict":
            print("Validating dictionary...")
            print("=" * 50)
            results = validate_dictionary()
            print(f"Total: {results['total']}")
            print(f"Valid: {results['valid']} ✓")
            print(f"Invalid: {results['invalid']} ✗")
            if results["invalid_words"]:
                print("\nInvalid words:")
                for w in results["invalid_words"]:
                    print(f"  • {w['nyrakai']} ({w['english']})")
                    for e in w["errors"]:
                        print(f"    - {e}")
        else:
            # Validate a single word
            word = sys.argv[1]
            result = validate_word(word)
            status = "✓ VALID" if result["valid"] else "✗ INVALID"
            print(f"{status}: {word}")
            print(f"  Normalized: {result['normalized']}")
            print(f"  Phonemes: {result['phonemes']}")
            print(f"  Syllables: {result['syllables']}")
            print(f"  Structure: {'.'.join(result['syllable_structures'])}")
            if result["warnings"]:
                print(f"  Warnings: {result['warnings']}")
            if result["errors"]:
                print(f"  Errors: {result['errors']}")
    else:
        print("Nyrakai Validator")
        print("=" * 40)
        print("Usage:")
        print("  python validator.py <word>       - Validate a word")
        print("  python validator.py --check-dict - Validate entire dictionary")
        print()
        print("Testing some words...")
        test_words = ["kæ", "n'æra", "ƶōrra", "ŧɒn", "ñœrek", "drōm", "xyz"]
        for w in test_words:
            result = validate_word(w)
            status = "✓" if result["valid"] else "✗"
            structs = ".".join(result["syllable_structures"]) if result["syllable_structures"] else "?"
            print(f"  {status} {w:12} → {result['syllables']} ({structs})")
            if result["errors"]:
                for e in result["errors"]:
                    print(f"      Error: {e}")
