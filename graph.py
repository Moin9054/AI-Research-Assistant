import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
import wikipedia

from LLM import call_llama

STATE_FILE = "state.json"


def load_state() -> Dict[str, Any]:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"sessions": {}}


def save_state(state: Dict[str, Any]):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def _ddg_instant_answer(query: str) -> List[Dict[str, str]]:
    """
    Call DuckDuckGo Instant Answer (no API key). Returns a small list of docs (may be empty).
    """
    try:
        url = "https://api.duckduckgo.com/"
        params = {"q": query, "format": "json", "no_html": 1, "skip_disambig": 1}
        r = requests.get(url, params=params, timeout=8)
        r.raise_for_status()
        data = r.json()
        docs: List[Dict[str, str]] = []

        abstract = data.get("AbstractText", "") or data.get("Answer", "")
        if abstract:
            docs.append({"id": "ddg_abstract", "title": f"DuckDuckGo: {query}", "text": abstract})

        related = data.get("RelatedTopics", []) or []
        count = 0
        for item in related:
            if isinstance(item, dict):
                text = item.get("Text") or item.get("Result") or ""
                name = item.get("Name") or ""
                if text:
                    docs.append({"id": f"ddg_rel_{count}", "title": name or f"Related {count}", "text": text})
                    count += 1
                if count >= 2:
                    break
        return docs
    except Exception:
        return []


def _wiki_summary(query: str) -> List[Dict[str, str]]:
    """
    Attempt Wikipedia lookup. Returns a single doc with the page summary if found, else [].
    """
    try:
        titles = wikipedia.search(query, results=3)
        if not titles:
            return []
        title = titles[0]
        summary = wikipedia.summary(title, sentences=3, auto_suggest=False)
        return [{"id": f"wiki:{title}", "title": f"Wikipedia: {title}", "text": summary}]
    except Exception:
        return []


def retriever_node(query: str, k: int = 3, docs_folder: str = "knowledge") -> List[Dict[str, str]]:
    """
    Enhanced retriever:
      1) Prefer local knowledge files (token overlap ranking).
      2) If local results < k, call Wikipedia for a short summary.
      3) If still fewer, call DuckDuckGo Instant Answer and return those snippets.
      4) Final fallback: mocked docs.
    """
    results: List[Dict[str, str]] = []

    if os.path.isdir(docs_folder):
        files = [f for f in os.listdir(docs_folder) if f.lower().endswith(".txt")]
        scores: List[tuple] = []
        qtokens = set(query.lower().split())
        for fname in files:
            path = os.path.join(docs_folder, fname)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                    text = fh.read()
            except Exception:
                text = ""
            score = len(qtokens.intersection(set(text.lower().split())))
            scores.append((score, fname, text))
        scores.sort(reverse=True)
        for score, fname, text in scores[:k]:
            if text.strip():
                results.append({"id": fname, "title": fname, "text": text[:2000]})
        if len(results) >= k:
            return results[:k]

    try:
        wiki_docs = _wiki_summary(query)
        for d in wiki_docs:
            if all(d["id"] != ex["id"] for ex in results):
                results.append(d)
            if len(results) >= k:
                return results[:k]
    except Exception:
        pass

    try:
        ddg_docs = _ddg_instant_answer(query)
        for d in ddg_docs:
            if all(d["id"] != ex["id"] for ex in results):
                results.append(d)
            if len(results) >= k:
                return results[:k]
    except Exception:
        pass

    if not results:
        base = query.strip().split()[:3]
        key = " ".join(base) if base else query
        return [
            {"id": "doc1", "title": f"{key} — intro", "text": f"Intro about {key}. Keep it short and actionable."},
            {"id": "doc2", "title": f"{key} — use-cases", "text": f"Common use cases and quick examples for {key}."},
            {"id": "doc3", "title": f"{key} — tips", "text": f"Helpful tips: split tasks, persist state, and iterate quickly."},
        ]
    return results[:k]


