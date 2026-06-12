from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lotoia.data.loader import DEFAULT_HISTORY_PATH, load_draws_csv
from lotoia.database.contest_repository import ContestRepository
from lotoia.database.database import DEFAULT_DATABASE_PATH, LotofacilOfficialHistory, get_session
from lotoia.governance.lei15a_operational import NUCLEO_LEI15_15D_CONGELADO
from lotoia.statistics.basic import number_frequency
from lotoia.statistics.temporal import calculate_delays

HISTORY_WINDOW = 500


@dataclass(frozen=True)
class _Draw:
    contest: int
    numbers: list[int]
    date: str = ""


def _parse_numbers(raw: str | list[Any]) -> list[int]:
    if isinstance(raw, list):
        return sorted(int(n) for n in raw)
    return sorted(int(part) for part in str(raw or "").replace(";", ",").split(",") if str(part).strip().isdigit())


def _load_draws(db_path: Path, *, limit: int = HISTORY_WINDOW) -> list[_Draw]:
    draws: list[_Draw] = []
    with get_session(db_path) as session:
        rows = (
            session.query(LotofacilOfficialHistory)
            .order_by(LotofacilOfficialHistory.contest_number.desc())
            .limit(max(1, int(limit)))
            .all()
        )
        for row in reversed(rows):
            numbers = _parse_numbers(row.numbers)
            if len(numbers) == 15:
                draws.append(
                    _Draw(
                        contest=int(row.contest_number),
                        numbers=numbers,
                        date=str(row.draw_date or ""),
                    )
                )
    if draws:
        return draws

    repo = ContestRepository(db_path)
    max_contest = int(repo.get_official_history_max_contest() or repo.get_last_contest() or 0)
    if max_contest:
        start = max(1, max_contest - limit + 1)
        for contest_number in range(start, max_contest + 1):
            row = repo.get_official_history_contest(contest_number) or repo.get_contest(contest_number)
            if not row:
                continue
            numbers = _parse_numbers(row.get("dezenas") or [])
            if len(numbers) == 15:
                draws.append(
                    _Draw(
                        contest=int(row.get("concurso") or contest_number),
                        numbers=numbers,
                        date=str(row.get("data") or ""),
                    )
                )
    if draws:
        return draws

    try:
        csv_draws = load_draws_csv(DEFAULT_HISTORY_PATH)
    except Exception:
        return []
    ordered = sorted(csv_draws, key=lambda draw: int(draw.contest))[-limit:]
    return [
        _Draw(contest=int(draw.contest), numbers=sorted(int(n) for n in draw.numbers), date=str(draw.date or ""))
        for draw in ordered
    ]


def _format_numbers(numbers: list[int]) -> str:
    return " ".join(f"{number:02d}" for number in sorted(numbers))


def _format_numbers_lines(numbers: list[int]) -> str:
    sorted_numbers = sorted(numbers)
    first_line = " ".join(f"{n:02d}" for n in sorted_numbers[:9])
    second_line = " ".join(f"{n:02d}" for n in sorted_numbers[9:])
    return f"{first_line}\n{second_line}"


