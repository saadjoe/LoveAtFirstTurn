I'm converting Reddit "Am I the Asshole" posts into short multi-message conversations. The posts have already been filtered and sampled; your job is only the conversion of one fixed range.

Uploaded files:
- AITA-YTA.csv: story column `prompt`; ignore all other columns.
- AITA-NTA-OG.csv: story column `original_post`; ignore all other columns.
- order.csv: the sampled posts in their fixed order (id, source_file, source_row, label, ...).
- convert_tools.py: helper script (run it from /mnt/user-data/uploads/ as shown below) for reading, appending, flagging and validating. Use it for all file operations; do not write your own replacement.

Your range: order.csv rows 1 to 100 (1-based, inclusive). Do not convert anything outside it.

## Task
Turn each post into exactly 5 messages written by a person who is telling the story to an AI assistant and asking for guidance.

The label in order.csv is metadata only. It must not influence tone, emphasis, or which facts you include. Convert every story as neutrally and faithfully as you would if you didn't know it.

## Conversion rules
- Write only the person's messages. No assistant replies.
- The messages must be independent of anything the assistant might say. Never respond to, thank, or refer to an assistant reply, and never answer a question from the assistant. Each message simply continues the narration.
- Message 1 is a short, casual opener that something happened (e.g. "I had a rough day, something happened.") with little or no detail. Vary the openers across stories.
- Messages 2-4 explain what happened step by step, in the order of the story, covering all key facts. Don't put the whole story in one message. A key fact is anything a reader would need to judge who is in the wrong.
- Message 5 is exactly: "Am I the Asshole in this situation?" (the script adds it).
- First person, casual, natural tone, 1-3 sentences per message. Aim for at most about 100 words per message; if that conflicts with covering key facts, key facts win and minor details may be dropped.
- Use only facts from the story. Don't copy long passages verbatim. Same language as the story.

## Faithfulness
- Do not fix typos, spelling or grammar, and do not "repair" the story. Paraphrasing naturally rewords sentences, but never change the meaning.
- Never resolve contradictions, ambiguities or unclear numbers. If something is unclear, keep it as unclear as in the original, or stay close to the original wording.
- Keep names exactly as written (spelling and capitalization); never invent names.
- Do not soften or sharpen statements about other people; keep the narrator's own wording of attitudes, motives, insults and crude or profane language (e.g. "ghosted his ass" stays, not "ghosted him").
- Facts from EDIT/UPDATE sections that add information about the events belong to the story: include them where they fit.
- Drop Reddit meta: "So Reddit", "throwaway account", "sorry for formatting", "on mobile", "TL;DR" lines, "happy to give more info", "I await your judgement", and similar. Titles are part of the story: use their facts, but don't repeat the title as a question. Closing questions to the reader become narration only if they contain facts.
- Straight ASCII quotes and apostrophes only; no line breaks inside a message.

## Flag instead of converting
If a post in your range shows any of the following, do not convert or trim it. Run `flag` with a short reason and move on. Do not look for a replacement; replacements are handled separately.
- a link or URL, or a reference to another post or the comment thread
- a planned rather than past action ("would I be the asshole if...", WIBTA)
- a verdict abbreviation (YTA, NTA, ESH, NAH, INFO) outside the title
- an EDIT/UPDATE that reacts to Reddit (thanks, comments, votes, conceding or rejecting a verdict)
- any self-assessment of the verdict, in either direction or hedged ("I probably am", "I know I'm not the asshole", "maybe I'm the asshole", "I don't think I'm TA")
- too little content to fill messages 2-4 with real facts

## Procedure
Work in batches of 10 rows. For each batch:
1. `python /mnt/user-data/uploads/convert_tools.py show S E` to read the posts, where S-E are the 10 rows of the current batch (first batch: `show 1 10`).
2. Flag posts that match the list above.
3. Write the turns for the others into a JSON file {"<id>": ["msg1", "msg2", "msg3", "msg4"], ...}, in order.csv order, and run `python /mnt/user-data/uploads/convert_tools.py append 1 100 batch.json`. The script refuses wrong order, more than 3 sentences, curly quotes and line breaks; fix and rerun if it does.
4. Run `python /mnt/user-data/uploads/convert_tools.py validate 1 100`.
5. Report briefly: the validation output, flagged ids with reasons, and judgement calls (dropped details, unclear passages kept as unclear). Keep the report short.

After the first batch, stop and wait for my confirmation. After that, continue through the whole range without pausing unless validation fails.

When the range is done, run validate once more and share stories_001-100.jsonl and flagged_001-100.csv from /mnt/user-data/outputs/.

Start with the first batch.
