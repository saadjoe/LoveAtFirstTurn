# MyBoyfriendIsAI

We test whether open-weight reasoning models tell users what they want to hear, and whether their
reasoning trace disagrees with what they finally say. Three models,
[Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B),
[Gemma 4 31B-it](https://huggingface.co/google/gemma-4-31B-it) and
[Olmo 3.1 32B Think](https://huggingface.co/allenai/Olmo-3.1-32B-Think), get Reddit "Am I the Asshole"
(AITA) stories from the [ELEPHANT](https://arxiv.org/abs/2505.13995) benchmark. Every story comes in four
versions: as one message, split over 5 or 10 messages, or retold in third person. An LLM judge then labels the verdict in each final answer and in the reasoning behind it.

## Authors

Polina Krupitsa, Joe Saad, Victor Schwarzenberger, Francesca Tubaro

## Pipeline

1. `scripts/run_conversations.py` lets every model answer every story on Modal (H200, vLLM). For the
   multi-turn stories we send one user message at a time and keep the model's real replies in the
   history. Reasoning and final answer are saved separately.
2. `scripts/run_judge.py` has [gpt-oss-120b](https://huggingface.co/openai/gpt-oss-120b) read the last
   assistant turn of each conversation in two separate calls. The first call only sees the final answer and labels it YTA, NTA or UNCLEAR. The second
   only sees the reasoning, labels it the same way and sets `softening`, which says whether the reasoning
   softens or changes the verdict to please the user or to avoid upsetting them.
3. `scripts/analyze_judgements.py` writes the tables and figures in `results/`. It leaves out reasoning
   labels that are UNCLEAR and quote the start of the reasoning. This judge failure happened almost
   only with Qwen; the counts are in `results/tables/reliability.csv`.

We measure sycophancy as the share of YTA stories (the Reddit community said the author was in the wrong)
that the model calls NTA. The NTA stories are the control for a model that leans towards NTA in general.

## Data

`data/stories/` holds the four versions: `1_prompt` is the original post, `5_prompt` and `10_prompt` split
it into a conversation, and `third_person` retells it about "a person". All four contain the same 500 posts
(250 YTA, 250 NTA, matched in length) in the same order, one story per line, for example from `5_prompt`:

```json
{"id": "yta_0004", "source_file": "AITA-YTA", "source_row": 4, "label": "YTA",
 "user_turns": ["...", "...", "...", "...", "Am I the Asshole in this situation?"]}
```

`label` is the Reddit community verdict. `source_file` and `source_row` point to the post in the ELEPHANT
CSVs.

We filtered the posts with `data/dataset_creation/filter.py` and sampled them with `sample.py`. The filter
dropped 1,794 posts, each listed with its reason in `excluded.csv`. The sample is matched in length with
25-word bins between 100 and 450 words, using seed 42. Claude wrote the multi-turn and third-person
versions, and the exact prompts and tools are in `data/prompt/`. During that conversion
we dropped 74 more posts, mostly ones where the author judges themselves or edits that react to comments,
and replaced each with a post of the same label and length bin (`conversion_exclusions.csv`). The
third-person run is documented in `third_person_notes.md` and `third_person_qa_report.json`. To 
rebuild the stories you need `AITA-YTA.csv` and `AITA-NTA-OG.csv` from the
[ELEPHANT data on OSF](https://osf.io/r3dmj/files/4chzv?view_only=37ee66a8020a45c29a38bd704ca61067).
We don't include them because we didn't change them.

### Conversations and judgements

Each line of `data/conversations/<model>/conversations_<dataset>.jsonl` is one story:
`{"id", "messages"}`. User messages have `role` and `content`. Assistant messages have `role`,
`thinking` (the reasoning), `content` (the final answer), `finish_reason` and `tokens` (number of
generated tokens).

Each line of `data/judgements/<model>/judgements_<dataset>.jsonl` is one story:
`{"dataset", "id", "label", "answer", "cot"}`. `answer` is the judgement of the final answer,
`{"verdict", "quote"}`, and `cot` the judgement of the reasoning, `{"verdict", "quote", "softening",
"softening_quote"}`. `verdict` is YTA, NTA or UNCLEAR and `quote` is the judge's evidence. Either one is
`null` when the model's answer or reasoning was empty.

### Results

The tables in `results/tables/` have one row per model and dataset:

- `sycophancy.csv`: for the answer and the reasoning (`part`), the share of YTA stories judged NTA with a
  95% Wilson interval (`ci_low`, `ci_high`), and `nta_agreement`, the share of NTA stories judged NTA.
- `comparisons.csv`: the change in sycophancy from `1_prompt` to each other dataset on the same stories
  (`diff`), with a bootstrap interval and an exact McNemar `p`.
- `cot_vs_answer.csv`: how often the two labels agree, the difference in sycophancy between answer and
  reasoning on YTA stories (`diff`, interval, `p`), the number of stories where the reasoning says YTA but
  the answer NTA and the other way round, a sign test on those two counts (`p_switch`), and the share of
  reasoning with `softening`.
- `reliability.csv`: missing judgements, empty answers and excluded judge failures.

`results/figures/sycophancy.png` plots the sycophancy table and `switches.png` the two switch counts.

## Repository

```
config/                 model configs and judge prompts
data/stories/           the four datasets
data/conversations/     <model>/conversations_<dataset>.jsonl
data/judgements/        <model>/judgements_<dataset>.jsonl
data/dataset_creation/  filtering, sampling, exclusions, third-person run notes
data/prompt/            conversion prompts and tools for 5_prompt, 10_prompt and third_person
results/                tables/*.csv and figures/*.png
scripts/                run_conversations.py, run_judge.py, analyze_judgements.py
requirements.txt        Python packages needed locally
```

## Reproduce

You need Python 3.12 to 3.14:

```bash
pip install -r requirements.txt
```

All conversations and judgements are already in the repo, so `python scripts/analyze_judgements.py`
reproduces every table and figure in `results/` without Modal.

To regenerate the data itself you also need a [Modal](https://modal.com) account with H200 access:

```bash
modal setup
```

vLLM and the other GPU packages are installed inside the Modal image that the scripts define. The models
are downloaded from Hugging Face on their first run and cached on the Modal volume `huggingface-cache`, so
there is nothing to download by hand.

Generate the conversations with one command per model and dataset. `--model` is one of `qwen3.8-27b`,
`gemma-4-31b-it` or `olmo-3.1-32b-think` (the configs in `config/`) and `--dataset` is one of `1_prompt`,
`5_prompt`, `10_prompt` or `third_person`; both are required:

```bash
modal run scripts/run_conversations.py --model qwen3.8-27b --dataset 1_prompt
modal run scripts/run_conversations.py --model qwen3.8-27b --dataset 5_prompt
modal run scripts/run_conversations.py --model qwen3.8-27b --dataset 10_prompt
modal run scripts/run_conversations.py --model qwen3.8-27b --dataset third_person
```

To keep a run going after you close the terminal, put `--detach` directly after `modal run`:

```bash
modal run --detach scripts/run_conversations.py --model qwen3.8-27b --dataset 1_prompt
```

Then judge all four datasets of a model and run the analysis:

```bash
modal run scripts/run_judge.py --model qwen3.8-27b
python scripts/analyze_judgements.py
```

Results are saved on the Modal volume `aita-results` and copied into `data/`. A run picks up where it
stopped. `--fetch-only` only downloads what is already saved, which you need after a detached run whose
terminal you closed. `--n` is optional and limits the number of stories for a test run; without it the
full dataset is used.
