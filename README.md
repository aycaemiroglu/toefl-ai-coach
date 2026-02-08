# TOEFL Essay Scorer: Comparing LLM Prompting Strategies

## 🎯 Project Overview

This research project compares different prompting strategies for automated TOEFL essay scoring using Large Language Models (LLMs).

**Research Question:** Which prompting approach achieves highest correlation with human expert ratings?

## 🔬 Methodology

- **Dataset:** 30 TOEFL essays with human ratings
- **Models:** Llama 3.1 70B (via Groq API - free)
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

```bash
# Setup
pip install -r requirements.txt

# Configure API key
echo "GROQ_API_KEY=your_key_here" > .env

# Run evaluator
python src/evaluator.py
```

## 📧 Contact

Ayça Emiroğlu | ayca.emiroglu23@gmail.com

## 📄 License

MIT License
