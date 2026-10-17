import re, json
import pandas as pd

UP = "/mnt/user-data/uploads/"
OUT = "/mnt/user-data/outputs/data/"
MIN_WORDS, MAX_WORDS = 100, 450
CONV_EXCL = "/home/claude/aita/conversion_exclusions.csv"  # posts excluded during conversion (kept across reruns)

SOURCES = [
    ("AITA-YTA", "AITA-YTA.csv", "prompt", "YTA"),
    ("AITA-NTA-OG", "AITA-NTA-OG.csv", "original_post", "NTA"),
]

def norm(t):
    """Normalisation for matching/counting only (never used as output text)."""
    t = t.replace("\\n", "\n")  # stories store newlines as literal backslash-n
    return (t.replace("\u2019", "'").replace("\u2018", "'")
             .replace("\u201c", '"').replace("\u201d", '"'))

def words(t):
    return len(norm(t).split())

def split_title(t):
    """Title = text up to the first '?' if it occurs within the first 300 chars
    (AITA titles are questions); otherwise up to the first newline / sentence end."""
    t = norm(t)
    q = t.find("?")
    if 0 <= q < 300:
        return t[:q + 1], t[q + 1:]
    m = re.search(r"\n|[.!](\s|$)", t)
    if m and m.start() < 300:
        return t[:m.end()], t[m.end():]
    return "", t

# ---- rule patterns ----
R_URL = re.compile(r"https?://|\bwww\.|\[[^\]]*\]\([^)]*\)|\b[\w-]+\.(com|org|net|io|ly|co|gov|edu|me|gl)(/\S*)?\b|\bimgur\b|\bredd\.it\b", re.I)
R_REMOVED = re.compile(r"\[(removed|deleted)\]", re.I)
EN_STOP = set("the a an and or but i you he she it we they me my to of in on for with at by from is was are were be been have had has do did not that this so just as if".split())
R_WIBTA_TITLE = re.compile(r"\bWIBTAH?\b|\bwould i be\b|\bwould it be\b.*\basshole|\bwill i be the asshole", re.I)
R_WIBTA_ANY = re.compile(r"\bWIBTAH?\b", re.I)
R_WIBTA_BODY = re.compile(r"\bwould i be (the |an |a )?(asshole|a-? ?hole|jerk|wrong|in the wrong|(?-i:TA|AH))\b", re.I)
R_VERDICT_CI = re.compile(r"\b(YTA|NTA|ESH|YWBTA|YWNBTA)\b", re.I)
R_VERDICT_CS = re.compile(r"\b(INFO|NAH)\b")  # case-sensitive: 'info'/'nah' are normal words
R_EDIT = re.compile(r"(?i:\b(edit|update|eta)(\s*\d+)?\s*[:\-\u2013\u2014])|\b(EDIT|UPDATE)\b")
R_REACT = re.compile(
    r"\bthank(s| you)?,? (you|ya|y'?all|ya'?ll|everyone|all|so much|guys|reddit|for (the|your|all|everyone|reading|replying|input|advice|perspective|responses|comments|replies|feedback|help|judge?ment|votes))|"
    r"\bthank(s| you)[.!]|\bthanks reddit|\bcommenters?\b|\bcomments\b|\bcommented\b|\b(your|the|these) (replies|responses|answers|input|feedback|perspectives?)\b|"
    r"\bvotes?\b|\bvoted\b|\bvoting\b|\bupvote|\bdownvote|\bkarma\b|\bverdicts?\b|\b(your|the|reddit'?s?) judge?ments?\b|\bunanimous\b|"
    r"\byou guys\b|\bguys,|\bokay guys\b|\bok guys\b|\by'?all\b|\bya'?ll\b|\byou all\b|\beveryone'?s (input|responses|comments|replies|advice|opinions?|feedback)\b|\bsome of you\b|\bmany of you\b|\bmost of you\b|"
    r"reddit|\bthis sub\b|\bsubreddit\b|i see now|\byou'?re (all )?right\b|\byou are (all )?right\b|i'?m the asshole|i am the asshole|i'?m an asshole|i'?m ta\b|"
    r"i'?ll apologi|i will apologi|i'?m going to apologi|i'?ll go apologi|"
    r"\b(this|my|the|original|last|previous) post\b|\bposted this\b|\bupdate the post\b|"
    r"\b(a lot of|lots of|many|some|most|several) (people|folks|users|of you) (have |are |seem |keep )?(said|say|saying|ask|asked|asking|think|thought|point|pointed|suggest|suggested|mention|mentioned|wonder|telling|told|angry|upset)|"
    r"\bpeople (are |have been |keep )(asking|saying|pointing|suggesting|mentioning|telling)|"
    r"\b(many|some|others|people|a few|several|someone|somebody|a lot of people) (have |has )?(brought up|mentioned|asked|pointed out|requested|wondered)\b|\beveryone'?s questions?\b|\binfo request\b|\bas (per|requested)\b|\bsince (people|some|many|a few|someone) (have |has )?asked\b|\b(i|I) realize (i'?m |I am )?(ITA|TA|YTA)\b|\bIATA\b|\bI'?m (the )?(ITA|YTA)\b|\byeah,? i know\b|\bi (get|understand) (it )?now\b|\bi was wrong\b|\bpoint taken\b|\bfair enough\b|"
    r"\b(a lot|some|most|many|all|several|few|lots) of you\b|\bpeople (on here|here|in the comments|on this|seem to|keep|giving|suggested|suggesting|start commenting|are saying|have said|have asked|have told me|have pointed|think|who think|focusing|solely)|\bpeople saying\b|\bi (get|understand) that people\b|"
    r"\b(everyone|everybody|people|a lot of people|some people|most people|you) seems? to (think|believe)\b|\bthose (who|that) (think|say|said|are saying|are)\b|\banyone who (thinks|says)\b|"
    r"\bmisconceptions?\b|\bassumptions\b|\bthis thread\b|\bcommon question\b|\bu/\w|\br/\w|\bcomment form\b|\bcommenting\b|\blet you (all |guys )?know how it goes\b|\bjudge?ment\b|"
    r"\bnot the a-? ?hole\b|\bnot (the |an )?asshole\b|\bi'?m not ta\b|\bnot ta\b|\bi'?m the a-? ?hole\b|"
    r"\bfeel free to ask\b|\bask me (any )?questions\b|\bif you (need|want) (more|any)\b|\btell me if you\b|\b(sorry|thanks|thank you|ok|okay|hey|wow|well) guys\b|"
    r"\bto (those|everyone|people|anyone) (who|asking|saying|that)\b|\bfor (those|everyone|people|anyone) (who|asking|saying|wondering)\b|\bto answer (some|a few|the|your) questions\b", re.I)
