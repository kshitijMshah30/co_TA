# Week 10 (Oct 26 - Oct 30) - Eann Gatuna, Human Interface

## What I achieved / worked on this week
My week 10 task was lab sessions, and it is merged into main (PR #9). A TA starts a session for a lab from the new Lab sessions tab in the TA workspace, like starting class in iClicker. While it runs, students in the course see a banner, and every question they ask the AI TA is logged without their name. At the end the TA gets a summary: the questions asked most (similar wordings grouped together), questions per step, safety warnings, hand-offs to a TA, how many students said it was solved, and the busiest part of the lab. Copy summary pastes it anywhere. It works in the browser for the demo and on the class server for a real lab. I also security-checked Arwa and Ethar's microprocessor tab (PR #7). Nothing critical, but the paid AI pinout reader could still be used with its switch off, so PR #8 adds a server switch, its own hourly limit and file size caps. A full run-through of main found three small issues, fixed in PR #10. All 265 tests pass.

## What I am blocked on
The Intelligence API. The live path is still proven only against my stub, and Intelligence hasn't confirmed my proposed lab IDs and step names yet. Page 10 still has three open decisions: image transfer, the annotation box format, and CORS for the demo. Lab sessions also need a FERPA check with the advisors before real students use them.

## What I plan to do next week
Redeploy the demo so it shows course profiles, the Pinout tab and lab sessions. Rotate the class password. Help with the remaining week 10 tasks (capacitor and inductor codes, the QueUp button) if nobody has picked them up. When the API is ready, run `contract-check` and the seven shared cases against it and switch the demo to live.
