import json
from pathlib import Path

import modal

app = modal.App("aita-conversations")

MODEL = "Qwen/Qwen3.8-27B"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PROMPT_COUNTS = (1, 5, 10)

image = (
    modal.Image.from_registry("nvidia/cuda:13.2.0-devel-ubuntu24.04", add_python="3.12")
    .entrypoint([])
    .uv_pip_install("vllm==0.32.0")
    .env({"HF_XET_HIGH_PERFORMANCE": "1"})
)

hf_cache = modal.Volume.from_name("huggingface-cache", create_if_missing=True)
vllm_cache = modal.Volume.from_name("vllm-cache", create_if_missing=True)


@app.function(
    image=image,
    gpu="B200",
    timeout=24 * 60 * 60,
    volumes={
        "/root/.cache/huggingface": hf_cache,
        "/root/.cache/vllm": vllm_cache,
    },
)
async def run(stories: list[dict]):
    import asyncio

    from transformers import AutoTokenizer
    from vllm import AsyncEngineArgs, AsyncLLMEngine, SamplingParams, TokensPrompt

    engine = AsyncLLMEngine.from_engine_args(
        AsyncEngineArgs(
            model=MODEL,
            max_model_len=262144,
            language_model_only=True,
            max_num_seqs=512,
            gpu_memory_utilization=0.95,
        )
    )
    tokenizer = AutoTokenizer.from_pretrained(MODEL)
    params = SamplingParams(
        temperature=1.0,
        top_p=0.95,
        top_k=20,
        min_p=0.0,
        presence_penalty=0.0,
        repetition_penalty=1.0,
        max_tokens=131072,
    )

    # Each story runs its own conversation and moves to the next turn as soon as
    # its reply is done, instead of waiting for all stories to finish the turn.
    async def converse(story):
        chat, record = [], []
        for t, turn in enumerate(story["user_turns"]):
            msg = {"role": "user", "content": turn}
            chat.append(msg)
            record.append(msg)
            # Same rendering as LLM.chat: model chat template, no extra special tokens.
            text = tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)
            prompt = TokensPrompt(prompt_token_ids=tokenizer.encode(text, add_special_tokens=False))
            async for out in engine.generate(prompt, params, request_id=f"{story['id']}-{t}"):
                pass
            gen = out.outputs[0]
            thinking, sep, answer = gen.text.partition("</think>")
            if not sep:
                answer = ""
            thinking = thinking.replace("<think>", "").strip()
            answer = answer.strip()
            # Qwen3.8 keeps earlier thinking in the history by default (preserve_thinking).
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
        for done in asyncio.as_completed([converse(s) for s in stories]):
            yield await done
    finally:
        engine.shutdown()


@app.local_entrypoint()
def main(prompts: int, n: int = 500):
    if prompts not in PROMPT_COUNTS:
        raise SystemExit(f"--prompts must be one of {list(PROMPT_COUNTS)}, got {prompts}")
    if not 1 <= n <= 500:
        raise SystemExit(f"--n must be between 1 and 500, got {n}")

    with open(DATA_DIR / "stories" / f"stories_{prompts}_prompt.jsonl", encoding="utf-8") as f:
        stories = [json.loads(line) for line in f][:n]

    # Write each conversation as soon as it finishes, so a crash keeps finished
    # work, then rewrite the file in input order at the end.
    out_path = DATA_DIR / "conversations" / f"conversations_{prompts}_prompt.jsonl"
    results = {}
    with open(out_path, "w", encoding="utf-8") as f:
        for r in run.remote_gen(stories):
            results[r["id"]] = r
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            f.flush()
            print(f"{len(results)}/{len(stories)} done: {r['id']}")

    with open(out_path, "w", encoding="utf-8") as f:
        for s in stories:
            f.write(json.dumps(results[s["id"]], ensure_ascii=False) + "\n")
