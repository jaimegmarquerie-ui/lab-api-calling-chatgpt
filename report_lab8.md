# Report: Lab "API Calling to ChatGPT" (Day 8)

**Author:** Jaime · **Date:** 28/10/2026
**Submitted files:** `product_listing_generator.py`, `listings.json`, execution screenshots.

## 1. How the API integration works
The program generates product listings from a photo and some basic product data:

`data + image → Python → API → vision model → JSON response → validation → listings.json`

1. **Authentication:** the API key is stored in a `.env` file (not submitted) and loaded with `python-dotenv`. If the key is missing, the program stops with a clear message.
2. **Data:** a list of 3 products (name, price, category, image path) using my own product photos.
3. **Image:** each photo is read in binary mode and encoded as base64 so it can be sent inside the request.
4. **Prompt:** it sets a role (e-commerce copywriter) and includes the product data, the required JSON structure (`title`, `description`, `features`, `keywords`) and its limits.
5. **API call:** `client.chat.completions.create` with a two-part message, text plus image (`data:image/jpeg;base64,...`), and `timeout=60`.
6. **Processing:** the JSON is extracted from the response, converted to a dictionary with `json.loads`, and checked for the 4 required fields. The 3 products are processed in a loop, with a 2-second pause between calls, and saved to `listings.json`.

**Provider change:** I did not have an OpenAI key with credits, so I used **Google Gemini** (free tier) through its OpenAI-compatible endpoint. The code uses the same `openai` library; only `base_url`, the API key and the model (`gemini-3.5-flash-lite`) change. Everything else follows the lab instructions.

## 2. Challenges
- **Error 400 "Please pass a valid API key":** the key contained a duplicated character. I diagnosed it with a check that does not reveal the key (length and prefix).
- **Error 503 "model is experiencing high demand":** `gemini-3.8-flash` was overloaded and the call hung. I fixed it by switching to a lighter model and adding a `timeout`.
- **Two Python interpreters:** VS Code was using one without `dotenv` (`ModuleNotFoundError`). I fixed it by selecting the Anaconda interpreter.
- **JSON wrapped in Markdown:** the model returns ```` ```json ... ``` ```` even when asked for "JSON only". I fixed it by extracting the text from the first `{` to the last `}`.

## 3. Quality of the generated listings
Final run (3/3 successful):

| Product | Title (≤60 chars) | Description (150–200 words) | Features (5–7) | Keywords (10–15) |
|---|---|---|---|---|
| Mug | ✅ | 149 ❌ | 7 ✅ | 11 ✅ |
| Sneakers | ✅ | 143 ❌ | 7 ✅ | 11 ✅ |
| Headphones | ✅ | 139 ❌ | 6 ✅ | 12 ✅ |

- **Strengths:** the listings use details **visible in the photo** (colours, materials, design), are not generic, and follow the required structure.
- **Weaknesses:** the descriptions fall **below 150 words**, and some titles include the price (bad SEO practice, since prices change).
- **Conclusion:** stating a limit in the prompt does not guarantee it is met, so the output must be **validated in code**.

## 4. Error handling (evidence in screenshots)
There is a specific `except` for each type of failure, not a generic one: missing image, authentication (400/401), rate limit (429), timeout or connection error, server unavailable (5xx), and malformed JSON or missing fields.

Tests run:
- **Missing image:** the program reports the error and continues with the other products (2/3).
- **Missing API key:** the program stops at start-up without making any calls.
- **Real API errors:** 400 and 503.

## 5. Possible improvements
- **Validate the limits** (word and character counts) and **retry the call** if they are not met.
- Use **structured output with Pydantic** (shown in the class notebook) instead of extracting JSON from text.
- **Retries with exponential backoff** for 429 and 503 errors.
- **Resize images** before sending them, to make calls faster and use fewer tokens.
- Tell the model in the prompt **not to include the price in the title**.
- Test with more products from the HuggingFace dataset.
