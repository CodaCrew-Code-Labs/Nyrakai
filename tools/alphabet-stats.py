#!/usr/bin/env python3
"""
Nyrakai Alphabet Distribution Analyzer
Shows usage statistics for each phoneme in the dictionary.
"""

import json
from pathlib import Path
from collections import Counter
from validator import tokenize, normalize

DICT_PATH = Path(__file__).parent / "nyrakai-dictionary.json"

# Phoneme categories for grouping
CATEGORIES = {
    "consonants": set("dfghklmnñprstz") | {"ț"},
    "vowels_short": set("aeiou"),
    "vowels_long": {"ā", "ē", "ī", "ō", "ū"},
    "glides": {"w", "y"},
    "ejectives": {"k^", "p^", "t^"},
    "affricates": {"ƨ", "š", "ƶ", "ŧ"},
    "diphthongs_short": {"æ", "ɒ", "ɛ", "ə", "œ"},
    "diphthongs_long": {"ǣ", "ɒ̄", "ɛ̄", "ə̄", "œ̄"},
    "special": {"'"},  # schwa marker
}

# All possible phonemes
ALL_PHONEMES = set()
for cat in CATEGORIES.values():
    ALL_PHONEMES.update(cat)


def get_category(phoneme: str) -> str:
    """Get the category of a phoneme."""
    for cat_name, phonemes in CATEGORIES.items():
        if phoneme in phonemes:
            return cat_name
    return "unknown"


def analyze_dictionary():
    """Analyze phoneme distribution in the dictionary."""
    
    with open(DICT_PATH, 'r') as f:
        dictionary = json.load(f)
    
    words = dictionary["words"]
    total_words = len(words)
    
    # Count phonemes
    phoneme_counter = Counter()
    word_has_phoneme = {p: 0 for p in ALL_PHONEMES}  # words containing each phoneme
    
    total_phonemes = 0
    
    for word_entry in words:
        nyrakai = word_entry["nyrakai"]
        phonemes = tokenize(nyrakai)
        
        # Count each phoneme
        for p in phonemes:
            phoneme_counter[p] += 1
            total_phonemes += 1
        
        # Track which words have which phonemes (for word coverage)
        seen_in_word = set(phonemes)
        for p in seen_in_word:
            if p in word_has_phoneme:
                word_has_phoneme[p] += 1
    
    return {
        "total_words": total_words,
        "total_phonemes": total_phonemes,
        "phoneme_counts": phoneme_counter,
        "word_coverage": word_has_phoneme,
    }


def print_report(stats: dict):
    """Print a formatted report."""
    
    total_words = stats["total_words"]
    total_phonemes = stats["total_phonemes"]
    phoneme_counts = stats["phoneme_counts"]
    word_coverage = stats["word_coverage"]
    
    print("=" * 60)
    print("NYRAKAI ALPHABET DISTRIBUTION REPORT")
    print("=" * 60)
    print(f"\nTotal words: {total_words}")
    print(f"Total phonemes used: {total_phonemes}")
    print(f"Average phonemes per word: {total_phonemes / total_words:.1f}")
    
    # Sort by usage percentage (descending)
    sorted_phonemes = sorted(
        phoneme_counts.items(),
        key=lambda x: x[1],
        reverse=True
    )
    
    print("\n" + "-" * 60)
    print("PHONEME USAGE (sorted by frequency)")
    print("-" * 60)
    print(f"{'Phoneme':<10} {'Count':<8} {'%':<8} {'Category':<15} {'Bar'}")
    print("-" * 60)
    
    max_count = sorted_phonemes[0][1] if sorted_phonemes else 1
    
    for phoneme, count in sorted_phonemes:
        pct = (count / total_phonemes) * 100
        category = get_category(phoneme)
        bar_len = int((count / max_count) * 20)
        bar = "█" * bar_len
        
        # Display name for special chars
        display = phoneme
        if phoneme == "'":
            display = "' (schwa)"
        
        print(f"{display:<10} {count:<8} {pct:>5.1f}%   {category:<15} {bar}")
    
    # Unused phonemes
    print("\n" + "-" * 60)
    print("UNUSED PHONEMES")
    print("-" * 60)
    
    unused = []
    for cat_name, phonemes in CATEGORIES.items():
        for p in phonemes:
            if p not in phoneme_counts:
                unused.append((p, cat_name))
    
    if unused:
        for p, cat in sorted(unused, key=lambda x: x[1]):
            print(f"  {p:<10} ({cat})")
    else:
        print("  All phonemes used! 🎉")
    
    # Category summary
    print("\n" + "-" * 60)
    print("CATEGORY SUMMARY")
    print("-" * 60)
    
    cat_totals = {}
    for phoneme, count in phoneme_counts.items():
        cat = get_category(phoneme)
        cat_totals[cat] = cat_totals.get(cat, 0) + count
    
    for cat, total in sorted(cat_totals.items(), key=lambda x: -x[1]):
        pct = (total / total_phonemes) * 100
        print(f"  {cat:<20} {total:>4} ({pct:>5.1f}%)")
    
    # Suggestions
    print("\n" + "-" * 60)
    print("SUGGESTIONS FOR BALANCE")
    print("-" * 60)
    
    # Find underused categories
    underused = []
    for cat_name, phonemes in CATEGORIES.items():
        used_count = sum(1 for p in phonemes if p in phoneme_counts)
        total_in_cat = len(phonemes)
        if used_count < total_in_cat * 0.5:
            unused_in_cat = [p for p in phonemes if p not in phoneme_counts]
            underused.append((cat_name, unused_in_cat))
    
    if underused:
        print("Consider using these underused sounds in new words:\n")
        for cat, phonemes in underused:
            print(f"  {cat}: {', '.join(phonemes)}")
    else:
        print("Good phoneme coverage! Keep varying the sounds.")


def main():
    stats = analyze_dictionary()
    print_report(stats)


if __name__ == "__main__":
    main()
