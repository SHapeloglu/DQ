"""scoring.py — Kaynak başına 0-100 sağlık skoru."""
from __future__ import annotations
from database import get_conn


def get_health_score(source_id: int) -> dict:
    """Son run'a göre 0-100 skor + trafik ışığı."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT total, passed, run_at FROM runs
                   WHERE source_id = %s
                   ORDER BY run_at DESC LIMIT 1""",
                (source_id,),
            )
            row = cur.fetchone()
    finally:
        conn.close()

    if not row or not row["total"]:
        return {"source_id": source_id, "score": None, "light": "grey", "run_at": None}

    score = round(row["passed"] / row["total"] * 100, 1)
    light = "green" if score >= 80 else ("yellow" if score >= 50 else "red")
    return {
        "source_id": source_id,
        "score": score,
        "light": light,
        "passed": row["passed"],
        "total": row["total"],
        "run_at": str(row["run_at"]),
    }


def get_score_trend(source_id: int, days: int = 7) -> list[dict]:
    """Son N gün günlük ortalama skor."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT DATE(run_at) AS day,
                          ROUND(SUM(passed)/NULLIF(SUM(total),0)*100, 1) AS score
                   FROM runs
                   WHERE source_id = %s
                     AND run_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
                   GROUP BY DATE(run_at)
                   ORDER BY day""",
                (source_id, days),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    return [{"day": str(r["day"]), "score": r["score"]} for r in rows]


def get_all_scores() -> list[dict]:
    """Tüm kaynaklar için son skor özeti."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT s.id, s.name,
                          r.total, r.passed, r.run_at
                   FROM sources s
                   LEFT JOIN runs r ON r.id = (
                       SELECT id FROM runs
                       WHERE source_id = s.id
                       ORDER BY run_at DESC LIMIT 1
                   )"""
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    result = []
    for r in rows:
        if r["total"]:
            score = round(r["passed"] / r["total"] * 100, 1)
            light = "green" if score >= 80 else ("yellow" if score >= 50 else "red")
        else:
            score, light = None, "grey"
        result.append({
            "source_id": r["id"],
            "source_name": r["name"],
            "score": score,
            "light": light,
            "run_at": str(r["run_at"]) if r["run_at"] else None,
        })
    return result