R_THREAD = re.compile(
    r"\b(see|read|check out|in|from|of|this is|here'?s|link to) part\s*(\d+|one|two|three|ii)\b|\bpart\s*(\d+|one|two|three|ii) (here|is here|post|link|of my)\b|"
    r"\bmy (last|previous|other|original|earlier|old) post\b|\bprevious post\b|\boriginal post\b|\bsee (the )?link\b|\blink(ed)? (below|above|in)\b|"
    r"\b(ask|answer|post|put|tell|explain|link|clarify|mention|share|add)\w* .{0,40}?in the comments\b|\bin the comments (below|section)\b|\b(the|this) comment section\b|"
    r"\bposted (here|this) (before|earlier)|\bupdate (to|on) my\b|\bx-?post|\bcross-?post|\bpiggy-?backing\b|"
    r"\bdeleted (my|the) (last |other |original )?post\b|\b(see|check) my (profile|history)\b|\bif you didn'?t see it\b", re.I)

VERD = r"(the |an |a )?(asshole|a-? ?hole|jerk|one in the wrong|in the wrong|(?-i:TA|ITA|YTA|NTA|AH))\b"
QUAL = r"((probably|definitely|maybe|kinda|kind of|totally|really|actually|clearly|obviously|not|still|being|just|also|truly|honestly|so)\s+)*"
R_SELF = re.compile(
    r"\b(i'?m|i am|i was|i'?ll be|i could be|i might be|i may be|i must be|i'?d be|i would be|i'?ve been)\s+" + QUAL + VERD + r"|"
    r"\bi (probably|definitely|guess i|might|may|must|know i|think i) am(?=\s*([,.!?;:)\-]|but\b|and\b|$))|"
    r"\b(i'?m|i am) (probably |definitely |maybe )?(wrong|in the wrong) here\b|"
    r"\bi (know|admit|realize|realise|guess|think|feel like) (that )?(i was|i'?m|i am) (probably |definitely |kind of |kinda |a bit |a little )?(wrong|in the wrong)\b|"
    r"(?-i:\bIA?N?TA\b)", re.I)

