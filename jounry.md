Let me make this dead simple with a real story, then answer your vitals question clearly.

## The whole thing as a real story

Meet **Ahmed, 65.** He was in hospital for a heart problem. Today he goes home. As he leaves, a nurse says "you'll get a daily WhatsApp message to see how you're doing." That's it — no app to download, no password.

**Day 1, evening. His phone buzzes — a WhatsApp message:**

> **AfterCare:** Hi Ahmed 👋 This is your check-in from City Hospital. Just 2 minutes to see how you're recovering. How are you feeling today?

> **Ahmed:** Okay I think. A bit tired.

> **AfterCare:** That's normal in the first days. A few quick questions — any swelling in your legs or ankles? *(buttons: Yes / No / A little)*

> **Ahmed:** *taps No*

> **AfterCare:** Any trouble breathing? *(Yes / No / A little)*

> **Ahmed:** *taps No*

> **AfterCare:** Are you managing to take your medicines?

> **Ahmed:** *taps Yes*

> **AfterCare:** Wonderful — sounds like you're recovering well. I'll check in tomorrow. Message me anytime if anything changes. Take care, Ahmed 💙

Two minutes. He feels looked after. **Nothing happened on the hospital's side — no nurse needed.** That's a normal day.

**Now jump to Day 4. Same check-in, but this time:**

> **AfterCare:** Any trouble breathing?

> **Ahmed:** Yes, when I climb the stairs I get really out of breath. And my ankles are swollen.

Here's the magic moment. The agent *understands* that swelling + breathlessness in a heart patient is a danger sign. To Ahmed, it stays calm:

> **AfterCare:** Thank you for telling me, Ahmed. I'm letting your care team know so someone can call you shortly. You're doing the right thing.

It does **not** scare him. It does **not** say "you might have heart failure." It just reassures him.

But at that exact second, on a **second screen at the hospital** — the nurse's dashboard — Ahmed's name jumps to the top and turns **red**: *"⚠️ Ahmed K. — swelling + breathlessness — needs a call."* The nurse clicks, reads the whole chat, and phones him. He gets help *today* — instead of collapsing next week and landing back in the emergency room.

**That's the entire product in one story:** a friendly daily message that quietly watches for danger, and the moment it spots something, it taps a real nurse on the shoulder.

## So there are two screens

Think of it like a **smoke detector in a house connected to the fire station.**

- **Screen 1 — the patient's phone (the smoke detector in the room):** friendly, calm, simple. Just asks how they feel.
- **Screen 2 — the nurse's dashboard (the alarm at the fire station):** quiet most of the time, then one light goes red when there's smoke.

The patient never sees the alarm. The nurse never sees the daily chit-chat unless there's a problem. Your demo shows *both at once* — you type the scary answer as Ahmed, and the nurse's screen lights up live. That's the moment that wins.

## Why we don't collect vitals (blood pressure, heart rate, sugar)

You asked a smart question, so here's the honest, simple reasoning — four real problems with asking for vitals:

**1. Most patients can't give them.** Ahmed doesn't own a blood pressure machine. He has no idea what his heart rate is right now. So if your app asks "enter your blood pressure," he just… can't answer. The check-in dies right there. But *everyone* can answer "are your ankles swollen?" — they just look down. You want questions every single patient can answer, not ones that need equipment.

**2. It makes your app feel like a homework form, not a caring check-in.** "Enter BP: ___, Enter heart rate: ___, Enter sugar: ___" feels cold and clinical, like filling out a hospital form. "How are you feeling? Any swelling?" feels like a kind nurse texting you. Simple and human is what makes patients actually reply every day. The moment it feels like a chore, they stop responding — and a check-in nobody answers is worthless.

**3. Vitals drag you into "medical device" territory — legally dangerous.** This is the big one. The moment your app *collects numbers and reacts to them* — "your blood pressure is 180, that's dangerous" — the government can classify you as a **medical device**, which means heavy regulation, approvals, and huge liability. That's a wall you cannot climb in a hackathon, or even as a small startup. By sticking to "how do you feel?" and only ever *flagging a human*, you stay a safe **early-warning helper**, not a regulated medical device. You *want* to stay on the safe side of that line.

**4. Numbers can be wrong and give false confidence.** A patient typing "120" for blood pressure could fat-finger it, or read their machine wrong. Now your app is making decisions on bad data. Whereas "I'm short of breath and my legs are swollen" is a plain human description a nurse can trust and act on. You're not trying to be a measuring instrument — you're trying to notice when someone needs a human.

**The simple rule to remember:** your agent asks **"how do you feel?"**, not **"what are your numbers?"** Feelings, symptoms, and plain words — that's what keeps it simple for patients, useful for nurses, and safe from regulation.

*(One small exception you can mention to a judge to sound sharp: if a patient already has a device and volunteers a reading, the app can accept it and pass it along to the nurse — but it never demands one, and never makes the medical decision itself. That keeps the safe framing intact.)*

