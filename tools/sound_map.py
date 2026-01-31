#!/usr/bin/env python3
"""
Nyrakai Sound Map
Onset-to-domain mappings for phonosemantic word generation and validation.
"""

# Sound Map: onset -> (primary_domain, secondary_domain, example_words)
SOUND_MAP = {
    # Vowel-initial
    'a': ('spatial', 'postposition', ['añ']),  # over, above
    
    # Basic consonants
    'd': ('action', 'quality', ['dōn', 'dem']),  # give, bad
    'f': ('nature', 'body', ['fœra', 'fə̄n']),  # earth, foot
    'g': ('nature', None, ['gān', 'gīn', 'gɒr', 'gūr']),  # tree family
    'h': ('celestial', 'body', ['hīra', 'hūn', 'hīn', 'hǣn', 'hɒ̄r']),  # sun, moon, star, hand, heart
    'k': ('action', 'body', ['kōm', 'kæ']),  # come, tongue
    'l': ('body', 'action', ['lɛ̄r', 'lem']),  # liver, hear
    'm': ('body', None, ['mɒ̄l']),  # mouth
    'n': ('nature', 'body', ['na\'ēr', 'nærŧ', 'nəl', 'nɒ̄k', 'nɛ̄l']),  # water family, nose, knee
    'p': ('action', None, ['pæl']),  # walk
    'r': ('abstract', 'time', ['r\'ōk', 'raț']),  # death, night
    's': ('body', 'quality', ['sɛ̄l', 'sem']),  # ear, good
    't': ('nature', 'speech', ['tūk', 'tal']),  # bird, say
    'w': ('body', None, ['wōr']),  # flesh
    'y': ('body', 'nature', ['yūm', 'yīr', 'yə̄m', 'yīk', 'yɛn']),  # blood, eye, hair, louse, see
    'z': ('grammar', None, ['zæ']),  # not (negation)
    
    # Special consonants
    'ñ': ('quantity', None, ['ñœr']),  # many
    'š': ('body', 'cognition', ['šœ̄k', 'šōr']),  # head, know
    'ț': ('social', 'action', ['țræn', 'țūn', 'țīf\'æ']),  # person, drink, divine
    
    # Affricates
    'ƨ': ('nature', 'body', ['ƨæ', 'ƨæñor', 'ƨœn', 'ƨɛ̄n']),  # air, wind, skin, breast
    'ƶ': ('nature', None, ['ƶōrra', 'ƶæ', 'ƶōrțal']),  # fire family
    'ŧ': ('body', 'nature', ['ŧōn', 'ŧɒ̄k', 'ŧ\'ōm']),  # bone, tooth, thunder
    
    # Clusters
    'dr': ('spatial', 'law', ['drōm']),  # long
    'dw': (None, None, []),
    'fl': (None, None, []),
    'fr': ('nature', None, []),  # flow, stream
    'gl': ('domestic', None, []),  # house, shelter
    'gr': ('spatial', 'nature', ['grōm']),  # big, storm
    'gw': ('nature', None, ['gwōr']),  # mammals (dog)
    'hr': ('celestial', None, ['hro']),  # white/bright
    'kl': (None, None, []),
    'kr': ('nature', None, ['krōk']),  # ice, cold, dry
    'kw': ('domestic', 'grammar', ['kwæ']),  # door; what
    'pl': ('social', None, ['plūrek']),  # community, village
    'pr': ('abstract', None, ['pr\'ōk^']),  # fate
    'sl': ('nature', 'action', ['slōm']),  # vegetation; sleep
    'sm': ('spatial', None, []),  # small
    'sn': ('time', None, []),  # new
    'sp': ('domestic', None, []),  # possess
    'sr': ('action', None, ['sre\'un']),  # create
    'st': ('action', None, ['stīr']),  # stand
    'sw': ('action', 'spatial', ['swōl']),  # swim; round
    'tr': ('quantity', None, ['trəna']),  # two, pair
    'zl': (None, None, []),
    'zr': ('action', None, []),  # fight, strike
    'zw': ('nature', None, ['zwūr', 'zwūrk^e']),  # stone, sand
    'țr': ('social', None, ['țræn']),  # person (alternate analysis)
    
    # Ejectives
    'k^': ('speech', 'quantity', ['k^æl', 'k^æn\'œ', 'k^œl']),  # voice, dream, zero
    'p^': ('emotion', 'quantity', ['p^æñ', 'p^œr', 'p^ān']),  # fear, four, path
    't^': ('nature', 'quantity', ['t^arak', 't^ūn']),  # mountain, one
    
    # Glottal combinations (sacred/abstract)
    'n\'': ('abstract', None, ['n\'æ', 'n\'æra']),  # true, truth
    'ñ\'': ('abstract', None, ['ñ\'ān']),  # wisdom
    'r\'': ('abstract', None, ['r\'ōk']),  # death
    'ræ': ('abstract', None, ['ræțm']),  # soul
    'hœ': ('grammar', None, ['hœr']),  # who
    
    # Glottal with affricates (sacred/special)
    'ț\'': ('time', 'abstract', ['ț\'ūs', 'ț\'œmen', 'ț\'ɒm']),  # whisper, time, messenger
    't\'': ('emotion', 'social', ['t\'ōni', 't\'ōzar']),  # love, servant
    'ŧ\'': ('nature', 'onomatopoeia', ['ŧ\'ōm']),  # thunder
    
    # Vowel-initial (rare)
    'ə': ('grammar', None, ['əda']),  # and (conjunction)
    'i': ('time', None, ['in\'æl']),  # today
}

