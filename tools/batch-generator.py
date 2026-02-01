#!/usr/bin/env python3
"""
Nyrakai Batch Word Generator
Parallel generation of multiple words with collision detection.
Uses ThreadPoolExecutor for concurrent API calls.

Usage:
    python3 batch-generator.py words.txt --domain action
    python3 batch-generator.py --words "blow,breathe,cut,dig" --domain action
    python3 batch-generator.py --swadesh-missing
    python3 batch-generator.py --validate-batch words.txt
"""

import os
import sys
import json
import argparse
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Dict, Tuple, Optional

# Import from existing scripts
try:
    from validator import validate_word, normalize, edit_distance
    from sound_map import SOUND_MAP, DOMAINS, suggest_onset
    
    # word-generator.py has a hyphen, so import it differently
    import importlib.util
    spec = importlib.util.spec_from_file_location("word_generator", 
        Path(__file__).parent / "word-generator.py")
    word_generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(word_generator)
    generate_words = word_generator.generate_words
    load_dictionary = word_generator.load_dictionary
    
    IMPORTS_OK = True
except ImportError as e:
    print(f"⚠️  Import error: {e}")
    print("Make sure you're running from the tools directory")
    IMPORTS_OK = False

# Configuration
MAX_WORKERS = 5  # Parallel API calls (be nice to the API)
SUGGESTIONS_PER_WORD = 3  # How many suggestions to generate per word
MIN_DISTANCE = 2  # Minimum edit distance for similarity check

DICTIONARY_PATH = Path(__file__).parent / "nyrakai-dictionary.json"


