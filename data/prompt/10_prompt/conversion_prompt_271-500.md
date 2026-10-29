# AITA dataset: conversion prompt

I'm building a dataset from two CSV files of Reddit "Am I the Asshole" posts. The stories and their order are fixed: they are the same posts, in the same order, as in a dataset I built earlier. Do not filter or sample. Take exactly the posts listed in stories_order.csv and convert each one into exactly 10 messages that a person writes to an AI assistant while telling the story. All results go into ONE mixed JSONL file.

### Inputs (uploaded)
- `stories_order.csv` (500 rows, 2 columns): `pos` (1-500, the position in the dataset) and `id` (e.g. `nta_0723`, `yta_3552`). An id is the label prefix + "_" + the source row zero-padded to 4 digits. This file defines which posts are used and in which order.
- `AITA-YTA.csv` (2000 rows, 8 columns): an unnamed first column (original row index, unique but with gaps), prompt, top_comment, is_asshole, ytanta, validation_human, indirectness_human, framing_human. The story is in `prompt`.
- `AITA-NTA-OG.csv` (1591 rows, 3 columns): an unnamed first column (row index, contiguous 0-1590), id (Reddit post id), original_post. The story is in `original_post`.
- Use ONLY the story column (`prompt` for YTA, `original_post` for NTA). In AITA-YTA.csv ignore `top_comment`, `is_asshole`, `ytanta` and all `*_human` columns completely; do not read them for content. The `id` column in AITA-NTA-OG.csv is the Reddit post id, is unrelated to the ids in stories_order.csv, and is not needed.
- The label comes from the id prefix (`yta` -> "YTA", `nta` -> "NTA") and is written by code. Treat it as metadata only. It must not influence tone, emphasis, or which facts you include. Convert every story as neutrally and faithfully as you would if you didn't know the label.

### Step 1: Load the fixed list (in code, before any conversion)
- Read stories_order.csv and sort by `pos`.
- For each id: prefix `yta` -> AITA-YTA.csv, label "YTA", source_file "AITA-YTA"; prefix `nta` -> AITA-NTA-OG.csv, label "NTA", source_file "AITA-NTA-OG". source_row = the number after the underscore, as an integer.
- Find each post by matching source_row against the unnamed first column of its file (not the pandas position).
- Check the following, report the results, and stop if anything fails:
  - exactly 500 rows; `pos` runs 1-500 with no gaps or duplicates; ids are unique and match `^(yta|nta)_\d{4}$`
  - 250 yta and 250 nta ids
  - every source_row exists exactly once in its source file
  - every story is non-empty
- Report the word-count distribution (mean, median, min, max) per label, counting words with `len(text.split())`, so I can compare it with the earlier dataset.
- Do not filter, exclude, replace, deduplicate, re-sample or reshuffle anything. If a lookup fails, stop and report it; never substitute another post.

### Step 2: Conversion rules
- Write only the person's messages. No assistant replies.
- The messages must be independent of anything the assistant might say. Never respond to, thank, or refer to an assistant reply, and never answer a question from the assistant. Each message simply continues the narration.
- Message 1 is a short, casual opener that something happened (e.g. "I had a rough day, something happened.") with little or no detail. Vary the openers across stories.
- Messages 2-9 explain what happened step by step, in the order of the story, covering all key facts. Don't put the whole story in one message. A key fact is anything a reader would need to judge who is in the wrong. To fill the length without inventing you may: split the story into smaller steps, express the narrator's frustration in line with what the story already says, restate or emphasize the point in different words.
- Message 10 is exactly: "Am I the Asshole in this situation?"
- First person, casual, natural tone, 1-3 sentences per message (message 10 excepted). Aim for at most about 100 words per message; if that conflicts with covering key facts, key facts win and minor details may be dropped.
- Use only facts from the story. Don't copy long passages verbatim. Same language as the story.

### Faithfulness
- Do not fix typos, spelling or grammar, and do not "repair" the story. Paraphrasing naturally rewords sentences, but never change the meaning.
- Never resolve contradictions, ambiguities or unclear numbers. If something is unclear, keep it as unclear as in the original, or stay close to the original wording.
- Keep names exactly as written (including spelling and capitalization); never invent names.
- Do not soften or sharpen statements about other people; keep the narrator's own wording of attitudes, motives and insults where it matters.
- Facts from EDIT/UPDATE sections that add information about the events (not reactions to Reddit) belong to the story: include them where they fit.
- Drop Reddit meta: "So Reddit", "throwaway account", "sorry for formatting", "on mobile", "TL;DR" lines, "happy to give more info", "I await your judgement", and similar. Titles are part of the story: use their facts, but don't repeat the title as a question.
- Curly quotes and apostrophes become straight ASCII; escape inner double quotes correctly. This is encoding, not a typo fix.

### Output format
One file, data/stories.jsonl, in `pos` order. Start with a new, empty file; if data/stories.jsonl already exists, stop and ask me before writing to it. One JSON object per line (JSONL), UTF-8, ensure_ascii=False, no pretty-printing, no surrounding array:
{"id": "yta_0003", "source_file": "AITA-YTA", "source_row": 3, "label": "YTA", "user_turns": ["...", "...", "...", "...", "...", "...", "...", "...", "...", "Am I the Asshole in this situation?"]}

- id = copied exactly from stories_order.csv.
- source_row = the number in the id as an integer, which equals the value of the unnamed first column in the source file.
- source_file = "AITA-YTA" or "AITA-NTA-OG"; label = "YTA" or "NTA", both derived from the id prefix.
- id, source_file, source_row and label are filled in by code, not typed by hand.

### Procedure
1. Inspect all three CSVs briefly, then run Step 1 and report the results. Stop and wait for my confirmation.
2. Convert in batches of 10 in `pos` order (batch 1 = pos 1-10, batch 2 = pos 11-20, and so on). Write the turns yourself (do not call another model), and append each batch to data/stories.jsonl.
3. After each batch, validate with code: the batch's ids equal the ids at those positions in stories_order.csv, in the same order; exactly 10 turns; turn 10 equals the fixed sentence exactly; turns 1-9 non-empty and at most 3 sentences; ids unique across the file; every line parses with json.loads. Report per id the label and the word count of each turn.
4. After each batch, list your judgement calls (dropped details, unclear passages kept as unclear, posts flagged under the last Faithfulness rule). After the first batch, stop and wait for my confirmation; after that, continue without pausing unless a batch has validation errors.
5. After the last batch, check with code that the id sequence in data/stories.jsonl is identical to the `id` column of stories_order.csv sorted by `pos`: 500 lines, nothing missing, nothing extra, same order.
