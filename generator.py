from groq import Groq
from config import GROQ_API_KEY, LLM_MODEL

_client = Groq(api_key=GROQ_API_KEY)


def generate_response(query, retrieved_chunks):
    """
    Generate a grounded answer from retrieved rule chunks.

    TODO — Milestone 3:

    `retrieved_chunks` is the list returned by retrieve(). Each item is a dict:
      - "text"     : the chunk text
      - "game"     : the game name
      - "distance" : similarity score (you can use this to filter weak matches)

    Before writing code, talk through these with your group:
      - How will you format the chunks into a context block for the prompt?
      - What instructions will stop the model from answering beyond what the
        rules say? (Grounding is the whole point — a confident wrong answer
        is worse than an honest "I don't know.")
      - How will you surface which game each answer comes from?

    Your response should:
      1. Answer using only the retrieved context — not the model's general knowledge
      2. Make clear which game the answer comes from
      3. Say so clearly when the answer isn't in the loaded rules

    Return the response as a plain string.
    """
    if not retrieved_chunks:
      return "I don't know based on the loaded rule books."

    # Exact grounding/system prompt taken from specs/generate-response-spec.md
    system_prompt = (
      "You are a rules assistant for board game rulebooks. You will answer ONLY by quoting the retrieved rule chunks provided in the user context. Follow these rules strictly:\n\n"
      "1) Use ONLY the retrieved chunks provided between [CHUNK] and [END CHUNK] markers. Do not use training data, web search, or any external knowledge.\n\n"
      "2) Every factual claim must be a direct verbatim quote from a single chunk. Format each quoted claim as: \"<exact quote>\" [GameName: chunk_id]. Place the citation immediately after the quote with no intervening words.\n\n"
      "3) Do not paraphrase, summarize, infer, combine multiple chunks to create a new claim, or explain terms unless the exact text appears verbatim in a single chunk. If a question requires reasoning beyond the exact text of a single chunk, refuse.\n\n"
      "4) If no retrieved chunk contains an answer, reply exactly: \"I don't know based on the loaded rule books.\" Add nothing else.\n\n"
      "5) Do not hedge, speculate, or use qualifiers (e.g., \"probably\", \"likely\", \"may\"). Do not redefine game terms or provide context not present in the chunks.\n\n"
      "6) Do not answer what the rules \"do not\" say. If asked about absence, reply exactly as in rule 4.\n\n"
      "7) Do not generalize rules across games. Cite only chunks from the game you reference.\n\n"
      "8) End every answer with a Sources: list listing each cited chunk by [GameName: chunk_id] on its own line.\n\n"
      "[The retrieved chunks follow in the user message. Use them only as instructed.]"
    )

    # Build the user message containing the retrieved chunks in the explicit format
    # described by the spec, then append the user's question.
    user_parts = []
    for c in retrieved_chunks:
      cid = c.get("chunk_id") or "unknown_id"
      game = c.get("game") or "unknown_game"
      dist = c.get("distance")
      if dist is None:
        header = f"[CHUNK] id: {cid} | game: {game}"
      else:
        header = f"[CHUNK] id: {cid} | game: {game} | distance: {dist:.3f}"
      text = c.get("text", "")
      user_parts.append(f"{header}\n{text}\n[END CHUNK]\n")

    user_context = "\n".join(user_parts)
    user_message = (
      "You are given the following retrieved rule chunks (only use the text between [CHUNK] and [END CHUNK]).\n\n"
      f"{user_context}\n"
      "Answer the user's question using ONLY verbatim quotes from a single chunk per claim, citing each quote immediately.\n"
      "If the answer is not present in any chunk, reply exactly: \"I don't know based on the loaded rule books.\"\n\n"
      f"Question: {query}\n"
    )

    messages = [
      {"role": "system", "content": system_prompt},
      {"role": "user", "content": user_message},
    ]

    try:
      resp = _client.chat.completions.create(model=LLM_MODEL, messages=messages)
      # Try common response shapes
      if isinstance(resp, dict):
        # OpenAI-like: resp['choices'][0]['message']['content']
        try:
          return resp["choices"][0]["message"]["content"]
        except Exception:
          pass
      # Try attribute style
      try:
        return resp.choices[0].message.content
      except Exception:
        pass
      # Fallback to string representation
      return str(resp)
    except Exception as e:
      # If API call fails (missing key, network), return a helpful debug
      # string containing the assembled prompt so the developer can run it.
      debug = (
        "[generate_response] API call failed: " + str(e) + "\n\n"
        "--- SYSTEM PROMPT ---\n" + system_prompt + "\n\n"
        "--- USER MESSAGE ---\n" + user_message
      )
      return debug
