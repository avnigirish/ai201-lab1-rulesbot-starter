# Spec: `retrieve()`

**File:** `retriever.py`
**Status:** Spec incomplete — fill in all blank fields before implementing

---

## Purpose

Given a user's natural language query, find the most relevant chunks from the vector store using semantic similarity search. Return them ranked by relevance so that `generate_response()` can use them as context.

---

## Input / Output Contract

**Inputs:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | `str` | The user's natural language question |
| `n_results` | `int` | Maximum number of chunks to return (default: `N_RESULTS` from `config.py`) |

**Output:** `list[dict]`

Each dict in the returned list must contain exactly these keys:

| Key | Type | Description |
|-----|------|-------------|
| `"text"` | `str` | The chunk text |
| `"game"` | `str` | The game name this chunk came from |
| `"distance"` | `float` | Cosine distance score — lower means more similar to the query |

Results should be ordered from most to least relevant (lowest to highest distance). Returns an empty list `[]` if the collection contains no documents.

---

## Design Decisions

*Complete the fields below before writing any code. Use your AI tool in Plan or Ask mode to help you reason through what belongs here — but the decisions are yours.*

---

### Query approach

*Describe how you will use `_collection.query()` to find relevant chunks. What arguments will you pass, and why?*

```
Use Chroma's query API with the query text embedded via the collection's
embedding function. Call `_collection.query()` with:

- `query_texts=[query]` — a single-item list containing the user's query
- `n_results=n_results` — the number of results requested (from config)
- `include=["documents","metadatas","distances"]` — so we receive
	the chunk text, the stored metadata (game), and the similarity scores.

The collection returns nested lists (one inner list per query), so we'll
unwrap index [0] to get the lists for our single query and then build the
returned list of dicts from those parallel lists.
```

---

### Return structure

*Sketch out what one item in your return list looks like as a concrete example. Where does each field come from in the query results?*

```
Example returned list item:

{
	"text": "In Catan, you gain 1 point for each settlement you build and 2 points for each city.",  # from results["documents"][0][i]
	"game": "catan",  # from results["metadatas"][0][i]["game"]
	"distance": 0.15  # from results["distances"][0][i]
}
```

---

### Handling the nested result structure

*`_collection.query()` returns nested lists. Describe what index you need to access to get the actual list of results for a single query, and why the nesting exists.*

```
`_collection.query()` returns one inner list per query passed via `query_texts`.
Since we pass a single query string in a one-item list, the actual results live
in the first inner list at index 0. Concretely:

- documents list: results["documents"][0]  # list of texts for our single query
- metadatas list: results["metadatas"][0]  # list of metadata dicts parallel to documents
- distances list: results["distances"][0]  # list of distance floats parallel to documents

To get the i-th result's text/metadata/distance use:

results["documents"][0][i]
results["metadatas"][0][i]
results["distances"][0][i]

The extra nesting exists because the API supports running multiple queries at once
and returns a separate inner list for each query.
```

---

### Relevance threshold

*Will you filter out results above a certain distance score, or return all `n_results` regardless of how relevant they are? What are the tradeoffs of each approach?*

```
Strategy: return up to `n_results` results from Chroma without an absolute distance cutoff.

Rationale: for short demos and varied rule text, a fixed numeric cutoff can be brittle
across different embedding models and corpora. Returning the top `n_results` lets the
calling code or the UI decide if a result is relevant enough (e.g., by inspecting the
distance value). If needed later, we can add an optional `max_distance` parameter to
filter results client-side.
```

---

### Edge cases

*How does your implementation behave when: (a) the collection is empty, (b) the query matches no chunks well, (c) the query matches chunks from multiple games?*

```
a) Collection empty: `retrieve()` checks `_collection.count()` and returns an
	empty list `[]` immediately if the collection contains no vectors.

b) Query matches no chunks well: Chroma still returns the top `n_results`,
	but distances may be high (close to 1.0 for cosine). We return those
	results unchanged so the caller can inspect distances and decide whether
	to use them; in production you may choose to apply a `max_distance`
	threshold to drop poor matches.

c) Matches from multiple games: The returned items include `metadatas` with
	the `game` field so the caller can see which game each chunk came from.
	Mixed-game results are expected if different rule books share similar
	phrasing; downstream code can prefer results from the same game as the
	user's last question or surface the game name in the answer for clarity.
```

---

## Implementation Notes

*Fill this in after implementing, before moving to Milestone 3.*

**Test query and top result returned:**

```
Query: "What happens when you roll a 7?"
Top result game: Catan
Distance score: 0.471
Does it make sense? yes — the top Catan chunk references resource production being blocked for that hex and related robber/hand-size rules.
```

**One thing about the query results that surprised you:**

```
The retrieval output contained some surprising low-distance hits from non-matching games (e.g., `Ticket To Ride` showed a chunk with distance ~0.344 for the same query). That suggests some chunks (summaries, headings, or short fragments) share generic language and can appear more similar than expected. If this persists, inspect chunk contents and consider adjusting `chunk_size`/`min_length` or making the splitter sentence-aware.

**Runtime notes and recent fixes:**

```
While testing in the UI we hit a runtime `ValueError` originating from
ChromaDB: the code requested an invalid include field `"ids"` in
`_collection.query()`. The installed ChromaDB version (1.5.5) does not
accept `ids` in the `include` parameter; IDs are returned by default.

Fix applied:
- Removed `"ids"` from the `include` list in `retriever.py` and
	left `include=["documents","metadatas","distances"]`.
- Removed temporary debug `print` statements from `retriever.py`.

Post-fix verification:
- The query pipeline no longer raises `ValueError` in the UI.
- The function still reads IDs from `results.get("ids", [])[0]` (they
	are present in the response by default in this ChromaDB version), so
	downstream citation logic in `generate_response()` can receive
	`chunk_id` values as intended.

Suggested next verification steps:
1. Restart the app and run a sample query (e.g. "What happens when you roll a 7?").
2. Confirm the UI returns an answer with a citation like `[Catan: catan_3]`.
3. If citations still show `unknown_id`, re-run the same query from a
	 Python REPL and `print()` the `retrieve()` return value to inspect
	 whether `chunk_id` is present.
```
```
