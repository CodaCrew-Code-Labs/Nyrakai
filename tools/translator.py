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

# Voice markers
VOICES = {
    'active': '',          # unmarked
    'passive': 'rōn',      # be [verb]ed
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
# Subject pronouns (can be subjects)
SUBJECT_PRONOUNS = {'i', 'you', 'he', 'she', 'it', 'we', 'they'}
# Object pronouns (are objects, not subjects)
OBJECT_PRONOUNS = {'me', 'you', 'him', 'her', 'it', 'us', 'them'}

# Possessive determiners → prefix form
POSSESSIVE_DETERMINERS = {
    'my': 'fā',
    'your': 'gæ',
    'his': 'šā',
    'her': 'šā',
    'its': 'šā',
    'our': 'fāri',
    'their': 'šāri',
}

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

# Prepositions → Nyrakai case suffixes
PREPOSITION_TO_CASE = {
    'with': 'instrumental',    # -ek (with/by means of)
    'by': 'instrumental',      # -ek
    'as': 'instrumental',      # -ek (in the capacity of)
    'to': 'dative',            # -iț (indirect object, direction)
    'for': 'dative',           # -iț
    'from': 'ablative',        # -ɒr (source/origin)
    'in': 'locative',          # -ñen (location)
    'on': 'locative',          # -ñen
    'at': 'locative',          # -ñen
    'without': 'privative',    # -zɒț
    'of': 'genitive',          # -šar (possession)
}

# Contractions → expanded form (Nyrakai drops the copula anyway)
CONTRACTIONS = {
    "we're": "we", "i'm": "i", "you're": "you", "they're": "they",
    "he's": "he", "she's": "she", "it's": "it",
    "we've": "we", "i've": "i", "you've": "you", "they've": "they",
    "we'll": "we", "i'll": "i", "you'll": "you", "they'll": "they",
    "he'll": "he", "she'll": "she", "it'll": "it",
    "isn't": "not", "aren't": "not", "wasn't": "not", "weren't": "not",
    "there's": "there", "here's": "here", "what's": "what", "who's": "who",
}

# Adverbs that should be translated (not treated as grammar)
ADVERB_WORDS = {
    'again', 'never', 'always', 'often', 'sometimes', 'now', 'then',
    'here', 'there', 'today', 'yesterday', 'tomorrow', 'soon', 'later',
    'quickly', 'slowly', 'well', 'badly', 'very', 'really', 'still',
    'every',  # "every sometimes" = k^āl ț'œmenk^e
}

# Particles (yes, no, etc.) - should be translated
PARTICLE_WORDS = {'yes', 'no', 'please', 'okay', 'ok'}

# Verb forms that map to adverb/verb words (these should be verbs, not adverbs)
VERB_FORMS_OF_ADVERBS = {'agained', 'agains'}  # "I agained" = verb, not adverb

# Conjunctions that connect clauses
CONJUNCTION_WORDS = {
    'but', 'and', 'or', 'so', 'yet', 'because', 'although', 'while',
    'if', 'when', 'before', 'after', 'until', 'unless',
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
        'went': 'go', 'goes': 'go', 'gone': 'go',  # go
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
        'agained': 'again', 'agains': 'again',  # again as verb = repeat
        'stayed': 'stay', 'stays': 'stay',  # stay
        'hitting': 'hit', 'hits': 'hit',  # hit
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
        'beings': 'human',  # human beings = humans = țræn
        'being': 'human',
        'humans': 'human',
        'people': 'person',  # people = persons = țræn
        'persons': 'person',
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
            'voice': 'active',  # active or passive
            'mood': 'declarative',
            'adjectives': [],
            'adverbs': [],
            'prepositional_phrases': [],  # [(preposition, noun, case), ...]
            'prep_phrase_words': set(),    # Words used in prepositional phrases (to exclude from objects)
            'raw_words': [],
        }
        
        # Clean and tokenize
        sentence = sentence.strip()
        
        # Remove quotation marks (but NOT apostrophes in contractions)
        # Only remove: " " " ' ' ` (curly quotes and backticks)
        sentence = re.sub(r'["""`]', '', sentence)
        
        # Expand contractions (We're → We, I'm → I, etc.)
        for contraction, expansion in CONTRACTIONS.items():
            pattern = rf"\b{re.escape(contraction)}\b"
            sentence = re.sub(pattern, expansion, sentence, flags=re.IGNORECASE)
        
        # Extract prepositional phrases (with X, to Y, from Z, etc.)
        # Captures: "with one shot", "to the man", etc.
        # Special pattern: "for the X he/she has done" → possessive ablative
        # "for the damage he's done" → šāk^ețɒr (his-damage-from)
        # Note: contractions expand "he's" → "he", so also match "he done"
        possessive_ablative_pattern = r"\bfor\s+(?:the\s+)?(\w+)\s+(he|she|it)(?:'s|'s| has| had|)\s*(?:done|made|caused)\b"
        poss_abl_match = re.search(possessive_ablative_pattern, sentence, re.IGNORECASE)
        if poss_abl_match:
            noun = poss_abl_match.group(1)
            # Store as special possessive ablative phrase
            result['possessive_ablative'] = {'noun': noun, 'possessor': 'he'}  # Could detect he/she/it
            # Remove from sentence
            sentence = re.sub(possessive_ablative_pattern, '', sentence, flags=re.IGNORECASE).strip()
        
        # Detect possessive noun phrases: "my water", "your dog", "his car"
        # Store as possessive_noun: {'determiner': 'my', 'noun': 'water'}
        possessive_pattern = r'\b(my|your|his|her|its|our|their)\s+(\w+)\b'
        poss_match = re.search(possessive_pattern, sentence, re.IGNORECASE)
        if poss_match:
            det = poss_match.group(1).lower()
            noun = poss_match.group(2)
            result['possessive_noun'] = {'determiner': det, 'noun': noun}
            # Remove from sentence
            sentence = re.sub(possessive_pattern, '', sentence, count=1, flags=re.IGNORECASE).strip()
        
        for prep, case in PREPOSITION_TO_CASE.items():
            # Match preposition + up to 3 words
            pattern = rf'\b{prep}\s+((?:\w+\s*){{1,3}})'
            match = re.search(pattern, sentence, re.IGNORECASE)
            if match:
                phrase = match.group(1).strip()
                # Filter: skip grammar words, stop at adverbs/determiners
                stop_words = ADVERB_WORDS | {'every', 'all', 'some', 'any', 'each', 'no', 'none'}
                words = []
                for w in phrase.split():
                    w_lower = w.lower()
                    if w_lower in stop_words:
                        break  # Stop at adverbs and determiners
                    if w_lower not in GRAMMAR_WORDS:
                        words.append(w)  # Skip grammar words but continue
                if words:
                    result['prepositional_phrases'].append((prep, words, case))
                    # Track these words to exclude them from object detection
                    result['prep_phrase_words'].update(w.lower() for w in words)
                    # Remove only what we captured (prep + words), not the full regex match
                    to_remove = f"{prep} {' '.join(words)}"
                    sentence = re.sub(rf'\b{re.escape(to_remove)}\b', '', sentence, flags=re.IGNORECASE).strip()
        
        # Check for question
        if sentence.endswith('?'):
            result['question'] = True
            result['mood'] = 'interrogative'
            sentence = sentence.rstrip('?').strip()
        
        # Check for negation (but keep 'never' as adverb too)
        negation_patterns = ['not', "don't", "doesn't", "didn't", "won't", "can't", "couldn't"]
        for neg in negation_patterns:
            if neg in sentence.lower():
                result['negated'] = True
                sentence = re.sub(rf"\b{neg}\b", "", sentence, flags=re.IGNORECASE).strip()
        
        # Check for 'never' - it's an adverb, NOT verb negation
        # (the negation is inherent in ñɒt itself, don't apply za- to verb)
        if 'never' in sentence.lower():
            # Do NOT set result['negated'] = True here!
            result['adverbs'].append('never')
            sentence = re.sub(r"\bnever\b", "", sentence, flags=re.IGNORECASE).strip()
        
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
        
        # Find subject (usually first noun/pronoun - but only SUBJECT pronouns)
        for i, word in enumerate(content_words):
            w_lower = word.lower()
            # Only subject pronouns can be subjects
            if w_lower in SUBJECT_PRONOUNS:
                result['subject'] = word
                content_words = content_words[:i] + content_words[i+1:]
                break
            # Object pronouns are NOT subjects
            elif w_lower in OBJECT_PRONOUNS:
                continue  # Skip, will handle as object later
            elif self.lookup(word):
                entry = self.lookup(word)
                if entry.get('pos') in ['noun', 'proper noun', 'pron']:
                    result['subject'] = word
                    content_words = content_words[:i] + content_words[i+1:]
                    break
        
        # Find verb
        # First pass: look for clear verbs
        for i, word in enumerate(content_words):
            entry = self.lookup(word)
            if entry:
                pos = entry.get('pos', '')
                # Check if it's a verb (including 'adverb/verb' dual-class words)
                if pos == 'verb' or (pos == 'adverb/verb' and word.lower() not in ADVERB_WORDS):
                    result['verb'] = word
                    content_words = content_words[:i] + content_words[i+1:]
                    break
        
        # Second pass: check if any word was originally a verb form (e.g., "agained" → "again")
        if not result['verb']:
            for raw_word in result['raw_words']:
                raw_lower = raw_word.lower().strip('.,!?;:')
                if raw_lower in self.IRREGULAR_VERBS:
                    base = self.IRREGULAR_VERBS[raw_lower]
                    entry = self.lookup(base)
                    if entry and 'verb' in entry.get('pos', ''):
                        result['verb'] = base
                        # Remove from content_words if present
                        content_words = [w for w in content_words if w.lower() != base]
                        break
        
        # Remaining content words are likely objects, adjectives, adverbs, or conjunctions
        for word in content_words:
            w_lower = word.lower()
            
            # Check if it's an adverb we should translate
            # But skip if we already have a verb for this word (e.g., "agained" → "again" as verb)
            if w_lower in ADVERB_WORDS and w_lower not in [a.lower() for a in result['adverbs']]:
                # Don't add as adverb if it's the same as our detected verb
                if result['verb'] and w_lower == result['verb'].lower():
                    continue
                result['adverbs'].append(word)
                continue
            
            # Check if it's a conjunction
            if w_lower in CONJUNCTION_WORDS:
                if 'conjunctions' not in result:
                    result['conjunctions'] = []
                result['conjunctions'].append(word)
                continue
            
            # Object pronouns are always objects
            if w_lower in OBJECT_PRONOUNS:
                if not result['object']:
                    result['object'] = word
                continue
            
            entry = self.lookup(word)
            if entry:
                pos = entry.get('pos', '')
                if pos == 'adj':
                    # Skip if word is already in a prepositional phrase
                    if w_lower not in result['prep_phrase_words']:
                        result['adjectives'].append(word)
                elif pos == 'adverb':
                    result['adverbs'].append(word)
                elif pos == 'conjunction':
                    if 'conjunctions' not in result:
                        result['conjunctions'] = []
                    result['conjunctions'].append(word)
                elif pos in ['noun', 'proper noun', 'pron']:
                    # Skip if word is already in a prepositional phrase
                    if w_lower in result['prep_phrase_words']:
                        continue
                    if not result['object']:
                        result['object'] = word
                    else:
                        result['indirect_object'] = word
            else:
                # Unknown word - could be object (but not if it's a preposition or in a prep phrase)
                if not result['object'] and w_lower not in PREPOSITION_TO_CASE and w_lower not in result['prep_phrase_words']:
                    result['object'] = word
        
        # Determine aspect from tense markers
        original_lower = result['original'].lower()
        words_lower = [w.lower() for w in words]
        
        # Check for universal truth patterns first
        # "All X are..." statements use completed aspect (truth is established/sealed)
        universal_truth_patterns = [
            r'\ball\b.*\bare\b',           # "all humans are..."
            r'\beveryone\b.*\bis\b',        # "everyone is..."
            r'\beverything\b.*\bis\b',      # "everything is..."
            r'\bno one\b.*\bis\b',          # "no one is..."
            r'\bnothing\b.*\bis\b',         # "nothing is..."
        ]
        is_universal_truth = any(re.search(p, original_lower) for p in universal_truth_patterns)
        
        # Check for irregular past tense verbs
        past_tense_irregulars = ['saw', 'ate', 'drank', 'gave', 'came', 'knew', 'heard', 
                                  'said', 'sat', 'stood', 'slept', 'swam', 'flew', 'died',
                                  'killed', 'burned', 'burnt', 'lay', 'went', 'took', 'made']
        
        if is_universal_truth:
            result['aspect'] = 'completed'  # Universal truths are "sealed/established"
        elif any(w in original_lower for w in ['will', 'shall', 'going to', 'might', 'could', 'can']):
            # Check modals FIRST (before -ed check, since "can be used" has "used")
            result['aspect'] = 'potential'
        elif any(w in words_lower for w in past_tense_irregulars):
            result['aspect'] = 'completed'
        elif any(w in original_lower for w in ['did', 'was', 'were', 'had']):
            result['aspect'] = 'completed'
        elif any(w.endswith('ed') for w in words_lower):
            result['aspect'] = 'completed'
        elif any(w in original_lower for w in ['always', 'usually', 'often']):
            # 'every' alone doesn't trigger habitual (could be "every sometimes" = adverb phrase)
            result['aspect'] = 'habitual'
        else:
            result['aspect'] = 'ongoing'
        
        # Detect passive voice: "be + past participle" patterns
        # Examples: "be used", "can be seen", "is being eaten", "was killed"
        passive_patterns = [
            r'\bcan be (\w+)',      # "can be used"
            r'\bto be (\w+)',       # "to be seen"
            r'\bbe (\w+ed)\b',      # "be used", "be killed"
            r'\bis being (\w+)',    # "is being eaten"
            r'\bwas (\w+ed)\b',     # "was used"
            r'\bwere (\w+ed)\b',    # "were killed"
            r'\bbeen (\w+ed)\b',    # "has been used"
            r'\bget (\w+ed)\b',     # "get used"
        ]
        for pattern in passive_patterns:
            match = re.search(pattern, original_lower)
            if match:
                result['voice'] = 'passive'
                # Extract the main verb from the passive construction
                passive_verb = match.group(1).rstrip('ed')
                # Map common past participles to base verbs
                participle_to_base = {
                    'us': 'use', 'seen': 'see', 'known': 'know', 'taken': 'take',
                    'given': 'give', 'eaten': 'eat', 'drunk': 'drink', 'kill': 'kill',
                    'said': 'say', 'told': 'tell', 'made': 'make', 'done': 'do',
                }
                if passive_verb in participle_to_base:
                    result['verb'] = participle_to_base[passive_verb]
                elif not result['verb']:
                    result['verb'] = passive_verb
                break
        
        # Handle quoted speech: "I said X" where X (adverbs) is the quoted content
        # Speech verbs take their "adverbs" as the object (what was said)
        speech_verbs = ['said', 'say', 'told', 'tell', 'asked', 'ask', 'shouted', 'shout',
                        'whispered', 'whisper', 'cried', 'cry', 'called', 'call', 'yelled', 'yell']
        if result['verb'] and result['verb'].lower() in speech_verbs:
            # If we have adverbs but no object, the adverbs are likely quoted content
            if result['adverbs'] and not result['object']:
                # Convert adverbs to quoted object (join them as a phrase)
                result['quoted_speech'] = result['adverbs'].copy()
                result['adverbs'] = []  # Clear adverbs since they're now the object
        
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
            # Handle gender variant notation (e.g., "fāri / fārā") - use first (masc/mixed)
            if ' / ' in nyr:
                nyr = nyr.split(' / ')[0].strip()
            return self.apply_case(nyr, case), True
        
        # Word not found
        self.missing_words.append(english)
        return f"[{english}?]", False
    
    def translate_compound(self, sentence: str) -> Dict:
        """
        Handle compound sentences with conjunctions.
        Splits on 'but', 'and', 'or', then translates each clause.
        """
        # Special pattern: "yes or no" at end of question
        yes_no_pattern = r',?\s*(yes\s+or\s+no)\s*\??$'
        yes_no_match = re.search(yes_no_pattern, sentence, re.IGNORECASE)
        if yes_no_match:
            # Remove "yes or no" from sentence, translate main part, then append
            main_sentence = sentence[:yes_no_match.start()].strip()
            if main_sentence.endswith(','):
                main_sentence = main_sentence[:-1]
            main_sentence += '?'  # Keep it as question
            
            result = self.translate_single(main_sentence)
            # Add "yes or no" as: n'æk wɒ zān
            yes_nyr = self.lookup('yes')
            no_nyr = self.lookup('no')
            if yes_nyr and no_nyr:
                yes_word = yes_nyr['nyrakai']
                no_word = no_nyr['nyrakai']
                result['nyrakai'] = f"{result['nyrakai']}, {yes_word} wɒ {no_word}?"
                result['breakdown'].append(f"yes or no → {yes_word} wɒ {no_word}")
            return result
        
        # Check for comma-separated parallel clauses with repeated subject
        # Pattern: "I'm X, I'm Y" → translate as two separate clauses
        comma_pattern = r",\s*(?=I'm|I am|you're|you are|he's|he is|she's|she is|we're|we are|they're|they are)"
        comma_match = re.search(comma_pattern, sentence, re.IGNORECASE)
        if comma_match:
            clause1 = sentence[:comma_match.start()].strip()
            clause2 = sentence[comma_match.end():].strip().rstrip('.')
            
            if clause1 and clause2:
                result1 = self.translate_single(clause1)
                result2 = self.translate_single(clause2)
                
                combined = {
                    'input': sentence,
                    'parsed': {'parallel_clauses': True},
                    'nyrakai': f"{result1['nyrakai']}, {result2['nyrakai']}",
                    'literal': f"{result1.get('literal', '')} // {result2.get('literal', '')}",
                    'breakdown': result1['breakdown'] + ['---'] + result2['breakdown'],
                    'missing_words': result1.get('missing_words', []) + result2.get('missing_words', []),
                    'warnings': result1.get('warnings', []) + result2.get('warnings', []),
                    'success': result1.get('success', True) and result2.get('success', True),
                }
                return combined
        
        # Conjunctions we handle
        conjunction_map = {
            'but': 'mur',
            'and': 'əda',
            'or': 'wɒ',
            'then': 'țɒ',
            'so': 'țɒ',  # use 'then' for 'so'
        }
        
        # Check if sentence contains a conjunction that splits clauses
        sentence_clean = sentence.strip().rstrip('?!.')
        sentence_lower = sentence_clean.lower()
        
        split_conj = None
        split_pos = -1
        
        for conj in conjunction_map:
            # Look for conjunction with word boundaries
            pattern = rf'\b{conj}\b'
            match = re.search(pattern, sentence_lower)
            if match:
                # Make sure it's not at the very start
                if match.start() > 2:
                    # Don't split on "and" if it's joining adjectives (X and Y before a verb)
                    # or if it's inside a prepositional phrase (in X and Y)
                    if conj == 'and':
                        before = sentence_lower[:match.start()].strip()
                        after = sentence_lower[match.end():].strip()
                        
                        # Check if "and" is joining adjectives (pattern: ADJ and ADJ ... VERB)
                        # Skip if both sides look like single words (adjective pairs)
                        before_words = before.split()
                        after_words = after.split()
                        
                        # Skip if this looks like adjective joining (single word before "and")
                        # and sentence contains verb after the conjunction
                        if len(before_words) > 0 and len(after_words) > 0:
                            # Check for "in X and Y" pattern (inside prepositional phrase)
                            if before_words[-1] in ['in', 'on', 'at', 'with', 'by', 'from', 'to']:
                                continue
                            # Check for previous "in" indicating we're inside a PP
                            if 'in ' in before and len(before.split('in ')[-1].split()) <= 2:
                                continue
                            # Check for adjective pairs: word AND word followed by noun/verb
                            last_before = before_words[-1]
                            first_after = after_words[0]
                            # If the word after "and" is followed by "in" or end, likely adjective pair
                            if len(after_words) >= 2 and after_words[1] == 'in':
                                continue  # "free and equal in" - don't split
                        
                    split_conj = conj
                    split_pos = match.start()
                    break
        
        if split_conj and split_pos > 0:
            # Split into two clauses
            clause1 = sentence_clean[:split_pos].strip().rstrip(',')
            clause2 = sentence_clean[split_pos + len(split_conj):].strip().lstrip(',').strip()
            
            if clause1 and clause2:
                # Translate each clause
                result1 = self.translate_single(clause1)
                result2 = self.translate_single(clause2)
                
                # Get conjunction Nyrakai
                conj_nyr = conjunction_map[split_conj]
                
                # Combine results
                combined = {
                    'input': sentence,
                    'parsed': {'compound': True, 'conjunction': split_conj},
                    'nyrakai': f"{result1['nyrakai']}, {conj_nyr} {result2['nyrakai']}",
                    'literal': f"{result1['literal']} {split_conj.upper()} {result2['literal']}",
                    'breakdown': result1['breakdown'] + [f"[{split_conj}] → {conj_nyr} (conjunction)"] + result2['breakdown'],
                    'missing_words': result1['missing_words'] + result2['missing_words'],
                    'warnings': result1['warnings'] + result2['warnings'],
                    'success': result1['success'] and result2['success'],
                }
                return combined
        
        # No conjunction found, translate as single sentence
        return self.translate_single(sentence)
    
    def translate(self, sentence: str) -> Dict:
        """
        Main translation entry point.
        Handles compound sentences, then falls back to single.
        """
        return self.translate_compound(sentence)
    
    def translate_single(self, sentence: str) -> Dict:
        """
        Translate a single English clause to Nyrakai.
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
        # [INST] + O (Object) + V+Asp (Verb+Aspect) + S (Subject) + [Adverbs]
        
        parts = []
        breakdown = []
        adverb_parts = []  # Store adverbs for end of sentence
        adjective_parts = []  # Store adjectives for after verb
        
        # 0. Collect adverbs (will be placed at END of sentence)
        if parsed.get('adverbs'):
            for adv in parsed['adverbs']:
                adv_entry = self.lookup(adv)
                if adv_entry:
                    adv_nyr = adv_entry['nyrakai']
                    adverb_parts.append(adv_nyr)
                    breakdown.append(f"{adv} → {adv_nyr} (adverb)")
                else:
                    self.missing_words.append(adv)
                    adverb_parts.append(f"[{adv}?]")
                    breakdown.append(f"{adv} → [NOT FOUND] (adverb)")
        
        # 0a. Separate locative from instrumental phrases
        locative_phrases = []
        instrumental_phrases = []
        if parsed.get('prepositional_phrases'):
            for prep, words, case in parsed['prepositional_phrases']:
                if case == 'locative':
                    locative_phrases.append((prep, words, case))
                else:
                    instrumental_phrases.append((prep, words, case))
        
        # 0a. Possessive ablative (reason/cause with possessor)
        # "for the damage he's done" → šāk^ețɒr (his-damage-from)
        if parsed.get('possessive_ablative'):
            poss_abl = parsed['possessive_ablative']
            noun = poss_abl['noun']
            possessor = poss_abl.get('possessor', 'he')
            
            # Get possessive prefix
            poss_prefix = {'he': 'šā', 'she': 'šā', 'it': 'šā', 'i': 'fā', 'you': 'gæ', 'we': 'fāri'}.get(possessor.lower(), 'šā')
            
            # Translate noun
            noun_nyr, _ = self.translate_word(noun, 'nominative')
            
            # Apply possessive prefix + ablative suffix
            ablative_suffix = CASES.get('ablative', 'ɒr')
            poss_abl_word = poss_prefix + apply_interfix(noun_nyr, ablative_suffix)
            
            parts.append(poss_abl_word)
            breakdown.append(f"for {noun} {possessor}'s done → {poss_abl_word} (possessive + ablative)")
        
        # 0b. Locative phrases first (at VERY FRONT)
        # For locative, apply suffix to EACH noun (not just last)
        # "in dignity and rights" → "n'ærñorñen əda šōrænñen"
        for prep, words, case in locative_phrases:
            phrase_parts = []
            case_suffix = CASES.get(case, '')
            for word in words:
                if word.lower() == 'and':
                    phrase_parts.append('əda')
                else:
                    word_nyr, word_ok = self.translate_word(word, 'nominative')
                    # Apply locative suffix to each noun
                    word_nyr = apply_interfix(word_nyr, case_suffix)
                    phrase_parts.append(word_nyr)
            if phrase_parts:
                phrase_str = ' '.join(phrase_parts)
                parts.append(phrase_str)
                breakdown.append(f"{prep} {' '.join(words)} → {phrase_str} ({case}, -{case_suffix})")
        
        # 0c. Instrumental phrases next
        for prep, words, case in instrumental_phrases:
            phrase_parts = []
            for word in words:
                word_nyr, word_ok = self.translate_word(word, 'nominative')
                phrase_parts.append(word_nyr)
            if phrase_parts:
                last_word = phrase_parts[-1]
                case_suffix = CASES.get(case, '')
                phrase_parts[-1] = apply_interfix(last_word, case_suffix)
                phrase_str = ' '.join(phrase_parts)
                parts.append(phrase_str)
                breakdown.append(f"{prep} {' '.join(words)} → {phrase_str} ({case}, -{case_suffix})")
        
        # 1. Collect adjectives (will be placed AFTER verb)
        # First, identify quantifiers (they go with subject, not as regular adjectives)
        quantifiers = ['all', 'every', 'each', 'some', 'no', 'any', 'none']
        quantifier = None
        if parsed['adjectives']:
            for adj in parsed['adjectives']:
                if adj.lower() in quantifiers:
                    quantifier = adj
                else:
                    adj_nyr, adj_ok = self.translate_word(adj)
                    adjective_parts.append(adj_nyr)
                    breakdown.append(f"{adj} → {adj_nyr} (adj)")
        
        # 1b. Quoted speech (if present) - placed as object
        if parsed.get('quoted_speech'):
            quoted_parts = []
            for word in parsed['quoted_speech']:
                word_entry = self.lookup(word)
                if word_entry:
                    quoted_parts.append(word_entry['nyrakai'])
                else:
                    self.missing_words.append(word)
                    quoted_parts.append(f"[{word}?]")
            quoted_str = ' '.join(quoted_parts)
            parts.append(quoted_str)
            breakdown.append(f"'{' '.join(parsed['quoted_speech'])}' → {quoted_str} (quoted speech)")
        
        # 1c. Possessive noun phrase: "my water" → fāna'ēraš (prefix + noun + accusative)
        if parsed.get('possessive_noun'):
            poss = parsed['possessive_noun']
            det = poss['determiner']
            noun = poss['noun']
            
            # Get possessive prefix
            poss_prefix = POSSESSIVE_DETERMINERS.get(det, 'šā')
            
            # Translate noun
            noun_nyr, _ = self.translate_word(noun, 'nominative')
            
            # Combine: prefix + noun + accusative
            combined = poss_prefix + noun_nyr
            acc_suffix = CASES.get('accusative', 'aš')
            combined_acc = apply_interfix(combined, acc_suffix)
            
            parts.append(combined_acc)
            breakdown.append(f"{det} {noun} → {combined_acc} (possessive + accusative)")
        
        # 1d. Object (accusative case) - skip "beings" if subject is "human"
        obj = parsed['object']
        if obj and obj.lower() == 'beings' and parsed['subject'] and parsed['subject'].lower() == 'human':
            # "human beings" → just use "human" as subject, skip "beings" as object
            obj = None
        
        # Skip object if it's the same as subject (compound predicate adjective: "I'm X, I'm Y")
        if obj and parsed['subject'] and obj.lower() == parsed['subject'].lower():
            obj = None
        
        # For copula-less sentences (no verb, just subject + adjectives), 
        # don't treat anything as object
        is_copula_less = not parsed['verb'] and parsed['adjectives']
        if is_copula_less:
            obj = None
        
        if obj:
            obj_nyr, obj_ok = self.translate_word(obj, 'accusative')
            parts.append(obj_nyr)
            breakdown.append(f"{obj} → {obj_nyr} (object, accusative)")
        
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
        
        # 2b. Adjectives (after verb, or as predicate if no verb)
        # For copula-less sentences, adjectives are the main predicate
        if adjective_parts:
            if len(adjective_parts) > 1:
                parts.append(' əda '.join(adjective_parts))
                breakdown.append("(adjectives joined with əda)")
            else:
                parts.extend(adjective_parts)
        
        # 2c. Add negation for copula-less sentences (I am NOT X)
        # If negated but no verb, add 'zæ' (not) after adjectives
        if is_copula_less and parsed['negated']:
            parts.append('zæ')
            breakdown.append("[not] → zæ (negation)")
        
        # 3. Quantifier + Subject (nominative - unmarked)
        # quantifier was already extracted in step 1
        if parsed['subject']:
            subj_nyr, subj_ok = self.translate_word(parsed['subject'], 'nominative')
            if quantifier:
                quant_nyr, _ = self.translate_word(quantifier)
                parts.append(f"{quant_nyr} {subj_nyr}")
                breakdown.append(f"{quantifier} {parsed['subject']} → {quant_nyr} {subj_nyr} (quantifier + subject)")
            else:
                parts.append(subj_nyr)
                breakdown.append(f"{parsed['subject']} → {subj_nyr} (subject)")
        
        # 4. Verb voice and aspect
        if parsed['verb']:
            verb_entry = self.lookup(parsed['verb'])
            if verb_entry:
                # Add voice if passive
                if parsed.get('voice') == 'passive':
                    voice_suffix = VOICES.get('passive', 'rōn')
                    breakdown.append(f"[passive] → {voice_suffix} (voice)")
                
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
                # Build verb: VERB + VOICE + ASPECT
                voice_suffix = VOICES.get(parsed.get('voice', 'active'), '')
                aspect_suffix = ASPECTS.get(parsed['aspect'], ASPECTS['ongoing'])
                
                # Apply voice first, then aspect
                verb_with_voice = verb_form + voice_suffix if voice_suffix else verb_form
                final_parts[verb_idx] = apply_interfix(verb_with_voice, aspect_suffix)
        
        # Add adverbs at end (after subject, before question particle)
        if adverb_parts:
            final_parts.extend(adverb_parts)
        
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

def validate_all_sentences(translator):
    """Validate translator against all stored sentences."""
    data = load_sentences()
    
    # Categories to skip (special structures that translator doesn't handle)
    skip_categories = {'motto'}  # Add more if needed: 'ritual', etc.
    
    print('=' * 70)
    print('TRANSLATOR VALIDATION: All Stored Sentences')
    print('=' * 70)
    
    matches = 0
    skipped = 0
    total = len(data['sentences'])
    
    for s in data['sentences']:
        english = s['english']
        stored = s['nyrakai']
        category = s.get('category', 'dialogue')
        
        # Skip special categories
        if category in skip_categories:
            eng_display = english[:40] + '...' if len(english) > 40 else english
            print(f"#{s['id']} ⏭️  {eng_display}")
            print(f"   (skipped: {category} - special structure)")
            skipped += 1
            continue
        
        # Translate
        result = translator.translate(english)
        generated = result.get('nyrakai', '')
        
        match = '✅' if generated == stored else '❌'
        if generated == stored:
            matches += 1
        
        eng_display = english[:40] + '...' if len(english) > 40 else english
        print(f"#{s['id']} {match} {eng_display}")
        if generated != stored:
            print(f"   Stored:    {stored}")
            print(f"   Generated: {generated}")
    
    validated = total - skipped
    print()
    print('=' * 70)
    print(f"🎯 SCORE: {matches}/{validated} validated sentences match")
    if skipped:
        print(f"   ({skipped} skipped: special structure)")
    print('=' * 70)


def main():
    translator = NyrakaiTranslator()
    
    if len(sys.argv) < 2:
        print("Usage: python translator.py \"English sentence\"")
        print("       python translator.py --interactive")
        print("       python translator.py --save \"English sentence\"")
        print("       python translator.py --validate")
        print()
        print("Options:")
        print("  --interactive, -i    Interactive translation mode")
        print("  --save, -s           Save approved translation to sentences.json")
        print("  --validate, -v       Validate against all stored sentences")
        print()
        print("Examples:")
        print("  python translator.py \"I see the star\"")
        print("  python translator.py \"She drinks water\"")
        print("  python translator.py --save \"Do you know the truth?\"")
        sys.exit(1)
    
    # Parse arguments
    save_mode = False
    interactive_mode_flag = False
    validate_mode = False
    sentence_parts = []
    
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg in ['--interactive', '-i']:
            interactive_mode_flag = True
        elif arg in ['--save', '-s']:
            save_mode = True
        elif arg in ['--validate', '-v']:
            validate_mode = True
        else:
            sentence_parts.append(arg)
        i += 1
    
    if validate_mode:
        validate_all_sentences(translator)
    elif interactive_mode_flag:
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
