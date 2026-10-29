import json
from pathlib import Path

import modal
import yaml

app = modal.App("aita-judge")

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CONFIG_DIR = ROOT / "config"
DATASETS = ["1_prompt", "5_prompt", "10_prompt", "third_person"]
LABELS = {"YTA", "NTA", "UNCLEAR"}
TASKS = {"answer": ("content", "response"), "cot": ("thinking", "reasoning")}
FIELDS = {
    "answer": ["verdict", "quote"],
    "cot": ["verdict", "quote", "softening", "softening_quote"],
}

image = (
    modal.Image.from_registry("nvidia/cuda:13.2.0-devel-ubuntu24.04", add_python="3.12")
    .entrypoint([])
    .uv_pip_install("vllm==0.32.0", "openai-harmony")
    .env({"HF_XET_HIGH_PERFORMANCE": "1", "VLLM_USE_FLASHINFER_SAMPLER": "0"})
)

hf_cache = modal.Volume.from_name("huggingface-cache", create_if_missing=True)
vllm_cache = modal.Volume.from_name("vllm-cache", create_if_missing=True)
results = modal.Volume.from_name("aita-results", create_if_missing=True)


def key(record):
    return record["dataset"], record["id"]


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
async def run(config: dict, prompts: dict, items: list[dict], out_name: str):
    import asyncio

    from openai_harmony import (
        Conversation,
        DeveloperContent,
        HarmonyEncodingName,
        Message,
        ReasoningEffort,
        Role,
        SystemContent,
        load_harmony_encoding,
    )
    from vllm import AsyncEngineArgs, AsyncLLMEngine, SamplingParams, TokensPrompt

    out_path = Path("/results") / out_name
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out_path.exists():
        done = {key(json.loads(line)) for line in out_path.read_text(encoding="utf-8").splitlines()}
    todo = [it for it in items if key(it) not in done]
    print(f"{len(done)} already saved, {len(todo)} to run")
    if not todo:
        return

    engine = AsyncLLMEngine.from_engine_args(
        AsyncEngineArgs(
            model=config["model"],
            max_model_len=config["max_model_len"],
            max_num_seqs=512,
            gpu_memory_utilization=0.95,
        )
    )
    encoding = load_harmony_encoding(HarmonyEncodingName.HARMONY_GPT_OSS)
    params = SamplingParams(**config["sampling"], stop_token_ids=encoding.stop_tokens_for_assistant_actions())
    system = SystemContent.new().with_reasoning_effort(ReasoningEffort[config["reasoning_effort"].upper()])

    async def judge(item, task):
        field, tag = TASKS[task]
        if not item[field]:
            return None
        text = f"<story>\n{item['story']}\n</story>\n\n<{tag}>\n{item[field]}\n</{tag}>"
        convo = Conversation.from_messages(
            [
                Message.from_role_and_content(Role.SYSTEM, system),
                Message.from_role_and_content(Role.DEVELOPER, DeveloperContent.new().with_instructions(prompts[task])),
                Message.from_role_and_content(Role.USER, text),
            ]
        )
        prompt = TokensPrompt(prompt_token_ids=encoding.render_conversation_for_completion(convo, Role.ASSISTANT))
        for attempt in range(3):
            request_id = f"{item['dataset']}-{item['id']}-{task}-{attempt}"
            async for out in engine.generate(prompt, params, request_id=request_id):
                pass
            gen = out.outputs[0]
            try:
                messages = encoding.parse_messages_from_completion_tokens(gen.token_ids, Role.ASSISTANT)
                final = next(m for m in messages if m.channel == "final")
                result = json.loads(final.content[0].text)
                if (
                    result["verdict"] in LABELS
                    and result["quote"].strip()
                    and (task == "answer" or isinstance(result["softening"], bool))
                ):
                    return {k: result.get(k, "") for k in FIELDS[task]}
            except Exception:
                pass
        raise RuntimeError(
            f"no valid {task} judgement for {item['dataset']}/{item['id']} "
            f"(finish_reason={gen.finish_reason}, tokens={len(gen.token_ids)}): {gen.text[-300:]!r}"
        )

    async def evaluate(item):
        answer, cot = await asyncio.gather(judge(item, "answer"), judge(item, "cot"))
        return {"dataset": item["dataset"], "id": item["id"], "label": item["label"], "answer": answer, "cot": cot}

    failed = 0
    try:
        with open(out_path, "a", encoding="utf-8") as f:
            for i, finished in enumerate(asyncio.as_completed([evaluate(it) for it in todo]), 1):
                try:
                    r = await finished
                except RuntimeError as e:
                    failed += 1
                    print(e)
                    continue
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
                f.flush()
                if i % 50 == 0 or i == len(todo):
                    await results.commit.aio()
                print(f"{i}/{len(todo)} done: {r['dataset']}/{r['id']}")
    finally:
        await results.commit.aio()
        engine.shutdown()
    print(f"{failed} failed, rerun to retry them")


@app.local_entrypoint()
def main(model: str = "qwen3.8-27b", n: int = 500, fetch_only: bool = False):
    config = yaml.safe_load((CONFIG_DIR / "gpt-oss-120b.yaml").read_text(encoding="utf-8"))
    prompts = yaml.safe_load((CONFIG_DIR / "judge_prompts.yaml").read_text(encoding="utf-8"))

    items = []
    for dataset in DATASETS:
        path = DATA_DIR / "conversations" / model / f"conversations_{dataset}.jsonl"
        if not path.exists():
            raise SystemExit(f"Missing {path.relative_to(ROOT)}")
        with open(DATA_DIR / "stories" / f"stories_{dataset}.jsonl", encoding="utf-8") as f:
            labels = {s["id"]: s["label"] for s in map(json.loads, f)}
        with open(path, encoding="utf-8") as f:
            conversations = [json.loads(line) for line in f][:n]
        for c in conversations:
            last = [m for m in c["messages"] if m["role"] == "assistant"][-1]
            items.append(
                {
                    "dataset": dataset,
                    "id": c["id"],
                    "label": labels[c["id"]],
                    "story": "\n\n".join(m["content"] for m in c["messages"] if m["role"] == "user"),
                    "thinking": last["thinking"],
                    "content": last["content"],
                }
            )

    name = f"judge/{model}.jsonl"
    if not fetch_only:
        run.spawn(config, prompts, items, name).get()

    try:
        text = b"".join(results.read_file(name)).decode("utf-8")
    except FileNotFoundError:
        raise SystemExit(f"Nothing saved yet for {name}")
    saved = {key(r): r for r in map(json.loads, text.splitlines())}

    out_dir = DATA_DIR / "judgements" / model
    out_dir.mkdir(parents=True, exist_ok=True)
    for dataset in DATASETS:
        wanted = [it for it in items if it["dataset"] == dataset]
        found = [saved[key(it)] for it in wanted if key(it) in saved]
        with open(out_dir / f"judgements_{dataset}.jsonl", "w", encoding="utf-8") as f:
            for r in found:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"Wrote {len(found)}/{len(wanted)} judgements to data/judgements/{model}/judgements_{dataset}.jsonl")
