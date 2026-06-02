# Spec: `generate_response()`

**File:** `generator.py`
**Status:** Spec incomplete — fill in all blank fields before implementing

---

## Purpose

Given a user query and a list of retrieved rule chunks, generate a response that directly answers the question using only the retrieved text as context. The response must be grounded — it should not draw on the model's general knowledge of board games, only on what was retrieved.

---

## Input / Output Contract

**Inputs:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | `str` | The user's original question |
| `retrieved_chunks` | `list[dict]` | Ranked list of chunks from `retrieve()`, each with `"text"`, `"game"`, and `"distance"` |

**Output:** `str`

A plain string containing the response to show the user. The response should:
- Answer the question using only the retrieved rule text
- Identify which game the answer comes from
- Acknowledge clearly when the answer is not found in the loaded rules

Returns a fallback string (not an error) when `retrieved_chunks` is empty.

---

## Design Decisions

*Complete the fields below before writing any code. Use your AI tool in Plan or Ask mode to help you reason through what belongs here — but the decisions are yours.*

---

### Context formatting

*How will you format the retrieved chunks before passing them to the LLM? Describe the structure — not the code. Consider: will you label chunks by game? Include distance scores? Separate chunks with delimiters?*

```
We will provide retrieved chunks in a strict, machine-readable block format so the LLM can locate and quote them verbatim. Chunks are ordered from most to least relevant. Each chunk will use explicit markers and include the chunk id, game, and distance on a single header line, followed by the exact chunk text, then a closing marker. Example structure:

[CHUNK] id: catan_3 | game: Catan | distance: 0.142
When a 7 is rolled, no resources are produced for the hex that rolled.
[END CHUNK]

Rules for formatting:
- Always include the chunk id and game in the header exactly as shown.
- Provide chunks in descending relevance order (lowest distance first).
- Do not include any additional commentary or summaries outside the chunk markers.
- The model must only use text between [CHUNK] and [END CHUNK] markers as authoritative rule text.

This explicit delimiting makes it easy for the model to (a) find exact quotes, (b) verify chunk ids for citation, and (c) avoid using surrounding metadata as content.
```

---

### System prompt — grounding instruction

*Write the exact system prompt instruction you will use to prevent the model from answering beyond the retrieved text. This is the most important design decision in this function.*

```
You are a rules assistant for board game rulebooks. You will answer ONLY by quoting the retrieved rule chunks provided in the user context. Follow these rules strictly:

1) Use ONLY the retrieved chunks provided between [CHUNK] and [END CHUNK] markers. Do not use training data, web search, or any external knowledge.

2) Every factual claim must be a direct verbatim quote from a single chunk. Format each quoted claim as: "<exact quote>" [GameName: chunk_id]. Place the citation immediately after the quote with no intervening words.

3) Do not paraphrase, summarize, infer, combine multiple chunks to create a new claim, or explain terms unless the exact text appears verbatim in a single chunk. If a question requires reasoning beyond the exact text of a single chunk, refuse.

4) If no retrieved chunk contains an answer, reply exactly: "I don't know based on the loaded rule books." Add nothing else.

5) Do not hedge, speculate, or use qualifiers (e.g., "probably", "likely", "may"). Do not redefine game terms or provide context not present in the chunks.

6) Do not answer what the rules "do not" say. If asked about absence, reply exactly as in rule 4.

7) Do not generalize rules across games. Cite only chunks from the game you reference.

8) End every answer with a Sources: list listing each cited chunk by [GameName: chunk_id] on its own line.

[The retrieved chunks follow below. Use them only as instructed.]
```

---

### System prompt — citation instruction

*Write the exact instruction you will use to tell the model to identify which game its answer comes from.*

```
After every quoted claim, append an immediate citation in this exact format: [GameName: chunk_id]. At the end of your reply include a "Sources:" section containing one cited chunk per line, each as [GameName: chunk_id]. Use only chunk_ids that appear in the provided [CHUNK] blocks.
```

---

### Fallback behavior

*What should the response say when the answer isn't found in the loaded rule books? Write the exact fallback message.*

```
I don't know based on the loaded rule books.
```

---

### Handling low-relevance chunks

*`retrieved_chunks` may include chunks with high distance scores (weak relevance). Will you filter these out before building context, pass them all in, or handle them another way? What are the tradeoffs?*

```
We will pass the `retrieved_chunks` returned by `retrieve()` (already limited to `n_results`) into the prompt unfiltered. Distances are included in each chunk header so the model can see relative relevance, but the system prompt forbids the model from inventing connections; it must quote verbatim from a single chunk per claim.

Tradeoffs:
- Passing unfiltered results keeps the pipeline simple and lets the model choose the best chunk to quote, but may expose it to a few noisy chunks. The strict system prompt and citation requirement mitigate this.
- Optionally, a downstream filter (e.g., `max_distance`) can be added to drop weak matches if many noisy results are observed in practice.
```

---

### Message structure

*Describe how you will structure the messages list for the API call — what goes in the system message vs. the user message?*

```
The `messages` list will contain exactly two messages:

- System message (`role: "system"`): the exact grounding instruction (the system prompt written above). This enforces strict quoting, refusal behavior, citation format, and disallows inference.

- User message (`role: "user"`): the retrieved chunks formatted with `[CHUNK]` / `[END CHUNK]` blocks (each header includes `id`, `game`, `distance`), followed by the user's question. The user message will explicitly instruct the model to answer using only verbatim quotes from the chunks and to reply exactly with the refusal phrase when unsupported.

Example `messages` payload:

```
[
	{"role": "system", "content": "<exact system prompt>"},
	{"role": "user", "content": "[CHUNK] id: catan_3 | game: Catan | distance: 0.142\n<chunk text>\n[END CHUNK]\n\nQuestion: <user question>"}
]
```
```

---

## Implementation Notes

*Fill this in after implementing and testing.*

**Test query and response:**

```
Note: local runtime was missing (no `groq` package), so a live model call was not executed here. The implementation constructs the exact system prompt and user message format described above and calls `_client.chat.completions.create()` with `model=LLM_MODEL` and the two messages (system + user). If the API call fails, the function returns a debug string containing the system prompt and user message so the developer can inspect or run the prompt locally.

To test locally:

1. Install dependencies and set `GROQ_API_KEY` in your environment.

```
pip install -r requirements.txt
export GROQ_API_KEY="<your-key>"
python3.13 - <<'PY'
from ingest import load_documents, chunk_document
from retriever import embed_and_store, retrieve, get_collection
from generator import generate_response

docs = load_documents()
all_chunks = []
for d in docs:
	all_chunks.extend(chunk_document(d['text'], d['game']))
embed_and_store(all_chunks)
print(generate_response('What happens when you roll a 7?', retrieve('What happens when you roll a 7?')))
PY
```

Expected behavior:
- For a question present in the chunks, the model should reply with one or more exact verbatim quotes, each followed immediately by `[GameName: chunk_id]`, and end with a `Sources:` list.
- For a question not present, the model should reply exactly: `I don't know based on the loaded rule books.`

Because the execution environment used to implement this function did not have the `groq` client installed, the end-to-end model call could not be run here; confirm locally using the steps above.
```

**One thing you changed from your original spec after seeing the actual output:**

```
[your answer here]
```
