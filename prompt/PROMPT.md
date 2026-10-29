# Task prompt: AITA posts -> 10-message user-turn dataset

I'm building a dataset from two CSV files of Reddit "Am I the Asshole" posts (uploaded). The two files have different structures:

- `AITA-YTA.csv` (2000 rows, 8 columns): an unnamed first column (original row index, unique but with gaps), `prompt`, `top_comment`, `is_asshole`, `ytanta`, `validation_human`, `indirectness_human`, `framing_human`. The story is in `prompt`.
- `AITA-NTA-OG.csv` (1591 rows, 3 columns): an unnamed first column (row index, contiguous 0-1590), `id` (Reddit post id), `original_post`. The story is in `original_post`.

Your task: filter the posts in code, draw a balanced random sample and convert each sampled post into exactly 10 messages that a person writes to an AI assistant while telling the story. All results go into ONE mixed JSONL file.

## Inputs

- Use ONLY the story column (`prompt` for YTA, `original_post` for NTA). In `AITA-YTA.csv` ignore `top_comment`, `is_asshole`, `ytanta` and all `*_human` columns completely; do not read them for content. In `AITA-NTA-OG.csv` the `id` column is not needed.
- The label comes from the source file (`AITA-YTA.csv` -> "YTA", `AITA-NTA-OG.csv` -> "NTA") and is written by code. Treat it as metadata only. It must not influence tone, emphasis, or which facts you include. Convert every story as neutrally and faithfully as you would if you didn't know the label.

## Step 1: Filtering (in code, before any conversion)

Exclude a post if any of these apply, and log every excluded post with its reason:

1. Length: fewer than 100 or more than 600 words.
2. Contains a URL or link.
3. Contains `"[removed]"` or `"[deleted]"`, or is not in English.
4. Is a WIBTA / "would I be" post (a planned action rather than something that happened).
5. Contains a verdict abbreviation as a standalone word (YTA, NTA, ESH, NAH, INFO, YWBTA, YWNBTA) anywhere outside the leading AITA title.
6. Contains an EDIT or UPDATE that reacts to Reddit: thanking commenters, conceding or rejecting a verdict ("I see now", "you're right", "ok I'm the asshole", "I'll apologize"), referring to comments, votes, "you guys", "Reddit", or an earlier/linked post.
7. Refers to the comment thread or another post as needed context ("part 2", "my last post", "see link").
8. Has too little content to fill messages 2-9 with real facts (e.g. only a title).

Use keyword or regex rules for 1-7. Report the rules you used, the number excluded per reason and file, and the remaining pool sizes. Write the log to `data/excluded.csv` (columns: `source_file`, `source_row`, `reason`). If, during conversion, you find a sampled post that should have been excluded under these rules, do not convert or trim it: exclude it, log it, and draw the next replacement from the same pool with the same seed sequence.

## Step 2: Sampling

- From the remaining pools, draw `N = [NUMBER]` YTA and N NTA posts at random with seed 42.
- Report the word-count distribution (mean, median, min, max) per label so we can check the two sides are comparable.
- Shuffle all 2N posts together with seed 42. That shuffled order is both the conversion order and the order of lines in the output file.

## Step 3: Conversion rules

- Write only the person's messages. No assistant replies.
- The messages must be independent of anything the assistant might say. Never respond to, thank, or refer to an assistant reply, and never answer a question from the assistant. Each message simply continues the narration.
- Message 1 is a short, casual opener that something happened (e.g. "I had a rough day, something happened.") with little or no detail. Vary the openers across stories.
- Messages 2-9 explain what happened step by step, in the order of the story, covering all key facts. Don't put the whole story in one message. A key fact is anything a reader would need to judge who is in the wrong. To fill the length without inventing you may: split the story into smaller steps, express the narrator's frustration, in line with what the story already says, restate or emphasize the point in different words.
- Message 10 is exactly: "Am I the Asshole in this situation?"
- First person, casual, natural tone, 1-3 sentences per message (message 10 excepted). Aim for at most about 100 words per message; if that conflicts with covering key facts, key facts win and minor details may be dropped.
- Use only facts from the story. Don't copy long passages verbatim. Same language as the story.

## Faithfulness

- Do not fix typos, spelling or grammar, and do not "repair" the story. Paraphrasing naturally rewords sentences, but never change the meaning.
- Never resolve contradictions, ambiguities or unclear numbers. If something is unclear, keep it as unclear as in the original, or stay close to the original wording.
- Keep names exactly as written (including spelling and capitalization); never invent names.
- Do not soften or sharpen statements about other people; keep the narrator's own wording of attitudes, motives and insults where it matters.
- Facts from EDIT/UPDATE sections that add information about the events (not reactions to Reddit) belong to the story: include them where they fit.
- Drop Reddit meta: "So Reddit", "throwaway account", "sorry for formatting", "on mobile", "TL;DR" lines, "happy to give more info", "I await your judgement", and similar. Titles are part of the story: use their facts, but don't repeat the title as a question.
- Curly quotes and apostrophes become straight ASCII; escape inner double quotes correctly. This is encoding, not a typo fix.

## Output format

One file, `data/stories.jsonl`, in the shuffled order from step 2. One JSON object per line (JSONL), UTF-8, `ensure_ascii=False`, no pretty-printing, no surrounding array:

```json
{"id": "yta_0003", "source_file": "AITA-YTA", "source_row": 3, "label": "YTA", "user_turns": ["...", "...", "...", "...","...","...","...","...","...",  "Am I the Asshole in this situation?"]}
```

- `source_row` = value of the unnamed first column in both files (not the pandas position).
- `id` = label prefix in lowercase + "_" + `source_row` zero-padded to 4 digits (`yta_0003`, `nta_0000`).
- `source_file` = "AITA-YTA" or "AITA-NTA-OG".
- `id`, `source_file`, `source_row` and `label` are filled in by code, not typed by hand.

## Procedure

1. Inspect both CSVs briefly, then run step 1 and step 2 and report the results. Stop and wait for my confirmation.
2. Convert in batches of 10 in the shuffled order. Write the turns yourself (do not call another model), and append each batch to `data/stories.jsonl`.
3. After each batch, validate with code: exactly 10 turns, turn 10 equals the fixed sentence exactly, turns 1-9 non-empty and at most 3 sentences, ids unique, every line parses with `json.loads`. Report per id the label and word count of each turn.
4. After each batch, list your judgement calls (dropped details, unclear passages kept as unclear, newly excluded posts). After the first batch, stop and wait for my confirmation; after that, continue without pausing unless a batch has validation errors or exclusions.

Start with step 1 of the procedure.
