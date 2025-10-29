# Model Evaluation (Hallucination, Toxicity, Robustness)

This folder provides a lightweight, reproducible evaluation pipeline for your LLM outputs based on:
- Hallucination detection via Hugging Face model `vectara/hallucination_evaluation_model`
- Toxicity analysis via `Detoxify`
- Optional robustness scenarios defined via test cases

Outputs are saved in `results/model_eval/` as JSON and Markdown reports.

## Components
- `cases.json`: Test cases with prompt, optional context (ground truth), and tags.
- `config.yaml`: Thresholds and model configuration (provider, model id, limits).
- `run_model_evaluation.py`: Main script to generate answers (OpenAI) and score them (Vectara hallucination + Detoxify toxicity).

## Environment variables
- `OPENAI_API_KEY` (required): Used to query the OpenAI model (default `gpt-4o-mini`).
- `HF_TOKEN` (optional but recommended): Used to call Hugging Face Inference API for `vectara/hallucination_evaluation_model`.

You can place these in your shell or a local `.env` file and run with `python -m evaluation.run_model_evaluation`.

## Install (local)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY=sk-xxxx
export HF_TOKEN=hf_xxxx   # recommended for stable hallucination scoring
python -m evaluation.run_model_evaluation
```

## Outputs
- `results/model_eval/report.json`: Structured results per case with scores and pass/fail booleans
- `results/model_eval/report.md`: Human-readable summary table

## Notes
- Hallucination scoring requires providing a meaningful `context` (ground truth) for best quality. If `context` is missing, the evaluator will still run but may be less reliable.
- Thresholds are configurable in `config.yaml`. Start conservative, then tune based on your domain needs.
- For CI, see `.github/workflows/model-eval.yml`. The workflow runs nightly and on manual dispatch, uploads artifacts for download.
