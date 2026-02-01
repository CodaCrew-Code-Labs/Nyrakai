# 🔍 NYRAKAI DICTIONARY AUDIT REPORT
Generated: 2026-02-01 12:21

## 📊 SUMMARY

- **Total words:** 297
- **Root words:** 268
- **Derived words:** 29

### Issues Found

| Issue | Count | Severity |
|-------|-------|----------|
| Phonotactic errors | 0 | ✅ None |
| Duplicate Nyrakai words | 3 | 🔴 High |
| Domain misalignment | 20 | 🟡 Medium |
| Similar pairs (dist=1) | 408 | 🟢 Acceptable |
| Missing optional fields | 17 | 🟢 Low |

## 🔴 DUPLICATES (Action Required)

- **r'ōk** = die, death
- **țræn** = person, human
- **țōr** = law, prisoner

*These need disambiguation - same Nyrakai word for different meanings.*

## 🟡 DOMAIN MISALIGNMENT

Words where onset doesn't match category's expected domain:

### Verbs needing attention:

| Word | English | Onset | Has | Needs |
|------|---------|-------|-----|-------|
| skōr | scratch | s- | body | action |
| kwīr | squeeze | kw- | grammar | action |
| kæršo | laugh | k- | action | emotion |
| kɛlæ | play | k- | action | emotion |
| lōm | lie | l- | body | action |
| prōn | pull | pr- | abstract | action |
| swōr | swell | sw- | action | body |
| pūl | vomit | p- | action | body |

### Time words using h- (celestial):

These are actually **semantically consistent** - time is tied to celestial cycles!
Consider updating sound_map.py to add 'time' domain to h- onset.

- raț (night)
- hræ (day)
- hōț (morning)
- hæț (evening)
- hūț (year)
- hōm (month)
- hēr (week)
- hīñ (now)
- hæl (tomorrow)
- hīk (yesterday)
- hōl (old)
- hæn (young)

## 📝 RECOMMENDATIONS

### 1. Fix Duplicates (Priority: HIGH)
```
r'ōk = die/death  → Keep as noun/verb polysemy (common in languages)
țræn = person/human  → Merge entries (synonyms)
țōr = law/prisoner  → NEEDS FIX - different meanings!
```

### 2. Update Sound Map (Priority: MEDIUM)
Add 'time' domain to these onsets in sound_map.py:
- `h-` → add 'time' (for celestial-time connection)
- `sn-` already has 'time'

### 3. Similarity is OK (Priority: LOW)
408 similar pairs is acceptable for a monosyllabic language.
Context and grammar will disambiguate.
