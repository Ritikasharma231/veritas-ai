"""Linguistic signal analysis.

Computes transparent, rule-based stylistic features. These are presented to
users as *signals*, not proof of falsity — sensational wording correlates with
misinformation but also with legitimate breaking news and opinion writing.
"""
import math
import re
from collections import Counter

EXCLAMATION_RE = re.compile(r"!")
QUESTION_RE = re.compile(r"\?")
ELLIPSIS_RE = re.compile(r"\.\.\.|…")
ALLCAPS_WORD_RE = re.compile(r"\b[A-Z]{4,}\b")
WORD_RE = re.compile(r"[A-Za-z']+")
SENTENCE_RE = re.compile(r"[^.!?\n]+[.!?]+|[^.!?\n]+$")

# Lexicons (deliberately small, documented, and editable)
SENSATIONAL_TERMS = {
    "shocking", "explosive", "bombshell", "devastating", "terrifying",
    "incredible", "unbelievable", "mind-blowing", "jaw-dropping", "outrageous",
    "horrifying", "stunning", "epic", "massive", "catastrophic", "apocalyptic",
}
URGENCY_TERMS = {
    "urgent", "breaking", "immediately", "act now", "limited time", "hurry",
    "deadline", "warning", "alert", "emergency", "rush", "last chance",
}
EMOTION_TERMS = {
    "outraged", "furious", "disgusting", "pathetic", "brilliant", "amazing",
    "terrible", "awful", "love", "hate", "angry", "happy", "sad", "cry",
    "scream", "shame", "disgrace", "hero", "villain",
}
CLICKBAIT_PATTERNS = [
    r"\byou won'?t believe\b", r"\bwhat happens next\b", r"\bthis is why\b",
    r"\bstop what you'?re doing\b", r"\beveryone needs to know\b",
    r"\bthe real reason\b", r"\bdoctors hate\b", r"\bone weird trick\b",
    r"\bnumber \d+\b.*\b(reason|way|thing)\b",
]
CLICKBAIT_RES = [re.compile(p, re.IGNORECASE) for p in CLICKBAIT_PATTERNS]


def _rate(count: int, total: float) -> float:
    return round(count / total, 4) if total else 0.0


