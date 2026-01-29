#!/usr/bin/env python3
"""
Nyrakai Translator
==================
Translates English sentences to Nyrakai following all grammatical rules.
Reports missing vocabulary instead of hallucinating.

Usage:
    python translator.py "I see the star"
    python translator.py --interactive
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Tuple

# ============================================================================
# DICTIONARY & GRAMMAR DATA
# ============================================================================

SCRIPT_DIR = Path(__file__).parent
DICT_PATH = SCRIPT_DIR / "nyrakai-dictionary.json"
SENTENCES_PATH = SCRIPT_DIR / "sentences.json"

# Load dictionary
def load_dictionary() -> Dict:
    with open(DICT_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

# Build lookup tables
def build_lookups(data: Dict) -> Tuple[Dict, Dict]:
    """Build English→Nyrakai and Nyrakai→Entry lookups."""
    eng_to_nyr = {}
    nyr_to_entry = {}
    
    for word in data['words']:
        eng = word['english'].lower()
        nyr = word['nyrakai']
        
        # Handle multi-word English entries like "he/she/it"
        for variant in eng.replace('/', ' ').replace('(', ' ').replace(')', ' ').split():
            variant = variant.strip()
            if variant and variant not in eng_to_nyr:
                eng_to_nyr[variant] = word
        
        # Also store the full original
        eng_to_nyr[eng] = word
        nyr_to_entry[nyr] = word
    
    return eng_to_nyr, nyr_to_entry

# ============================================================================
# GRAMMAR RULES
# ============================================================================

# Case suffixes
CASES = {
    'nominative': '',      # subject (unmarked)
    'accusative': 'aš',    # direct object
    'genitive': 'šar',     # possession (noun-to-noun)
    'dative': 'iț',        # indirect object (to/for)
    'instrumental': 'ek',  # with/by
    'locative': 'ñen',     # in/on/at
    'ablative': 'ɒr',      # from
    'vocative': 'ți',      # O! (invocation)
    'privative': 'zɒț',    # without
}

# Aspect suffixes
ASPECTS = {
    'completed': 'arek',   # past/finished
    'ongoing': 'iræn',     # present continuous
    'habitual': 'aneț',    # always/regularly
    'potential': 'ațar',   # could/might
}

# Mood suffixes
MOODS = {
    'declarative': '',     # statement (unmarked)
    'interrogative': 'ka', # question (but this is a particle, not suffix)
    'imperative': 'țiræ',  # command
    'optative': 'hāli',    # wish/blessing
    'conditional': 'wɒț',  # if/would
}

# Pronouns mapping
PRONOUNS = {
    'i': 'fā',
    'me': 'fā',
    'my': 'fā',
    'you': 'gæ',
    'your': 'gæ',
    'he': 'šā',
    'she': 'šā',
    'it': 'šā',
    'him': 'šā',
    'her': 'šā',
    'his': 'šā',
    'its': 'šā',
    'we': 'fāri',  # default to masculine/mixed
    'us': 'fāri',
    'our': 'fāri',
    'they': 'šāri',
    'them': 'šāri',
    'their': 'šāri',
    'this': 'šœ',
    'that': 'šɒ',
    'what': 'kwæ',
    'who': 'hœr',
}

# Common English words that map to grammar, not vocabulary
GRAMMAR_WORDS = {
    'the', 'a', 'an',  # articles (not used in Nyrakai)
    'is', 'are', 'am', 'was', 'were', 'be', 'been', 'being',  # copula
    'do', 'does', 'did',  # auxiliary
    'have', 'has', 'had',  # auxiliary
    'will', 'would', 'shall', 'should', 'can', 'could', 'may', 'might', 'must',  # modals
    'to',  # infinitive marker
    'not', "don't", "doesn't", "didn't", "won't", "can't", "couldn't",  # negation
}

# ============================================================================
# INTERFIX RULES
# ============================================================================

def is_vowel(char: str) -> bool:
    """Check if character is a Nyrakai vowel."""
    vowels = set('aeiouāēīōūæɒɛəœǣɒ̄ɛ̄ə̄œ̄')
    return char.lower() in vowels

def apply_interfix(base: str, suffix: str) -> str:
    """Apply interfix rules for vowel collision."""
    if not base or not suffix:
        return base + suffix
    
    base_ends_vowel = is_vowel(base[-1])
    suffix_starts_vowel = is_vowel(suffix[0])
    
    # Vowel + Vowel → insert -w-
    if base_ends_vowel and suffix_starts_vowel:
        return base + 'w' + suffix
    
    return base + suffix

def apply_feminine_bridge(root: str, suffix: str = 'ñī') -> str:
    """Apply -a- bridge for feminine suffix."""
    if not root:
        return suffix
    
    # If root ends in consonant, insert -a-
    if not is_vowel(root[-1]):
        return root + 'a' + suffix
    
    return root + suffix

# ============================================================================
# TRANSLATION ENGINE
# ============================================================================

class NyrakaiTranslator:
    def __init__(self):
        self.data = load_dictionary()
        self.eng_to_nyr, self.nyr_to_entry = build_lookups(self.data)
        self.missing_words = []
    
    # Irregular verb forms → base form
    IRREGULAR_VERBS = {
        'saw': 'see', 'seen': 'see', 'sees': 'see',
        'ate': 'eat', 'eaten': 'eat', 'eats': 'eat',
        'drank': 'drink', 'drunk': 'drink', 'drinks': 'drink',
        'gave': 'give', 'given': 'give', 'gives': 'give',
        'came': 'come', 'comes': 'come',
        'knew': 'know', 'known': 'know', 'knows': 'know',
        'heard': 'hear', 'hears': 'hear',
        'said': 'say', 'says': 'say',
        'sat': 'sit', 'sits': 'sit',
        'stood': 'stand', 'stands': 'stand',
        'slept': 'sleep', 'sleeps': 'sleep',
        'swam': 'swim', 'swum': 'swim', 'swims': 'swim',
        'flew': 'fly', 'flown': 'fly', 'flies': 'fly',
        'walked': 'walk', 'walks': 'walk',
        'died': 'die', 'dies': 'die',
        'killed': 'kill', 'kills': 'kill',
        'created': 'create', 'creates': 'create',
        'burned': 'burn', 'burnt': 'burn', 'burns': 'burn',
        'lay': 'lie', 'lain': 'lie', 'lies': 'lie',
        'spoke': 'say', 'spoken': 'say',  # speak → say
        'speak': 'say', 'speaks': 'say',  # speak → say
        'told': 'say', 'tells': 'say', 'tell': 'say',  # tell → say
    }
    
    # Synonyms → dictionary word
    SYNONYMS = {
        'speak': 'say',
        'tell': 'say',
        'talk': 'say',
        'look': 'see',
        'watch': 'see',
        'observe': 'see',
        'listen': 'hear',
        'walk': 'walk',
        'run': 'walk',  # closest approximation
        'big': 'big',
        'large': 'big',
        'great': 'big',
        'huge': 'big',
        'small': 'small',
        'little': 'small',
        'tiny': 'small',
        'wise': 'know',  # approximate: "one who knows"
        'ancient': 'new',  # will need za- prefix for "not new" = old
        'old': 'new',  # za-ŧa'un = not-new
        'words': 'say',  # approximate: what is said
        'word': 'say',
    }
    
    def lookup(self, english: str) -> Optional[Dict]:
        """Look up an English word in the dictionary."""
        eng_lower = english.lower().strip()
        
        # Try exact match first
        if eng_lower in self.eng_to_nyr:
            return self.eng_to_nyr[eng_lower]
        
        # Try irregular verb mapping
        if eng_lower in self.IRREGULAR_VERBS:
            base = self.IRREGULAR_VERBS[eng_lower]
            if base in self.eng_to_nyr:
                return self.eng_to_nyr[base]
        
        # Try synonym mapping
        if eng_lower in self.SYNONYMS:
            syn = self.SYNONYMS[eng_lower]
            if syn in self.eng_to_nyr:
                return self.eng_to_nyr[syn]
        
        # Try without common suffixes
        for suffix in ['ing', 'ed', 'es', 's', 'ly', 'er', 'est']:
            if eng_lower.endswith(suffix):
                stem = eng_lower[:-len(suffix)]
                if stem and stem in self.eng_to_nyr:
                    return self.eng_to_nyr[stem]
                # Try adding 'e' back (e.g., 'making' → 'make')
                if stem + 'e' in self.eng_to_nyr:
                    return self.eng_to_nyr[stem + 'e']
        
        return None
    
    def get_pronoun(self, english: str) -> Optional[str]:
        """Get Nyrakai pronoun for English pronoun."""
        return PRONOUNS.get(english.lower())
    
    def apply_case(self, nyrakai: str, case: str) -> str:
        """Apply case suffix to a Nyrakai word."""
        suffix = CASES.get(case, '')
        if not suffix:
            return nyrakai
        return apply_interfix(nyrakai, suffix)
    
    def apply_aspect(self, verb: str, aspect: str = 'ongoing') -> str:
        """Apply aspect suffix to a verb with interfix if needed."""
        suffix = ASPECTS.get(aspect, ASPECTS['ongoing'])
        return apply_interfix(verb, suffix)
    
    def apply_negation(self, verb: str) -> str:
        """Apply za- negation prefix to verb."""
        return 'za' + verb
    
    def parse_english(self, sentence: str) -> Dict:
        """
        Simple English sentence parser.
        Returns structure: {subject, verb, object, negated, question, ...}
        """
        result = {
            'original': sentence,
            'subject': None,
            'verb': None,
            'object': None,
            'indirect_object': None,
            'negated': False,
            'question': False,
            'aspect': 'ongoing',
            'mood': 'declarative',
            'adjectives': [],
            'adverbs': [],
            'raw_words': [],
        }
        
        # Clean and tokenize
        sentence = sentence.strip()
        
        # Check for question
        if sentence.endswith('?'):
            result['question'] = True
            result['mood'] = 'interrogative'
            sentence = sentence.rstrip('?').strip()
        
        # Check for negation
        negation_patterns = ['not', "don't", "doesn't", "didn't", "won't", "can't", "couldn't", "never"]
        for neg in negation_patterns:
            if neg in sentence.lower():
                result['negated'] = True
                sentence = re.sub(rf"\b{neg}\b", "", sentence, flags=re.IGNORECASE).strip()
        
        # Tokenize
        words = sentence.split()
        words = [w.strip('.,!?;:') for w in words if w.strip('.,!?;:')]
        result['raw_words'] = words
        
        # Filter out grammar words (articles, auxiliaries)
        content_words = []
        for w in words:
            w_lower = w.lower()
            if w_lower not in GRAMMAR_WORDS:
                content_words.append(w)
        
        # Simple SVO detection
        # Pattern: [Subject] [Verb] [Object]
        
        pronouns_list = list(PRONOUNS.keys())
        
        # Find subject (usually first noun/pronoun)
        for i, word in enumerate(content_words):
            w_lower = word.lower()
            if w_lower in pronouns_list:
                result['subject'] = word
                content_words = content_words[:i] + content_words[i+1:]
                break
            elif self.lookup(word):
                entry = self.lookup(word)
                if entry.get('pos') in ['noun', 'proper noun', 'pron']:
                    result['subject'] = word
                    content_words = content_words[:i] + content_words[i+1:]
                    break
        
        # Find verb
        for i, word in enumerate(content_words):
            entry = self.lookup(word)
            if entry and entry.get('pos') == 'verb':
                result['verb'] = word
                content_words = content_words[:i] + content_words[i+1:]
                break
        
        # Remaining content words are likely objects or adjectives
        for word in content_words:
            entry = self.lookup(word)
            if entry:
                pos = entry.get('pos', '')
                if pos == 'adj':
                    result['adjectives'].append(word)
                elif pos in ['noun', 'proper noun', 'pron']:
                    if not result['object']:
                        result['object'] = word
                    else:
                        result['indirect_object'] = word
            else:
                # Unknown word - could be object
                if not result['object']:
                    result['object'] = word
        
        # Determine aspect from tense markers
        original_lower = result['original'].lower()
        words_lower = [w.lower() for w in words]
        
        # Check for irregular past tense verbs
        past_tense_irregulars = ['saw', 'ate', 'drank', 'gave', 'came', 'knew', 'heard', 
                                  'said', 'sat', 'stood', 'slept', 'swam', 'flew', 'died',
                                  'killed', 'burned', 'burnt', 'lay', 'went', 'took', 'made']
        
        if any(w in words_lower for w in past_tense_irregulars):
            result['aspect'] = 'completed'
        elif any(w in original_lower for w in ['did', 'was', 'were', 'had']):
            result['aspect'] = 'completed'
        elif any(w.endswith('ed') for w in words_lower):
            result['aspect'] = 'completed'
        elif any(w in original_lower for w in ['will', 'shall', 'going to', 'might', 'could']):
            result['aspect'] = 'potential'
        elif any(w in original_lower for w in ['always', 'usually', 'often', 'every']):
            result['aspect'] = 'habitual'
        else:
            result['aspect'] = 'ongoing'
        
        return result
    
    def translate_word(self, english: str, case: str = 'nominative') -> Tuple[str, bool]:
        """
        Translate a single English word to Nyrakai.
        Returns (nyrakai_word, success).
        """
        eng_lower = english.lower()
        
        # Check pronouns first
        if eng_lower in PRONOUNS:
            nyr = PRONOUNS[eng_lower]
            return self.apply_case(nyr, case), True
        
        # Look up in dictionary
        entry = self.lookup(english)
        if entry:
            nyr = entry['nyrakai']
            return self.apply_case(nyr, case), True
        
        # Word not found
        self.missing_words.append(english)
        return f"[{english}?]", False
    
    def translate(self, sentence: str) -> Dict:
        """
        Translate an English sentence to Nyrakai.
        Returns detailed translation result.
        """
        self.missing_words = []
        
        parsed = self.parse_english(sentence)
        
        result = {
            'input': sentence,
            'parsed': parsed,
            'nyrakai': '',
            'literal': '',
            'breakdown': [],
            'missing_words': [],
            'warnings': [],
            'success': True,
        }
        
        # Build Nyrakai sentence in OVSV order
        # O (Object) + Vs (Verb Stem) + S (Subject) + Va (Verb Aspect)
        
        parts = []
        breakdown = []
        
        # 1. Adjectives + Object (accusative case)
        if parsed['adjectives']:
            for adj in parsed['adjectives']:
                adj_nyr, adj_ok = self.translate_word(adj)
                parts.append(adj_nyr)
                breakdown.append(f"{adj} → {adj_nyr} (adj)")
        
        if parsed['object']:
            obj_nyr, obj_ok = self.translate_word(parsed['object'], 'accusative')
            parts.append(obj_nyr)
            breakdown.append(f"{parsed['object']} → {obj_nyr} (object, accusative)")
        
        # 2. Verb stem (with negation if needed)
        if parsed['verb']:
            verb_entry = self.lookup(parsed['verb'])
            if verb_entry:
                verb_stem = verb_entry['nyrakai']
                if parsed['negated']:
                    verb_stem = self.apply_negation(verb_stem)
                    breakdown.append(f"{parsed['verb']} → za{verb_entry['nyrakai']} (verb, negated)")
                else:
                    breakdown.append(f"{parsed['verb']} → {verb_stem} (verb stem)")
                parts.append(verb_stem)
            else:
                self.missing_words.append(parsed['verb'])
                parts.append(f"[{parsed['verb']}?]")
                breakdown.append(f"{parsed['verb']} → [NOT FOUND]")
        
        # 3. Subject (nominative - unmarked)
        if parsed['subject']:
            subj_nyr, subj_ok = self.translate_word(parsed['subject'], 'nominative')
            parts.append(subj_nyr)
            breakdown.append(f"{parsed['subject']} → {subj_nyr} (subject)")
        
        # 4. Verb aspect
        if parsed['verb']:
            verb_entry = self.lookup(parsed['verb'])
            if verb_entry:
                aspect_suffix = ASPECTS.get(parsed['aspect'], ASPECTS['ongoing'])
                parts.append(aspect_suffix)
                breakdown.append(f"[{parsed['aspect']}] → {aspect_suffix} (aspect)")
        
        # 5. Question particle (if question)
        if parsed['question']:
            parts.append('ka')
            breakdown.append(f"[question] → ka (particle)")
        
        # Build final sentence
        # Filter empty parts
        parts = [p for p in parts if p]
        
        # Combine verb stem + aspect into one unit
        # Restructure: [O] [za-V] [S] [aspect] [ka?]
        # Actually in Nyrakai the aspect attaches to verb
        
        # Rebuild properly
        final_parts = []
        verb_with_aspect = None
        
        for i, p in enumerate(parts):
            # Check if this is an aspect suffix
            if p in ASPECTS.values():
                continue  # Skip, we'll attach to verb
            final_parts.append(p)
        
        # Attach aspect to verb
        if parsed['verb'] and self.lookup(parsed['verb']):
            verb_idx = None
            verb_entry = self.lookup(parsed['verb'])
            verb_form = verb_entry['nyrakai']
            if parsed['negated']:
                verb_form = 'za' + verb_form
            
            for i, p in enumerate(final_parts):
                if p == verb_form or p == 'za' + verb_entry['nyrakai']:
                    verb_idx = i
                    break
            
            if verb_idx is not None:
                aspect_suffix = ASPECTS.get(parsed['aspect'], ASPECTS['ongoing'])
                final_parts[verb_idx] = apply_interfix(verb_form, aspect_suffix)
        
        # Add question particle at end
        if parsed['question'] and 'ka' not in final_parts:
            final_parts.append('ka')
        
        result['nyrakai'] = ' '.join(final_parts)
        result['breakdown'] = breakdown
        result['missing_words'] = list(set(self.missing_words))
        
        if self.missing_words:
            result['success'] = False
            result['warnings'].append(f"Missing vocabulary: {', '.join(set(self.missing_words))}")
        
        # Generate literal back-translation
        literal_parts = []
        for b in breakdown:
            if '→' in b:
                eng = b.split('→')[0].strip()
                literal_parts.append(eng)
        result['literal'] = ' '.join(literal_parts)
        
        return result

# ============================================================================
# SENTENCE STORAGE
# ============================================================================

def load_sentences() -> Dict:
    """Load sentences database."""
    if SENTENCES_PATH.exists():
        with open(SENTENCES_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "meta": {
            "language": "Nyrakai",
            "version": "1.0",
            "created": datetime.now().strftime("%Y-%m-%d"),
            "updated": datetime.now().strftime("%Y-%m-%d"),
            "total_sentences": 0,
            "categories": ["motto", "greeting", "dialogue", "narrative", "ritual", "proverb"]
        },
        "sentences": []
    }

def save_sentence(result: Dict, category: str = "dialogue", context: str = "", register: str = "everyday") -> bool:
    """Save an approved translation to sentences.json."""
    if not result.get('success'):
        print("❌ Cannot save: translation has missing words")
        return False
    
    data = load_sentences()
    
    # Generate next ID
    next_id = max([s.get('id', 0) for s in data['sentences']], default=0) + 1
    
    # Build breakdown from result
    breakdown = []
    for step in result.get('breakdown', []):
        if '→' in step:
            parts = step.split('→')
            eng = parts[0].strip()
            rest = parts[1].strip()
            nyr = rest.split('(')[0].strip()
            role = rest.split('(')[1].rstrip(')') if '(' in rest else ''
            breakdown.append({
                "word": nyr,
                "gloss": eng,
                "role": role
            })
    
    sentence = {
        "id": next_id,
        "english": result['input'],
        "nyrakai": result['nyrakai'],
        "ipa": "",  # TODO: Generate IPA
        "literal": result.get('literal', ''),
        "breakdown": breakdown,
        "context": context,
        "category": category,
        "register": register,
        "notes": "",
        "validated": True,
        "added": datetime.now().strftime("%Y-%m-%d")
    }
    
    data['sentences'].append(sentence)
    data['meta']['total_sentences'] = len(data['sentences'])
    data['meta']['updated'] = datetime.now().strftime("%Y-%m-%d")
    
    with open(SENTENCES_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Saved sentence #{next_id} to sentences.json")
    return True

# ============================================================================
# CLI INTERFACE
# ============================================================================

def print_result(result: Dict):
    """Pretty print translation result."""
    print()
    print("=" * 60)
    print(f"📝 English: {result['input']}")
    print("-" * 60)
    
    if result['success']:
        print(f"✅ Nyrakai: {result['nyrakai']}")
    else:
        print(f"⚠️  Nyrakai: {result['nyrakai']}")
    
    print()
    print("📖 Breakdown:")
    for step in result['breakdown']:
        print(f"   {step}")
    
    if result['missing_words']:
        print()
        print(f"❌ Missing words: {', '.join(result['missing_words'])}")
        print("   (These words need to be added to the dictionary)")
    
    if result['warnings']:
        print()
        for warn in result['warnings']:
            print(f"⚠️  {warn}")
    
    print("=" * 60)
    print()

def interactive_mode(translator: NyrakaiTranslator):
    """Interactive translation mode."""
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║          NYRAKAI TRANSLATOR - Interactive Mode           ║")
    print("║                  Type 'quit' to exit                     ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()
    
    while True:
        try:
            sentence = input("English > ").strip()
            if sentence.lower() in ['quit', 'exit', 'q']:
                print("Farewell! N'æra añ r'ōk.")
                break
            if not sentence:
                continue
            
            result = translator.translate(sentence)
            print_result(result)
            
        except KeyboardInterrupt:
            print("\nFarewell! N'æra añ r'ōk.")
            break
        except Exception as e:
            print(f"Error: {e}")

def main():
    translator = NyrakaiTranslator()
    
    if len(sys.argv) < 2:
        print("Usage: python translator.py \"English sentence\"")
        print("       python translator.py --interactive")
        print("       python translator.py --save \"English sentence\"")
        print()
        print("Options:")
        print("  --interactive, -i    Interactive translation mode")
        print("  --save, -s           Save approved translation to sentences.json")
        print()
        print("Examples:")
        print("  python translator.py \"I see the star\"")
        print("  python translator.py \"She drinks water\"")
        print("  python translator.py --save \"Do you know the truth?\"")
        sys.exit(1)
    
    # Parse arguments
    save_mode = False
    interactive_mode_flag = False
    sentence_parts = []
    
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg in ['--interactive', '-i']:
            interactive_mode_flag = True
        elif arg in ['--save', '-s']:
            save_mode = True
        else:
            sentence_parts.append(arg)
        i += 1
    
    if interactive_mode_flag:
        interactive_mode(translator)
    elif sentence_parts:
        sentence = ' '.join(sentence_parts)
        result = translator.translate(sentence)
        print_result(result)
        
        if save_mode:
            if result.get('success'):
                print()
                confirm = input("Save this translation? [y/N] ").strip().lower()
                if confirm == 'y':
                    category = input("Category (motto/greeting/dialogue/narrative/ritual/proverb) [dialogue]: ").strip() or "dialogue"
                    context = input("Context (optional): ").strip()
                    save_sentence(result, category=category, context=context)
            else:
                print("❌ Cannot save: translation has missing words")
    else:
        print("No sentence provided.")
        sys.exit(1)

if __name__ == '__main__':
    main()
