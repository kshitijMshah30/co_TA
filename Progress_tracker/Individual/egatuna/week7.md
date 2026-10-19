# Week 7 (Oct 5 - Oct 9) - Eann Gatuna, Human Interface

## What I achieved / worked on this week
Redeployed the demo from main, so it now includes everything merged this week, including the TA workspace preview (the "TA preview" link in the top bar). I checked it locally before publishing: chat replies, opening and leaving the TA preview, and no console errors. Login stays off on the demo, and Ethar's accounts server isn't hosted, so sign-in there only uses accounts saved in the browser. Demo (mock mode): https://vip-ai-ta-demo.netlify.app. I also tested Codespaces after the merges. A codespace created before Oct 5 doesn't update itself and still runs the old app, so I deleted mine and made a new one from main, and sign-in and the TA preview both work there. Anyone on the sub-team with an older codespace needs to do the same, or run `git pull`, `npm ci` and restart the dev server. Logan opened PR #3, which adds a Labs view and lets a student upload a new lab from its manual.

## What I am blocked on
The Intelligence API. The live path is still proven only against my stub, and Intelligence hasn't confirmed my proposed lab IDs and step names yet. Page 10 still has three open decisions: image transfer, the annotation box format, and CORS for the demo. The sub-team also still needs to decide whether students should see the TA preview link.

## What I plan to do next week
Review and merge Logan's PR #3. Rotate the class password, since the old one is still in the repo history, and check FERPA requirements with the advisors before any real student signs in. Fix the safety banner that mentions a function generator Labs 1-2 don't use. When the API is ready, run `contract-check` and the seven shared cases against it and switch the demo to live.