def analyze_linguistic_signals(text: str) -> dict:
    """Return a dict of stylistic signals with human-readable labels."""
    if not text or not text.strip():
        return {"available": False}

    words = WORD_RE.findall(text)
    n_words = len(words)
    lower_words = [w.lower() for w in words]
    lower_text = text.lower()

    sentences = [s.strip() for s in SENTENCE_RE.findall(text) if s.strip()]
    n_sentences = max(len(sentences), 1)

    # --- punctuation / formatting ---
    exclaim = len(EXCLAMATION_RE.findall(text))
    question = len(QUESTION_RE.findall(text))
    ellipsis = len(ELLIPSIS_RE.findall(text))
    caps_words = ALLCAPS_WORD_RE.findall(text)
    caps_ratio = _rate(len(caps_words), n_words)

    punct_density = _rate(exclaim + question + ellipsis, n_words)

    # --- repetition ---
    word_counts = Counter(lower_words)
    repeated = sum(1 for w, c in word_counts.items() if c > 1 and len(w) > 3)
    unique_ratio = _rate(len(word_counts), n_words)

    # --- sentiment-ish lexicon hits ---
    sensational_hits = sorted({w for w in lower_words if w in SENSATIONAL_TERMS})
    urgency_hits = sorted({t for t in URGENCY_TERMS if t in lower_text})
    emotion_hits = sorted({w for w in lower_words if w in EMOTION_TERMS})

    clickbait_hits = [m.group(0) for rx in CLICKBAIT_RES for m in [rx.search(text)] if m]

    # --- sentence length stats (burstiness proxy) ---
    sent_lens = [len(WORD_RE.findall(s)) for s in sentences]
    avg_sent_len = round(sum(sent_lens) / len(sent_lens), 2) if sent_lens else 0.0
    if len(sent_lens) > 1:
        mean = sum(sent_lens) / len(sent_lens)
        var = sum((x - mean) ** 2 for x in sent_lens) / len(sent_lens)
        sent_len_std = round(math.sqrt(var), 2)
    else:
        sent_len_std = 0.0

    # --- subjectivity markers ---
    subjective_markers = [
        "i think", "i believe", "in my opinion", "obviously", "clearly",
        "everyone knows", "no one can deny", "the truth is", "let's be honest",
    ]
    subjective_hits = [m for m in subjective_markers if m in lower_text]

    # --- hedging markers (often indicate more careful writing) ---
    hedge_markers = [
        "according to", "reportedly", "sources say", "it is unclear",
        "may", "might", "could", "allegedly", "appears to",
    ]
    hedge_hits = [m for m in hedge_markers if m in lower_text]

    # --- readability proxy: avg word length ---
    avg_word_len = round(sum(len(w) for w in words) / n_words, 2) if n_words else 0.0

    # Overall "sensationalism score" 0-1 (weighted sum of normalized signals)
    score = 0.0
    score += min(exclaim / max(n_sentences, 1), 3) * 0.15
    score += min(len(sensational_hits), 5) * 0.06
    score += min(len(urgency_hits), 4) * 0.06
    score += min(len(clickbait_hits), 3) * 0.10
    score += min(len(emotion_hits), 6) * 0.03
    score += caps_ratio * 0.5
    score += min(punct_density * 4, 0.3)
    score = round(min(score, 1.0), 4)

    def sig(value, label, detail, severity="info"):
        return {"value": value, "label": label, "detail": detail, "severity": severity}

    signals = {
        "available": True,
        "word_count": n_words,
        "sentence_count": len(sentences),
        "avg_sentence_length": avg_sent_len,
        "sentence_length_std": sent_len_std,
        "avg_word_length": avg_word_len,
        "unique_word_ratio": unique_ratio,
        "sensationalism_score": score,
        "metrics": {
            "exclamation_marks": exclaim,
            "question_marks": question,
            "ellipsis_count": ellipsis,
            "all_caps_words": len(caps_words),
            "all_caps_ratio": caps_ratio,
            "punctuation_density": punct_density,
            "repeated_content_words": repeated,
        },
        "lexicon_hits": {
            "sensational_terms": sensational_hits,
            "urgency_terms": urgency_hits,
            "emotional_terms": emotion_hits[:20],
            "clickbait_patterns": clickbait_hits,
            "subjective_markers": subjective_hits,
            "hedging_markers": hedge_hits,
        },
        "interpretation": [
            sig(
                round(_rate(exclaim, n_sentences), 3),
                "Exclamation usage",
                f"{exclaim} exclamation mark(s) across {len(sentences)} sentence(s). "
                "Frequent exclamation can indicate sensational tone, though it is common in sports and opinion pieces.",
                "warning" if exclaim > len(sentences) else "info",
            ),
            sig(
                caps_ratio,
                "Excessive capitalization",
                f"{len(caps_words)} all-caps word(s) ({caps_ratio:.1%} of words). "
                "Heavy capitalization is associated with clickbait and low editorial standards.",
                "warning" if caps_ratio > 0.02 else "info",
            ),
            sig(
                len(sensational_hits),
                "Sensational wording",
                ", ".join(sensational_hits[:10]) if sensational_hits else "No strong sensational terms detected.",
                "warning" if sensational_hits else "info",
            ),
            sig(
                len(urgency_hits),
                "Urgency indicators",
                ", ".join(urgency_hits) if urgency_hits else "No urgency language detected.",
                "warning" if urgency_hits else "info",
            ),
            sig(
                len(clickbait_hits),
                "Clickbait patterns",
                "; ".join(clickbait_hits[:5]) if clickbait_hits else "No common clickbait phrases detected.",
                "warning" if clickbait_hits else "info",
            ),
            sig(
                round(sent_len_std, 2),
                "Sentence-length variation",
                f"Std-dev of sentence length is {sent_len_std} words "
                f"(mean {avg_sent_len}). Higher variation is typical of natural prose.",
                "info",
            ),
            sig(
                len(hedge_hits),
                "Hedging language",
                ", ".join(hedge_hits[:8]) if hedge_hits else "Few hedging markers; claims may be stated without attribution.",
                "info",
            ),
            sig(
                unique_ratio,
                "Vocabulary diversity",
                f"{unique_ratio:.1%} of words are unique. Very low diversity may indicate repetitive or generated text.",
                "warning" if unique_ratio < 0.35 and n_words > 50 else "info",
            ),
        ],
        "disclaimer": (
            "These are stylistic signals computed by rule-based analysis. They describe "
            "writing style only and are not evidence that content is true or false."
        ),
    }
    return signals