def load_existing_words() -> Dict[str, str]:
    """Load all existing Nyrakai words from dictionary."""
    try:
        with open(DICTIONARY_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return {w['nyrakai']: w['english'] for w in data.get('words', [])}
    except:
        return {}


def generate_single_word(english: str, domain: str = None) -> Tuple[str, List[Dict]]:
    """Generate suggestions for a single word. Returns (english, suggestions)."""
    try:
        suggestions = generate_words(english, count=SUGGESTIONS_PER_WORD, domain=domain)
        valid_suggestions = []
        
        for suggestion in suggestions:
            nyrakai = suggestion.get('word', '')
            if not nyrakai:
                continue
            
            # Normalize the word
            nyrakai = normalize(nyrakai)
                
            # Validate phonotactics
            result = validate_word(nyrakai)
            # Handle both old (4-tuple) and new (dict) return formats
            if isinstance(result, tuple):
                is_valid = result[0]
            else:
                is_valid = result.get('valid', False)
            
            if is_valid:
                valid_suggestions.append({
                    'english': english,
                    'nyrakai': nyrakai,
                    'reasoning': suggestion.get('reasoning', ''),
                    'validated': True
                })
        
        return (english, valid_suggestions)
    except Exception as e:
        import traceback
        return (english, [{'error': f"{str(e)}: {traceback.format_exc()[:100]}"}])


def check_collisions(new_words: List[Dict], existing_words: Dict[str, str]) -> Tuple[List[Dict], List[Dict]]:
    """
    Check for collisions:
    1. Exact matches with existing dictionary
    2. Too similar (edit distance < MIN_DISTANCE) to existing
    3. Duplicates within the new batch
    
    Returns: (valid_words, collision_words)
    """
    valid = []
    collisions = []
    seen_in_batch = {}  # nyrakai -> english
    
    for word in new_words:
        nyrakai = word.get('nyrakai', '')
        english = word.get('english', '')
        
        if not nyrakai:
            continue
        
        collision_type = None
        collision_with = None
        
        # Check 1: Exact match with existing dictionary
        if nyrakai in existing_words:
            collision_type = 'exact_existing'
            collision_with = existing_words[nyrakai]
        
        # Check 2: Exact match within batch
        elif nyrakai in seen_in_batch:
            collision_type = 'exact_batch'
            collision_with = seen_in_batch[nyrakai]
        
        # Check 3: Too similar to existing (if no exact match)
        if not collision_type:
            for existing_nyr, existing_eng in existing_words.items():
                dist = edit_distance(nyrakai, existing_nyr)
                if dist < MIN_DISTANCE:
                    collision_type = 'similar_existing'
                    collision_with = f"{existing_nyr} ({existing_eng}) - distance {dist}"
                    break
        
        # Check 4: Too similar within batch
        if not collision_type:
            for seen_nyr, seen_eng in seen_in_batch.items():
                dist = edit_distance(nyrakai, seen_nyr)
                if dist < MIN_DISTANCE:
                    collision_type = 'similar_batch'
                    collision_with = f"{seen_nyr} ({seen_eng}) - distance {dist}"
                    break
        
        if collision_type:
            word['collision_type'] = collision_type
            word['collision_with'] = collision_with
            collisions.append(word)
        else:
            valid.append(word)
            seen_in_batch[nyrakai] = english
    
    return valid, collisions


def parallel_generate(words: List[str], domain: str = None, workers: int = MAX_WORKERS) -> Dict:
    """Generate words in parallel using ThreadPoolExecutor."""
    results = {
        'generated': [],
        'errors': [],
        'timing': {}
    }
    
    start_time = time.time()
    completed = 0
    total = len(words)
    
    print(f"\n🚀 Generating {total} words in parallel (max {workers} workers)...")
    print(f"   Domain: {domain or 'auto-detect'}")
    print("-" * 50)
    
    with ThreadPoolExecutor(max_workers=workers) as executor:
        # Submit all tasks
        future_to_word = {
            executor.submit(generate_single_word, word, domain): word 
            for word in words
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_word):
            word = future_to_word[future]
            completed += 1
            
            try:
                english, suggestions = future.result()
                
                if suggestions and not any('error' in s for s in suggestions):
                    results['generated'].extend(suggestions)
                    status = f"✓ {len(suggestions)} suggestions"
                else:
                    error_msg = suggestions[0].get('error', 'No valid suggestions') if suggestions else 'No suggestions'
                    results['errors'].append({'word': english, 'error': error_msg})
                    status = f"✗ {error_msg[:30]}"
                
                # Progress indicator
                pct = int(completed / total * 100)
                print(f"  [{completed}/{total}] {pct:3d}% | {english:<15} | {status}")
                
            except Exception as e:
                results['errors'].append({'word': word, 'error': str(e)})
                print(f"  [{completed}/{total}] {word:<15} | ✗ Exception: {e}")
    
    end_time = time.time()
    results['timing'] = {
        'total_seconds': round(end_time - start_time, 2),
        'per_word_avg': round((end_time - start_time) / total, 2) if total > 0 else 0
    }
    
    return results


def parallel_validate(words: List[str], workers: int = MAX_WORKERS) -> Dict:
    """Validate words in parallel."""
    results = {
        'valid': [],
        'invalid': [],
        'timing': {}
    }
    
    start_time = time.time()
    
    def validate_single(word: str) -> Tuple[str, bool, List[str]]:
        is_valid, normalized, errors, _ = validate_word(word)
        return (word, is_valid, errors, normalized)
    
    print(f"\n🔍 Validating {len(words)} words in parallel...")
    
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(validate_single, w): w for w in words}
        
        for future in as_completed(futures):
            word, is_valid, errors, normalized = future.result()
            if is_valid:
                results['valid'].append({'word': word, 'normalized': normalized})
            else:
                results['invalid'].append({'word': word, 'errors': errors})
    
    results['timing'] = {'total_seconds': round(time.time() - start_time, 2)}
    return results


