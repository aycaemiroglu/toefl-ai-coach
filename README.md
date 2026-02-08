# TOEFL Essay Scorer: Comparing LLM Prompting Strategies

## 🎯 Project Overview

This research project compares different prompting strategies for automated TOEFL essay scoring using Large Language Models (LLMs).

**Research Question:** Which prompting approach achieves highest correlation with human expert ratings?

## 🔬 Methodology

- **Dataset:** 30 TOEFL essays with human ratings
- **Models:** Llama 3.3 70B (via Groq API - free)
- **Strategies Tested:**
  1. Baseline (simple prompt)
  2. Rubric-based (detailed scoring criteria)
  3. Few-shot (with examples)
  4. Chain-of-thought (step-by-step reasoning)

## 📊 Results

[Coming soon after experiments]

## 🛠️ Tech Stack

- Python 3.11
- Groq API (free LLM access)
- Pandas, NumPy, SciPy (data analysis)
- Matplotlib, Seaborn (visualization)

## 🚀 How to Run

### 1. First-time setup (once)

```bash
# Go to project directory
cd toefl-ai-coach

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set API key (creates .env file)
echo "GROQ_API_KEY=your_groq_key_here" > .env
```

The `.env` file should contain only this line (use your key from Groq Console):
```
GROQ_API_KEY=gsk_xxxxxxxxxxxx
```

### 2. Essay scoring (evaluator)

Scores a sample essay with 4 strategies (baseline, rubric, few_shot, chain_of_thought):

```bash
source .venv/bin/activate
python src/evaluator.py
```

### 3. Synthetic essay generation (30 essays)

Generates 10 prompts × 3 levels (B1, B2, C1) = 30 essays; saves JSON and TXT under `data/essays/`:

```bash
source .venv/bin/activate
python scripts/generate_essays.py
```

- **Test without API:** `python scripts/generate_essays.py --dry-run`
- **Fixed seed (reproducible):** `python scripts/generate_essays.py --seed 42`
- **Overwrite existing files:** `python scripts/generate_essays.py --overwrite`

### 4. Later runs

```bash
cd toefl-ai-coach
source .venv/bin/activate
# Then run one of the python commands above
```

## 📧 Contact

Ayça Emiroğlu | ayca.emiroglu23@gmail.com

## 📄 License

MIT License
