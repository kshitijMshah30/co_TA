# Week 3 (Sep 7 - Sep 11) - Eann Gatuna, Human Interface

## What I achieved / worked on this week
Built the first end-to-end student-facing UI prototype (React + TypeScript + Tailwind) with a Socratic chat loop, streaming responses, and a mock backend so the frontend can be demoed and tested before the Intelligence endpoint exists. Added a pinned breadboard photo panel with clickable hotspot annotations, a resistor color-code tool, a session dashboard, and cross-session context (`priorSessions`) so the model can pick up where a student left off. The team voted my design the favorite of the group's prototypes, so it is now the backbone for the Human Interface sub-team and everyone is building their features and ideas on top of it. Live demo (mock mode): https://vip-ai-ta-demo.netlify.app

## What I am blocked on
Real backend integration. The Intelligence team's flow doc (`AI_TA_Glasses_Intelligence_Flow_Expanded.pdf`) uses a different request/response schema than my current contract (`session_id` / `lab_id` / `lab_step` / `measurements` in, `response_type` / `safety_level` / `needs_ta` out), so we need to lock one input schema and one output schema before wiring. Also need to agree on image transfer (multipart upload vs URL) and the annotation coordinate format.

## What I plan to do next week
Start the actual Human Interface to Intelligence integration: map my `StudentQueryPayload` to the `POST /api/ai-ta/query` contract, add a response adapter that renders `response_type` (hint, clarifying question, safety warning, escalate to TA, solved) with the right UI treatment, and point the HTTP client at their endpoint behind a feature flag. Run their shared test cases (DMM reads 0 mA, PSU voltage drops, "I'm stuck", spark/hot smell, "that fixed it") against the live API.