def get_missing_swadesh() -> List[str]:
    """Get missing Swadesh 207 words."""
    # Standard Swadesh 207 list
    SWADESH_207 = [
        'I', 'you', 'he', 'we', 'you', 'they', 'this', 'that', 'here', 'there',
        'who', 'what', 'where', 'when', 'how', 'not', 'all', 'many', 'some', 'few',
        'other', 'one', 'two', 'three', 'four', 'five', 'big', 'long', 'wide', 'thick',
        'heavy', 'small', 'short', 'narrow', 'thin', 'woman', 'man', 'person', 'child', 'wife',
        'husband', 'mother', 'father', 'animal', 'fish', 'bird', 'dog', 'louse', 'snake', 'worm',
        'tree', 'forest', 'stick', 'fruit', 'seed', 'leaf', 'root', 'bark', 'flower', 'grass',
        'rope', 'skin', 'meat', 'blood', 'bone', 'fat', 'egg', 'horn', 'tail', 'feather',
        'hair', 'head', 'ear', 'eye', 'nose', 'mouth', 'tooth', 'tongue', 'fingernail', 'foot',
        'leg', 'knee', 'hand', 'wing', 'belly', 'guts', 'neck', 'back', 'breast', 'heart',
        'liver', 'drink', 'eat', 'bite', 'suck', 'spit', 'vomit', 'blow', 'breathe', 'laugh',
        'see', 'hear', 'know', 'think', 'smell', 'fear', 'sleep', 'live', 'die', 'kill',
        'fight', 'hunt', 'hit', 'cut', 'split', 'stab', 'scratch', 'dig', 'swim', 'fly',
        'walk', 'come', 'lie', 'sit', 'stand', 'turn', 'fall', 'give', 'hold', 'squeeze',
        'rub', 'wash', 'wipe', 'pull', 'push', 'throw', 'tie', 'sew', 'count', 'say',
        'sing', 'play', 'float', 'flow', 'freeze', 'swell', 'sun', 'moon', 'star', 'water',
        'rain', 'river', 'lake', 'sea', 'salt', 'stone', 'sand', 'dust', 'earth', 'cloud',
        'fog', 'sky', 'wind', 'snow', 'ice', 'smoke', 'fire', 'ash', 'burn', 'road',
        'mountain', 'red', 'green', 'yellow', 'white', 'black', 'night', 'day', 'year', 'warm',
        'cold', 'full', 'new', 'old', 'good', 'bad', 'rotten', 'dirty', 'straight', 'round',
        'sharp', 'dull', 'smooth', 'wet', 'dry', 'correct', 'near', 'far', 'right', 'left',
        'at', 'in', 'with', 'and', 'if', 'because', 'name'
    ]
    
    # Load existing dictionary
    existing = load_existing_words()
    existing_english = {v.lower() for v in existing.values()}
    
    # Find missing
    missing = [w for w in SWADESH_207 if w.lower() not in existing_english]
    return list(set(missing))  # Dedupe


