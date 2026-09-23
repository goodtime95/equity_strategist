"""Small, transient presentation context, independent of financial intent."""

import re
from dataclasses import dataclass
from typing import Literal

Language = Literal["en", "fr"]


@dataclass(frozen=True, slots=True)
class InterpretationContext:
    question: str = ""
    language: Language = "en"

    @classmethod
    def from_question(
        cls,
        question: str,
        fallback_language: Language = "en",
        asset_references: tuple[str, ...] = (),
    ) -> "InterpretationContext":
        # Match function words, not accents in instrument names such as Hermès.
        language_text = question
        references = {value.strip() for value in asset_references if value.strip()}
        for reference in sorted(references, key=lambda value: (-len(value), value)):
            pattern = rf"(?<!\w){re.escape(reference)}(?!\w)"
            matches = list(re.finditer(pattern, language_text))
            if not matches:
                matches = list(re.finditer(pattern, language_text, re.IGNORECASE))
            if matches:
                # Mask one mention per reference, preferring exact case. Choose the
                # last match so preceding homographs ("de DE", "ET ET") remain.
                match = matches[-1]
                language_text = (
                    language_text[: match.start()] + " " + language_text[match.end() :]
                )
        words = set(re.findall(r"[^\W\d_]+", language_text.casefold()))
        french = words & {
            "quel",
            "quelle",
            "quels",
            "quelles",
            "le",
            "la",
            "les",
            "des",
            "du",
            "de",
            "sur",
            "entre",
            "depuis",
            "avec",
            "contre",
            "hier",
            "aujourd",
            "donne",
            "classe",
            "comparez",
            "rendement",
            "volatilité",
            "année",
            "cette",
            "moi",
            "plus",
            "moins",
            "pour",
            "et",
        }
        english = words & {
            "what",
            "which",
            "the",
            "of",
            "between",
            "since",
            "with",
            "against",
            "yesterday",
            "today",
            "give",
            "rank",
            "return",
            "volatility",
            "year",
            "this",
            "most",
            "least",
            "for",
            "and",
            "from",
            "to",
        }
        language = fallback_language
        if len(french) > len(english):
            language = "fr"
        elif len(english) > len(french):
            language = "en"
        return cls(question, language)
