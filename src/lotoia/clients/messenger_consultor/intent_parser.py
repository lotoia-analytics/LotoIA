from __future__ import annotations

import re
import unicodedata

INTENTS: dict[str, tuple[str, ...]] = {
    "resultado": ("resultado", "concurso", "saiu", "sorteio", "hoje", "ultimo", "último"),
    "atrasadas": ("atrasada", "atraso", "faltando", "nao sai", "não sai", "sumida", "demorada"),
    "frequentes": ("frequente", "mais sai", "comum", "popular", "campea", "campeã", "sempre sai"),
    "score": ("score", "pontuacao", "pontuação", "desempenho", "acerto", "nucleo", "núcleo"),
    "conferir": ("conferir", "confere", "verificar", "check", "pontuar", "meu jogo"),
    "gerar": (
        "gerar",
        "quero jogo",
        "me da jogo",
        "me dá jogo",
        "criar",
        "fazer jogo",
        "x15d",
        "x16d",
        "x17d",
        "x18d",
        "x19d",
        "x20d",
    ),
    "planos": ("plano", "preco", "preço", "valor", "assinar", "quanto custa", "como pago"),
    "menu": ("menu", "ajuda", "help", "oi", "ola", "olá", "opa", "inicio", "início"),
}


class MessengerIntentParser:
    def normalize(self, text: str) -> str:
        lowered = str(text or "").strip().lower()
        normalized = unicodedata.normalize("NFKD", lowered)
        without_accents = "".join(ch for ch in normalized if not unicodedata.combining(ch))
        return re.sub(r"\s+", " ", without_accents)

    def parse(self, text: str) -> str:
        normalized = self.normalize(text)
        if not normalized:
            return "unknown"
        if re.fullmatch(r"[\d\s,;.-]+", normalized) and len(self.parse_dezenas(normalized) or []) >= 10:
            return "conferir"
        for intent, keywords in INTENTS.items():
            if any(keyword in normalized for keyword in keywords):
                return intent
        if parse_game_request_hint(normalized):
            return "gerar"
        return "unknown"

    def parse_dezenas(self, text: str) -> list[int] | None:
        tokens = re.findall(r"\d{1,2}", str(text or ""))
        numbers: list[int] = []
        for token in tokens:
            value = int(token)
            if 1 <= value <= 25 and value not in numbers:
                numbers.append(value)
            if len(numbers) == 15:
                break
        return numbers if len(numbers) == 15 else None


def parse_game_request_hint(text: str) -> bool:
    normalized = str(text or "").lower()
    return bool(re.search(r"\d{1,2}\s*[x×]\s*\d{2}\s*d", normalized) or re.fullmatch(r"\d{1,2}", normalized))
