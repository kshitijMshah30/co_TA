# Week 4 (Sep 14 - Sep 18) - Eann Gatuna, Human Interface

## What I achieved / worked on this week
Built the Human Interface side of the Intelligence integration without a live server. The app sends the exact `POST /api/ai-ta/query` request from the flow doc (`session_id`, `lab_id`, `lab_step`, `question`, image, `measurements`) and renders every `response_type`: hint, clarifying question, concept explanation, safety warning, "Ask a TA" card, and a solved card the student confirms. Added a "Current step" selector and a measurements tray that parses readings like "0 mA" from the question. Wrote a stub server that speaks the contract, a `contract-check` CLI for validating any server, 45 tests, and `docs/INTEGRATION.md` with a proposed OpenAPI spec. Verified the live path in the browser against the stub: all seven shared cases pass, plus escalation, photo annotations and streaming. Demo (mock mode): https://vip-ai-ta-demo.netlify.app

## What I am blocked on
Two inputs from outside the sub-team: the ECE lab manuals the professor wants the TA to cover, and the actual Intelligence API. Without the manuals, the lab catalog (`lab_id` values, `lab_step` vocabulary, Socratic prompts per step) runs on placeholder labs. Without the API, the live path is proven only against my stub. Still open from page 10: image transfer (both modes built), the annotation box format, and CORS on their dev server for the demo.

## What I plan to do next week
Both are expected at this week's meeting with the other groups and the professor. With the manuals: rebuild the lab catalog from the real labs and steps. With the API: run `contract-check` and the seven shared cases against it, fix any mapping gaps, and flip the demo from mock to live behind the flag. Then start the eval feed: `response_type`, votes and solved outcomes per session, in the shape Intelligence wants.
