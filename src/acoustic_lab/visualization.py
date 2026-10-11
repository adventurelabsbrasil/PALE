"""Self-contained HTML report with clickable audio examples."""

import html
import json
from pathlib import Path

import numpy as np

from .projection import fit_projection, transform_projection


def project_2d(
    index: list[dict], vectors: dict[str, np.ndarray],
    *, checkpoint_sha256: str = "unknown", config: dict | None = None,
) -> tuple[dict[str, list[float]], dict]:
    """Fit PCA on training embeddings once, then transform every item."""
    train = np.stack([vectors[item["id"]] for item in index if item["split"] == "train"])
    fitted = fit_projection(
        train, checkpoint_sha256=checkpoint_sha256, config=config or {}, dimensions=2,
    )
    matrix = np.stack([vectors[item["id"]] for item in index])
    transformed = transform_projection(matrix, fitted)
    coordinates = {item["id"]: transformed[i].tolist() for i, item in enumerate(index)}
    return coordinates, fitted.to_dict()


def _plot(index: list[dict], coords: dict[str, list[float]]) -> str:
    xy = np.array(list(coords.values()))
    lower, upper = xy.min(axis=0), xy.max(axis=0)
    span = np.maximum(upper - lower, 1e-9)
    colors = {"train": "#377eb8", "validation": "#e69f00", "test": "#009e73"}
    circles = []
    for item in index:
        x, y = coords[item["id"]]
        cx = 32 + 736 * (x - lower[0]) / span[0]
        cy = 368 - 336 * (y - lower[1]) / span[1]
        item_id = html.escape(item["id"], quote=True)
        path = html.escape(item["path"], quote=True)
        circles.append(f'<circle cx="{cx:.3f}" cy="{cy:.3f}" r="3.2" fill="{colors[item["split"]]}" opacity="0.76" data-id="{item_id}" data-audio="{path}" tabindex="0"><title>{item_id} · {item["split"]}</title></circle>')
    return '<svg viewBox="0 0 800 400" role="img" aria-label="PCA dos embeddings">' + "".join(circles) + "</svg>"


def _history_svg(history: list[dict]) -> str:
    values = [row[key] for row in history for key in ("train_masked_mse", "model_masked_mse", "baseline_masked_mse")]
    top = max(max(values) * 1.05, 1e-9)
    lines = []
    for key, color in (("train_masked_mse", "#377eb8"), ("model_masked_mse", "#e69f00"), ("baseline_masked_mse", "#555")):
        points = " ".join(f"{40 + 720 * i / max(len(history) - 1, 1):.2f},{350 - 310 * row[key] / top:.2f}" for i, row in enumerate(history))
        lines.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2"/>')
    return '<svg viewBox="0 0 800 380" role="img" aria-label="Erro por época">' + "".join(lines) + "</svg>"


def write_report(output: Path, index: list[dict], metrics: dict, coordinates: dict[str, list[float]], started_at: str) -> None:
    validation = metrics["validation"]
    test = metrics["test"]
    report = f"""<!doctype html>
<html lang="pt-BR"><meta charset="utf-8"><title>Experimento acústico · Fase 1</title>
<style>body{{font:16px system-ui;max-width:900px;margin:2rem auto;padding:0 1rem;color:#17212b}}svg{{width:100%;border:1px solid #ccd4dc;background:#f8fafc}}circle{{cursor:pointer}}circle:hover{{stroke:#111;stroke-width:2}}table{{border-collapse:collapse}}td,th{{padding:.5rem;border:1px solid #ccd4dc;text-align:right}}th:first-child{{text-align:left}}.legend span{{margin-right:1rem}}audio{{width:100%}}</style>
<h1>Experimento acústico · Fase 1</h1>
<p>Execução iniciada em {html.escape(started_at)} (UTC).</p>
<p>Rede treinada do zero com reconstrução de trechos ocultos. Os gráficos descrevem representações; não demonstram descoberta de teoria acústica ou musical.</p>
<p>Melhor época por validação: {metrics['best_epoch']}. Erro: média quadrática na região oculta; menor é melhor.</p>
<table><tr><th>Conjunto</th><th>Modelo</th><th>Interpolação</th><th>Arquivos</th><th>Janelas</th></tr>
<tr><th>Validação</th><td>{validation['model_masked_mse']:.8f}</td><td>{validation['baseline_masked_mse']:.8f}</td><td>{validation['files']}</td><td>{validation['windows']}</td></tr>
<tr><th>Teste reservado</th><td>{test['model_masked_mse']:.8f}</td><td>{test['baseline_masked_mse']:.8f}</td><td>{test['files']}</td><td>{test['windows']}</td></tr></table>
<h2>Erro por época</h2><p>Azul: treino · laranja: validação do modelo · cinza: baseline de validação</p>
{_history_svg(metrics['history'])}
<h2>Embeddings · PCA ajustada apenas no treino</h2>
<p class="legend"><span style="color:#377eb8">● Treino</span><span style="color:#e69f00">● Validação</span><span style="color:#009e73">● Teste</span></p>
<p>Selecione um ponto para ouvir seu WAV original.</p>{_plot(index, coordinates)}
<p id="selection">Nenhum áudio selecionado.</p><audio id="player" controls preload="none"></audio>
<script>for(const point of document.querySelectorAll('circle[data-audio]')){{const play=()=>{{document.getElementById('selection').textContent='Áudio '+point.dataset.id;const player=document.getElementById('player');player.src=point.dataset.audio;player.load()}};point.addEventListener('click',play);point.addEventListener('keydown',event=>{{if(event.key==='Enter'||event.key===' ')play()}})}}</script>
</html>"""
    (output / "report.html").write_text(report, encoding="utf-8")
    (output / "projection.json").write_text(json.dumps(coordinates, indent=2, sort_keys=True) + "\n", encoding="utf-8")
