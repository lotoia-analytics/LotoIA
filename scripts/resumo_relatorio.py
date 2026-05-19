from pathlib import Path
import re
import pypdf

pdf_path = Path(r"C:\Projetos\LotoIA\RELATORIO.pdf")
reader = pypdf.PdfReader(str(pdf_path))
text = "\n".join((p.extract_text() or "") for p in reader.pages)

parts = re.split(r'\{\s*"id"\s*:\s*', text)

def extract_game(part, label):
    m = re.search(rf'"{label}"\s*:\s*\{{', part)
    if not m:
        return None
    sub = part[m.start():]
    contest = re.search(r'"contest"\s*:\s*(\d+)', sub)
    hits = re.search(r'"hits"\s*:\s*(\d+)', sub)
    nums = re.search(r'"numbers"\s*:\s*\[([^\]]+)\]', sub)
    numbers = None
    if nums:
        numbers = [int(x.strip()) for x in nums.group(1).split(",") if x.strip().isdigit()]
    return {
        "contest": int(contest.group(1)) if contest else None,
        "hits": int(hits.group(1)) if hits else None,
        "numbers": numbers,
    }

runs = []
for part in parts[1:]:
    m = re.match(r'(\d+)\s*,', part)
    if not m:
        continue
    rid = int(m.group(1))
    created = re.search(r'"created_at"\s*:\s*"([^"]+)"', part)
    avg = re.search(r'"average_hits"\s*:\s*([0-9.]+)', part)
    corr = re.search(r'"correlation"\s*:\s*([-0-9.]+)', part)
    conf = re.search(r'"configuration"\s*:\s*"([^"]+)"', part)
    runs.append({
        "id": rid,
        "created_at": created.group(1) if created else None,
        "configuration": conf.group(1) if conf else None,
        "average_hits": float(avg.group(1)) if avg else None,
        "correlation": float(corr.group(1)) if corr else None,
        "best_game": extract_game(part, "best_game"),
        "worst_game": extract_game(part, "worst_game"),
    })

out = Path("resumo_relatorio.txt")
lines = []
lines.append(f"Arquivo: {pdf_path.name}")
lines.append(f"Runs encontradas: {len(runs)}")
lines.append("")
for r in runs:
    lines.append(f"- id={r['id']} | created_at={r['created_at']} | config={r['configuration']} | avg_hits={r['average_hits']} | corr={r['correlation']}")
    if r["best_game"]:
        bg = r["best_game"]
        lines.append(f"  best_game: concurso={bg['contest']} hits={bg['hits']} dezenas={bg['numbers']}")
    if r["worst_game"]:
        wg = r["worst_game"]
        lines.append(f"  worst_game: concurso={wg['contest']} hits={wg['hits']} dezenas={wg['numbers']}")
    lines.append("")

out.write_text("\n".join(lines), encoding="utf-8")
print("OK ->", out.resolve())
