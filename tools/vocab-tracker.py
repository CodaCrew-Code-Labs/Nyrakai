#!/usr/bin/env python3
"""
Nyrakai Vocabulary Progress Tracker

Tracks vocabulary completion against:
1. Swadesh 100 (core universal concepts)
2. Swadesh 207 (extended basic vocabulary)
3. Target 912+ word list (comprehensive vocabulary)
4. WOLD 100 (World Loanword Database - borrowing resistance)
5. IDS 200 (Intercontinental Dictionary Series)
6. Concepticon 100 (Cross-linguistic core concepts)
7. NorthEuraLex 100 (Northern Eurasian core)
8. Zompist 200 (Conlanger's essential vocabulary)

Usage:
    python vocab-tracker.py                    # Full report
    python vocab-tracker.py --summary          # Quick summary
    python vocab-tracker.py --missing swadesh100  # Show missing Swadesh 100
    python vocab-tracker.py --missing swadesh207  # Show missing Swadesh 207
    python vocab-tracker.py --missing wold100     # Show missing WOLD 100
    python vocab-tracker.py --missing ids200      # Show missing IDS 200
    python vocab-tracker.py --missing concepticon # Show missing Concepticon
    python vocab-tracker.py --missing northeuralex # Show missing NorthEuraLex
    python vocab-tracker.py --missing zompist     # Show missing Zompist
    python vocab-tracker.py --lists               # Show all available lists
    python vocab-tracker.py --category "The Body" # Show specific category
    python vocab-tracker.py --export              # Export to markdown
"""

import json
import argparse
from pathlib import Path
from collections import defaultdict

# Import extended word lists
try:
    from wordlists import CONCEPTICON, WOLD, NORTHEURALEX, ZOMPIST, ALL_LISTS
    EXTENDED_LISTS_AVAILABLE = True
except ImportError:
    EXTENDED_LISTS_AVAILABLE = False
    CONCEPTICON = []
    WOLD = []
    NORTHEURALEX = []
    ZOMPIST = []
    ALL_LISTS = {}

# Swadesh 100 list (Leipzig-Jakarta based)
SWADESH_100 = [
    "I", "you", "we", "this", "that", "who", "what", "not", "all", "many",
    "one", "two", "big", "long", "small", "woman", "man", "person", "fish", "bird",
    "dog", "louse", "tree", "seed", "leaf", "root", "bark", "skin", "flesh", "blood",
    "bone", "grease", "egg", "horn", "tail", "feather", "hair", "head", "ear", "eye",
    "nose", "mouth", "tooth", "tongue", "claw", "foot", "knee", "hand", "belly", "neck",
    "breast", "heart", "liver", "drink", "eat", "bite", "see", "hear", "know", "sleep",
    "die", "kill", "swim", "fly", "walk", "come", "lie", "sit", "stand", "give",
    "say", "sun", "moon", "star", "water", "rain", "stone", "sand", "earth", "cloud",
    "smoke", "fire", "ash", "burn", "path", "mountain", "red", "green", "yellow", "white",
    "black", "night", "hot", "cold", "full", "new", "good", "round", "dry", "name"
]

# Swadesh 207 list (extended)
SWADESH_207 = SWADESH_100 + [
    "he", "she", "it", "they", "other", "some", "few", "here", "there", "near",
    "far", "right", "left", "at", "in", "with", "and", "if", "because", "no",
    "yes", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "hundred",
    "wide", "thick", "heavy", "narrow", "thin", "short", "old", "young", "bad", "rotten",
    "dirty", "straight", "wet", "correct", "dull", "smooth", "sharp", "warm",
    "snake", "worm", "back", "arm", "wing", "stomach", "guts", "breathe", "smell", "fear",
    "scratch", "cut", "split", "stab", "sew", "count", "think", "sing", "play", "float",
    "flow", "freeze", "swell", "pull", "push", "throw", "tie", "hold", "squeeze", "rub",
    "wash", "wipe", "turn", "fall", "hunt", "fight", "hit", "dig", "suck", "blow",
    "laugh", "vomit", "when", "where", "how", "year", "day", "wind", "fog", "sky",
    "sea", "river", "lake", "salt", "dust", "ice", "snow", "rope", "husband", "wife",
    "mother", "father", "animal", "flower", "grass", "meat"
]

