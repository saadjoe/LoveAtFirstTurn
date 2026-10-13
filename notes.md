# 8th October 2026:
  - **USE ELEPHANT BENCHMARK AND DATASET!**
  - Further Exploring of ELEPHANT paper
    
  - come up with a story using ELEPHANT data (~150-300 prompts but still suitable for context window of open weight models) --ELEPHANT data: https://osf.io/r3dmj/files/4chzv?view_only=37ee66a8020a45c29a38bd704ca61067
  - Literature research needed
  - chose x amount models (prob. Open weight like vLLM, Ollama...)
  - create script to feed the prompts (story) each after another
  - report each conversation with each model -> analyze where it started to hallucinate
  - recreating ELEPHANT with longer dialog, see if results change compared to ELPHANTs results (Include CoT, see how model reasoned -> Truthful / Honest; created false answers on purpose)
  - similar stories with different contexts and maybe length(?)

**Need to be aware of:** Context Window, length of report / answers / CoT to analyze -> Using LLM judge(?), correct data usage.

**Prio:**
1) Dataset! -> What story, how to look like, how long, Tags(?)(Friendly, Romance, Advise, etc.),
2) Chose models, first one is Qwen. Other models tbd.
3) Run Tests, one sided conversation, do we need to react to the models answers
4) What and how to measure, see how other paper do that(?)


# 13th October 2026:
- LLM as a judge, keep prompts the same.
- Instead of using different stories use one story -> Ask sota LLM to split the long sample(s) from AITA / ... to split into a dialog
- short: 1 prompt, medium: 7 prompts, long:  20 or different splits: 1/5/10 , 1/10/20, etc. experiment if time left. 
- Start small with ~100 samples

- PLAN: come up with a prompt to enhance the data
- Instruction: template from reddit (https://docs.google.com/document/d/1UtTB-M_IzYqC5h7yWmP1J8UIMnCmqHIDSRpfDYiiUDQ/edit?tab=t.0)
- log conversation for judge afterwards, doing that like in the ELEPHANT paper.
