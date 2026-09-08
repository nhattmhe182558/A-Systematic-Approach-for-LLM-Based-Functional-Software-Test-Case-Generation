# Input

This folder holds the **inputs** to the IntelliTest pipeline.

## What goes in

### 1. The RDS/SRS document (required)
A single **PDF** file: the software Requirement & Design Specification (also
called an RDS or SRS document). This is the only mandatory input and is passed
on the command line:

```bash
python main.py --pdf input/your-spec.pdf --provider gemini
```

Place your PDF here, e.g. `input/4lv-ieee830-lastest.pdf`.

The document should describe, in natural language:
- **Screens / pages** of the application,
- **Use cases** (with IDs such as `UC-101`),
- **Business processes / workflows** (end-to-end user journeys),
- **Business rules and field constraints** (formats, ranges, mandatory fields),
- optionally, **user roles** (customer, seller, admin, …).

The richer and more explicit the document, the better the generated artifacts.

### 2. API credentials (required, via `.env`)
Not a file in this folder — configured in the project-root `.env` (copy from
`.env.example`). Provide the key for whichever provider you choose:

| Provider  | Env var             | Notes                                   |
|-----------|---------------------|-----------------------------------------|
| Gemini    | `GEMINI_API_KEY`    | Uploads the PDF + uses context caching. |
| DeepSeek  | `DEEPSEEK_API_KEY`  | PDF text is extracted and sent inline.  |

Select the provider with `LLM_PROVIDER` in `.env` or `--provider` on the CLI.

## How the input is consumed per provider

- **Gemini** — the PDF is uploaded once and stored in a Gemini *context cache*;
  every stage references that cache, so the document is only sent once.
- **DeepSeek** — DeepSeek has no PDF upload, so the text is extracted with
  `pypdf` and prepended to each request as system context.

## What is NOT needed here
Unlike the original research code, there is **no** `input_data.json`, no
per-module config files, and no pre-selected PDF path baked into a config
module. Everything is driven by the `--pdf` argument and the `.env` file.
