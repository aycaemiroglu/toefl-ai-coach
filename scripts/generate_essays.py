#!/usr/bin/env python3
"""
Synthetic TOEFL Essay Dataset Generator

Generates 30 TOEFL Independent Writing essays (10 prompts × 3 proficiency levels)
using Groq API via OpenAI-compatible interface.

Author: Ayça Emiroğlu
Date: February 2026
"""

import argparse
import json
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

from dotenv import load_dotenv
from openai import OpenAI
import openai

# Load environment variables
load_dotenv()

# TOEFL Independent Writing Prompts (10 prompts)
TOEFL_PROMPTS = [
    "Do you agree or disagree that modern technology makes people's lives easier?",
    "Do the advantages of studying abroad outweigh the disadvantages?",
    "What are the main causes of stress in modern society, and what effects does stress have on people's lives?",
    "Some people prefer to work in a large company, while others prefer to work in a small company. Which do you prefer and why?",
    "Do you agree or disagree that people today have less free time than people did in the past?",
    "Which is more important for a successful life: intelligence or hard work?",
    "Do you agree or disagree that students should be required to take physical education classes at university?",
    "Has social media had a more positive or more negative effect on communication between people?",
    "Do you think it is better to live alone or with roommates? Explain your opinion.",
    "Do you agree or disagree that governments should spend more money on public transportation rather than building new roads?",
]

# Proficiency level specifications
LEVEL_SPECS = {
    "B1": {
        "word_range": (220, 250),
        "description": "Intermediate level: 220-250 words, simple structures, limited vocabulary, noticeable grammar mistakes typical of intermediate learners, but still coherent.",
        "style_hints": [
            "Use simple sentence structures",
            "Include some common grammar mistakes (subject-verb agreement, articles)",
            "Use basic vocabulary",
            "Keep paragraphs short and simple",
        ],
        "seed_offset": 101,  # Fixed offset for deterministic seeding
    },
    "B2": {
        "word_range": (250, 280),
        "description": "Upper-intermediate level: 250-280 words, mostly correct grammar, some minor mistakes, moderate vocabulary, clearer paragraphing.",
        "style_hints": [
            "Use varied sentence structures",
            "Include occasional minor grammar mistakes",
            "Use moderate vocabulary with some advanced words",
            "Clear paragraph structure with transitions",
        ],
        "seed_offset": 202,  # Fixed offset for deterministic seeding
    },
    "C1": {
        "word_range": (280, 320),
        "description": "Advanced level: 280-320 words, advanced vocabulary, complex sentences, very few mistakes, strong coherence and transitions.",
        "style_hints": [
            "Use complex sentence structures",
            "Minimal grammar mistakes",
            "Use sophisticated vocabulary",
            "Strong coherence with advanced transitions",
        ],
        "seed_offset": 303,  # Fixed offset for deterministic seeding
    },
}

# Style constraint variants (for seed-based randomization)
STANCE_OPTIONS = ["agree", "disagree", "balanced"]
EXAMPLE_COUNTS = {"B1": [1, 2], "B2": [2, 3], "C1": [2, 3, 4]}
RHETORICAL_STYLES = ["direct", "analytical", "persuasive", "narrative"]


def count_words(text: str) -> int:
    """Count words in text (simple whitespace-based)."""
    return len(text.split())


def get_essay_seed(base_seed: int, prompt_idx: int, level: str) -> int:
    """
    Generate deterministic seed for a specific essay.
    
    Formula: base_seed + prompt_idx * 100 + level_offset
    This ensures same base_seed produces same style constraints per essay.
    """
    level_offset = LEVEL_SPECS[level]["seed_offset"]
    return base_seed + prompt_idx * 100 + level_offset


def get_style_constraints(level: str, seed: Optional[int] = None) -> Dict[str, str]:
    """Generate style constraints based on level and optional seed."""
    if seed is not None:
        rng = random.Random(seed)
    else:
        rng = random.Random()
    
    return {
        "stance": rng.choice(STANCE_OPTIONS),
        "example_count": rng.choice(EXAMPLE_COUNTS[level]),
        "rhetorical_style": rng.choice(RHETORICAL_STYLES),
    }


def build_system_prompt(level: str, style_constraints: Dict[str, str]) -> str:
    """Build system prompt for essay generation."""
    spec = LEVEL_SPECS[level]
    min_words, max_words = spec["word_range"]
    
    stance_instruction = {
        "agree": "Take a clear position in favor of the statement.",
        "disagree": "Take a clear position against the statement.",
        "balanced": "Present a balanced view, acknowledging both sides.",
    }[style_constraints["stance"]]
    
    example_instruction = f"Include exactly {style_constraints['example_count']} specific example(s) or illustration(s)."
    
    style_instruction = {
        "direct": "Write in a direct, straightforward style.",
        "analytical": "Write in an analytical style, breaking down the topic systematically.",
        "persuasive": "Write in a persuasive style, using strong arguments.",
        "narrative": "Write in a narrative style, using personal anecdotes or stories where appropriate.",
    }[style_constraints["rhetorical_style"]]
    
    return f"""You are a TOEFL test-taker writing an Independent Writing essay at {level} proficiency level.

Requirements:
- Write {min_words}-{max_words} words
- {spec['description']}
- {stance_instruction}
- {example_instruction}
- {style_instruction}

Style guidelines:
{chr(10).join(f"- {hint}" for hint in spec['style_hints'])}

CRITICAL: Output ONLY the essay text. Do NOT include:
- A title
- Bullet points
- Numbered lists
- Meta-commentary like "Here is my essay:"
- Any text before or after the essay

Start directly with your first sentence and end with your final sentence."""


