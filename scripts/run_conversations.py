import json
from pathlib import Path
from typing import Literal

import modal
import yaml

app = modal.App("aita-conversations")

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CONFIG_DIR = ROOT / "config"

image = (
    modal.Image.from_registry("nvidia/cuda:13.2.0-devel-ubuntu24.04", add_python="3.12")
    .entrypoint([])
    .uv_pip_install("vllm==0.32.0")
    .env({"HF_XET_HIGH_PERFORMANCE": "1"})
)

hf_cache = modal.Volume.from_name("huggingface-cache", create_if_missing=True)
vllm_cache = modal.Volume.from_name("vllm-cache", create_if_missing=True)
results = modal.Volume.from_name("aita-results", create_if_missing=True)


def key(story_id, user_turns):
    return story_id, tuple(user_turns)


def record_key(record):
    return key(record["id"], [m["content"] for m in record["messages"] if m["role"] == "user"])


@app.function(
    image=image,
    gpu="H200",
    timeout=24 * 60 * 60,
    volumes={
        "/root/.cache/huggingface": hf_cache,
        "/root/.cache/vllm": vllm_cache,
        "/results": results,
    },
)
async def run(config: dict, stories: list[dict], out_name: str):
    import asyncio

    from transformers import AutoTokenizer
    from vllm import AsyncEngineArgs, AsyncLLMEngine, SamplingParams, TokensPrompt

    out_path = Path("/results") / out_name
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out_path.exists():
        done = {record_key(json.loads(line)) for line in out_path.read_text(encoding="utf-8").splitlines()}
    todo = [s for s in stories if key(s["id"], s["user_turns"]) not in done]
    print(f"{len(done)} already saved, {len(todo)} to run")
    if not todo:
        return

    engine = AsyncLLMEngine.from_engine_args(
        AsyncEngineArgs(
            model=config["model"],
            max_model_len=config["max_model_len"],
            language_model_only=True,
            max_num_seqs=512,
            gpu_memory_utilization=0.95,
        )
    )
    tokenizer = AutoTokenizer.from_pretrained(config["model"])
    params = SamplingParams(**config["sampling"])
    think_start, think_end = config["thinking"]["start"], config["thinking"]["end"]

    async def converse(story):
        chat, record = [], []
        for t, turn in enumerate(story["user_turns"]):
            msg = {"role": "user", "content": turn}
            chat.append(msg)
            record.append(msg)
            text = tokenizer.apply_chat_template(
                chat, tokenize=False, add_generation_prompt=True, **config["chat_template_kwargs"]
            )
            prompt = TokensPrompt(prompt_token_ids=tokenizer.encode(text, add_special_tokens=False))
            async for out in engine.generate(prompt, params, request_id=f"{story['id']}-{t}"):
                pass
            gen = out.outputs[0]
            thinking, sep, answer = gen.text.partition(think_end)
            if not sep:
                answer = ""
            thinking = thinking.replace(think_start, "").strip()
            answer = answer.strip()
            chat.append({"role": "assistant", "reasoning_content": thinking, "content": answer})
            record.append(
                {
                    "role": "assistant",
                    "thinking": thinking,
                    "content": answer,
                    "finish_reason": gen.finish_reason,
                    "tokens": len(gen.token_ids),
                }
            )
        return {"id": story["id"], "messages": record}

    try:
        with open(out_path, "a", encoding="utf-8") as f:
            for i, finished in enumerate(asyncio.as_completed([converse(s) for s in todo]), 1):
                r = await finished
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
                f.flush()
                if i % 10 == 0 or i == len(todo):
                    await results.commit.aio()
                print(f"{i}/{len(todo)} done: {r['id']}")
    finally:
        engine.shutdown()


@app.local_entrypoint()
def main(
    model: str,
    dataset: Literal["1_prompt", "5_prompt", "10_prompt", "third_person"],
    n: int | None = None,
    fetch_only: bool = False,
):
    config_path = CONFIG_DIR / f"{model}.yaml"
    if not config_path.exists():
        raise SystemExit(f"No config for --model {model} in config/")
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    with open(DATA_DIR / "stories" / f"stories_{dataset}.jsonl", encoding="utf-8") as f:
        stories = [json.loads(line) for line in f][:n]

    name = f"{model}/conversations_{dataset}.jsonl"
    if not fetch_only:
        run.spawn(config, stories, name).get()

    try:
        text = b"".join(results.read_file(name)).decode("utf-8")
    except FileNotFoundError:
        raise SystemExit(f"Nothing saved yet for {name}")
    saved = {record_key(r): r for r in map(json.loads, text.splitlines())}
    found = [saved[k] for s in stories if (k := key(s["id"], s["user_turns"])) in saved]

    out_path = DATA_DIR / "conversations" / name
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for r in found:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Wrote {len(found)}/{len(stories)} conversations to data/conversations/{name}")
