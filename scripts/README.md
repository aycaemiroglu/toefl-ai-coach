# Scripts

This directory contains utility scripts for the TOEFL AI Coach project.

## generate_essays.py

Generates a synthetic TOEFL Independent Writing dataset (30 essays: 10 prompts × 3 proficiency levels).

### Features

- ✅ Generates essays at B1, B2, and C1 proficiency levels
- ✅ Saves essays as JSON (metadata) and TXT (plain text)
- ✅ Retry logic with exponential backoff for API errors
- ✅ Dry-run mode for testing without API calls
- ✅ Seed-based randomization for style variation
- ✅ Overwrite protection (skip existing files by default)
- ✅ Progress logging and error reporting

### Usage

#### 1. Install Dependencies

```bash
# Activate virtual environment
source .venv/bin/activate

# Install required packages
pip install -r requirements.txt
```

#### 2. Set Environment Variables

Ensure your `.env` file contains:

```bash
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant  # Optional, defaults to llama-3.1-8b-instant
```

#### 3. Run the Script

**Basic usage (generate all 30 essays):**
```bash
python scripts/generate_essays.py
```

**Dry-run (test without API calls):**
```bash
python scripts/generate_essays.py --dry-run
```

**With custom seed for reproducible style variation:**
```bash
python scripts/generate_essays.py --seed 42
```

**Overwrite existing files:**
```bash
python scripts/generate_essays.py --overwrite
```

**Custom temperature:**
```bash
python scripts/generate_essays.py --temperature 0.9
```

**Custom model:**
```bash
python scripts/generate_essays.py --model llama-3.3-70b-versatile
```

**Custom output directory:**
```bash
python scripts/generate_essays.py --output-dir data/my_essays
```

### Output Format

Each essay is saved as two files:

1. **JSON file** (`{prompt_id}_{level}.json`):
   ```json
   {
     "id": "p01_b1",
     "prompt_id": "p01",
     "level": "B1",
     "prompt": "Do you agree or disagree...",
     "word_target": {"min": 220, "max": 250},
     "word_count": 237,
     "essay": "I strongly agree...",
     "created_at": "2026-02-08T12:34:56.789Z",
     "model": "llama-3.1-8b-instant"
   }
   ```

2. **TXT file** (`{prompt_id}_{level}.txt`):
   Plain text essay content only.

### Command-Line Options

| Option | Description |
|--------|-------------|
| `--dry-run` | Generate placeholder essays without API calls |
| `--seed INT` | Random seed for style constraint variation |
| `--overwrite` | Overwrite existing files (default: skip) |
| `--temperature FLOAT` | Generation temperature (default: 0.7) |
| `--model STR` | Model name (default: from GROQ_MODEL env or llama-3.1-8b-instant) |
| `--output-dir STR` | Output directory (default: data/essays) |

### Example Output

```
✅ Connected to Groq API (model: llama-3.1-8b-instant)
📁 Output directory: /path/to/toefl-ai-coach/data/essays
🌱 Seed: random
🌡️  Temperature: 0.7

📝 Generating p01_b1... ✅ done (237 words)
📝 Generating p01_b2... ✅ done (265 words)
📝 Generating p01_c1... ✅ done (298 words)
...

============================================================
📊 SUMMARY
============================================================
Total essays: 30
✅ Success: 30
⏭️  Skipped: 0
❌ Errors: 0

✅ Essays saved to: /path/to/toefl-ai-coach/data/essays
```

### Notes

- The script automatically creates the output directory if it doesn't exist.
- Generated essays are ignored by git (see `.gitignore`).
- Word count is calculated automatically and included in JSON metadata.
- Style constraints (stance, example count, rhetorical style) are randomized per essay when using `--seed`.
