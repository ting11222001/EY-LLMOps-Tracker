import time
import json
import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic()

# CHANGE: Each variant now has a system prompt so they behave differently from each other.
# Without this, all three variants produce nearly identical responses and scores are meaningless.
VARIANTS = [
    {
        "name": "conservative",
        "temperature": 0.2,
        # CHANGE: Told to be concise and skip recommendations, so output stays short and factual.
        "system": (
            "You are a legal analyst. Be concise and direct. "
            "Use plain language. Do not add recommendations or opinions. "
            "Stick only to what the clause explicitly states."
        ),
    },
    {
        "name": "balanced",
        "temperature": 0.7,
        # CHANGE: Allowed to add a recommendation if useful, sits between conservative and creative.
        "system": (
            "You are a legal analyst. Give a clear, structured response. "
            "You may include a brief recommendation if it adds value."
        ),
    },
    {
        "name": "creative",
        "temperature": 1.0,
        # CHANGE: Instructed to find non-obvious points and always end with a negotiation tip.
        # This intentionally produces longer, richer output so the judge can reward depth.
        "system": (
            "You are a legal analyst. Think broadly. "
            "Include non-obvious risks or obligations a junior reader might miss. "
            "Always end with a concrete negotiation recommendation."
        ),
    },
]

# CHANGE: Replaced rules-based scoring (word count + keyword matching) with LLM-as-judge.
# Rules-based scoring gave all variants 100/100 because every response passed the same simple checks.
# The judge scores on accuracy, completeness, clarity, and usefulness, which reflects actual quality.
JUDGE_SYSTEM = """You are an expert evaluator of legal analysis responses.
You will be given a task, a contract clause, and a response to evaluate.
Score the response from 0 to 100 based on these criteria:
- Accuracy: does it correctly identify what the clause says? (30 pts)
- Completeness: does it cover the key points for the task? (30 pts)
- Clarity: is it easy to understand? (20 pts)
- Usefulness: would a consultant actually use this? (20 pts)

Respond with ONLY valid JSON in this exact format, no other text:
{"score": <integer 0-100>, "reason": "<one sentence explaining the score>"}"""


def score_with_llm(response: str, task: str, clause: str) -> tuple[int, str]:
    # CHANGE: Truncate to 2000 chars before sending to the judge.
    # The creative variant produces long responses. Without truncation, the combined prompt
    # can cause the API to return an empty response, which breaks JSON parsing.
    truncated = response[:2000] if len(response) > 2000 else response

    prompt = f"""Task: {task}

Contract clause:
{clause}

Response to evaluate:
{truncated}"""

    # CHANGE: Retry once on failure. Empty API responses and JSON parse errors are transient.
    # If both attempts fail, return score=50 with the error message so the UI still renders.
    for attempt in range(2):
        try:
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=200,
                # CHANGE: temperature=0 for the judge so scores are consistent across runs.
                # A non-zero temperature would cause the same response to score differently each time.
                temperature=0,
                system=JUDGE_SYSTEM,
                messages=[{"role": "user", "content": prompt}]
            )
            raw = message.content[0].text.strip()
            if not raw:
                raise ValueError("Empty response from judge")
            parsed = json.loads(raw)
            score = max(0, min(100, int(parsed["score"])))
            reason = parsed.get("reason", "")
            return score, reason
        except Exception as e:
            last_error = e

    return 50, f"Scoring failed after 2 attempts: {last_error}"


def run_experiments(clause_text: str, task: str, run_id: str) -> list:
    results = []

    for variant in VARIANTS:
        prompt = f"{task} from this contract clause:\n\n{clause_text}"

        start = time.time()
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=512,
            temperature=variant["temperature"],
            system=variant["system"],
            messages=[{"role": "user", "content": prompt}]
        )
        latency = round(time.time() - start, 2)

        response_text = message.content[0].text
        score, reason = score_with_llm(response_text, task, clause_text)

        results.append({
            "run_id": run_id,
            "variant_name": variant["name"],
            "temperature": variant["temperature"],
            "task": task,
            "clause_text": clause_text,
            "response": response_text,
            "score": score,
            "score_reason": reason,
            "latency_seconds": latency,
        })

    return results