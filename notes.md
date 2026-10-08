8th October 2026:
  - **USE ELEPHANT BENCHMARK AND DATASET!**
  - Further Exploring of ELEPHANT paper
    
  - come up with a story using ELEPHANT data (~150-300 prompts but still suitable for context window of open weight models) --ELEPHANT data: https://osf.io/r3dmj/files/4chzv?view_only=37ee66a8020a45c29a38bd704ca61067
  - Literature research needed
  - chose x amount models (prob. Open weight like vLLM, Ollama...)
  - create script to feed the prompts (story) each after another
  - report each conversation with each model -> analyze where it started to hallucinate
  - recreating ELEPHANT with longer dialoge, see if results change compared to ELPHANTs results (Include CoT, see how model reasoned -> Truthful / Honest; created false answers on purpose)
  - similar stories with different contexts and maybe length(?)

**Need to be aware of:** Context Window, length of report / answers / CoT to analyze -> Using LLM judge(?), correct data usage.

**Prio:**
1) Dataset! -> What story, how to look like, how long, Tags(?)(Friendly, Romance, Advise, etc.),
2) Chose models, first one is Qwen. Other models tbd.
3) Run Tests, one sided conversation, do we need to react to the models answers
4) What and how to measure, see how other paper do that(?)
