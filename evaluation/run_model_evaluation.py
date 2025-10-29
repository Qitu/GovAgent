import os
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml
import requests
from detoxify import Detoxify
from openai import OpenAI


def load_config() -> Dict[str, Any]:
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_cases() -> List[Dict[str, Any]]:
    cases_path = Path(__file__).parent / "cases.json"
    with open(cases_path, "r", encoding="utf-8") as f:
        return json.load(f)


def ensure_output_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def call_openai(prompt: str, system_prompt: str, model: str, max_tokens: int, temperature: float) -> Tuple[str, Dict[str, Any]]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    client = OpenAI(api_key=api_key)
    start = time.time()
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    latency = time.time() - start

    text = resp.choices[0].message.content if resp.choices else ""
    usage = getattr(resp, "usage", None)
    usage_dict = {
        "prompt_tokens": getattr(usage, "prompt_tokens", None) if usage else None,
        "completion_tokens": getattr(usage, "completion_tokens", None) if usage else None,
        "total_tokens": getattr(usage, "total_tokens", None) if usage else None,
        "latency_sec": round(latency, 3),
    }
    return text or "", usage_dict


def call_vectara_hallucination(question: str, answer: str, context: str) -> Dict[str, Any]:
    # Hugging Face Inference API
    hf_token = os.getenv("HF_TOKEN", "").strip()
    headers = {"Authorization": f"Bearer {hf_token}"} if hf_token else {}
    url = "https://api-inference.huggingface.co/models/vectara/hallucination_evaluation_model"

    payload = {
        "inputs": {
            "question": question,
            "answer": answer,
            "context": context or "",
        }
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        # The API may return different shapes depending on the model backend.
        # Try to normalize into {label, score} where label is hallucination / grounded
        result = {
            "raw": data,
            "hallucination_score": None,
            "hallucination_label": None,
        }
        # Common formats:
        # 1) [{"label": "hallucination", "score": 0.73}, {"label": "grounded", "score": 0.27}]
        if isinstance(data, list) and data and isinstance(data[0], dict) and "label" in data[0]:
            # pick the score for label == hallucination if present
            scores = {d.get("label"): d.get("score") for d in data}
            result["hallucination_label"] = max(scores, key=scores.get) if scores else None
            result["hallucination_score"] = float(scores.get("hallucination", 0.0))
            return result
        # 2) {"labels": ["hallucination","grounded"], "scores": [0.73,0.27]}
        if isinstance(data, dict) and "labels" in data and "scores" in data:
            labels = data.get("labels", [])
            scores = data.get("scores", [])
            label_to_score = {lbl: scr for lbl, scr in zip(labels, scores)}
            result["hallucination_label"] = max(label_to_score, key=label_to_score.get) if label_to_score else None
            result["hallucination_score"] = float(label_to_score.get("hallucination", 0.0))
            return result
        # Fallback: unknown format
        return result
    except Exception as e:
        return {"error": str(e), "hallucination_score": None, "hallucination_label": None}


def score_toxicity(text: str) -> Dict[str, float]:
    # Detoxify returns multiple dimensions
    model = Detoxify("unbiased")
    scores = model.predict(text or "")
    # Ensure float conversion
    return {k: float(v) for k, v in scores.items()}


def evaluate_case(case: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    provider = cfg.get("provider", {})
    system_prompt = (cfg.get("prompt_style", {}) or {}).get("system", "")

    answer, usage = call_openai(
        prompt=case.get("prompt", ""),
        system_prompt=system_prompt,
        model=provider.get("model", "gpt-4o-mini"),
        max_tokens=int(provider.get("max_tokens", 512)),
        temperature=float(provider.get("temperature", 0.2)),
    )

    hallucination = call_vectara_hallucination(
        question=case.get("prompt", ""),
        answer=answer,
        context=case.get("context", ""),
    )

    toxicity = score_toxicity(answer)

    thresholds = cfg.get("thresholds", {})
    hallucination_fail_threshold = float(thresholds.get("hallucination_fail_threshold", 0.5))
    toxicity_fail_threshold = float(thresholds.get("toxicity_fail_threshold", 0.5))

    hallucination_score = hallucination.get("hallucination_score")
    hallucination_fail = (
        hallucination_score is not None and hallucination_score >= hallucination_fail_threshold
    )

    toxicity_fail = any(score >= toxicity_fail_threshold for score in toxicity.values()) if toxicity else False

    return {
        "id": case.get("id"),
        "roles": [case.get("roleA"), case.get("roleB")],
        "prompt": case.get("prompt"),
        "context": case.get("context"),
        "answer": answer,
        "usage": usage,
        "hallucination": hallucination,
        "toxicity": toxicity,
        "pass": not (hallucination_fail or toxicity_fail),
        "fail_reasons": {
            "hallucination": hallucination_fail,
            "toxicity": toxicity_fail,
        },
    }


def generate_markdown(results: List[Dict[str, Any]], cfg: Dict[str, Any]) -> str:
    lines = []
    lines.append("# Model Evaluation Report")
    lines.append("")
    lines.append("| Case ID | Pass | HallucinationScore | AnyToxicity>=thr | Latency(s) | TotalTokens |")
    lines.append("|---|:---:|:---:|:---:|:---:|:---:|")
    thr_h = cfg.get("thresholds", {}).get("hallucination_fail_threshold", 0.5)
    thr_t = cfg.get("thresholds", {}).get("toxicity_fail_threshold", 0.5)
    lines.append(f"Thresholds: hallucination>={thr_h}, toxicity>={thr_t}")
    lines.append("")

    for r in results:
        hscore = r.get("hallucination", {}).get("hallucination_score")
        tox_scores = r.get("toxicity", {}) or {}
        any_tox = any(v >= float(thr_t) for v in tox_scores.values()) if tox_scores else False
        latency = (r.get("usage") or {}).get("latency_sec")
        total_tokens = (r.get("usage") or {}).get("total_tokens")
        lines.append(
            f"| {r.get('id')} | {'✅' if r.get('pass') else '❌'} | {hscore if hscore is not None else 'NA'} | {any_tox} | {latency} | {total_tokens} |"
        )

    lines.append("")
    lines.append("## Details")
    for r in results:
        lines.append(f"### {r.get('id')}")
        lines.append("")
        lines.append("Prompt:")
        lines.append("")
        lines.append(f"> {r.get('prompt')}")
        lines.append("")
        lines.append("Answer:")
        lines.append("")
        lines.append(f"> {r.get('answer')}")
        lines.append("")
        lines.append("Scores:")
        lines.append("")
        lines.append(f"- Hallucination: {json.dumps(r.get('hallucination'), ensure_ascii=False)}")
        lines.append(f"- Toxicity: {json.dumps(r.get('toxicity'), ensure_ascii=False)}")
        lines.append(f"- Usage: {json.dumps(r.get('usage'), ensure_ascii=False)}")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    cfg = load_config()
    cases = load_cases()

    out_dir = Path(cfg.get("output", {}).get("dir", "results/model_eval"))
    ensure_output_dir(out_dir)

    results: List[Dict[str, Any]] = []
    for case in cases:
        res = evaluate_case(case, cfg)
        results.append(res)

    report_json = out_dir / "report.json"
    with open(report_json, "w", encoding="utf-8") as f:
        json.dump({"results": results, "config": cfg}, f, ensure_ascii=False, indent=2)

    report_md = out_dir / "report.md"
    with open(report_md, "w", encoding="utf-8") as f:
        f.write(generate_markdown(results, cfg))

    print(f"Saved reports to {out_dir}")


if __name__ == "__main__":
    main()
