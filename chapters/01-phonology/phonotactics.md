# Phonotactics

Phonotactics describes the rules for how sounds can combine in Nyrakai. These rules give the language its distinctive rhythm and ensure all words "feel" authentically Nyrakai.

---

## Syllable Structure

Nyrakai follows a strict syllable template:

```
(C)(C)V(')(C)
```

Where:
- **(C)** = Optional consonant
- **V** = Required vowel (including diphthongs)
- **(')** = Optional glottal marker
- Parentheses indicate optional elements

---

## Valid Syllable Patterns

| Pattern | Example | Word |
|---------|---------|------|
| V | a | (rare) |
| CV | kæ | kæ (tongue) |
| CVC | tal | tal (say) |
| CCV | hro | hro (white) |
| CCVC | drōm | drōm (long) |
| CV'C | n'æ | n'æ (true) |

---

## Onset Rules (Beginning of Syllable)

### Single Consonant
Any consonant except the glottal marker (') can begin a syllable.

### Consonant Clusters
When two consonants begin a syllable, they must follow these rules:

**Allowed first consonants (C1):**
All consonants except '

**Forbidden second consonants (C2):**
- Ejectives (k^, p^, t^)
- Affricates š, ƨ
- Velar nasal ñ

**Valid cluster combinations:**
| C1 | Allowed C2 |
|----|-----------|
| d | r, w |
| f | r, l |
| g | r, l, w |
| h | r |
| k | r, l, w |
| p | r, l |
| s | r, l, w, n, m, k, p, t |
| t | r, w |
| z | r, w, l |
| ț | r |

---

## Coda Rules (End of Syllable)

A syllable can end with:
- No consonant (open syllable): CV, CCV
- One consonant: CVC, CCVC
- Glottal marker before consonant: CV'C

**Forbidden in coda position:**
- The glottal marker (') alone at word end

---

## The Glottal Marker (')

The apostrophe represents a schwa + glottal stop (/əʔ/) and has special rules:

✅ **Allowed:**
- Between consonant and vowel: n'æ, r'ōk
- After vowel, before consonant: kre'net

❌ **Forbidden:**
- At the start of a syllable
- At the end of a word

---

## Forbidden Sequences

These specific sound combinations are **phonotactically invalid** in Nyrakai:

| Sequence | Rule | Reason |
|----------|------|--------|
| **^'** | Ejective + Glottal | The ejective release (^) cannot immediately precede a glottal catch ('). Creates an unpronounceable articulatory conflict. |
| **'a** | Glottal + 'a' | The glottal marker (') already contains schwa /əʔ/. Following with 'a' creates awkward /əʔa/ sequence. Use **'æ** or **'e** instead. |

### Examples

❌ **Invalid:**
- `k^'el` — ejective k^ cannot precede '
- `n'ara` — glottal ' cannot precede 'a'

✅ **Valid alternatives:**
- `k^el` — remove glottal, or use `k'el`
- `n'æra` — use 'æ instead of 'a
- `n'era` — use 'e instead of 'a

---

## Stress

Stress typically falls on the **root syllable** of a word. In compounds and derived words, the original root retains primary stress.

---

## Examples

| Word | Structure | Breakdown |
|------|-----------|-----------|
| kæ | CV | k + æ |
| tal | CVC | t + a + l |
| n'æra | CV.CV | n'æ + ra |
| ƶōrțal | CVC.CVC | ƶōr + țal |
| Ŧɒñœrek | CCV.CVC.VC | ŧɒ + ñœ + rek |
