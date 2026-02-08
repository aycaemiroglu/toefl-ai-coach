# Test Checklist - generate_essays.py Refactor

## Prerequisites

```bash
# Ensure virtual environment is active
source .venv/bin/activate

# Verify dependencies
pip list | grep -E "(openai|dotenv)"
```

## Test Commands and Expected Outcomes

### 1. Dry-Run Deterministic Seeding Test

**Command:**
```bash
rm -rf data/essays/*
python scripts/generate_essays.py --dry-run --seed 42
```

**Expected:**
- ✅ All 30 essays generated
- ✅ Word counts match target ranges (B1: 220-250, B2: 250-280, C1: 280-320)
- ✅ No API calls made
- ✅ Files created: `data/essays/p01_b1.json`, `p01_b1.txt`, etc.

**Verify determinism:**
```bash
# Run again with same seed
rm -rf data/essays/*
python scripts/generate_essays.py --dry-run --seed 42

# Compare first essay content (should be identical)
cat data/essays/p01_b1.txt
# Run again and compare - content should match
```

**Expected:** Same seed produces identical essay content (metadata timestamps may differ).

---

### 2. Dry-Run Word Count Validation

**Command:**
```bash
python scripts/generate_essays.py --dry-run --seed 100
```

**Verify:**
```bash
# Check word counts in JSON files
python3 -c "
import json
import glob
for f in sorted(glob.glob('data/essays/*.json')):
    d = json.load(open(f))
    level = d['level']
    target_min, target_max = d['word_target']['min'], d['word_target']['max']
    actual = d['word_count']
    status = '✅' if target_min <= actual <= target_max else '❌'
    print(f'{status} {d[\"id\"]}: {actual} words (target: {target_min}-{target_max})')
"
```

**Expected:** All essays show ✅ with word counts within their level's range.

---

### 3. Overwrite Protection Test

**Command:**
```bash
# Generate once
python scripts/generate_essays.py --dry-run --seed 42

# Try to generate again (should skip)
python scripts/generate_essays.py --dry-run --seed 999
```

**Expected:**
- ✅ First run: "✅ done" for all essays
- ✅ Second run: "⏭️ skipped (exists)" for all essays
- ✅ Files unchanged (seed 999 not applied)

**With overwrite:**
```bash
python scripts/generate_essays.py --dry-run --seed 999 --overwrite
```

**Expected:** All essays regenerated with new seed.

---

### 4. Max-Tokens CLI Argument Test

**Command:**
```bash
python scripts/generate_essays.py --dry-run --max-tokens 800
```

**Expected:**
- ✅ Output shows "🎯 Max tokens: 800"
- ✅ Script runs successfully (dry-run doesn't use API, but arg is accepted)

**With real API (if available):**
```bash
python scripts/generate_essays.py --max-tokens 600 --seed 42
```

**Expected:** Shorter essays generated (if model respects token limit).

---

### 5. Real API Test (if GROQ_API_KEY is set)

**Command:**
```bash
# Generate one essay to test word range enforcement
python scripts/generate_essays.py --seed 42 --overwrite 2>&1 | head -20
```

**Expected:**
- ✅ API connection successful
- ✅ Essays generated
- ✅ If word count out of range: "⚠️ Word count out of range, retrying with stronger instructions..."
- ✅ Final word counts within ranges

**Verify word range enforcement:**
```bash
# Check all generated essays
python3 -c "
import json
import glob
out_of_range = []
for f in sorted(glob.glob('data/essays/*.json')):
    d = json.load(open(f))
    level = d['level']
    target_min, target_max = d['word_target']['min'], d['word_target']['max']
    actual = d['word_count']
    if not (target_min <= actual <= target_max):
        out_of_range.append(f'{d[\"id\"]}: {actual} (target: {target_min}-{target_max})')
if out_of_range:
    print('❌ Out of range:', out_of_range)
else:
    print('✅ All essays within word range')
"
```

---

### 6. Meta-Text Detection Test (Manual)

**Note:** This requires API calls. If model generates meta-text, should see retry messages.

**Command:**
```bash
python scripts/generate_essays.py --seed 42 --overwrite 2>&1 | grep -i "meta"
```

**Expected:** If meta-text detected: "⚠️ Meta-text detected, retrying..."

---

### 7. Error Handling Test

**Command (without API key):**
```bash
unset GROQ_API_KEY
python scripts/generate_essays.py
```

**Expected:**
- ✅ Clear error: "❌ Error: GROQ_API_KEY not found..."
- ✅ Exit code 1

**Command (dry-run should work without key):**
```bash
unset GROQ_API_KEY
python scripts/generate_essays.py --dry-run
```

**Expected:** ✅ Runs successfully (no API key needed for dry-run).

---

### 8. JSON Schema Validation

**Command:**
```bash
python scripts/generate_essays.py --dry-run --seed 42
python3 -c "
import json
import glob
required_fields = ['id', 'prompt_id', 'level', 'prompt', 'word_target', 'word_count', 'essay', 'created_at', 'model']
for f in glob.glob('data/essays/*.json'):
    d = json.load(open(f))
    missing = [f for f in required_fields if f not in d]
    if missing:
        print(f'❌ {f}: Missing fields: {missing}')
    else:
        print(f'✅ {f}: All fields present')
" | head -5
```

**Expected:** All JSON files have required fields.

---

### 9. Deterministic Seed Formula Verification

**Command:**
```bash
python3 -c "
# Test seed formula
seed_offsets = {'B1': 101, 'B2': 202, 'C1': 303}
base_seed = 42
prompt_idx = 1

for level in ['B1', 'B2', 'C1']:
    essay_seed = base_seed + prompt_idx * 100 + seed_offsets[level]
    print(f'{level}: seed={essay_seed} (base={base_seed} + prompt*100={prompt_idx*100} + offset={seed_offsets[level]})')
"
```

**Expected:** 
- B1: seed=243
- B2: seed=344  
- C1: seed=445

---

### 10. Full Integration Test

**Command:**
```bash
# Clean slate
rm -rf data/essays/*

# Generate with seed
python scripts/generate_essays.py --dry-run --seed 123 --overwrite

# Verify all files exist
ls data/essays/*.json | wc -l  # Should be 30
ls data/essays/*.txt | wc -l  # Should be 30

# Verify determinism: regenerate and compare
python scripts/generate_essays.py --dry-run --seed 123 --overwrite
# Compare a few files - content should match
```

**Expected:** ✅ All 30 essays generated, deterministic with same seed.

---

## Quick Smoke Test (All-in-One)

```bash
# Clean and test
rm -rf data/essays/*
python scripts/generate_essays.py --dry-run --seed 42 --max-tokens 1000

# Verify
echo "Files generated: $(ls data/essays/*.json 2>/dev/null | wc -l | tr -d ' ')/30"
echo "Word count check:"
python3 -c "
import json, glob
for f in sorted(glob.glob('data/essays/*.json'))[:5]:
    d = json.load(open(f))
    print(f\"  {d['id']}: {d['word_count']} words (target: {d['word_target']['min']}-{d['word_target']['max']})\")
"
```

**Expected:** ✅ 30 files, word counts within ranges.
