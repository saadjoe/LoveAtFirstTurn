import json
from pathlib import Path

import modal

app = modal.App("aita-conversations")

MODEL = "Qwen/Qwen3.5-9B"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
LENGTHS = {"short": "stories.jsonl", "long": "10_prompt_stories.jsonl"}

image = (
    modal.Image.from_registry("nvidia/cuda:13.2.0-devel-ubuntu24.04", add_python="3.12")
    .entrypoint([])
    .uv_pip_install("vllm")
    .env({"HF_XET_HIGH_PERFORMANCE": "1"})
)

hf_cache = modal.Volume.from_name("huggingface-cache", create_if_missing=True)
vllm_cache = modal.Volume.from_name("vllm-cache", create_if_missing=True)


@app.function(
    image=image,
    gpu="A100-40GB",
    timeout=3 * 60 * 60,
    volumes={
        "/root/.cache/huggingface": hf_cache,
        "/root/.cache/vllm": vllm_cache,
    },
)
def run(stories: list[dict]):
    from vllm import LLM, SamplingParams

    llm = LLM(model=MODEL, max_model_len=65536, language_model_only=True)
    params = SamplingParams(
        temperature=1.0,
        top_p=0.95,
        top_k=20,
        min_p=0.0,
        presence_penalty=1.5,
        repetition_penalty=1.0,
        max_tokens=32768,
    )

    chats = [[] for _ in stories]
    records = [[] for _ in stories]
    for t in range(len(stories[0]["user_turns"])):
        for chat, record, story in zip(chats, records, stories):
            msg = {"role": "user", "content": story["user_turns"][t]}
            chat.append(msg)
            record.append(msg)
        outputs = llm.chat(chats, params)
        for chat, record, out in zip(chats, records, outputs):
            thinking, sep, answer = out.outputs[0].text.partition("</think>")
            if not sep:
                answer = ""
            thinking = thinking.replace("<think>", "").strip()
            answer = answer.strip()
            chat.append({"role": "assistant", "content": answer})
            record.append({"role": "assistant", "thinking": thinking, "content": answer})

    return [{"id": s["id"], "messages": r} for s, r in zip(stories, records)]


@app.local_entrypoint()
def main(length: str, n: int = 500):
    if length not in LENGTHS:
        raise SystemExit(f"--length must be one of {list(LENGTHS)}, got {length!r}")
    if not 1 <= n <= 500:
        raise SystemExit(f"--n must be between 1 and 500, got {n}")

    with open(DATA_DIR / LENGTHS[length], encoding="utf-8") as f:
        stories = [json.loads(line) for line in f][:n]

    with open(DATA_DIR / f"conversations_{length}.jsonl", "w", encoding="utf-8") as f:
        for r in run.remote(stories):
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