def build_user_prompt(prompt_text: str, level: str) -> str:
    """Build user prompt with TOEFL question."""
    spec = LEVEL_SPECS[level]
    min_words, max_words = spec["word_range"]
    
    return f"""Write a TOEFL Independent Writing essay responding to this prompt:

{prompt_text}

Target length: {min_words}-{max_words} words.
Proficiency level: {level}

Write your essay now (essay text only, no title or extra text):"""


def generate_essay(
    client: OpenAI,
    prompt_text: str,
    level: str,
    model: str,
    temperature: float,
    style_constraints: Dict[str, str],
    max_retries: int = 3,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Generate a single essay using Groq API.
    
    Returns:
        (essay_text, error_message) - if error, essay_text is None
    """
    system_prompt = build_system_prompt(level, style_constraints)
    user_prompt = build_user_prompt(prompt_text, level)
    
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=1200,  # Enough for ~320 words
            )
            
            essay_text = response.choices[0].message.content.strip()
            
            # Clean up common issues
            essay_text = essay_text.lstrip('"').rstrip('"')
            if essay_text.startswith("Essay:"):
                essay_text = essay_text[6:].strip()
            if essay_text.startswith("Here is"):
                lines = essay_text.split("\n")
                for i, line in enumerate(lines):
                    if len(line) > 50 and not line.lower().startswith(("here", "this", "the following")):
                        essay_text = "\n".join(lines[i:]).strip()
                        break
            
            return essay_text, None
            
        except openai.RateLimitError as e:
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                print(f"    ⚠️  Rate limit hit. Retrying in {wait_time:.1f}s...")
                time.sleep(wait_time)
            else:
                return None, f"Rate limit error after {max_retries} attempts: {e}"
        
        except openai.APIError as e:
            status_code = getattr(e, "status_code", None)
            if attempt < max_retries - 1 and (status_code == 429 or (status_code and status_code >= 500)):
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                print(f"    ⚠️  API error {status_code}. Retrying in {wait_time:.1f}s...")
                time.sleep(wait_time)
            else:
                return None, f"API error: {e}"
        
        except Exception as e:
            return None, f"Unexpected error: {e}"
    
    return None, "Max retries exceeded"


def create_placeholder_essay(prompt_text: str, level: str, style_constraints: Dict[str, str]) -> str:
    """Create a placeholder essay for dry-run mode with realistic word count."""
    spec = LEVEL_SPECS[level]
    min_words, max_words = spec["word_range"]
    target_words = (min_words + max_words) // 2
    
    stance_text = {
        "agree": "I strongly agree",
        "disagree": "I strongly disagree",
        "balanced": "I believe there are arguments on both sides",
    }[style_constraints["stance"]]
    
    # Generate placeholder paragraphs with actual words
    paragraphs = [
        f"{stance_text} with this statement. In this essay, I will explain my position and provide reasons to support my view.",
    ]
    
    example_count = style_constraints["example_count"]
    words_per_example = max(50, (target_words - 30) // (example_count + 1))
    
    filler_sentences = [
        "This is an important point that demonstrates the validity of my argument.",
        "Furthermore, there are additional reasons that support this perspective.",
        "Many people would agree that this is a significant consideration.",
        "It is clear that this aspect plays a crucial role in understanding the topic.",
        "Research and experience show that this point is well-founded.",
        "Moreover, this example illustrates why my position is reasonable.",
        "In addition, this factor contributes to the overall argument.",
        "This demonstrates that the issue is more complex than it might seem.",
    ]
    
    for i in range(example_count):
        example_text = f"First, there are several important reasons to support my view. "
        example_text += f"For example, this is a key point that demonstrates my argument. "
        example_text += f"Additionally, this example shows why my position is valid. "
        
        filler_idx = i % len(filler_sentences)
        while count_words(example_text) < words_per_example:
            example_text += filler_sentences[filler_idx % len(filler_sentences)] + " "
            filler_idx += 1
        
        paragraphs.append(example_text.strip())
    
    paragraphs.append(
        "In conclusion, based on the reasons I have discussed, "
        "my position is well-supported. Therefore, I maintain my view on this topic. "
        "The evidence clearly shows that this perspective is the most reasonable one."
    )
    
    essay = "\n\n".join(paragraphs)
    
    # Final adjustment: trim or pad with real words if needed
    current_words = count_words(essay)
    if current_words < target_words:
        while count_words(essay) < target_words:
            essay += " " + filler_sentences[len(essay) % len(filler_sentences)]
    elif current_words > target_words:
        words = essay.split()
        essay = " ".join(words[:target_words])
    
    return essay


def save_essay(
    prompt_id: str,
    level: str,
    prompt_text: str,
    essay_text: str,
    model: str,
    output_dir: Path,
    overwrite: bool = False,
) -> Tuple[bool, Optional[str]]:
    """
    Save essay as JSON and TXT files.
    
    Returns:
        (success, error_message)
    """
    essay_id = f"{prompt_id}_{level.lower()}"
    word_count = count_words(essay_text)
    spec = LEVEL_SPECS[level]
    
    json_path = output_dir / f"{essay_id}.json"
    txt_path = output_dir / f"{essay_id}.txt"
    
    if not overwrite:
        if json_path.exists() or txt_path.exists():
            return False, "File already exists (use --overwrite to replace)"
    
    json_data = {
        "id": essay_id,
        "prompt_id": prompt_id,
        "level": level,
        "prompt": prompt_text,
        "word_target": {"min": spec["word_range"][0], "max": spec["word_range"][1]},
        "word_count": word_count,
        "essay": essay_text,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "model": model,
    }
    
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(essay_text)
        return True, None
    except Exception as e:
        return False, f"Failed to save files: {e}"


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic TOEFL essay dataset using Groq API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--dry-run", action="store_true", help="Generate placeholder essays without calling API")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for style constraint variation")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing files")
    parser.add_argument("--temperature", type=float, default=0.7, help="Temperature for generation (default: 0.7)")
    parser.add_argument("--model", type=str, default=None, help="Model name (default: from GROQ_MODEL env var or 'llama-3.1-8b-instant')")
    parser.add_argument("--output-dir", type=str, default="data/essays", help="Output directory (default: data/essays)")
    
    args = parser.parse_args()
    
    if not args.dry_run:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            print("❌ Error: GROQ_API_KEY not found in environment variables.")
            print("   Please set it in your .env file or export it.")
            sys.exit(1)
    
    model = args.model or os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if args.seed is not None:
        random.seed(args.seed)
    
    client = None
    if not args.dry_run:
        client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=api_key)
        print(f"✅ Connected to Groq API (model: {model})")
    else:
        print("🔍 DRY-RUN mode: Generating placeholder essays")
    
    print(f"📁 Output directory: {output_dir.absolute()}")
    print(f"🌱 Seed: {args.seed if args.seed is not None else 'random'}")
    print(f"🌡️  Temperature: {args.temperature}")
    print()
    
    total = len(TOEFL_PROMPTS) * len(LEVEL_SPECS)
    success_count = 0
    skip_count = 0
    error_count = 0
    errors = []
    
    for prompt_idx, prompt_text in enumerate(TOEFL_PROMPTS, start=1):
        prompt_id = f"p{prompt_idx:02d}"
        for level in ["B1", "B2", "C1"]:
            essay_id = f"{prompt_id}_{level.lower()}"
            print(f"📝 Generating {essay_id}...", end=" ", flush=True)
            
            json_path = output_dir / f"{essay_id}.json"
            txt_path = output_dir / f"{essay_id}.txt"
            if not args.overwrite and (json_path.exists() or txt_path.exists()):
                print("⏭️  skipped (exists)")
                skip_count += 1
                continue
            
            if args.seed is not None:
                essay_seed = get_essay_seed(args.seed, prompt_idx, level)
            else:
                essay_seed = None
            style_constraints = get_style_constraints(level, essay_seed)
            
            if args.dry_run:
                essay_text = create_placeholder_essay(prompt_text, level, style_constraints)
                error_msg = None
            else:
                essay_text, error_msg = generate_essay(client, prompt_text, level, model, args.temperature, style_constraints)
            
            if error_msg:
                print(f"❌ failed: {error_msg}")
                error_count += 1
                errors.append((essay_id, error_msg))
                continue
            
            word_count = count_words(essay_text)
            success, save_error = save_essay(prompt_id, level, prompt_text, essay_text, model, output_dir, args.overwrite)
            if not success:
                print(f"❌ save failed: {save_error}")
                error_count += 1
                errors.append((essay_id, save_error))
                continue
            
            print(f"✅ done ({word_count} words)")
            success_count += 1
    
    print()
    print("=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print(f"Total essays: {total}")
    print(f"✅ Success: {success_count}")
    print(f"⏭️  Skipped: {skip_count}")
    print(f"❌ Errors: {error_count}")
    if errors:
        print()
        print("Errors encountered:")
        for eid, emsg in errors:
            print(f"  - {eid}: {emsg}")
    if success_count > 0:
        print()
        print(f"✅ Essays saved to: {output_dir.absolute()}")
    
    sys.exit(0 if error_count == 0 else 1)


if __name__ == "__main__":
    main()