R_Q = re.compile(r"\b(if|whether)\b")
R_REPORTED = re.compile(
    r"\b(?:he|she|they|we|you|it|everyone|everybody|people|someone|somebody|friends?|family|(?:my|his|her|our|their|the) \w+|[A-Z][a-z]+)\s+"
    r"(?:(?!I\b)\w+\s+)?(?:think|thinks|thought|say|says|said|saying|feel|feels|felt|believe|believes|insist|insists|insisted|claim|claims|claimed|agree|agrees|agreed|tell me|told me|telling me)\b"
    r"|\b(?:told me|telling me|tells me|called me|calling me|calls me|accus\w* me|saying|acted like|acting like|acts like|apparently)\b")

def self_assessment(t):
    """Narrator's own verdict on themself (incl. hedges). Not counted: questions ('if/whether I'm
    the asshole') and other people's judgements the narrator reports ('my friends think I'm...')."""
    for m in R_SELF.finditer(t):
        start = max(t.rfind(c, 0, m.start()) for c in ".!?\n") + 1
        prefix = t[start:m.start()]
        if R_Q.search(prefix[-40:]) or R_REPORTED.search(prefix):
            continue
        return m
    return None

def check(raw):
    t = norm(raw)
    n = len(t.split())
    title, body = split_title(raw)
    reasons = []
    if n < MIN_WORDS or n > MAX_WORDS:
        reasons.append(f"1_length ({n} words)")
    if R_URL.search(t):
        reasons.append("2_url")
    if R_REMOVED.search(t):
        reasons.append("3_removed_deleted")
    toks = re.findall(r"[a-z']+", t.lower())
    if toks and sum(w in EN_STOP for w in toks) / len(toks) < 0.2:
        reasons.append("3_non_english")
    if R_WIBTA_TITLE.search(title) or R_WIBTA_ANY.search(t) or R_WIBTA_BODY.search(t):
        reasons.append("4_wibta")
    if R_VERDICT_CI.search(body) or R_VERDICT_CS.search(body):
        reasons.append("5_verdict_abbrev")
    m = R_EDIT.search(body)
    if m and R_REACT.search(body[m.start():]):
        reasons.append("6_edit_reacts_to_reddit")
    if R_THREAD.search(body):
        reasons.append("7_thread_or_post_reference")
    if len(body.split()) < 80:
        reasons.append("8_too_little_content")
    if self_assessment(t):
        reasons.append("9_self_assessment")
    return reasons, n

def run():
    import os
    conv = pd.read_csv(CONV_EXCL) if os.path.exists(CONV_EXCL) else pd.DataFrame(columns=["source_file", "source_row", "reason"])
    conv_keys = {(a, int(b)): c for a, b, c in conv.itertuples(index=False)}
    log, pools, stats = [], {}, {}
    for sf, fn, col, label in SOURCES:
        df = pd.read_csv(UP + fn, usecols=["Unnamed: 0", col]).rename(columns={"Unnamed: 0": "source_row", col: "text"})
        keep = []
        for r in df.itertuples(index=False):
            reasons, n = check(r.text)
            if not reasons and (sf, int(r.source_row)) in conv_keys:
                reasons = [conv_keys[(sf, int(r.source_row))]]
            if reasons:
                log.append({"source_file": sf, "source_row": int(r.source_row),
                            "reason": reasons[0], "all_reasons": "; ".join(reasons)})
            else:
                keep.append({"source_file": sf, "source_row": int(r.source_row), "label": label, "words": n})
        pools[label] = pd.DataFrame(keep)
    logdf = pd.DataFrame(log)
    logdf[["source_file", "source_row", "reason"]].to_csv(OUT + "excluded.csv", index=False)
    logdf.to_csv("/home/claude/aita/excluded_all_reasons.csv", index=False)
    for label, p in pools.items():
        p.to_csv(f"/home/claude/aita/pool_{label}.csv", index=False)
    return logdf, pools

if __name__ == "__main__":
    logdf, pools = run()
    logdf["primary"] = logdf.reason.str.split(" ").str[0]
    print(pd.crosstab(logdf.primary, logdf.source_file, margins=True))
    # any-reason counts (posts can hit several rules)
    ex = logdf.assign(r=logdf.all_reasons.str.split("; ")).explode("r").reset_index(drop=True)
    ex["r"] = ex.r.str.split(" ").str[0]
    print("\nAny-match counts:\n", pd.crosstab(ex.r, ex.source_file))
    for k, p in pools.items():
        print(k, "pool:", len(p), p.words.describe()[["mean", "50%", "min", "max"]].round(1).to_dict())

