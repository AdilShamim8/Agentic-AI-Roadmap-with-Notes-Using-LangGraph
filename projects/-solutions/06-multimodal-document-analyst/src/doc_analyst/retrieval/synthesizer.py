"""Answer synthesizer.

Takes a user question + a list of `RetrievedElement` and produces a
structured `Answer` with element-level citations.

Strategy:
  1. Build a single LLM prompt that lists each retrieved element with a
     stable citation id (`<doc_id>::p<page>::e<element_index>`).
  2. Ask the LLM (json_mode) to produce:
        {
          "summary": "<one-paragraph answer>",
          "blocks": [
            {"claim": "...", "citations": ["doc-abc::p3::e1", ...]},
            ...
          ],
          "confidence": 0.0..1.0
        }
  3. Validate the JSON, map citation ids back to `Citation` objects,
     and return the final `Answer`.

If the LLM call fails we degrade gracefully: a single block is built
from the top-1 retrieved element.
"""
from __future__ import annotations

import json
import time
from typing import Any

from ..embeddings.vlm import VLMError, get_llm_client, VLMClient
from ..retrieval.retriever import MultimodalRetriever
from ..schemas import Answer, AnswerBlock, Citation, RetrievedElement
from ..utils.logging import get_logger

log = get_logger(__name__)


_SYSTEM_PROMPT = (
    "You are a multimodal document analyst. You will receive a user "
    "question and a numbered list of retrieved elements (text snippets, "
    "image captions, table rows), each tagged with a stable citation id of "
    "the form '<doc_id>::p<page>::e<element_index>'.\n\n"
    "Write a structured answer that GROUNDS every claim in those citations. "
    "If the retrieved elements do not contain the answer, say so explicitly "
    "in the summary and return an empty blocks array.\n\n"
    "Respond with a single JSON object matching this exact schema:\n"
    "{\n"
    '  "summary": "string, one paragraph",\n'
    '  "blocks": [\n'
    '    {"claim": "string, a single factual claim",\n'
    '     "citations": ["<citation_id>", "..."]}\n'
    "  ],\n"
    '  "confidence": 0.0\n'
    "}\n"
    "Rules:\n"
    "- Only use citation ids that appear in the retrieved elements list.\n"
    "- Each claim must cite at least one element.\n"
    "- Do NOT include any text outside the JSON object.\n"
)


def _element_card(idx: int, retrieved: RetrievedElement) -> str:
    el = retrieved.element
    el_type = el.type.value
    snippet = ""
    if el_type == "image":
        snippet = f"[image caption] {el.caption or '(no caption)'}"
    elif el_type == "table":
        snippet = f"[table] {el.text}"
    else:
        snippet = el.text
    snippet = snippet.strip().replace("\n", " ")
    if len(snippet) > 600:
        snippet = snippet[:600] + "..."
    return f"[{idx}] id={el.element_id} type={el_type} page={el.page}\n    {snippet}"


class AnswerSynthesizer:
    def __init__(self, llm: VLMClient | None = None) -> None:
        self.llm = llm or get_llm_client()

    # ------------------------------------------------------------------
    async def synthesize(
        self,
        question: str,
        retrieved: list[RetrievedElement],
    ) -> Answer:
        t0 = time.perf_counter()
        if not retrieved:
            return Answer(
                question=question,
                summary="No relevant elements were retrieved for this question.",
                blocks=[],
                citations=[],
                confidence=0.0,
                latency_ms=0.0,
            )

        cards = "\n".join(_element_card(i, r) for i, r in enumerate(retrieved, 1))
        user_prompt = (
            f"USER QUESTION:\n{question}\n\n"
            f"RETRIEVED ELEMENTS:\n{cards}\n\n"
            "Return the JSON object now."
        )
        try:
            raw = await self.llm.chat(
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                json_mode=True,
            )
            parsed = self._parse_json(raw)
        except (VLMError, ValueError) as exc:
            log.warning("synthesizer LLM call failed (%s); using fallback", exc)
            parsed = self._fallback(retrieved)

        # Map citation ids back to elements.
        by_id: dict[str, RetrievedElement] = {
            r.element.element_id: r for r in retrieved
        }
        blocks: list[AnswerBlock] = []
        citations: list[Citation] = []
        seen_ids: set[str] = set()
        for blk in parsed.get("blocks", []):
            claim = (blk.get("claim") or "").strip()
            if not claim:
                continue
            cites: list[Citation] = []
            for cid in blk.get("citations", []):
                if cid in by_id and cid not in seen_ids:
                    seen_ids.add(cid)
                    r = by_id[cid]
                    cites.append(self._to_citation(r))
                    citations.append(cites[-1])
                elif cid in by_id:
                    r = by_id[cid]
                    cites.append(self._to_citation(r))
            if not cites and by_id:
                # If the model returned a claim but didn't cite, attach the
                # top-1 retrieval as a defensive citation.
                top = retrieved[0]
                cites.append(self._to_citation(top))
                if top.element.element_id not in seen_ids:
                    seen_ids.add(top.element.element_id)
                    citations.append(cites[-1])
            blocks.append(AnswerBlock(claim=claim, citations=cites))

        confidence = float(parsed.get("confidence", 0.0))
        confidence = max(0.0, min(1.0, confidence))
        summary = (parsed.get("summary") or "").strip()
        if not summary and blocks:
            summary = blocks[0].claim

        return Answer(
            question=question,
            summary=summary,
            blocks=blocks,
            citations=citations,
            confidence=confidence,
            latency_ms=(time.perf_counter() - t0) * 1000.0,
        )

    # ------------------------------------------------------------------
    @staticmethod
    def _to_citation(r: RetrievedElement) -> Citation:
        el = r.element
        snippet = el.caption if (el.type.value == "image" and el.caption) else (
            (el.text or "")[:200]
        )
        return Citation(
            doc_id=el.doc_id,
            page=el.page,
            element_index=el.element_index,
            element_type=el.type,
            snippet=snippet,
            source=r.source,  # type: ignore[arg-type]
        )

    @staticmethod
    def _parse_json(raw: str) -> dict[str, Any]:
        # Strip code fences if the LLM ignored json_mode.
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            # remove leading language hint
            if raw.lower().startswith("json"):
                raw = raw[4:]
        # Find first { ... last }
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            start = raw.find("{")
            end = raw.rfind("}")
            if start >= 0 and end > start:
                return json.loads(raw[start : end + 1])
            raise

    @staticmethod
    def _fallback(retrieved: list[RetrievedElement]) -> dict[str, Any]:
        top = retrieved[0]
        snippet = top.element.caption or top.element.text or ""
        return {
            "summary": snippet[:300] or "(no summary available)",
            "blocks": [
                {
                    "claim": snippet[:200] or "(no claim)",
                    "citations": [top.element.element_id],
                }
            ],
            "confidence": 0.3,
        }