---

So the flow, in one line: **friendly daily "how do you feel?" chat → agent quietly checks answers for danger → all good, warm goodbye; danger, calmly reassure the patient and light up the nurse's screen.**








# How to train LLM 


Excellent question — and this is exactly the kind of thing a sharp judge will probe, so it's worth getting right in your head before we design. Let me clear up the biggest misconception first, because it changes everything.

## You do NOT train the LLM. That's the whole point.

I think the word "train" is throwing you off. In the old way of building AI, yes — you'd have to collect thousands of examples and *train* a model for months, and you'd need a separate trained model for heart patients, another for liver patients, another for surgery, and so on. That would be impossible for you, solo, in a weekend. If that were the requirement, this project would be dead.

But modern LLMs (like the ones you already build with) come **pre-trained on essentially all of human medical writing.** The model *already knows* that swelling and breathlessness matter for a heart patient, that fever and a hot, oozing wound matter after surgery, that yellow skin and confusion matter for a liver patient. You don't teach it medicine — it already absorbed medicine during its original training. Your job isn't to *train* it. Your job is to **tell it what to watch for and what to do about it.** That's a completely different, much easier task — and it's the thing you're already good at.

## So how does it actually know a red flag? You *give it the rules.*

Instead of training, you hand the agent a **checklist per condition** — in plain English, written into its instructions. Think of it like giving a new assistant a one-page cheat sheet, not sending them to medical school.

For example, you write into the agent's instructions something like: *"This patient had heart failure. Watch for: swelling in legs/ankles, sudden weight gain, breathlessness, chest pain. If any appear, flag a nurse."* And for a different patient: *"This patient had abdominal surgery. Watch for: fever, wound redness or pus, severe pain, no bowel movement. If any appear, flag a nurse."*

The LLM reads the patient's plain-English reply, compares it against that checklist, and decides. You're not teaching it *how* to understand English or medicine — it already can. You're just telling it *which specific things matter for this specific patient.*

**Where do these checklists come from?** Not from you inventing them — that would be unsafe and a judge would call it out. They come from **real, published discharge guidelines** that already exist for every major condition (hospitals hand patients "warning signs" sheets when they leave — "call your doctor if you notice X, Y, Z"). You're just digitising those official warning-sign lists into the agent's instructions. That's your honest answer to "where did your medical logic come from" — *"from established clinical discharge guidelines, not from me guessing."*

## Now — your real question: many conditions, not just heart

Here's the honest strategic answer, and it splits into "the demo" and "the real product."

**For the hackathon (this weekend):** you do **not** try to cover liver transplants, brain surgery, and every condition. That's a trap — spread thin, you'll do all of them badly and have nothing solid to show. You pick **one condition, done really well** — heart failure — because it's the #1 readmission cause and the symptoms are vivid and easy to demo. You then *mention* that the system is built to expand: "adding a new condition is just adding a new checklist, not rebuilding anything." That sentence alone shows the judges your design scales, without you having to build it all. **Narrow and deep beats broad and shallow** — remember that rule.

**For the real product (later):** you'd build a **library of these condition checklists** — one for heart failure, one for post-surgical, one for COPD, one for liver, etc. — each drawn from that condition's official discharge guidelines and, ideally, reviewed by a real clinician. When a patient is enrolled, the hospital tells you their condition, and the agent loads the matching checklist. Same engine every time; only the cheat sheet changes. *That's* the architecture, and it's genuinely elegant: you're not building 50 different apps, you're building one agent that reads from 50 different one-page instructions.

## The safety backstop that makes this bulletproof

Here's the part that makes the "what if it's a condition you didn't plan for?" worry disappear, and it's your best answer to a tough judge:

**The agent is deliberately biased toward escalating.** It doesn't need to be a perfect diagnostician. When in doubt, it flags a human. So even if a patient says something the checklist didn't specifically anticipate — but it *sounds* worrying — the agent's instruction is "if anything sounds serious or you're unsure, escalate to a nurse anyway." The cost of a false alarm is tiny (a nurse glances and says "fine"). The cost of missing something is huge. So you tune it to over-flag, not under-flag. That means it doesn't have to know *everything* — it just has to know "this sounds bad enough that a human should look." A human always makes the real call.

So your clean answer if a judge asks "how does it handle all the different conditions?":

> "I don't train it — modern LLMs already understand medical language. I give it a checklist of warning signs per condition, taken from real discharge guidelines. For the demo I've done heart failure deeply; adding another condition is just adding another checklist, not rebuilding the system. And it's tuned to escalate to a human whenever anything sounds serious — so it errs on the side of safety, and a nurse always makes the final decision."

That answer shows you understand the technology, the medicine's honest source, the scalable design, *and* the safety — in four sentences. It's a knockout.

---

Does that clear up the "training" worry? The short version to hold onto: **you don't train it, you brief it — with real warning-sign checklists, one condition deep for the demo, and always tilted toward calling a human when unsure.**

