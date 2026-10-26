# Week 9 (Oct 19 - Oct 23) - Eann Gatuna, Human Interface

## What I achieved / worked on this week
Arwa and Ethar's course profiles (PR #5) went into main. A TA can now set up a course with its own class password, labs and student tools, and a student who signs up with that password lands in that course. Students can also join another course. I reviewed and tested it: all 185 tests passed, and in the browser I made a new course, uploaded a manual, signed up as a student with the new password and chatted with no errors. Uploaded labs are now named from the manual's title, which fixes the naming issue from last week. I also tested the accounts server directly and found six issues, which I fixed in PR #6 (merged, 190 tests pass). The main ones: wrong TA keys now lock out after 8 tries, and reading manuals with AI is capped so it can't run up a bill. The rest tighten TA access and keep labs uploaded under PR #3 from being lost. Everyone should run `git pull origin main`. The demo hasn't been redeployed yet, so it still shows the Oct 19 version: https://vip-ai-ta-demo.netlify.app.

## What I am blocked on
The Intelligence API. The live path is still proven only against my stub, and Intelligence hasn't confirmed my proposed lab IDs and step names yet. Page 10 still has three open decisions: image transfer, the annotation box format, and CORS for the demo. We also need to decide whether manuals should be stored on the backend.

## What I plan to do next week
Redeploy the demo with course profiles once the sub-team agrees. Rotate the class password and check FERPA requirements with the advisors before any real student signs in. Fix the safety banner that mentions a function generator Labs 1-2 don't use. When the API is ready, run `contract-check` and the seven shared cases against it and switch the demo to live.
