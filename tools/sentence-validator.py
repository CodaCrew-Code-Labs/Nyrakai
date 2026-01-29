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

# Mood suffixes
MOOD_SUFFIXES = {
    'țiræ': 'imperative',
    'hāli': 'optative',
    'wɒț': 'conditional',
}

# Pronouns
PRONOUNS = {'fā', 'gæ', 'šā', 'fāri', 'fārā', 'gæri', 'gærā', 'šāri', 'šārā', 'šœ', 'šɒ', 'kwæ', 'hœr'}

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
    
    # Check for interfix -w- before suffix (e.g., fāwaš → fā + w + aš)
    if 'w' in word and len(word) > 2:
        # Check if removing 'w' gives us a valid pronoun
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
    
    # Handle negation prefix
    has_negation = False
    if word.startswith('za'):
        has_negation = True
        word = word[2:]
        if verbose:
            print(f"    Found negation prefix za-")
    
    # Check if it's a pronoun
    if word in PRONOUNS:
        return True, []
    
    # Check if it's a postposition
    if word in POSTPOSITIONS:
        return True, []
    
    # Check if it's the question particle
    if word == QUESTION_PARTICLE:
        return True, []
    
    # Strip suffixes and check root
    root, suffixes = strip_suffixes(word)
    
    if verbose and suffixes:
        print(f"    Stripped suffixes: {suffixes}")
        print(f"    Root: {root}")
    
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
        # Check if question ends with 'ka'
        if '?' in sentence.get('english', '') and words[-1] != 'ka':
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