# 912+ word target list organized by category
TARGET_CATEGORIES = {
    "The Physical World": [
        "air", "area/region", "ash", "cave", "cloud", "earth", "fire", "flame", "fog", 
        "forest/woods", "darkness", "dust", "earth (land)", "gulf/bay", "ice", "island", 
        "lake", "light", "light/kindle/ignite", "lightning", "mainland", "match", "mist", 
        "moon", "mountain", "mud", "plain/field", "rain", "river", "sand", "sea", 
        "shade/shadow", "shore", "sky", "smoke", "snow", "spring/well", "star", "stone", 
        "sun", "thunder", "valley", "water", "wave", "weather", "wind", "world", "wood"
    ],
    "Kinship": [
        "ancestors", "aunt", "boy", "brother", "child", "cousin", "daughter", 
        "daughter-in-law", "descendants", "family", "father", "father-in-law", 
        "female (human)", "girl", "granddaughter", "grandfather", "grandmother", 
        "grandson", "husband", "infant/baby", "male (human)", "man", "marry", "mother", 
        "mother-in-law", "nephew", "niece", "offspring", "orphan", "parents", "person",
        "relatives", "sister", "son-in-law", "stepdaughter", "stepfather", "stepmother", 
        "stepson", "uncle", "widow", "woman"
    ],
    "Animals": [
        "animal", "ass/donkey", "bear", "bee", "bird", "camel", "cat", "chicken", "cow", 
        "deer", "dog", "duck", "elephant", "female (animal)", "fish", "fly", "fox", 
        "goat", "goose", "herdsman", "horse", "insect", "lion", "livestock", "louse",
        "male (animal)", "manure", "monkey", "mouse/rat", "mule", "pasture", "pig", 
        "sheep", "snake", "stable", "wing", "wolf", "worm"
    ],
    "The Body": [
        "arm", "back", "bald", "beard", "beget", "bite", "blind", "blood", "body", 
        "bone", "brain", "break wind", "breast", "breathe", "bury", "buttocks", "cheek", 
        "chest", "chin", "claw", "conceive", "corpse", "cough", "cure", "deaf", 
        "defecate", "die", "dream", "ear", "elbow", "eye", "eyebrow", "eyelash", 
        "eyelid", "eyeball", "face", "feather", "finger", "flesh", "foot", "forehead", 
        "genitals", "grave", "hair", "hand", "have sexual intercourse", "head", "heart", 
        "horn", "intoxicated", "jaw", "joint", "kill", "knee", "lame", "lazy", "leg", 
        "lick", "life", "lip", "live", "liver", "medicine", "mouth", "mute", "naked", 
        "navel", "neck", "nose", "perspire", "physician", "poison", "pregnant", "rest", 
        "shoulder", "sick", "skin", "skull", "sleep", "sneeze", "spit", "stomach", 
        "strong", "tail", "throat", "thumb", "tired", "toe", "tongue", "tooth", "udder", 
        "urinate", "vomit", "wake up", "weak", "well/health", "womb", "wound", "yawn"
    ],
    "Food and Drink": [
        "bake", "beer", "boil", "bread", "breakfast", "butter", "cheese", "cook", 
        "dinner", "dough", "drink", "drunk", "eat", "egg", "fat/grease", "feast", 
        "flour", "food", "fruit", "grape", "grind", "honey", "hunger", "hungry", 
        "juice", "kitchen", "knead", "lunch", "meal", "meat", "milk", "nut", "oil", 
        "olive", "onion", "oven", "pepper", "pour", "roast", "salt", "slice", "smell", 
        "sour", "spice", "stir", "sugar", "supper", "sweet", "taste", "thirst", 
        "thirsty", "vegetable", "vinegar", "wheat", "wine"
    ],
    "Clothing and Grooming": [
        "apron", "barefoot", "bathe", "belt", "boot", "bracelet", "braid", "brooch", 
        "buckle", "button", "cap", "cloak", "cloth", "clothe", "clothing", "coat", 
        "collar", "comb", "dress", "dye", "garment", "glove", "gown", "hat", "helmet", 
        "hood", "jewel", "linen", "necklace", "needle", "pants", "pin", "pocket", 
        "ring", "robe", "sandal", "scissors", "sew", "shirt", "shoe", "silk", "sleeve", 
        "sock", "spin", "thread", "weave", "wool"
    ],
    "The House": [
        "bed", "blanket", "broom", "building", "ceiling", "chair", "chest", "chimney", 
        "door", "fence", "floor", "furniture", "gate", "hearth", "house", "hut", "key", 
        "lock", "pillow", "roof", "room", "stairs", "table", "village", "wall", "window"
    ],
    "Agriculture and Vegetation": [
        "acre", "bark", "branch", "bud", "crop", "cultivate", "dig", "farm", "farmer", 
        "field", "flower", "fruit", "garden", "grain", "grass", "grow", "harvest", 
        "hay", "leaf", "meadow", "mow", "orchard", "pick", "plant", "plow", "reap", 
        "ripe", "root", "seed", "sow", "sprout", "straw", "thorn", "thresh", "tree", 
        "vegetable", "vine", "weed", "wheat", "wood", "forest", "bush", "log", "stick"
    ],
    "Basic Actions and Technology": [
        "axe", "bellows", "bend", "blacksmith", "blade", "blunt", "bow", "break", 
        "build", "carpenter", "carry", "chain", "charcoal", "chisel", "clay", "copper", 
        "craft", "create", "crush", "cut", "drill", "file", "fold", "forge", "gold", 
        "hammer", "handle", "harden", "hoe", "hook", "iron", "kiln", "knife", "ladder", 
        "lead", "make", "melt", "mold", "nail", "pick", "pliers", "poke", "pot", 
        "potter", "press", "pump", "rake", "saw", "scrape", "sharpen", "silver", 
        "smith", "spade", "steel", "strike", "sword", "tin", "tool", "tongs", "wedge", 
        "wheel", "wire", "work"
    ],
    "Motion": [
        "arrive", "bring", "carry", "chase", "climb", "come", "crawl", "creep", "dance", 
        "descend", "drag", "drive", "enter", "escape", "fall", "flee", "flow", "fly", 
        "follow", "gallop", "go", "hang", "hurry", "jump", "kick", "kneel", "lead", 
        "leap", "leave", "lift", "limp", "lower", "move", "pull", "push", "put", 
        "raise", "reach", "return", "ride", "rise", "roll", "run", "send", "shake", 
        "sink", "sit", "slide", "slip", "stand", "step", "stop", "swim", "swing", 
        "throw", "travel", "turn", "twist", "wade", "walk", "wander"
    ],
    "Possession": [
        "barter", "beggar", "borrow", "buy", "change", "cheap", "cost", "debt", "earn", 
        "exchange", "expensive", "free", "gain", "get", "give", "gold", "goods", "guard", 
        "have", "hide", "keep", "lack", "lend", "load", "lose", "market", "merchant", 
        "money", "owe", "own", "pay", "poor", "possess", "price", "property", "receive", 
        "rich", "rob", "save", "sell", "share", "silver", "steal", "store", "take", 
        "thief", "trade", "wealth", "weigh"
    ],
    "Spatial Relations": [
        "above", "across", "after", "against", "along", "among", "around", "at", "back", 
        "before", "behind", "below", "beneath", "beside", "between", "beyond", "bottom", 
        "by", "center", "close", "corner", "deep", "direction", "distance", "down", 
        "east", "edge", "end", "far", "flat", "forward", "front", "here", "high", 
        "in", "inside", "left", "low", "middle", "narrow", "near", "north", "on", 
        "opposite", "out", "outside", "over", "place", "right", "side", "south", 
        "straight", "surface", "there", "through", "to", "top", "toward", "under", 
        "up", "west", "where", "wide"
    ],
    "Quantity": [
        "all", "both", "count", "double", "each", "empty", "enough", "equal", "every", 
        "few", "first", "full", "group", "grow", "half", "heap", "heavy", "increase", 
        "last", "least", "less", "light", "little", "long", "many", "measure", "more", 
        "most", "much", "none", "number", "only", "pair", "part", "piece", "pile", 
        "plenty", "second", "several", "short", "single", "size", "some", "tall", 
        "thick", "thin", "total", "whole", "zero", "one", "two", "three", "four", 
        "five", "six", "seven", "eight", "nine", "ten", "hundred", "thousand"
    ],
    "Time": [
        "after", "afternoon", "age", "always", "ancient", "annual", "autumn", "before", 
        "begin", "birthday", "calendar", "century", "date", "dawn", "day", "during", 
        "early", "end", "era", "evening", "ever", "finish", "first", "forever", 
        "former", "frequent", "future", "generation", "hour", "immediate", "instant", 
        "last", "late", "later", "long", "midnight", "minute", "moment", "month", 
        "morning", "never", "new", "next", "night", "noon", "now", "occasion", "often", 
        "old", "once", "past", "present", "previous", "quick", "rare", "recent", 
        "season", "second", "seldom", "slow", "sometimes", "soon", "spring", "start", 
        "still", "sudden", "summer", "sunrise", "sunset", "then", "time", "today", 
        "tomorrow", "tonight", "week", "when", "while", "winter", "year", "yesterday", 
        "young", "youth"
    ],
    "Sense Perception": [
        "appear", "beautiful", "bitter", "blind", "blunt", "bright", "clean", "clear", 
        "color", "dark", "deaf", "dim", "dirty", "dull", "feel", "flavor", "fragrant", 
        "hear", "heavy", "hot", "cold", "light", "listen", "look", "loud", "mild", 
        "mute", "noise", "odor", "pain", "pale", "quiet", "rough", "salty", "see", 
        "sense", "sharp", "shine", "show", "silent", "smell", "smooth", "soft", "solid", 
        "sound", "sour", "stink", "sweet", "taste", "thick", "thin", "touch", "ugly", 
        "visible", "warm", "watch", "wet"
    ],
    "Emotions and Values": [
        "admire", "afraid", "amuse", "anger", "angry", "annoy", "anxiety", "ashamed", 
        "bad", "blame", "bold", "bore", "brave", "calm", "careful", "careless", 
        "comfort", "complain", "courage", "coward", "cruel", "cry", "curious", 
        "despair", "disgust", "emotion", "enjoy", "envy", "excite", "fair", "false", 
        "fame", "fault", "fear", "feel", "fierce", "fool", "forgive", "frighten", 
        "glad", "good", "grateful", "greed", "grief", "guilt", "happy", "hate", 
        "honest", "honor", "hope", "humble", "jealous", "joy", "kind", "laugh", 
        "like", "lonely", "love", "loyal", "mercy", "merry", "mourn", "noble", "offend", 
        "patience", "peace", "pity", "please", "pleasure", "praise", "pride", "proud", 
        "regret", "respect", "revenge", "right", "sad", "satisfy", "shame", "shy", 
        "sorrow", "sorry", "suffer", "surprise", "sympathy", "temper", "thank", "true", 
        "trust", "vanity", "weep", "wicked", "wise", "wish", "wonder", "worry", "wrong"
    ],
    "Cognition": [
        "believe", "compare", "consider", "decide", "doubt", "expect", "explain", 
        "forget", "guess", "idea", "ignore", "imagine", "intend", "judge", "know", 
        "knowledge", "learn", "mean", "memory", "mind", "mistake", "notice", "opinion", 
        "perceive", "plan", "prefer", "prove", "purpose", "realize", "reason", 
        "recognize", "remember", "secret", "solve", "suppose", "teach", "think", 
        "thought", "understand", "wisdom", "wise", "wonder"
    ],
    "Speech and Language": [
        "admit", "advise", "agree", "announce", "answer", "argue", "ask", "boast", 
        "call", "claim", "command", "complain", "confess", "conversation", "cry", 
        "curse", "declare", "deny", "describe", "discuss", "exclaim", "explain", 
        "forbid", "gossip", "greet", "insult", "interrupt", "joke", "language", "lie", 
        "mention", "message", "name", "noise", "offer", "order", "permit", "persuade", 
        "praise", "pray", "preach", "promise", "propose", "question", "quote", "read", 
        "refuse", "repeat", "reply", "report", "request", "say", "scold", "scream", 
        "secret", "shout", "shut up", "sign", "silence", "sing", "speak", "speech", 
        "story", "suggest", "swear", "talk", "teach", "tell", "thank", "threaten", 
        "translate", "voice", "warn", "whisper", "word", "write", "yell"
    ],
    "Social and Political Relations": [
        "allow", "army", "attack", "battle", "betray", "capture", "chief", "city", 
        "citizen", "command", "conquer", "country", "defeat", "defend", "empire", 
        "enemy", "execute", "exile", "flag", "foreign", "free", "freedom", "friend", 
        "government", "guard", "guest", "guide", "help", "hero", "invade", "king", 
        "kingdom", "knight", "law", "leader", "lord", "master", "meeting", "messenger", 
        "nation", "neighbor", "noble", "obey", "officer", "palace", "peace", "people", 
        "permit", "power", "prince", "princess", "prison", "prisoner", "protect", 
        "punish", "queen", "rebel", "reign", "revolt", "reward", "rule", "ruler", 
        "servant", "serve", "shield", "slave", "soldier", "spy", "stranger", "subject", 
        "surrender", "throne", "tower", "traitor", "treason", "treaty", "tribe", 
        "troop", "victory", "village", "war", "warrior", "weapon"
    ],
    "Warfare and Hunting": [
        "aim", "ambush", "archer", "armor", "army", "arrow", "attack", "battle", "bow", 
        "capture", "conquer", "defend", "enemy", "fight", "flee", "fortress", "guard", 
        "helmet", "hide", "hit", "hunt", "hunter", "kill", "net", "peace", "pursue", 
        "quiver", "retreat", "scout", "shield", "shoot", "siege", "slay", "soldier", 
        "spear", "spy", "stab", "strike", "surrender", "sword", "target", "trap", 
        "troop", "victory", "war", "warrior", "weapon", "wound"
    ],
    "Law": [
        "accuse", "arrest", "authority", "ban", "blame", "court", "crime", "criminal", 
        "custom", "debt", "deserve", "duty", "evidence", "execute", "fault", "fine", 
        "forbid", "forgive", "free", "guilty", "heir", "inherit", "innocent", "judge", 
        "jury", "justice", "law", "lawyer", "legal", "marriage", "oath", "obey", 
        "offense", "order", "own", "permit", "prison", "prisoner", "prohibit", "proof", 
        "property", "prove", "punish", "release", "right", "rule", "sentence", "sue", 
        "swear", "testify", "thief", "trial", "verdict", "victim", "violate", "witness", 
        "wrong"
    ],
    "Religion and Belief": [
        "angel", "believe", "bless", "bury", "ceremony", "church", "curse", "demon", 
        "devil", "divine", "faith", "fast", "feast", "funeral", "ghost", "god", 
        "goddess", "grace", "grave", "heaven", "hell", "holy", "idol", "magic", 
        "miracle", "monk", "oracle", "paradise", "pilgrim", "pray", "prayer", "preach", 
        "priest", "prophet", "religion", "sacred", "sacrifice", "saint", "save", "sin", 
        "soul", "spirit", "temple", "tomb", "virgin", "witch", "worship"
    ],
    "Question Words": [
        "how", "what", "when", "where", "which", "who", "whom", "whose", "why"
    ]
}

