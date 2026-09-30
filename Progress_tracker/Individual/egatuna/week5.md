# Week 5 (Sep 21 - Sep 25) - Eann Gatuna, Human Interface

## What I achieved / worked on this week
Got the ECE 20007 lab manuals at the joint meeting and rebuilt the lab catalog from them. The placeholder labs are gone: the app now covers Lab 1 (Ohm's Law, 10 steps) and Lab 2 (Kirchhoff's Laws and voltage dividers, 11 steps), sent as `lab_1` / `lab_2`, with each `lab_step` tied to its manual section. Old saved sessions repair themselves instead of breaking. I added mock rules for dividers, loading and the LDR, plus new starter prompts for both labs. Tests pass, `contract-check` is still 7/7, and the redeployed demo shows the real labs: https://vip-ai-ta-demo.netlify.app. I confirmed the demo makes no AI calls and costs $0 on Netlify's free tier. I also moved the app into a private team repo with one-click Codespaces and a CONTRIBUTING guide, so teammates can branch and open PRs directly. The whole sub-team has now joined the repo. I presented the setup, data flow and app tour to the other sub-teams.

## What I am blocked on
The Intelligence API. The live path is still proven only against my stub. Intelligence also needs to confirm my proposed lab IDs and step names, and page 10 still has three open decisions: image transfer (both modes built), the annotation box format, and CORS for the demo.

## What I plan to do next week
Finish student login (Purdue email plus a class password, on in dev and off on the demo), rotate the password before real students use it, and turn it on for the demo. Start the professor/TA view and a FERPA check with the advisors. When the API is ready, run `contract-check` and the seven shared cases against it and switch the demo to live. I'll also fix the safety banner, which mentions a function generator Labs 1-2 don't use.