# Domain descriptions
DOMAINS = {
    'nature': 'Physical world: elements, weather, animals, plants',
    'body': 'Human body: organs, fluids, parts',
    'social': 'People and community: kinship, settlements',
    'action': 'Verbs and motion: give, walk, stand',
    'abstract': 'Sacred/philosophical: truth, death, soul, fate',
    'spatial': 'Space and size: long, big, over',
    'quantity': 'Numbers and amounts: one, two, many',
    'time': 'Temporal: night, new, today, time',
    'emotion': 'Feelings: fear, love',
    'quality': 'Properties: good, bad, dry',
    'grammar': 'Function words: not, what, who, and',
    'speech': 'Communication: say, voice',
    'cognition': 'Mind: know, dream',
    'celestial': 'Sky and light: sun, moon, stars, white',
    'domestic': 'Home and possession: house, village',
    'onomatopoeia': 'Sound words: thunder, whisper, crack',
}


def get_onset(word: str) -> str:
    """Extract the onset (initial consonant/cluster) from a word."""
    word = word.lower()
    
    # Check for glottal combinations first (C' patterns)
    if len(word) >= 2 and word[1] == "'":
        return word[:2]
    
    # Check for two-letter onsets (clusters, ejectives)
    if len(word) >= 2:
        two_char = word[:2]
        # Ejectives
        if two_char in ['k^', 'p^', 't^']:
            return two_char
        # Special diphthong-like onsets
        if two_char in ['ræ', 'hœ']:
            return two_char
        # Consonant clusters
        if two_char in SOUND_MAP:
            return two_char
    
    # Single character onset
    if len(word) >= 1 and word[0] in SOUND_MAP:
        return word[0]
    
    return word[0] if word else ''


def get_domain(word: str) -> tuple:
    """
    Get the semantic domain(s) for a word based on its onset.
    Returns: (primary_domain, secondary_domain) or (None, None) if not mapped
    """
    onset = get_onset(word)
    
    if onset in SOUND_MAP:
        return SOUND_MAP[onset][0], SOUND_MAP[onset][1]
    
    return None, None


def get_onsets_for_domain(domain: str) -> list:
    """Get all onsets that map to a given domain (primary or secondary)."""
    onsets = []
    for onset, (primary, secondary, _) in SOUND_MAP.items():
        if primary == domain or secondary == domain:
            onsets.append(onset)
    return onsets


def validate_domain(word: str, expected_domain: str) -> dict:
    """
    Check if a word's onset matches an expected semantic domain.
    Returns: {valid: bool, onset: str, domains: tuple, message: str}
    """
    onset = get_onset(word)
    primary, secondary = get_domain(word)
    
    valid = (primary == expected_domain or secondary == expected_domain)
    
    if valid:
        message = f"✓ '{word}' ({onset}-) matches {expected_domain} domain"
    else:
        if primary:
            message = f"✗ '{word}' ({onset}-) is {primary}/{secondary or 'none'}, not {expected_domain}"
        else:
            message = f"? '{word}' ({onset}-) has no domain mapping"
    
    return {
        'valid': valid,
        'onset': onset,
        'domains': (primary, secondary),
        'expected': expected_domain,
        'message': message
    }


def suggest_onset(domain: str) -> list:
    """Suggest onsets to use for a given semantic domain."""
    return get_onsets_for_domain(domain)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        word = sys.argv[1]
        onset = get_onset(word)
        primary, secondary = get_domain(word)
        print(f"Word: {word}")
        print(f"Onset: {onset}-")
        print(f"Primary domain: {primary or 'unmapped'}")
        print(f"Secondary domain: {secondary or 'none'}")
        
        if len(sys.argv) > 2:
            expected = sys.argv[2]
            result = validate_domain(word, expected)
            print(f"\nDomain check: {result['message']}")
    else:
        print("Nyrakai Sound Map")
        print("=" * 40)
        print("\nUsage:")
        print("  python sound_map.py <word>           - Get word's domain")
        print("  python sound_map.py <word> <domain>  - Check domain match")
        print("\nDomains:")
        for domain, desc in DOMAINS.items():
            print(f"  {domain}: {desc}")