def load_dictionary(dict_path):
    """Load the Nyrakai dictionary."""
    with open(dict_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('words', [])

def get_unique_word_count(dictionary_words):
    """Get count of unique English words (ignoring gender variants)."""
    unique = set(w['english'].lower().strip() for w in dictionary_words)
    return len(unique)

def normalize_word(word):
    """Normalize a word for comparison."""
    word = word.lower().strip()
    # Handle common variations
    word = word.replace('oil/grease', 'grease').replace('oil', 'grease')
    word = word.replace('he/she/it', 'he')
    word = word.replace('like/love', 'like')
    return word

def check_coverage(dictionary_words, target_list):
    """Check what percentage of target list is covered."""
    dict_english = set()
    dict_base_words = set()  # Store base words without parenthetical qualifiers
    
    for w in dictionary_words:
        eng = w['english'].lower().strip()
        dict_english.add(eng)
        
        # Add variations for slash-separated words
        if '/' in eng:
            for part in eng.split('/'):
                dict_english.add(part.strip())
                dict_base_words.add(part.strip())
        
        # Extract base word from parenthetical entries like "we (masculine/mixed)"
        if '(' in eng:
            base = eng.split('(')[0].strip()
            dict_base_words.add(base)
    
    have = []
    missing = []
    
    for word in target_list:
        word_lower = word.lower().strip()
        found = False
        
        # Exact match
        if word_lower in dict_english:
            found = True
        # Base word match (for pronouns like "we" matching "we (masculine/mixed)")
        elif word_lower in dict_base_words:
            found = True
        # Target has slash - check variants
        elif '/' in word:
            for part in word.split('/'):
                part_clean = part.strip().lower()
                if part_clean in dict_english or part_clean in dict_base_words:
                    found = True
                    break
        # Target has parenthetical - try base word
        elif '(' in word:
            base = word.split('(')[0].strip().lower()
            if base in dict_english or base in dict_base_words:
                found = True
        
        if found:
            have.append(word)
        else:
            missing.append(word)
    
    return have, missing

def main():
    parser = argparse.ArgumentParser(description='Nyrakai Vocabulary Progress Tracker')
    parser.add_argument('--summary', action='store_true', help='Show quick summary only')
    parser.add_argument('--missing', choices=[
        'swadesh100', 'swadesh207', 'all',
        'wold', 'concepticon', 'northeuralex', 'zompist'
    ], help='Show missing words for a list')
    parser.add_argument('--lists', action='store_true', help='Show all available word lists')
    parser.add_argument('--category', type=str, help='Show specific category progress')
    parser.add_argument('--export', action='store_true', help='Export to markdown file')
    args = parser.parse_args()
    
    # Show available lists
    if args.lists:
        print("📚 Available Word Lists")
        print("=" * 60)
        lists_info = [
            ("swadesh100", "Swadesh 100", 100, "Core universal concepts"),
            ("swadesh207", "Swadesh 207", 207, "Extended basic vocabulary"),
            ("wold", "WOLD", len(WOLD), "World Loanword Database (1460+ meanings)"),
            ("concepticon", "Concepticon", len(CONCEPTICON), "Cross-linguistic concepts (4000+)"),
            ("northeuralex", "NorthEuraLex", len(NORTHEURALEX), "Northern Eurasian lexicon (1000+)"),
            ("zompist", "Zompist", len(ZOMPIST), "Conlanger's vocabulary (2000+)"),
        ]
        for key, name, count, desc in lists_info:
            status = "✅" if count > 0 else "❌"
            print(f"  {status} {name:<15} ({count:>4} words) - {desc}")
        return
    
    # Find dictionary
    script_dir = Path(__file__).parent
    dict_path = script_dir / 'nyrakai-dictionary.json'
    
    if not dict_path.exists():
        print(f"Error: Dictionary not found at {dict_path}")
        return
    
    words = load_dictionary(dict_path)
    total_words = len(words)
    unique_words = get_unique_word_count(words)
    
    # Check Swadesh coverage
    sw100_have, sw100_missing = check_coverage(words, SWADESH_100)
    sw207_have, sw207_missing = check_coverage(words, SWADESH_207)
    
    # Check extended list coverage
    wold_have, wold_missing = check_coverage(words, WOLD) if WOLD else ([], [])
    concept_have, concept_missing = check_coverage(words, CONCEPTICON) if CONCEPTICON else ([], [])
    northeur_have, northeur_missing = check_coverage(words, NORTHEURALEX) if NORTHEURALEX else ([], [])
    zompist_have, zompist_missing = check_coverage(words, ZOMPIST) if ZOMPIST else ([], [])
    
    # Check category coverage
    all_target_words = []
    category_stats = {}
    for cat_name, cat_words in TARGET_CATEGORIES.items():
        have, missing = check_coverage(words, cat_words)
        category_stats[cat_name] = {
            'total': len(cat_words),
            'have': len(have),
            'missing': len(missing),
            'have_words': have,
            'missing_words': missing
        }
        all_target_words.extend(cat_words)
    
    # Deduplicate target words
    all_target_words = list(set(all_target_words))
    all_have, all_missing = check_coverage(words, all_target_words)
    
    # Output
    if args.summary:
        print(f"📊 Nyrakai Vocabulary Progress")
        print(f"=" * 55)
        print(f"Unique Words:      {unique_words} ({total_words} entries)")
        print(f"─" * 55)
        print(f"Swadesh 100:       {len(sw100_have):>3}/100   ({len(sw100_have)}%)")
        print(f"Swadesh 207:       {len(sw207_have):>3}/207   ({len(sw207_have)*100//207}%)")
        print(f"Target 912+:       {len(all_have):>3}/{len(all_target_words):<4}  ({len(all_have)*100//len(all_target_words)}%)")
        if EXTENDED_LISTS_AVAILABLE:
            print(f"─" * 55)
            print(f"WOLD:              {len(wold_have):>3}/{len(WOLD):<4}  ({len(wold_have)*100//max(len(WOLD),1)}%)")
            print(f"Concepticon:       {len(concept_have):>3}/{len(CONCEPTICON):<4}  ({len(concept_have)*100//max(len(CONCEPTICON),1)}%)")
            print(f"NorthEuraLex:      {len(northeur_have):>3}/{len(NORTHEURALEX):<4}  ({len(northeur_have)*100//max(len(NORTHEURALEX),1)}%)")
            print(f"Zompist:           {len(zompist_have):>3}/{len(ZOMPIST):<4}  ({len(zompist_have)*100//max(len(ZOMPIST),1)}%)")
        return
    
    if args.missing:
        missing_map = {
            'swadesh100': ('Swadesh 100', sw100_missing),
            'swadesh207': ('Swadesh 207', sw207_missing),
            'wold': ('WOLD', wold_missing),
            'concepticon': ('Concepticon', concept_missing),
            'northeuralex': ('NorthEuraLex', northeur_missing),
            'zompist': ('Zompist', zompist_missing),
            'all': ('Target List', all_missing),
        }
        
        if args.missing in missing_map:
            name, missing = missing_map[args.missing]
            print(f"❌ Missing from {name} ({len(missing)} words):")
            for w in sorted(missing)[:100]:  # Limit to 100
                print(f"  - {w}")
            if len(missing) > 100:
                print(f"  ... and {len(missing) - 100} more")
        return
    
    if args.category:
        cat = args.category
        if cat in category_stats:
            stats = category_stats[cat]
            print(f"📂 {cat}")
            print(f"Progress: {stats['have']}/{stats['total']} ({stats['have']*100//stats['total']}%)")
            print(f"\n✅ Have ({len(stats['have_words'])}):")
            for w in sorted(stats['have_words']):
                print(f"  - {w}")
            print(f"\n❌ Need ({len(stats['missing_words'])}):")
            for w in sorted(stats['missing_words']):
                print(f"  - {w}")
        else:
            print(f"Unknown category: {cat}")
            print(f"Available: {', '.join(TARGET_CATEGORIES.keys())}")
        return
    
    # Full report
    print(f"╔{'═'*60}╗")
    print(f"║{'📊 NYRAKAI VOCABULARY TRACKER':^60}║")
    print(f"╠{'═'*60}╣")
    print(f"║ Unique Words: {unique_words:>10} ({total_words} entries){' '*(29-len(str(total_words)))}║")
    print(f"╠{'═'*60}╣")
    print(f"║{'CORE LISTS':^60}║")
    print(f"╟{'─'*60}╢")
    print(f"║ Swadesh 100:     {len(sw100_have):>3}/100  {'█'*int(len(sw100_have)/5):<20} {len(sw100_have):>3}%       ║")
    print(f"║ Swadesh 207:     {len(sw207_have):>3}/207  {'█'*int(len(sw207_have)/10):<20} {len(sw207_have)*100//207:>3}%       ║")
    print(f"║ Target 912+:     {len(all_have):>3}/{len(all_target_words):<4} {'█'*int(len(all_have)/50):<20} {len(all_have)*100//len(all_target_words):>3}%       ║")
    
    if EXTENDED_LISTS_AVAILABLE:
        print(f"╠{'═'*60}╣")
        print(f"║{'EXTENDED LISTS':^60}║")
        print(f"╟{'─'*60}╢")
        
        def bar(have, total):
            pct = have * 100 // max(total, 1)
            return '█' * (pct // 5) + '░' * (20 - pct // 5)
        
        print(f"║ WOLD:            {len(wold_have):>3}/{len(WOLD):<4} {bar(len(wold_have), len(WOLD))} {len(wold_have)*100//max(len(WOLD),1):>3}%       ║")
        print(f"║ Concepticon:     {len(concept_have):>3}/{len(CONCEPTICON):<4} {bar(len(concept_have), len(CONCEPTICON))} {len(concept_have)*100//max(len(CONCEPTICON),1):>3}%       ║")
        print(f"║ NorthEuraLex:    {len(northeur_have):>3}/{len(NORTHEURALEX):<4} {bar(len(northeur_have), len(NORTHEURALEX))} {len(northeur_have)*100//max(len(NORTHEURALEX),1):>3}%       ║")
        print(f"║ Zompist:         {len(zompist_have):>3}/{len(ZOMPIST):<4} {bar(len(zompist_have), len(ZOMPIST))} {len(zompist_have)*100//max(len(ZOMPIST),1):>3}%       ║")
    
    print(f"╠{'═'*60}╣")
    print(f"║{'CATEGORY BREAKDOWN':^60}║")
    print(f"╟{'─'*60}╢")
    
    for cat_name, stats in sorted(category_stats.items(), key=lambda x: -x[1]['have']/max(x[1]['total'],1)):
        pct = stats['have']*100//max(stats['total'],1)
        bar = '█'*int(pct/10) + '░'*(10-int(pct/10))
        print(f"║ {cat_name[:30]:<30} {stats['have']:>3}/{stats['total']:<3} {bar} {pct:>3}%   ║")
    
    print(f"╚{'═'*60}╝")
    
    if args.export:
        export_markdown(total_words, sw100_have, sw100_missing, sw207_have, sw207_missing, 
                       all_have, all_missing, category_stats, all_target_words)

def export_markdown(total, sw100_have, sw100_missing, sw207_have, sw207_missing,
                   all_have, all_missing, category_stats, all_target):
    """Export progress to markdown file."""
    from datetime import datetime
    
    md = f"""# Nyrakai Vocabulary Tracker

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Total Words:** {total}

## Progress Summary

| List | Have | Total | Progress |
|------|------|-------|----------|
| Swadesh 100 | {len(sw100_have)} | 100 | {len(sw100_have)}% |
| Swadesh 207 | {len(sw207_have)} | 207 | {len(sw207_have)*100//207}% |
| Target 912+ | {len(all_have)} | {len(all_target)} | {len(all_have)*100//len(all_target)}% |

## Category Breakdown

| Category | Have | Total | Progress |
|----------|------|-------|----------|
"""
    for cat_name, stats in sorted(category_stats.items()):
        pct = stats['have']*100//max(stats['total'],1)
        md += f"| {cat_name} | {stats['have']} | {stats['total']} | {pct}% |\n"
    
    md += f"""
## Missing from Swadesh 100 ({len(sw100_missing)} words)

{', '.join(sorted(sw100_missing))}

## Missing from Swadesh 207 ({len(sw207_missing)} words)

{', '.join(sorted(sw207_missing))}
"""
    
    output_path = Path(__file__).parent.parent / 'VOCAB_PROGRESS.md'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(md)
    print(f"\n✅ Exported to {output_path}")

if __name__ == '__main__':
    main()
