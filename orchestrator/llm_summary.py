import os
import json
from typing import Dict, Any
import argparse
from groq import Groq
from .analysis import compare_run_to_baseline
from .config import load_config

def generate_with_llm(result: Dict[str, Any]) -> str:
    """
    Use the Groq API to generate a richer diagnostic summary,
    with behavior controlled by config.yaml.
    """
    
    config = load_config()
    llm_cfg = config.get("llm", {})

    if not llm_cfg.get("enabled", True):
        return "LLM summaries are disabled in config.yaml."

    model = llm_cfg.get("model", "llama-3.3-70b-versatile")
    temperature = llm_cfg.get("temperature", 0.2)
    max_words = llm_cfg.get("max_words", 300)


    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return "GROQ_API_KEY is not set. Please export it in your environment."

    client = Groq(api_key=api_key)

    prompt = (
        "You are a senior reliability engineer. Given this JSON describing a baseline vs failure run, "
        "write a clear, structured summary of what happened. Highlight:\n"
        "- Overall throughput vs baseline\n"
        "- Latency changes\n"
        "- Error rate behavior\n"
        "- Anomaly windows and their timing\n"
        "- Approximate recovery time and what it means for reliability\n\n"
        f"Keep it under ~{max_words} words and use bullet points where helpful.\n\n"
        f"JSON:\n{json.dumps(result, indent=2)}"
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a senior reliability engineer."},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
    )

    return response.choices[0].message.content.strip()


def generate_summary(result: Dict[str, Any]) -> str:

    return generate_with_llm(result)


def main():
    parser = argparse.ArgumentParser(description="Generate a human-readable summary for a run vs baseline.")
    parser.add_argument("--baseline-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output-path", required=False)
    args = parser.parse_args()

    result = compare_run_to_baseline(args.baseline_id, args.run_id)
    drop = result.get("throughput_drop_pct")
    if drop is not None:
        if drop < 0:
            explanation = (
                f"Run throughput is {abs(drop):.2f}% HIGHER than baseline on average despite failure injection"
            )
        else:
            explanation = (
                f"Run throughput is {drop:.2f}% LOWER than baseline on average."
            )
    result["throughput_explanation"] = explanation
    
    summary = generate_summary(result)

    if args.output_path:
        with open(args.output_path, "w") as f:
            f.write(summary)
        print(f"Summary written to {args.output_path}")
    else:
        print(summary)
    
if __name__ == "__main__":
    main()