def main():
    parser = argparse.ArgumentParser(
        description='Parallel Nyrakai word generator with collision detection',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s words.txt --domain action
  %(prog)s --words "blow,breathe,cut" --domain action
  %(prog)s --swadesh-missing
  %(prog)s --validate-batch words.txt
        """
    )
    
    parser.add_argument('input_file', nargs='?', help='File with words (one per line)')
    parser.add_argument('--words', '-w', help='Comma-separated list of words')
    parser.add_argument('--domain', '-d', help='Semantic domain (action, nature, body, etc.)')
    parser.add_argument('--swadesh-missing', action='store_true', help='Generate missing Swadesh 207 words')
    parser.add_argument('--validate-batch', '-v', help='Validate words from file')
    parser.add_argument('--workers', type=int, default=MAX_WORKERS, help=f'Parallel workers (default: {MAX_WORKERS})')
    parser.add_argument('--output', '-o', help='Output JSON file')
    parser.add_argument('--add-to-dict', action='store_true', help='Add valid words to dictionary')
    
    args = parser.parse_args()
    
    if not IMPORTS_OK:
        sys.exit(1)
    
    # Determine word list
    words = []
    
    if args.validate_batch:
        # Validation mode
        with open(args.validate_batch) as f:
            words = [line.strip() for line in f if line.strip()]
        results = parallel_validate(words, workers=args.workers)
        
        print(f"\n{'='*50}")
        print(f"✓ Valid:   {len(results['valid'])}")
        print(f"✗ Invalid: {len(results['invalid'])}")
        print(f"⏱️  Time:    {results['timing']['total_seconds']}s")
        
        if results['invalid']:
            print(f"\n❌ Invalid words:")
            for w in results['invalid']:
                print(f"   {w['word']}: {', '.join(w['errors'])}")
        
        return
    
    if args.swadesh_missing:
        words = get_missing_swadesh()
        print(f"📋 Found {len(words)} missing Swadesh 207 words")
    elif args.words:
        words = [w.strip() for w in args.words.split(',')]
    elif args.input_file:
        with open(args.input_file) as f:
            words = [line.strip() for line in f if line.strip()]
    else:
        parser.print_help()
        return
    
    if not words:
        print("❌ No words to generate!")
        return
    
    # Generate in parallel
    results = parallel_generate(words, domain=args.domain, workers=args.workers)
    
    # Collision check
    print(f"\n{'='*50}")
    print("🔍 Checking for collisions...")
    
    existing = load_existing_words()
    valid, collisions = check_collisions(results['generated'], existing)
    
    # Report
    print(f"\n{'='*50}")
    print("📊 RESULTS")
    print(f"{'='*50}")
    print(f"  Words requested:     {len(words)}")
    print(f"  Suggestions generated: {len(results['generated'])}")
    print(f"  ✓ Valid (no collision): {len(valid)}")
    print(f"  ⚠️  Collisions detected: {len(collisions)}")
    print(f"  ✗ Errors:             {len(results['errors'])}")
    print(f"  ⏱️  Total time:         {results['timing']['total_seconds']}s")
    print(f"  ⏱️  Avg per word:       {results['timing']['per_word_avg']}s")
    
    if collisions:
        print(f"\n⚠️  COLLISIONS:")
        for c in collisions[:10]:  # Show first 10
            print(f"   {c['english']} → {c['nyrakai']}: {c['collision_type']} with {c['collision_with']}")
        if len(collisions) > 10:
            print(f"   ... and {len(collisions) - 10} more")
    
    if valid:
        print(f"\n✅ VALID WORDS:")
        for v in valid:
            print(f"   {v['english']:<15} → {v['nyrakai']}")
    
    # Output
    output_data = {
        'generated_at': datetime.now().isoformat(),
        'domain': args.domain,
        'timing': results['timing'],
        'valid': valid,
        'collisions': collisions,
        'errors': results['errors']
    }
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Results saved to: {args.output}")
    
    # Add to dictionary
    if args.add_to_dict and valid:
        print(f"\n📚 Adding {len(valid)} words to dictionary...")
        with open(DICTIONARY_PATH) as f:
            dict_data = json.load(f)
        
        for word in valid:
            entry = {
                'english': word['english'],
                'nyrakai': word['nyrakai'],
                'pos': 'verb' if word['english'] in ['blow', 'breathe', 'cut', 'dig', 'fall', 'fight', 'float', 'flow', 'freeze', 'hold', 'hunt', 'laugh', 'play', 'pull', 'push', 'rub', 'scratch', 'sew', 'sing', 'split', 'squeeze', 'stab', 'suck', 'swell', 'throw', 'tie', 'turn', 'vomit', 'wash', 'wipe', 'think', 'count', 'smell'] else 'noun',
                'is_root': True,
                'validated': True,
                'notes': f"Batch generated - {word.get('reasoning', '')[:50]}"
            }
            dict_data['words'].append(entry)
        
        dict_data['meta']['total_words'] = len(dict_data['words'])
        dict_data['meta']['last_updated'] = datetime.now().strftime('%Y-%m-%d')
        
        with open(DICTIONARY_PATH, 'w') as f:
            json.dump(dict_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Dictionary updated! Total words: {dict_data['meta']['total_words']}")


if __name__ == '__main__':
    main()