def summarizer_node(query: str, docs: List[Dict[str, str]], context: str = "", chat_mode: bool = False) -> Dict[str, str]:
    """
    If chat_mode=True -> answer directly using the LLM (chatbot-style).
    Otherwise -> perform retrieval-augmented summarization (use docs).
    Returns dict with keys: 'summary' and 'mode' ('chat' | 'retrieval' | 'fallback').
    """
    if chat_mode:
        prompt = (
            f"You are a helpful assistant. Answer the user's question concisely and clearly.\n\n"
            f"User question: {query}\n\n"
            "If you're uncertain, say so and suggest where to verify."
        )
        if context:
            prompt = f"Previous context: {context}\n\n" + prompt
        answer = call_llama(prompt, max_tokens=300, temperature=0.2)
        return {"summary": answer, "mode": "chat"}

    if docs and len(docs) > 0:
        joined = "\n\n".join(f"{d['title']}: {d['text']}" for d in docs)
        prompt = (
            f"Summarize the following documents concisely for the user who asked: '{query}'\n\n"
            f"Documents:\n{joined}\n\n"
            "Provide a short (2-3 sentence) summary, followed by a 3-item actionable plan. "
            "Mark uncertainties if facts are unclear.\n\n"
        )
        if context:
            prompt = f"Previous context: {context}\n\n" + prompt
        summary = call_llama(prompt, max_tokens=250, temperature=0.2)
        return {"summary": summary, "mode": "retrieval"}
    else:
        prompt = (
            f"You are a helpful assistant. Answer the user's question concisely.\n\n"
            f"User question: {query}\n\n"
            "If you're uncertain, say so and suggest where to verify."
        )
        if context:
            prompt = f"Previous context: {context}\n\n" + prompt
        answer = call_llama(prompt, max_tokens=300, temperature=0.2)
        return {"summary": answer, "mode": "fallback"}


def planner_node(summary_text: str) -> Dict[str, Any]:
    prompt = (
        f"Given the short summary below, produce a concise 3-step implementation plan (each step 10-25 words).\n\n"
        f"Summary:\n{summary_text}\n\nPlan:"
    )
    plan_out = call_llama(prompt, max_tokens=200, temperature=0.2)
    return {"plan": plan_out}


class ResearchGraph:
    def __init__(self):
        pass

    def run(
        self,
        session_id: str,
        query: str,
        chat_mode: bool = False,
        user_name: Optional[str] = None
    ) -> Dict[str, Any]:
        state = load_state()
        sessions = state.setdefault("sessions", {})

        session = sessions.setdefault(session_id, {"history": [], "last_summary": "", "user_name": ""})
        if user_name:
            session["user_name"] = user_name

        if chat_mode:
            docs: List[Dict[str, str]] = []
        else:
            docs = retriever_node(query)

        summary_res = summarizer_node(query, docs, context=session.get("last_summary", ""), chat_mode=chat_mode)
        summary_text = summary_res.get("summary", "")
        mode_used = summary_res.get("mode", "retrieval")

        lower = query.lower()
        plan_out = None
        if any(k in lower for k in ("plan", "action", "next step", "how to", "implement")):
            plan_out = planner_node(summary_text)

        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "query": query,
            "docs": [{"id": d.get("id"), "title": d.get("title", d.get("id")), "url": d.get("url")} for d in docs],
            "summary": summary_text,
            "plan": plan_out,
            "mode": mode_used,
            "user": {"name": session.get("user_name", "")},
        }
        session["history"].append(entry)
        session["last_summary"] = summary_text
        save_state(state)

        return {
            "session_id": session_id,
            "session_name": session.get("user_name", ""),
            "summary": summary_text,
            "plan": plan_out,
            "docs": docs,
            "mode": mode_used
        }


if __name__ == "__main__":
    import argparse, json
    parser = argparse.ArgumentParser()
    parser.add_argument("--session", "-s", default="user1")
    parser.add_argument("--query", "-q", default=None)
    parser.add_argument("--chat", action="store_true", help="Use LLM-only chat mode (no retrieval).")
    parser.add_argument("--name", default=None, help="User name to attach")
    args = parser.parse_args()

    if not args.query:
        sid = input("Session id (e.g. user1): ").strip() or "user1"
        q = input("Query: ").strip()
    else:
        sid = args.session
        q = args.query

    g = ResearchGraph()
    out = g.run(sid, q, chat_mode=bool(args.chat), user_name=args.name)
    print(json.dumps(out, indent=2, ensure_ascii=False))
