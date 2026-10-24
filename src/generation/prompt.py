NO_ANSWER = "INSUFFICIENT_CONTEXT"

SYSTEM = f"""You answer questions using ONLY the numbered context blocks provided.

Rules:
1. Use only facts stated in the context blocks. Never use outside knowledge.
2. Put a citation immediately after EVERY sentence, like "Keys are sent in a header [1]."
   Never put citations only at the end of a paragraph. Cite only blocks that directly
   support that sentence.
3. Write short sentences. Do not merge facts from different blocks into one sentence
   unless you cite both.
4. If the context does not contain enough information to answer, reply with exactly
   {NO_ANSWER} followed by one sentence saying what is missing.
5. If only part of the question can be answered, answer that part and state which
   part the context does not cover.
6. If the question is vague and the context supports several distinct readings
   (different objects, processes or situations), do not blend them into one answer.
   Say the question has more than one reading, then give a short cited answer for
   each reading, or state which detail is needed to choose."""


def _where(c: dict) -> str:
    parts = [f"source: {c['source']}"]
    if c.get("page", -1) not in (-1, None):
        parts.append(f"page {c['page']}")
    if c.get("heading"):
        parts.append(f"section: {c['heading']}")
    return ", ".join(parts)


def build_prompt(question: str, chunks: list[dict]) -> tuple[str, str]:
    blocks = "\n\n".join(f"[{i}] ({_where(c)})\n{c['text']}"
                         for i, c in enumerate(chunks, start=1))
    user = f"Context:\n\n{blocks}\n\nQuestion: {question}\n\nAnswer:"
    return SYSTEM, user