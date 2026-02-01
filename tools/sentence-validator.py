#!/usr/bin/env python3
"""
Nyrakai Sentence Validator
==========================
Validates sentences in sentences.json against all grammatical rules.

Usage:
    python sentence-validator.py              # Validate all sentences
    python sentence-validator.py --id 1       # Validate specific sentence
    python sentence-validator.py --verbose    # Show detailed analysis
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional

SCRIPT_DIR = Path(__file__).parent
DICT_PATH = SCRIPT_DIR / "nyrakai-dictionary.json"
SENTENCES_PATH = SCRIPT_DIR / "sentences.json"

# ============================================================================
# GRAMMAR DATA
# ============================================================================

# Case suffixes
CASE_SUFFIXES = {
    'aš': 'accusative',
    'šar': 'genitive',
    'iț': 'dative',
    'ek': 'instrumental',
    'ñen': 'locative',
    'ɒr': 'ablative',
    'ți': 'vocative',
    'zɒț': 'privative',
}

# Aspect suffixes
ASPECT_SUFFIXES = {
    'arek': 'completed',
    'iræn': 'ongoing',
    'aneț': 'habitual',
    'ațar': 'potential',
}

# Gender/derivational suffixes
GENDER_SUFFIXES = {
    'ñī': 'feminine',
    'añī': 'feminine (with bridge)',
    'æn': 'masculine',
}

# Mood suffixes
MOOD_SUFFIXES = {
    'țiræ': 'imperative',
    'hāli': 'optative',
    'wɒț': 'conditional',
}

# Pronouns
PRONOUNS = {'fā', 'gæ', 'šā', 'fāri', 'fārā', 'gæri', 'gærā', 'šāri', 'šārā', 'šœ', 'šɒ', 'kwæ', 'hœr'}

# Possessive prefixes (used in compound words like fāna'ēraš = my water)
POSSESSIVE_PREFIXES = {
    'fā': 'my/I',
    'gæ': 'your/you', 
    'šā': 'his/her/it',
    'fāri': 'our/we',
    'gæri': 'your (pl)',
    'šāri': 'their/they',
}

# Voice markers (infixes)
VOICE_MARKERS = {
    'rōn': 'passive',
}

# Conjunctions
CONJUNCTIONS = {'əda', 'mur', 'wɒ', 'țɒ', 'zōn', 'zēn'}

# Postpositions
POSTPOSITIONS = {'añ'}

# Question particle
QUESTION_PARTICLE = 'ka'

# ============================================================================
# DICTIONARY LOADING
# ============================================================================

def load_dictionary() -> Dict:
    with open(DICT_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_sentences() -> Dict:
    if not SENTENCES_PATH.exists():
        return {"sentences": []}
    with open(SENTENCES_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def build_word_set(data: Dict) -> set:
    """Build set of all valid Nyrakai words (lowercase for comparison)."""
    words = set()
    for entry in data['words']:
        # Store both original and lowercase
        words.add(entry['nyrakai'])
        words.add(entry['nyrakai'].lower())
    return words

# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

def strip_suffixes(word: str) -> Tuple[str, List[str]]:
    """Strip known suffixes from a word, return (root, [suffixes])."""
    suffixes_found = []
    original = word
    
    # Check for aspect suffixes (longest first)
    for suffix in sorted(ASPECT_SUFFIXES.keys(), key=len, reverse=True):
        if word.endswith(suffix):
            word = word[:-len(suffix)]
            suffixes_found.append(f"{suffix} ({ASPECT_SUFFIXES[suffix]})")
            break
    
    # Check for mood suffixes
    for suffix in sorted(MOOD_SUFFIXES.keys(), key=len, reverse=True):
        if word.endswith(suffix):
            word = word[:-len(suffix)]
            suffixes_found.append(f"{suffix} ({MOOD_SUFFIXES[suffix]})")
            break
    
    # Check for case suffixes
    for suffix in sorted(CASE_SUFFIXES.keys(), key=len, reverse=True):
        if word.endswith(suffix):
            word = word[:-len(suffix)]
            suffixes_found.append(f"{suffix} ({CASE_SUFFIXES[suffix]})")
            break
    
    # Check for gender/derivational suffixes (before interfix check)
    for suffix in sorted(GENDER_SUFFIXES.keys(), key=len, reverse=True):
        if word.endswith(suffix):
            word = word[:-len(suffix)]
            suffixes_found.append(f"{suffix} ({GENDER_SUFFIXES[suffix]})")
            break
    
    # Check for interfix -w- at end (e.g., gwīƨañīw → gwīƨañī + w)
    if word.endswith('w') and len(word) > 2:
        word = word[:-1]
        suffixes_found.insert(0, "-w- (interfix)")
    
    # Check for interfix -w- before suffix for pronouns (e.g., fāw → fā + w)
    if 'w' in word and len(word) > 2:
        possible_root = word.replace('w', '', 1)
        if possible_root in PRONOUNS:
            word = possible_root
            suffixes_found.insert(0, "-w- (interfix)")
    
    return word, suffixes_found

def validate_word(word: str, dictionary_words: set, verbose: bool = False) -> Tuple[bool, List[str]]:
    """
    Validate a single Nyrakai word.
    Returns (is_valid, [issues]).
    """
    issues = []
    original = word
    
    # Handle negation prefix (za-)
    has_negation = False
    if word.startswith('za'):
        has_negation = True
        word = word[2:]
        if verbose:
            print(f"    Found negation prefix za-")
    
    # Check if it's a pronoun (with possible case suffix + interfix)
    # e.g., šāwaš = šā + w + aš (pronoun + interfix + accusative)
    if word in PRONOUNS:
        return True, []
    
    # Check for pronoun + interfix + case suffix pattern
    for pronoun in sorted(PRONOUNS, key=len, reverse=True):
        if word.startswith(pronoun):
            remainder = word[len(pronoun):]
            # Check for interfix -w- followed by case suffix
            if remainder.startswith('w'):
                suffix_part = remainder[1:]
                if suffix_part in CASE_SUFFIXES:
                    if verbose:
                        print(f"    Found pronoun+interfix+case: {pronoun} + w + {suffix_part}")
                    return True, []
            # Check for direct case suffix (no interfix)
            if remainder in CASE_SUFFIXES:
                if verbose:
                    print(f"    Found pronoun+case: {pronoun} + {remainder}")
                return True, []
    
    # Check if it's a conjunction
    if word in CONJUNCTIONS:
        return True, []
    
    # Check if it's a postposition
    if word in POSTPOSITIONS:
        return True, []
    
    # Check if it's the question particle
    if word == QUESTION_PARTICLE:
        return True, []
    
    # Handle possessive prefixes (fā-, šā-, gæ-, etc.)
    # e.g., fāna'ēraš = fā + na'ēr + aš, šāstamɒr = šā + stam + ɒr
    # BUT: only strip if the word without prefix ISN'T in dictionary
    # (to avoid stripping šā from šāk which means "praise")
    possessive_prefix = None
    word_without_prefix = word
    for prefix in sorted(POSSESSIVE_PREFIXES.keys(), key=len, reverse=True):
        if word.startswith(prefix) and len(word) > len(prefix):
            potential_remainder = word[len(prefix):]
            # Strip suffixes from remainder and check
            potential_root, _ = strip_suffixes(potential_remainder)
            # Only use prefix stripping if remainder root is in dictionary
            # AND the original word root is NOT in dictionary
            original_root, _ = strip_suffixes(word)
            if original_root not in dictionary_words and original_root.lower() not in dictionary_words:
                if potential_root in dictionary_words or potential_root.lower() in dictionary_words:
                    possessive_prefix = prefix
                    word = potential_remainder
                    if verbose:
                        print(f"    Found possessive prefix: {prefix}-")
                    break
    
    # Strip suffixes and check root
    root, suffixes = strip_suffixes(word)
    
    if verbose and suffixes:
        print(f"    Stripped suffixes: {suffixes}")
        print(f"    Root: {root}")
    
    # Handle voice markers (e.g., -rōn- for passive)
    # e.g., durrōnațar = dur + rōn + ațar
    for marker in VOICE_MARKERS.keys():
        if marker in root:
            # Try splitting at voice marker
            parts = root.split(marker)
            if len(parts) == 2:
                potential_root = parts[0]
                if potential_root in dictionary_words or potential_root.lower() in dictionary_words:
                    if verbose:
                        print(f"    Found voice marker: -{marker}-")
                    return True, []
    
    # Check if root is in dictionary (case-insensitive)
    if root in dictionary_words or root.lower() in dictionary_words:
        return True, []
    
    # Check if root with negation prefix stripped is in dictionary
    if has_negation and (root in dictionary_words or root.lower() in dictionary_words):
        return True, []
    
    # Check if original word (without suffix stripping) is in dictionary
    if original in dictionary_words or original.lower() in dictionary_words:
        return True, []
    
    # Try removing interfix -w- at different positions
    if 'w' in root:
        test_root = root.replace('w', '')
        if test_root in dictionary_words or test_root.lower() in dictionary_words:
            return True, []
    
    # Word not found
    issues.append(f"Unknown word or root: '{root}' (from '{original}')")
    return False, issues

def validate_sentence(sentence: Dict, dictionary_words: set, verbose: bool = False) -> Tuple[bool, List[str]]:
    """
    Validate a complete sentence entry.
    Returns (is_valid, [issues]).
    """
    issues = []
    nyrakai = sentence.get('nyrakai', '')
    
    if not nyrakai:
        issues.append("Empty Nyrakai sentence")
        return False, issues
    
    # Tokenize
    words = nyrakai.split()
    
    if verbose:
        print(f"\n  Analyzing: {nyrakai}")
        print(f"  Tokens: {words}")
    
    # Validate each word
    for word in words:
        # Clean punctuation
        clean_word = word.strip('.,!?;:')
        if not clean_word:
            continue
        
        if verbose:
            print(f"\n  Checking: {clean_word}")
        
        is_valid, word_issues = validate_word(clean_word, dictionary_words, verbose)
        
        if not is_valid:
            issues.extend(word_issues)
    
    # Check word order (basic OVSV check)
    # This is simplified - full validation would need parsing
    if len(words) >= 3:
        # Check if question ends with 'ka' (but allow "yes or no?" pattern)
        if '?' in sentence.get('english', ''):
            last_word = words[-1].rstrip('?')
            # Allow: ends with 'ka', or "yes or no" choice phrase (zān, zōl)
            if last_word != 'ka' and 'yes or no' not in sentence.get('english', '').lower():
                issues.append(f"Question should end with 'ka' particle")
    
    return len(issues) == 0, issues

# ============================================================================
# MAIN VALIDATION
# ============================================================================

def validate_all(verbose: bool = False) -> Tuple[int, int, List[Dict]]:
    """
    Validate all sentences in sentences.json.
    Returns (passed, failed, [failed_entries]).
    """
    data = load_sentences()
    dict_data = load_dictionary()
    dictionary_words = build_word_set(dict_data)
    
    passed = 0
    failed = 0
    failed_entries = []
    
    for sentence in data.get('sentences', []):
        sid = sentence.get('id', '?')
        english = sentence.get('english', '')
        
        if verbose:
            print(f"\n{'='*60}")
            print(f"Sentence #{sid}: {english}")
        
        is_valid, issues = validate_sentence(sentence, dictionary_words, verbose)
        
        if is_valid:
            passed += 1
            if verbose:
                print(f"  ✅ VALID")
        else:
            failed += 1
            failed_entries.append({
                'id': sid,
                'english': english,
                'nyrakai': sentence.get('nyrakai', ''),
                'issues': issues
            })
            if verbose:
                print(f"  ❌ INVALID")
                for issue in issues:
                    print(f"     - {issue}")
    
    return passed, failed, failed_entries

def validate_by_id(sentence_id: int, verbose: bool = False) -> bool:
    """Validate a specific sentence by ID."""
    data = load_sentences()
    dict_data = load_dictionary()
    dictionary_words = build_word_set(dict_data)
    
    for sentence in data.get('sentences', []):
        if sentence.get('id') == sentence_id:
            print(f"\nValidating sentence #{sentence_id}:")
            print(f"  English: {sentence.get('english', '')}")
            print(f"  Nyrakai: {sentence.get('nyrakai', '')}")
            
            is_valid, issues = validate_sentence(sentence, dictionary_words, verbose)
            
            if is_valid:
                print(f"\n  ✅ VALID")
                return True
            else:
                print(f"\n  ❌ INVALID")
                for issue in issues:
                    print(f"     - {issue}")
                return False
    
    print(f"Sentence #{sentence_id} not found")
    return False

# ============================================================================
# CLI
# ============================================================================

def main():
    verbose = '--verbose' in sys.argv or '-v' in sys.argv
    
    # Check for specific ID
    for i, arg in enumerate(sys.argv):
        if arg == '--id' and i + 1 < len(sys.argv):
            try:
                sentence_id = int(sys.argv[i + 1])
                validate_by_id(sentence_id, verbose)
                return
            except ValueError:
                print("Invalid sentence ID")
                sys.exit(1)
    
    # Validate all
    print("╔══════════════════════════════════════════════════════════╗")
    print("║           NYRAKAI SENTENCE VALIDATOR                     ║")
    print("╚══════════════════════════════════════════════════════════╝")
    
    passed, failed, failed_entries = validate_all(verbose)
    
    print(f"\n{'='*60}")
    print(f"RESULTS: {passed} passed, {failed} failed")
    print(f"{'='*60}")
    
    if failed_entries:
        print("\nFailed sentences:")
        for entry in failed_entries:
            print(f"\n  #{entry['id']}: {entry['english']}")
            print(f"    Nyrakai: {entry['nyrakai']}")
            for issue in entry['issues']:
                print(f"    ❌ {issue}")
    
    if failed > 0:
        sys.exit(1)

if __name__ == '__main__':
    main()
