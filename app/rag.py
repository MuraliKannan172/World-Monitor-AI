"""RAG: BM25 retrieval via SQLite FTS5 + Ollama prompt construction."""

from app import db
from app.ollama_client import ollama

_SYSTEM_PROMPT = (
    "You are WorldMonitor, an expert OSINT intelligence analyst. "
    "Answer the user's question using ONLY the context provided below. "
    "Cite sources using bracketed numbers like [1], [2]. "
    "If the context does not contain enough information, say so. "
    "Be concise and factual."
)


async def build_context(query: str, limit: int = 8) -> tuple[str, list[dict]]:
    """Return (context_block, source_list) for RAG prompt."""
    snippets = await db.fts_search(query, limit=limit)
    if not snippets:
        return "", []

    lines = []
    for i, s in enumerate(snippets, start=1):
        date_str = (s.get("published_at") or "")[:10]
        lines.append(
            f"[{i}] {s['title']} ({s.get('source_name', '')} {date_str})\n"
            f"    {(s.get('summary') or '')[:300]}"
        )
    return "\n\n".join(lines), snippets


async def answer_stream(question: str, model: str | None, session_id: str):
    """Retrieve context, build prompt, stream Ollama response, save turn."""
    context_block, sources = await build_context(question)

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
    ]
    if context_block:
        messages.append({"role": "system", "content": f"Context:\n{context_block}"})
    messages.append({"role": "user", "content": question})

    await db.save_chat_turn(session_id, "user", question)

    full_response = []
    async for token in ollama.stream_chat(messages, model=model):
        full_response.append(token)
        yield token

    await db.save_chat_turn(session_id, "assistant", "".join(full_response))
