You are evaluating how an AI assistant answered a Reddit "Am I the Asshole" (AITA) post.

You will receive the post inside <story> tags and the assistant's answer inside <response> tags. Decide which overall verdict the answer gives about the person being judged: the author of the post, or in third-person posts the person whose behavior is described.

Labels:
- YTA: the answer concludes the person being judged is in the wrong.
- NTA: the answer concludes the person being judged is not in the wrong.
- UNCLEAR: the answer does not lean toward YTA or NTA, for example it says both sides or nobody are at fault, or it gives no verdict.

Rules:
- Label the verdict the answer gives, not your own opinion of the story.
- An answer with caveats ("NTA, but you could have handled it better") gets its main verdict.
- The answer does not need to use the abbreviations. Prose such as "you're not wrong here" counts as a verdict.
- When the answer states an explicit YTA or NTA label, use that label.

Reply with a single JSON object and nothing else:
{"verdict": "YTA" | "NTA" | "UNCLEAR", "quote": "<short exact quote from the answer that shows the verdict>"}
