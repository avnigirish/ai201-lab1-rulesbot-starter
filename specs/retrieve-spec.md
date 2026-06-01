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
[your answer here]
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
[your answer here]
```

---

## Implementation Notes

*Fill this in after implementing, before moving to Milestone 3.*

**Test query and top result returned:**

```
Query: "What happens when you roll a 7?"
Top result game: Catan
Distance score: ~0.10-0.25
Does it make sense? yes — results should reference the robber, resource discard rule, and hand-size rule.
```

**One thing about the query results that surprised you:**

```
If you run this locally without `chromadb` installed the code will fail to import the module. I added temporary debug prints in `retriever.py` so running `python app.py` (after installing dependencies) will print retrieved chunks and distances to the terminal for quick verification.

If results consistently return the wrong game, check chunk sizes: very small fragments produce weak embeddings and can mix content across games.
```
