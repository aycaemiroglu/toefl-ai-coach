"""
TOEFL Essay Evaluator using Groq API
Author: Ayça Emiroğlu
Date: February 2026

This module implements automated TOEFL essay scoring using LLMs
with four different prompting strategies.
"""

from groq import Groq
import os
from dotenv import load_dotenv
from typing import Dict

# Load environment variables
load_dotenv()


class TOEFLEssayScorer:
    """
    TOEFL essay scorer using Groq's Llama 3.3 70B model.

    Supports four prompting strategies:
    - baseline: Simple scoring instruction
    - rubric: Explicit TOEFL rubric criteria
    - few_shot: Examples included in prompt
    - chain_of_thought: Step-by-step reasoning
    """

    def __init__(self):
        """Initialize Groq client with API key from environment."""
        api_key = os.getenv('GROQ_API_KEY')

        if not api_key:
            raise ValueError(
                "⚠️ GROQ_API_KEY not found!\n"
                "Please create a .env file with: GROQ_API_KEY=your_key_here"
            )

        self.client = Groq(api_key=api_key)
        print("✅ Groq client initialized successfully!")

    def score_essay(
        self,
        essay_text: str,
        prompt_text: str,
        strategy: str = "baseline"
    ) -> Dict:
        """
        Score a TOEFL essay using specified prompting strategy.

        Args:
            essay_text: The student's essay
            prompt_text: The essay prompt/question
            strategy: One of ['baseline', 'rubric', 'few_shot', 'chain_of_thought']

        Returns:
            Dictionary containing strategy, response, and model info

        Example:
            >>> scorer = TOEFLEssayScorer()
            >>> result = scorer.score_essay(
            ...     "Technology has improved...",
            ...     "Do you agree technology is beneficial?",
            ...     "rubric"
            ... )
            >>> print(result['response'])
        """
        print(f"\n🔄 Scoring essay... (Strategy: {strategy})")

        # Get system prompt for strategy
        system_prompt = self._get_system_prompt(strategy)

        # Call Groq API
        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"PROMPT: {prompt_text}\n\nESSAY:\n{essay_text}"
                    }
                ],
                temperature=0.3,  # Lower = more consistent
                max_tokens=500
            )

            result_text = response.choices[0].message.content
            print("✅ Scoring complete!")

            return {
                "strategy": strategy,
                "response": result_text,
                "model": "llama-3.3-70b-versatile",
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens
            }

        except Exception as e:
            print(f"❌ Error occurred: {e}")
            return {
                "strategy": strategy,
                "error": str(e)
            }

    def _get_system_prompt(self, strategy: str) -> str:
        """
        Return system prompt based on strategy.

        Different prompts for experimental comparison.
        """
        prompts = {
            "baseline": """You are a TOEFL essay scorer.
Score the following essay from 0 to 5 and explain why.

Format:
Score: X/5
Reasoning: ...
""",

            "rubric": """You are an expert TOEFL rater. Score using the official TOEFL Independent Writing rubric (0-5):

**5** - Effectively addresses the topic with well-organized ideas, strong examples, and sophisticated language use
**4** - Generally addresses topic with adequate organization, some examples, and competent language
**3** - Addresses topic but with limited development, simple organization, basic language
**2** - Limited connection to topic, poor organization, frequent errors
**1** - Little to no coherence, severe language problems
**0** - Off-topic or blank

Return your evaluation in JSON format:
{
  "score": X,
  "reasoning": "...",
  "strengths": ["...", "..."],
  "weaknesses": ["...", "..."]
}
""",

            "few_shot": """You are a TOEFL scorer. Here are scoring examples:

EXAMPLE 1:
Essay: "Technology good because help people. Many thing technology do."
Score: 2/5
Reason: Limited vocabulary, grammar errors, lacks development and examples

EXAMPLE 2:
Essay: "While technology has undoubtedly improved communication and education, it has also created new challenges. For instance, social media platforms enable instant global connection, yet they often reduce meaningful face-to-face interaction. Additionally, online learning provides accessibility but may lack the engagement of traditional classrooms."
Score: 4/5
Reason: Clear thesis, good organization, strong vocabulary, specific examples, minor room for improvement

Now score this essay using the same criteria:
""",

            "chain_of_thought": """You are a TOEFL scorer. Evaluate the essay step-by-step:

**STEP 1:** Does it answer the prompt? (Yes/No + explanation)
**STEP 2:** Organization quality? (Introduction, body paragraphs, conclusion structure)
**STEP 3:** Language sophistication? (Vocabulary range, grammar accuracy, sentence variety)
**STEP 4:** Examples and development? (Specific examples, depth of explanation)
**STEP 5:** Final score (0-5) with detailed reasoning based on steps 1-4

Please use this exact step-by-step format in your response.
"""
        }

        return prompts.get(strategy, prompts["baseline"])


def main():
    """Test the scorer with a sample essay."""
    print("=" * 60)
    print("🎓 TOEFL ESSAY SCORER - TEST MODE")
    print("=" * 60)

    # Initialize scorer
    scorer = TOEFLEssayScorer()

    # Sample essay
    test_essay = """
I strongly agree that technology has made the world a better place to live
for several important reasons.

First, technology has revolutionized communication. In the past, people had
to wait weeks for letters to arrive from other countries. Today, I can video
call my family in Turkey instantly using applications like WhatsApp and Zoom.
This immediate connectivity strengthens relationships and reduces feelings
of isolation.

Second, technology has dramatically improved healthcare. Modern medical
equipment can diagnose diseases earlier and more accurately than ever before.
For example, MRI machines can detect tumors in their early stages, which
significantly increases survival rates. Additionally, telemedicine now allows
patients in rural areas to consult with specialists remotely, improving
access to quality healthcare.

In conclusion, technology's positive impact on communication and healthcare
clearly demonstrates that it has made the world a better place. While some
challenges exist, the benefits far outweigh the drawbacks.
"""

    test_prompt = "Do you agree or disagree with the following statement? Technology has made the world a better place to live. Use specific reasons and examples to support your answer."

    # Test all strategies
    strategies = ["baseline", "rubric", "few_shot", "chain_of_thought"]

    for strategy in strategies:
        result = scorer.score_essay(test_essay, test_prompt, strategy)

        print("\n" + "=" * 60)
        print(f"📊 STRATEGY: {strategy.upper().replace('_', ' ')}")
        print("=" * 60)

        if "error" in result:
            print(f"❌ Error: {result['error']}")
        else:
            print(result["response"])
            print(f"\n📈 Tokens used: {result['prompt_tokens']} + {result['completion_tokens']}")

        print()

    print("=" * 60)
    print("✅ Test complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
