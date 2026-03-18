"""
Demo prompts for testing PromptView scanning and versioning.
Covers OpenAI, Anthropic, LangChain, and raw string patterns.
"""

# ── Raw string prompts ────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a helpful AI assistant specialized in software engineering.
You write clean, well-tested, production-ready code. You prefer simple solutions over
complex ones and always explain your reasoning step by step."""

CODE_REVIEW_PROMPT = """You are an expert code reviewer. When reviewing code, you check for:
- Security vulnerabilities (SQL injection, XSS, command injection)
- Performance bottlenecks and inefficiencies
- Readability and maintainability
- Test coverage and edge cases
- Adherence to SOLID principles

Be concise but thorough. Always suggest concrete improvements."""

USER_INSTRUCTION_TEMPLATE = """Please analyze the following {language} code and provide a detailed review.

Code:
```{language}
{code}
```

Focus on the top 3 most important issues. For each issue:
1. Describe the problem clearly
2. Explain why it matters
3. Show a corrected code snippet"""

SUMMARIZER_PROMPT = """You are a document summarization expert. Given a long document,
produce a structured summary with:
- A one-sentence TL;DR
- 3-5 key takeaways as bullet points
- Any action items or decisions required

Keep the summary under 200 words."""

PERSONA_PROMPT = """You are Alex, a friendly and knowledgeable customer support agent
for TechCorp. You have deep knowledge of our product line. You are patient, empathetic,
and always try to resolve issues in the first interaction. Never say you don't know —
instead, offer to find out and follow up."""


# ── OpenAI pattern ────────────────────────────────────────────────────────────

def review_code(code: str, language: str = "python") -> str:
    """Review code using GPT-4."""
    try:
        import openai
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": CODE_REVIEW_PROMPT},
                {"role": "user", "content": USER_INSTRUCTION_TEMPLATE.format(
                    language=language, code=code
                )},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content
    except ImportError:
        return "[openai not installed]"


def summarize_document(document: str) -> str:
    """Summarize a long document."""
    try:
        import openai
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SUMMARIZER_PROMPT},
                {"role": "user", "content": f"Please summarize the following document:\n\n{document}"},
            ],
        )
        return response.choices[0].message.content
    except ImportError:
        return "[openai not installed]"


# ── Anthropic pattern ─────────────────────────────────────────────────────────

def chat_with_claude(user_message: str) -> str:
    """Chat using Anthropic Claude."""
    try:
        import anthropic
        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": user_message},
            ],
        )
        return response.content[0].text
    except ImportError:
        return "[anthropic not installed]"


# ── LangChain pattern ─────────────────────────────────────────────────────────

def build_langchain_chain():
    """Build a LangChain prompt chain."""
    try:
        from langchain_core.prompts import ChatPromptTemplate, PromptTemplate

        chat_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant that translates {input_language} to {output_language}."),
            ("human", "{text}"),
        ])

        summary_prompt = PromptTemplate(
            template="Summarize the following text in {num_sentences} sentences:\n\n{text}",
            input_variables=["text", "num_sentences"],
        )

        return chat_prompt, summary_prompt
    except ImportError:
        return None, None


# ── LiteLLM pattern ───────────────────────────────────────────────────────────

def call_any_model(model: str, user_message: str) -> str:
    """Call any model via LiteLLM."""
    try:
        import litellm
        response = litellm.completion(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )
        return response.choices[0].message.content
    except ImportError:
        return "[litellm not installed]"


if __name__ == "__main__":
    print("PromptView demo prompts loaded.")
    print(f"SYSTEM_PROMPT preview: {SYSTEM_PROMPT[:80]}...")
