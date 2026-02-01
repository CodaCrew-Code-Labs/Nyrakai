#!/usr/bin/env python3
"""
Nyrakai Word Validator & Dictionary Manager
Checks if words follow Nyrakai phonotactic rules
Now with STRICT syllable structure validation!
Includes Sound Map domain validation.
"""

import json
import re
from pathlib import Path

# Import sound map for domain validation
try:
    from sound_map import get_onset, get_domain, validate_domain, DOMAINS
    SOUND_MAP_AVAILABLE = True
except ImportError:
    SOUND_MAP_AVAILABLE = False

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

# ============================================================
# AFFIX REGISTRY (for collision checking)
# ============================================================
AFFIXES = {
    'prefixes': {
        'za': 'negation/opposite',
        'fē': 'reversal/undo',
        "n'": 'abstract/truth quality',
    },
    'suffixes': {
        # Verbal derivation
        'ra': 'nominalizer (action→thing)',
        'ƨu': 'agentive (action→doer)',
        'țal': 'resultative (action→result)',
        "k^e": 'diminutive (verb)',
        'ñor': 'augmentative (great/intense)',
        'ɛm': 'adjectivizer (→like X)',
        # Nominal derivation
        'raš': 'keeper/guardian',
        'bren': 'place/domain',
        'țæl': 'essence/state',
        'šek': 'tool/instrument',
        'raun': 'collective/lineage',
        "k^æț": 'sacred intensifier',
        # Gender markers
        'æn': 'masculine gender',
        'ñī': 'feminine gender',
        'añī': 'feminine gender (with bridge)',
        # Plural markers
        'œ': 'masculine/mixed plural',
        'ā': 'feminine plural',
        # Pronoun plurals
        'ri': 'masc/mixed pronoun plural',
        'rā': 'feminine pronoun plural',
    }
}

# Minimum root length for affix checking (avoid false positives on short words)
MIN_ROOT_FOR_AFFIX = 2

# Category to sound map domain mapping
CATEGORY_TO_DOMAINS = {
    'The Body': ['body'],
    'The Physical World': ['nature', 'celestial'],
    'Animals': ['nature'],
    'Motion': ['action', 'spatial'],
    'Time': ['time', 'celestial'],
    'Emotions and Values': ['emotion', 'quality', 'abstract'],
    'Quantity': ['quantity'],
    'Question Words': ['grammar'],
    'Sense Perception': ['body', 'cognition', 'quality'],
    'Social and Political Relations': ['social'],
    'Basic Actions and Technology': ['action', 'domestic'],
    'Spatial Relations': ['spatial'],
    'Grammar and Pronouns': ['grammar'],
    'Speech and Language': ['speech', 'cognition'],
    'Cognition': ['cognition', 'abstract'],
    'Kinship': ['social'],
    'Law': ['social', 'abstract'],
    'Religion and Belief': ['abstract', 'celestial'],
    'Food and Drink': ['nature', 'domestic'],
    'Agriculture and Vegetation': ['nature'],
    'Warfare and Hunting': ['action'],
}

DICT_PATH = Path(__file__).parent / "nyrakai-dictionary.json"