class MessengerStatsService:
    """Formata estatísticas vivas do PostgreSQL para texto Messenger."""

    def __init__(self, db_path: Path = DEFAULT_DATABASE_PATH) -> None:
        self.db_path = db_path

    def get_resultado(self) -> str:
        draws = _load_draws(self.db_path, limit=1)
        if not draws:
            return "📊 Resultado ainda não disponível no PostgreSQL. Tente novamente em breve."
        latest = draws[-1]
        return (
            f"📊 Concurso {latest.contest}"
            + (f" — {latest.date}" if latest.date else "")
            + "\n\nDezenas sorteadas:\n"
            + f"{_format_numbers_lines(latest.numbers)}\n\n"
            + "Próximo sorteio: segunda-feira 🗓️"
        )

    def get_atrasadas(self) -> str:
        draws = _load_draws(self.db_path)
        if not draws:
            return "⏳ Dados históricos indisponíveis no momento."
        delays = calculate_delays(draws)
        ranked = sorted(
            ((int(number), int(contests)) for number, contests in delays.items()),
            key=lambda item: (-item[1], item[0]),
        )[:10]
        lines = ["⏳ Top 10 dezenas mais atrasadas:", ""]
        for index, (number, contests) in enumerate(ranked, start=1):
            lines.append(f"{index}. Dezena {number:02d} → {contests} concursos")
        lines.extend(["", f"📊 Base: últimos {min(len(draws), HISTORY_WINDOW)} concursos"])
        return "\n".join(lines)

    def get_frequentes(self) -> str:
        draws = _load_draws(self.db_path)
        if not draws:
            return "📈 Dados históricos indisponíveis no momento."
        frequencies = number_frequency(draws)
        total = len(draws)
        ranked = sorted(frequencies.items(), key=lambda item: (-item[1], item[0]))[:10]
        lines = ["📈 Top 10 dezenas que mais saem:", ""]
        for index, (number, count) in enumerate(ranked, start=1):
            percent = round((count / total) * 100, 1) if total else 0.0
            lines.append(f"{index}. Dezena {number:02d} → {percent}% dos concursos")
        lines.extend(["", f"📊 Base: {total} concursos analisados"])
        return "\n".join(lines)

    def get_score(self) -> str:
        draws = _load_draws(self.db_path)
        if not draws:
            return "🏆 Score indisponível — histórico não carregado."
        nucleus = sorted(NUCLEO_LEI15_15D_CONGELADO)
        nucleus_set = set(nucleus)
        hits_history = [
            len(nucleus_set & set(draw.numbers))
            for draw in draws
        ]
        last_hits = hits_history[-1]
        last10 = hits_history[-10:]
        last30 = hits_history[-30:]
        best = max(hits_history)
        avg10 = round(sum(last10) / len(last10), 1) if last10 else 0.0
        avg30 = round(sum(last30) / len(last30), 1) if last30 else 0.0
        latest = draws[-1]
        return (
            "🏆 Score LotoIA — Núcleo 15D:\n\n"
            f"Último concurso ({latest.contest}): {last_hits}/15 ✅\n"
            f"Média últimos 10:       {avg10} dezenas\n"
            f"Média últimos 30:       {avg30} dezenas\n"
            f"Melhor resultado:       {best}/15 🔥\n\n"
            f"Núcleo: {_format_numbers(nucleus[:8])}\n"
            f"        {_format_numbers(nucleus[8:])}\n\n"
            "💡 Análise estatística — não garante resultados"
        )

    def conferir_jogo(self, dezenas: list[int], concurso: int | None = None) -> str:
        draws = _load_draws(self.db_path)
        if not draws:
            return "🔍 Histórico indisponível para conferência."
        target_contest = int(concurso) if concurso is not None else draws[-1].contest
        official = next((draw for draw in draws if draw.contest == target_contest), None)
        if official is None:
            repo = ContestRepository(self.db_path)
            row = repo.get_official_history_contest(target_contest) or repo.get_contest(target_contest)
            if not row:
                return f"🔍 Concurso {target_contest} não encontrado no PostgreSQL."
            official = _Draw(
                contest=target_contest,
                numbers=_parse_numbers(row.get("dezenas") or []),
                date=str(row.get("data") or ""),
            )
        selected = sorted(set(int(n) for n in dezenas if 1 <= int(n) <= 25))
        if len(selected) != 15:
            return "🔍 Envie exatamente 15 dezenas entre 01 e 25 para conferir."
        hits = len(set(selected) & set(official.numbers))
        nucleus_hits = len(set(NUCLEO_LEI15_15D_CONGELADO) & set(official.numbers))
        premio = "premiado ✅" if hits >= 11 else "não premiado (mín. 11 pontos)"
        return (
            f"🔍 Conferência — Concurso {official.contest}:\n\n"
            f"Seu jogo:\n{_format_numbers(selected)}\n\n"
            f"Resultado oficial:\n{_format_numbers(official.numbers)}\n\n"
            f"✅ Pontos: {hits}/15\n\n"
            f"Premiação: {premio}\n\n"
            f"💡 Com o núcleo LotoIA você teria tido cobertura em {nucleus_hits} dezenas nesse concurso."
        )