def load_dictionary_words() -> dict:
    """Load dictionary and return lookup dicts."""
    if not DICT_PATH.exists():
        return {}, {}
    try:
        with open(DICT_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        nyr_to_eng = {}
        eng_to_nyr = {}
        for entry in data.get('words', []):
            nyr = entry.get('nyrakai', '')
            eng = entry.get('english', '')
            
            # Handle gender variant notation (e.g., "fāri / fārā")
            if ' / ' in nyr:
                variants = [v.strip() for v in nyr.split(' / ')]
                for variant in variants:
                    nyr_to_eng[variant] = eng
                    nyr_to_eng[variant.lower()] = eng
                # Also store the full form
                nyr_to_eng[nyr] = eng
            elif nyr:
                nyr_to_eng[nyr] = eng
                nyr_to_eng[nyr.lower()] = eng
            
            if eng:
                # Store first variant as default for eng→nyr lookup
                if ' / ' in nyr:
                    eng_to_nyr[eng.lower()] = nyr.split(' / ')[0].strip()
                else:
                    eng_to_nyr[eng.lower()] = nyr
        return nyr_to_eng, eng_to_nyr
    except:
        return {}, {}

# Load dictionary at module level for quick lookups
_NYR_TO_ENG, _ENG_TO_NYR = load_dictionary_words()

def word_exists_in_dictionary(nyrakai: str) -> tuple:
    """Check if a Nyrakai word exists in dictionary. Returns (exists, english_meaning)."""
    if nyrakai in _NYR_TO_ENG:
        return True, _NYR_TO_ENG[nyrakai]
    if nyrakai.lower() in _NYR_TO_ENG:
        return True, _NYR_TO_ENG[nyrakai.lower()]
    return False, None

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
    
    Supports gender variant notation: "word1 / word2" validates both.
    """
    # Handle gender variant pattern (e.g., "fāri / fārā")
    if ' / ' in word:
        variants = [v.strip() for v in word.split(' / ')]
        all_valid = True
        all_errors = []
        all_warnings = [f"Gender variants: {' / '.join(variants)}"]
        all_phonemes = []
        
        for variant in variants:
            v_result = validate_word(variant, auto_normalize)
            if not v_result['valid']:
                all_valid = False
                all_errors.extend([f"{variant}: {e}" for e in v_result['errors']])
            all_phonemes.extend(v_result['phonemes'])
        
        return {
            "word": word,
            "normalized": word,  # Keep original format
            "valid": all_valid,
            "errors": all_errors,
            "warnings": all_warnings,
            "syllables": variants,
            "syllable_structures": [],
            "phonemes": all_phonemes,
            "is_variant": True
        }
    
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
    
    # Check for forbidden sequences: ejective + glottal (^')
    if "^'" in normalized:
        result["errors"].append("Ejective marker ^ cannot precede glottal marker '")
        result["valid"] = False
        return result
    
    # Check for forbidden sequences: glottal + 'a' ('a)
    # The glottal marker already contains schwa, so 'a creates awkward /əʔa/ sequence
    if "'a" in normalized:
        result["errors"].append("Glottal marker ' cannot precede 'a' (use 'æ or 'e instead)")
        result["valid"] = False
        return result
    
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
    
    # Add sound map domain info if available
    if SOUND_MAP_AVAILABLE:
        onset = get_onset(normalized)
        primary, secondary = get_domain(normalized)
        result["onset"] = onset
        result["primary_domain"] = primary
        result["secondary_domain"] = secondary
    
    # Check if word already exists in dictionary
    exists, eng_meaning = word_exists_in_dictionary(normalized)
    if exists:
        result["exists_in_dictionary"] = True
        result["existing_meaning"] = eng_meaning
        result["warnings"].append(f"⚠️  Word already exists: '{normalized}' = '{eng_meaning}'")
    else:
        result["exists_in_dictionary"] = False
    
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


def edit_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return edit_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = prev_row[j + 1] + 1
            deletions = curr_row[j] + 1
            substitutions = prev_row[j] + (c1 != c2)
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row
    return prev_row[-1]


def check_similarity(word: str, threshold: int = 2) -> dict:
    """
    Check if a word is too similar to existing dictionary words.
    Returns dict with similar words found (edit distance <= threshold).
    """
    with open(DICT_PATH, 'r', encoding='utf-8') as f:
        dictionary = json.load(f)
    
    normalized = normalize(word)
    similar = []
    
    for w in dictionary["words"]:
        existing = w["nyrakai"]
        # Handle gender variants
        if ' / ' in existing:
            variants = [v.strip() for v in existing.split(' / ')]
        else:
            variants = [existing]
        
        for variant in variants:
            if variant == normalized:
                continue  # Skip exact match
            dist = edit_distance(normalized, variant)
            if dist <= threshold and len(normalized) > 2 and len(variant) > 2:
                similar.append({
                    "word": variant,
                    "meaning": w["english"],
                    "distance": dist
                })
    
    # Sort by distance
    similar.sort(key=lambda x: x["distance"])
    
    return {
        "word": word,
        "normalized": normalized,
        "similar_count": len(similar),
        "similar_words": similar,
        "has_conflicts": len([s for s in similar if s["distance"] == 1]) > 0
    }


def check_all_similarities(threshold: int = 1) -> list:
    """Find all confusingly similar pairs in dictionary."""
    with open(DICT_PATH, 'r', encoding='utf-8') as f:
        dictionary = json.load(f)
    
    # Build list of all words
    all_words = []
    for w in dictionary["words"]:
        nyr = w["nyrakai"]
        eng = w["english"]
        if ' / ' in nyr:
            for v in nyr.split(' / '):
                all_words.append((v.strip(), eng))
        else:
            all_words.append((nyr, eng))
    
    # Find similar pairs
    pairs = []
    for i, (w1, e1) in enumerate(all_words):
        for (w2, e2) in all_words[i+1:]:
            if len(w1) > 2 and len(w2) > 2:
                dist = edit_distance(w1, w2)
                if dist <= threshold:
                    pairs.append({
                        "word1": w1, "meaning1": e1,
                        "word2": w2, "meaning2": e2,
                        "distance": dist
                    })
    
    return pairs


# ============================================================
# CATEGORY-ONSET VALIDATION (Sound Map)
# ============================================================

def check_category_onset(include_all: bool = False) -> dict:
    """
    Check if words have correct onset for their semantic category.
    Uses sound map domain mappings.
    
    Returns:
        dict with mismatches, unmapped, and stats
    """
    if not SOUND_MAP_AVAILABLE:
        return {"error": "Sound map not available"}
    
    with open(DICT_PATH, 'r', encoding='utf-8') as f:
        dictionary = json.load(f)
    
    mismatches = []
    unmapped_onsets = []
    correct = []
    no_category_map = set()
    
    for entry in dictionary.get("words", []):
        nyr = entry.get("nyrakai", "").split(" / ")[0]
        eng = entry.get("english", "")
        category = entry.get("category", "")
        is_root = entry.get("is_root", True)
        
        if not nyr or not is_root:
            continue
        
        onset = get_onset(nyr)
        primary_domain, secondary_domain = get_domain(nyr)
        
        if not primary_domain:
            unmapped_onsets.append({
                "word": nyr,
                "meaning": eng,
                "onset": onset,
                "category": category
            })
            continue
        
        if category not in CATEGORY_TO_DOMAINS:
            no_category_map.add(category)
            continue
        
        expected_domains = CATEGORY_TO_DOMAINS[category]
        domains = [primary_domain]
        if secondary_domain:
            domains.append(secondary_domain)
        
        matches = any(d in expected_domains for d in domains)
        
        if matches:
            correct.append(nyr)
        else:
            mismatches.append({
                "word": nyr,
                "meaning": eng,
                "category": category,
                "onset": onset,
                "actual_domains": domains,
                "expected_domains": expected_domains
            })
    
    return {
        "total_checked": len(correct) + len(mismatches),
        "correct": len(correct),
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "unmapped_count": len(unmapped_onsets),
        "unmapped": unmapped_onsets,
        "missing_category_maps": list(no_category_map)
    }


# ============================================================
# AFFIX COLLISION CHECKING
# ============================================================

def check_affix_overlap(word: str) -> dict:
    """
    Check if a word accidentally contains affix patterns.
    Type 1 check: New translations shouldn't collide with affixes.
    
    Returns dict with:
      - word: original word
      - has_prefix_overlap: bool
      - has_suffix_overlap: bool
      - prefix_matches: list of (prefix, meaning, remaining)
      - suffix_matches: list of (suffix, meaning, remaining)
    """
    normalized = normalize(word)
    result = {
        "word": word,
        "normalized": normalized,
        "has_prefix_overlap": False,
        "has_suffix_overlap": False,
        "prefix_matches": [],
        "suffix_matches": [],
        "warnings": []
    }
    
    # Check prefixes
    for prefix, meaning in AFFIXES['prefixes'].items():
        if normalized.startswith(prefix):
            remaining = normalized[len(prefix):]
            # Only flag if remaining part could be a valid root
            if len(remaining) >= MIN_ROOT_FOR_AFFIX:
                result["prefix_matches"].append({
                    "affix": prefix,
                    "meaning": meaning,
                    "remaining": remaining
                })
                result["has_prefix_overlap"] = True
    
    # Check suffixes
    for suffix, meaning in AFFIXES['suffixes'].items():
        if normalized.endswith(suffix):
            remaining = normalized[:-len(suffix)]
            # Only flag if remaining part could be a valid root
            if len(remaining) >= MIN_ROOT_FOR_AFFIX:
                result["suffix_matches"].append({
                    "affix": suffix,
                    "meaning": meaning,
                    "remaining": remaining
                })
                result["has_suffix_overlap"] = True
    
    # Generate warnings
    if result["has_prefix_overlap"]:
        for m in result["prefix_matches"]:
            result["warnings"].append(
                f"Word starts with prefix '{m['affix']}' ({m['meaning']}). "
                f"Could be confused with {m['affix']}- + {m['remaining']}"
            )
    
    if result["has_suffix_overlap"]:
        for m in result["suffix_matches"]:
            result["warnings"].append(
                f"Word ends with suffix '-{m['affix']}' ({m['meaning']}). "
                f"Could be confused with {m['remaining']} + -{m['affix']}"
            )
    
    return result


def check_derived_collisions(verbose: bool = False, include_intentional: bool = False) -> dict:
    """
    Check if any root+affix combinations create words that already exist.
    Type 2 check: Derived forms shouldn't collide with existing dictionary words.
    
    Args:
        verbose: Print detailed output
        include_intentional: If True, include intentional derivations (marked with derived_from)
    
    Returns dict with:
      - total_roots: number of root words checked
      - total_derivations: number of derivations generated
      - collisions: list of collision details (accidental only by default)
      - intentional: list of intentional derivations (for reference)
    """
    with open(DICT_PATH, 'r', encoding='utf-8') as f:
        dictionary = json.load(f)
    
    # Build lookup of all existing words with their metadata
    existing_words = {}  # word -> {"meaning": str, "derived_from": dict or None}
    roots = []
    
    for entry in dictionary.get("words", []):
        nyr = entry.get("nyrakai", "")
        eng = entry.get("english", "")
        is_root = entry.get("is_root", False)
        derived_from = entry.get("derived_from", None)
        
        # Handle variant notation (e.g., "fāri / fārā" for gendered plurals)
        if ' / ' in nyr:
            variants = [v.strip() for v in nyr.split(' / ')]
            for v in variants:
                # For variants, store derived_from with the root (allows matching any affix from same root)
                existing_words[v] = {
                    "meaning": eng, 
                    "derived_from": derived_from,
                    "is_variant": True,
                    "all_variants": variants
                }
        else:
            existing_words[nyr] = {"meaning": eng, "derived_from": derived_from, "is_variant": False}
        
        # Collect roots for derivation
        if is_root and nyr and ' / ' not in nyr:
            roots.append({"nyrakai": nyr, "english": eng})
    
    collisions = []
    intentional = []
    total_derivations = 0
    
    for root in roots:
        nyr = root["nyrakai"]
        eng = root["english"]
        
        # Generate prefixed forms
        for prefix, prefix_meaning in AFFIXES['prefixes'].items():
            derived = prefix + nyr
            total_derivations += 1
            
            if derived in existing_words and existing_words[derived]["meaning"] != eng:
                collision_data = {
                    "type": "prefix",
                    "root": nyr,
                    "root_meaning": eng,
                    "affix": prefix,
                    "affix_meaning": prefix_meaning,
                    "derived": derived,
                    "collides_with": existing_words[derived]["meaning"]
                }
                
                # Check if this is an intentional derivation
                df = existing_words[derived].get("derived_from")
                is_variant = existing_words[derived].get("is_variant", False)
                
                # For variants (e.g., fāri/fārā), check if root matches (either affix is valid)
                if df and df.get("root") == nyr:
                    if df.get("affix") == prefix or is_variant:
                        collision_data["intentional"] = True
                        intentional.append(collision_data)
                    else:
                        collisions.append(collision_data)
                else:
                    collisions.append(collision_data)
        
        # Generate suffixed forms
        for suffix, suffix_meaning in AFFIXES['suffixes'].items():
            derived = nyr + suffix
            total_derivations += 1
            
            if derived in existing_words and existing_words[derived]["meaning"] != eng:
                collision_data = {
                    "type": "suffix",
                    "root": nyr,
                    "root_meaning": eng,
                    "affix": suffix,
                    "affix_meaning": suffix_meaning,
                    "derived": derived,
                    "collides_with": existing_words[derived]["meaning"]
                }
                
                # Check if this is an intentional derivation
                df = existing_words[derived].get("derived_from")
                is_variant = existing_words[derived].get("is_variant", False)
                
                # For variants (e.g., fāri/fārā), check if root matches (either affix is valid)
                if df and df.get("root") == nyr:
                    if df.get("affix") == suffix or is_variant:
                        collision_data["intentional"] = True
                        intentional.append(collision_data)
                    else:
                        collisions.append(collision_data)
                else:
                    collisions.append(collision_data)
    
    result = {
        "total_roots": len(roots),
        "total_derivations": total_derivations,
        "collision_count": len(collisions),
        "collisions": collisions,
        "intentional_count": len(intentional),
        "intentional": intentional
    }
    
    if include_intentional:
        result["all_collisions"] = collisions + intentional
    
    return result


def check_word_for_collisions(word: str, english: str = None, category: str = None) -> dict:
    """
    Combined check for a new word before adding to dictionary.
    Runs affix overlap, derivation collision, and onset validation checks.
    
    Args:
        word: Nyrakai word to check
        english: English meaning (optional)
        category: Dictionary category for onset validation (optional)
    
    Returns comprehensive collision report.
    """
    normalized = normalize(word)
    
    # Type 1: Check if word overlaps with affixes
    affix_check = check_affix_overlap(word)
    
    # Type 2: Check if word matches any existing root's derivation
    with open(DICT_PATH, 'r', encoding='utf-8') as f:
        dictionary = json.load(f)
    
    derivation_matches = []
    
    for entry in dictionary.get("words", []):
        nyr = entry.get("nyrakai", "")
        eng = entry.get("english", "")
        is_root = entry.get("is_root", False)
        
        if not is_root or ' / ' in nyr:
            continue
        
        # Check if our new word could be a derivation of an existing root
        for prefix, meaning in AFFIXES['prefixes'].items():
            if normalized == prefix + nyr:
                derivation_matches.append({
                    "type": "matches_prefix_derivation",
                    "existing_root": nyr,
                    "existing_meaning": eng,
                    "prefix": prefix,
                    "prefix_meaning": meaning
                })
        
        for suffix, meaning in AFFIXES['suffixes'].items():
            if normalized == nyr + suffix:
                derivation_matches.append({
                    "type": "matches_suffix_derivation",
                    "existing_root": nyr,
                    "existing_meaning": eng,
                    "suffix": suffix,
                    "suffix_meaning": meaning
                })
    
    # Check existing word collision
    exists, existing_meaning = word_exists_in_dictionary(normalized)
    
    # Onset validation (if category provided and sound map available)
    onset_check = None
    if category and SOUND_MAP_AVAILABLE:
        onset = get_onset(normalized)
        primary_domain, secondary_domain = get_domain(normalized)
        
        expected_domains = CATEGORY_TO_DOMAINS.get(category, [])
        actual_domains = [d for d in [primary_domain, secondary_domain] if d]
        
        onset_matches = any(d in expected_domains for d in actual_domains) if expected_domains else True
        
        onset_check = {
            "onset": onset,
            "actual_domains": actual_domains,
            "expected_domains": expected_domains,
            "category": category,
            "valid": onset_matches,
            "message": (
                f"✓ Onset '{onset}-' matches {category}" if onset_matches
                else f"✗ Onset '{onset}-' ({'/'.join(actual_domains) or 'unmapped'}) doesn't match {category} (expected: {expected_domains})"
            )
        }
    
    # Determine overall safety
    is_safe = (
        not exists and 
        not affix_check["has_prefix_overlap"] and 
        not affix_check["has_suffix_overlap"] and
        len(derivation_matches) == 0 and
        (onset_check is None or onset_check["valid"])
    )
    
    return {
        "word": word,
        "normalized": normalized,
        "proposed_meaning": english,
        "category": category,
        "already_exists": exists,
        "existing_meaning": existing_meaning,
        "affix_overlap": affix_check,
        "derivation_matches": derivation_matches,
        "onset_check": onset_check,
        "is_safe": is_safe
    }


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
        elif sys.argv[1] == "--check-similar":
            # Check for confusingly similar words
            threshold = int(sys.argv[2]) if len(sys.argv) > 2 else 1
            print(f"Checking for similar words (distance ≤ {threshold})...")
            print("=" * 60)
            pairs = check_all_similarities(threshold)
            if pairs:
                print(f"Found {len(pairs)} similar pairs:\n")
                for p in pairs:
                    print(f"  ⚠️  {p['word1']} ({p['meaning1']}) ↔ {p['word2']} ({p['meaning2']}) [dist={p['distance']}]")
            else:
                print("✅ No confusingly similar words found!")
        elif sys.argv[1] == "--similarity":
            # Check similarity for a specific word
            if len(sys.argv) < 3:
                print("Usage: validator.py --similarity <word> [threshold]")
            else:
                word = sys.argv[2]
                threshold = int(sys.argv[3]) if len(sys.argv) > 3 else 2
                result = check_similarity(word, threshold)
                print(f"Similarity check for: {word}")
                print("=" * 40)
                if result["similar_words"]:
                    print(f"Found {result['similar_count']} similar words:\n")
                    for s in result["similar_words"]:
                        warn = "🔴" if s["distance"] == 1 else "🟡"
                        print(f"  {warn} {s['word']} ({s['meaning']}) - distance {s['distance']}")
                    if result["has_conflicts"]:
                        print("\n⚠️  Has very similar words (distance=1)! Consider changing.")
                else:
                    print("✅ No similar words found - safe to use!")
        elif sys.argv[1] == "--domains":
            # List all domains
            if SOUND_MAP_AVAILABLE:
                print("Sound Map Domains")
                print("=" * 40)
                for domain, desc in DOMAINS.items():
                    print(f"  {domain}: {desc}")
            else:
                print("Sound map not available")
        elif sys.argv[1] == "--check-affixes":
            # Check if a word overlaps with affix patterns (Type 1)
            if len(sys.argv) < 3:
                print("Usage: validator.py --check-affixes <word>")
            else:
                word = sys.argv[2]
                result = check_affix_overlap(word)
                print(f"Affix Overlap Check: {word}")
                print("=" * 50)
                print(f"  Normalized: {result['normalized']}")
                
                if result["has_prefix_overlap"]:
                    print("\n🔴 PREFIX OVERLAPS:")
                    for m in result["prefix_matches"]:
                        print(f"   • Starts with '{m['affix']}-' ({m['meaning']})")
                        print(f"     Could be confused with: {m['affix']}- + {m['remaining']}")
                
                if result["has_suffix_overlap"]:
                    print("\n🔴 SUFFIX OVERLAPS:")
                    for m in result["suffix_matches"]:
                        print(f"   • Ends with '-{m['affix']}' ({m['meaning']})")
                        print(f"     Could be confused with: {m['remaining']} + -{m['affix']}")
                
                if not result["has_prefix_overlap"] and not result["has_suffix_overlap"]:
                    print("\n✅ No affix overlaps detected - safe!")
        elif sys.argv[1] == "--check-collisions":
            # Check all dictionary words for derivation collisions (Type 2)
            show_all = "--all" in sys.argv
            print("Checking derived form collisions...")
            print("=" * 60)
            result = check_derived_collisions(include_intentional=show_all)
            print(f"Roots checked: {result['total_roots']}")
            print(f"Derivations generated: {result['total_derivations']}")
            print(f"Accidental collisions: {result['collision_count']}")
            print(f"Intentional derivations: {result['intentional_count']}")
            
            if result["collisions"]:
                print("\n🔴 ACCIDENTAL COLLISIONS (need review):")
                for c in result["collisions"]:
                    if c["type"] == "prefix":
                        print(f"\n   {c['affix']}- + {c['root']} ({c['root_meaning']})")
                        print(f"   = {c['derived']} → collides with '{c['collides_with']}'")
                    else:
                        print(f"\n   {c['root']} ({c['root_meaning']}) + -{c['affix']}")
                        print(f"   = {c['derived']} → collides with '{c['collides_with']}'")
            else:
                print("\n✅ No accidental collisions found!")
            
            if show_all and result["intentional"]:
                print("\n🟢 INTENTIONAL DERIVATIONS (marked in dictionary):")
                for c in result["intentional"]:
                    if c["type"] == "prefix":
                        print(f"   ✓ {c['affix']}- + {c['root']} = {c['derived']} ({c['collides_with']})")
                    else:
                        print(f"   ✓ {c['root']} + -{c['affix']} = {c['derived']} ({c['collides_with']})")
            elif result["intentional_count"] > 0:
                print(f"\n(Use --check-collisions --all to see {result['intentional_count']} intentional derivations)")
        elif sys.argv[1] == "--check-word":
            # Full collision check for a new word (Type 1 + Type 2 + onset)
            if len(sys.argv) < 3:
                print("Usage: validator.py --check-word <word> [english] [--category \"Category Name\"]")
                print("\nCategories:")
                for cat in sorted(CATEGORY_TO_DOMAINS.keys()):
                    print(f"  • {cat}")
            else:
                word = sys.argv[2]
                english = None
                category = None
                
                # Parse arguments
                i = 3
                while i < len(sys.argv):
                    if sys.argv[i] == "--category" and i + 1 < len(sys.argv):
                        category = sys.argv[i + 1]
                        i += 2
                    else:
                        if english is None:
                            english = sys.argv[i]
                        i += 1
                
                result = check_word_for_collisions(word, english, category)
                
                print(f"Full Collision Check: {word}")
                if english:
                    print(f"Proposed meaning: {english}")
                if category:
                    print(f"Category: {category}")
                print("=" * 60)
                
                if result["already_exists"]:
                    print(f"\n🔴 WORD ALREADY EXISTS: means '{result['existing_meaning']}'")
                
                if result["affix_overlap"]["has_prefix_overlap"] or result["affix_overlap"]["has_suffix_overlap"]:
                    print("\n🟡 AFFIX OVERLAP WARNINGS:")
                    for w in result["affix_overlap"]["warnings"]:
                        print(f"   • {w}")
                
                if result["derivation_matches"]:
                    print("\n🔴 MATCHES EXISTING DERIVATION:")
                    for m in result["derivation_matches"]:
                        if "prefix" in m:
                            print(f"   • Matches {m['prefix']}- + {m['existing_root']} ({m['existing_meaning']})")
                        else:
                            print(f"   • Matches {m['existing_root']} ({m['existing_meaning']}) + -{m['suffix']}")
                
                # Onset check
                if result["onset_check"]:
                    oc = result["onset_check"]
                    if oc["valid"]:
                        print(f"\n✅ ONSET: {oc['message']}")
                    else:
                        print(f"\n🔴 ONSET MISMATCH: {oc['message']}")
                
                if result["is_safe"]:
                    print("\n✅ SAFE TO ADD - all checks passed!")
                else:
                    print("\n⚠️  REVIEW REQUIRED - potential issues found!")
        elif sys.argv[1] == "--list-affixes":
            # List all registered affixes
            print("Nyrakai Affix Registry")
            print("=" * 50)
            print("\nPREFIXES:")
            for affix, meaning in AFFIXES['prefixes'].items():
                print(f"   {affix}-  → {meaning}")
            print("\nSUFFIXES:")
            for affix, meaning in AFFIXES['suffixes'].items():
                print(f"   -{affix}  → {meaning}")
        elif sys.argv[1] == "--check-onset":
            # Check category-onset alignment
            if not SOUND_MAP_AVAILABLE:
                print("Sound map not available")
            else:
                print("Checking category-onset alignment...")
                print("=" * 60)
                result = check_category_onset()
                print(f"Total checked: {result['total_checked']}")
                print(f"Correct: {result['correct']} ✓")
                print(f"Mismatches: {result['mismatch_count']} ✗")
                print(f"Unmapped onsets: {result['unmapped_count']}")
                
                if result["mismatches"]:
                    print("\n🔴 CATEGORY-ONSET MISMATCHES:")
                    for m in result["mismatches"][:25]:
                        print(f"\n   {m['word']} ({m['meaning']})")
                        print(f"     Category: {m['category']}")
                        print(f"     Onset: {m['onset']}- → {'/'.join(m['actual_domains'])}")
                        print(f"     Expected: {m['expected_domains']}")
                    if len(result["mismatches"]) > 25:
                        print(f"\n   ... and {len(result['mismatches']) - 25} more")
                
                if result["unmapped"]:
                    print(f"\n🟡 UNMAPPED ONSETS ({result['unmapped_count']}):")
                    for u in result["unmapped"][:10]:
                        print(f"   {u['word']} ({u['meaning']}) - onset '{u['onset']}' not in sound map")
                
                if result["missing_category_maps"]:
                    print(f"\n⚠️  Categories without domain mapping: {result['missing_category_maps']}")
                
                if result["mismatch_count"] == 0:
                    print("\n✅ All root words have correct onset for their category!")
        else:
            # Validate a single word
            word = sys.argv[1]
            expected_domain = sys.argv[2] if len(sys.argv) > 2 else None
            result = validate_word(word)
            status = "✓ VALID" if result["valid"] else "✗ INVALID"
            print(f"{status}: {word}")
            print(f"  Normalized: {result['normalized']}")
            print(f"  Phonemes: {result['phonemes']}")
            print(f"  Syllables: {result['syllables']}")
            print(f"  Structure: {'.'.join(result['syllable_structures'])}")
            
            # Show domain info
            if SOUND_MAP_AVAILABLE and 'onset' in result:
                print(f"  Onset: {result['onset']}-")
                print(f"  Domain: {result['primary_domain'] or 'unmapped'}", end="")
                if result.get('secondary_domain'):
                    print(f" / {result['secondary_domain']}", end="")
                print()
                
                # Check domain match if specified
                if expected_domain:
                    domain_result = validate_domain(word, expected_domain)
                    print(f"  Domain check: {domain_result['message']}")
            
            if result["warnings"]:
                print(f"  Warnings: {result['warnings']}")
            if result["errors"]:
                print(f"  Errors: {result['errors']}")
    else:
        print("Nyrakai Validator")
        print("=" * 40)
        print("Usage:")
        print("  python validator.py <word>           - Validate a word")
        print("  python validator.py --check-dict     - Validate entire dictionary")
        print("  python validator.py --check-similar  - Find similar word pairs")
        print("  python validator.py --similarity <w> - Check similarity for word")
        print("  python validator.py --domains        - List sound map domains")
        print()
        print("Collision Checking:")
        print("  python validator.py --check-affixes <word>   - Check affix overlap (Type 1)")
        print("  python validator.py --check-collisions       - Check all derivation collisions (Type 2)")
        print("  python validator.py --check-onset            - Check category-onset alignment")
        print("  python validator.py --check-word <word> [en] - Full collision check for new word")
        print("  python validator.py --list-affixes           - List all registered affixes")
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

# =============================================================================
# ENGLISH SIMILARITY CHECK - Avoid words that look/sound too English
# =============================================================================

from difflib import SequenceMatcher

def check_english_similarity(nyrakai_word: str, english_meaning: str, threshold: float = 0.5) -> tuple[bool, list[str]]:
    """
    Check if a Nyrakai word is too similar to its English translation.
    
    Args:
        nyrakai_word: The Nyrakai word to check
        english_meaning: The English translation(s), comma-separated if multiple
        threshold: Similarity threshold (0.0-1.0), default 0.5
        
    Returns:
        tuple: (is_valid, list of warnings)
    """
    warnings = []
    
    # Normalize Nyrakai word (remove diacritics for comparison)
    nyr_clean = nyrakai_word.lower()
    for old, new in [("^", ""), ("'", ""), ("ē", "e"), ("ā", "a"), ("ī", "i"), 
                      ("ō", "o"), ("ū", "u"), ("æ", "ae"), ("œ", "oe"), ("ɛ", "e"),
                      ("ɒ", "o"), ("ə", "e"), ("ț", "t"), ("ƨ", "ts"), ("ƶ", "z"),
                      ("š", "sh"), ("ñ", "n"), ("ŧ", "th")]:
        nyr_clean = nyr_clean.replace(old, new)
    
    # Check against each English meaning
    for eng in english_meaning.split(','):
        eng_clean = eng.lower().strip()
        
        if not eng_clean or len(eng_clean) < 2:
            continue
            
        # Calculate similarity
        sim = SequenceMatcher(None, nyr_clean, eng_clean).ratio()
        
        # Check for substring matches
        is_substring = (len(nyr_clean) > 2 and len(eng_clean) > 2 and 
                       (nyr_clean in eng_clean or eng_clean in nyr_clean))
        
        # Check same start (3+ chars)
        same_start = (len(nyr_clean) >= 3 and len(eng_clean) >= 3 and 
                     nyr_clean[:3] == eng_clean[:3])
        
        # Check same end (3+ chars)  
        same_end = (len(nyr_clean) >= 3 and len(eng_clean) >= 3 and 
                   nyr_clean[-3:] == eng_clean[-3:])
        
        if sim >= threshold:
            warnings.append(f"Too similar to English '{eng}' ({sim*100:.0f}% match)")
        if is_substring:
            warnings.append(f"Contains/contained in English '{eng}'")
        if same_start and same_end:
            warnings.append(f"Same start AND end as English '{eng}'")
    
    is_valid = len(warnings) == 0
    return is_valid, warnings


def validate_word_complete(nyrakai_word: str, english_meaning: str = None, 
                           check_english: bool = True, english_threshold: float = 0.5) -> dict:
    """
    Complete validation including English similarity check.
    
    Args:
        nyrakai_word: The Nyrakai word to validate
        english_meaning: Optional English meaning for similarity check
        check_english: Whether to check English similarity
        english_threshold: Similarity threshold for English check
        
    Returns:
        dict with 'valid', 'errors', 'warnings', 'english_warnings'
    """
    # Run standard validation
    result = validate_word(nyrakai_word)
    
    # Add English check if meaning provided
    result['english_warnings'] = []
    if check_english and english_meaning:
        eng_valid, eng_warnings = check_english_similarity(
            nyrakai_word, english_meaning, english_threshold
        )
        result['english_warnings'] = eng_warnings
        if not eng_valid:
            result['warnings'] = result.get('warnings', []) + eng_warnings
    
    return result

