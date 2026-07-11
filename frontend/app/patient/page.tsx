"use client";

/**
 * /patient — WhatsApp-style daily check-in chat (CLAUDE.md §9).
 *
 * Safety (§2): on a red flag the patient sees ONLY the calm reply text.
 * The `alert` field returned by POST /chat is never read or rendered here.
 */

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { getConversation, getPatients, sendChat, startCheckin } from "@/lib/api";
import type { Patient, Sender } from "@/lib/types";
import MockBadge from "@/components/MockBadge";

interface Bubble {
  key: string;
  sender: Sender;
  text: string;
}

const DEFAULT_PATIENT_ID = 1; // Ahmed Raza (heart failure demo patient)

/** Show Yes / No / A little chips only for closed (yes/no-style) questions. */
function isClosedQuestion(text: string): boolean {
  if (!text.includes("?")) return false;
  if (/how are you|what|tell me|anything (else|more)|why|feeling today/i.test(text)) {
    return false;
  }
  return /\b(any|are you|do you|did you|have you|has|is your|managing|taking|harder)\b/i.test(
    text
  );
}

export default function PatientChat() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [patientId, setPatientId] = useState(DEFAULT_PATIENT_ID);
  const [bubbles, setBubbles] = useState<Bubble[]>([]);
  const [typing, setTyping] = useState(false);
  const [input, setInput] = useState("");
  const [loadError, setLoadError] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const keyRef = useRef(0);

  const nextKey = () => `b${keyRef.current++}`;

  // Patient selector data (demo convenience — a real patient would be logged in).
  useEffect(() => {
    getPatients()
      .then(setPatients)
      .catch(() => setPatients([]));
  }, []);

  // Load history for the selected patient; start a check-in if it's empty.
  useEffect(() => {
    let cancelled = false;
    setBubbles([]);
    setLoadError(false);
    (async () => {
      try {
        const conv = await getConversation(patientId);
        if (cancelled) return;
        if (conv.messages.length > 0) {
          setBubbles(
            conv.messages.map((m) => ({ key: nextKey(), sender: m.sender, text: m.text }))
          );
        } else {
          setTyping(true);
          const started = await startCheckin(patientId);
          if (cancelled) return;
          setBubbles([{ key: nextKey(), sender: "agent", text: started.reply }]);
        }
      } catch {
        if (!cancelled) setLoadError(true);
      } finally {
        if (!cancelled) setTyping(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [patientId]);

  // Keep the newest message in view.
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [bubbles, typing]);

  const send = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || typing) return;
      setInput("");
      setBubbles((prev) => [...prev, { key: nextKey(), sender: "patient", text: trimmed }]);
      setTyping(true);
      try {
        // NOTE: response.alert is intentionally ignored on this screen (§2).
        const res = await sendChat(patientId, trimmed);
        setBubbles((prev) => [...prev, { key: nextKey(), sender: "agent", text: res.reply }]);
      } catch {
        setBubbles((prev) => [
          ...prev,
          {
            key: nextKey(),
            sender: "agent",
            text: "Sorry, I couldn't send that just now. Please try again in a moment.",
          },
        ]);
      } finally {
        setTyping(false);
      }
    },
    [patientId, typing]
  );

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    void send(input);
  };

  const lastBubble = bubbles[bubbles.length - 1];
  const showChips = !typing && lastBubble?.sender === "agent" && isClosedQuestion(lastBubble.text);
  const currentPatient = patients.find((p) => p.id === patientId);

  return (
    <div className="flex flex-1 justify-center">
      <div className="flex h-dvh w-full max-w-md flex-col bg-page sm:my-0 sm:shadow-card">
        {/* Header */}
        <header className="flex items-center gap-3 bg-pine px-4 py-3 text-white">
          <Link
            href="/"
            aria-label="Back to home"
            className="rounded-full p-1 text-white/80 transition-colors hover:bg-white/10 hover:text-white"
          >
            <svg aria-hidden width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path
                d="M12.5 4.5 7 10l5.5 5.5"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </Link>
          <div
            aria-hidden
            className="flex size-10 items-center justify-center rounded-full bg-white/15 text-lg font-bold"
          >
            A
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate font-semibold leading-tight">AfterCare check-in</p>
            <p className="flex items-center gap-1.5 text-xs text-white/75">
              <span aria-hidden className="size-1.5 rounded-full bg-good" />
              City Hospital care team
            </p>
          </div>
          {patients.length > 0 && (
            <label className="text-xs text-white/80">
              <span className="sr-only">Chatting as patient</span>
              <select
                value={patientId}
                onChange={(e) => setPatientId(Number(e.target.value))}
                className="max-w-28 rounded-lg border border-white/25 bg-pine-deep px-2 py-1.5 text-xs text-white"
              >
                {patients.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </label>
          )}
        </header>

        {/* Messages */}
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto px-4 py-4"
          aria-label={`Conversation with your care team${
            currentPatient ? ` as ${currentPatient.name}` : ""
          }`}
        >
          <ol className="flex flex-col gap-2.5" aria-live="polite">
            {bubbles.map((b) => (
              <li
                key={b.key}
                className={`max-w-[85%] rounded-bubble px-4 py-2.5 text-[17px] leading-relaxed shadow-card ${
                  b.sender === "agent"
                    ? "self-start rounded-bl-md bg-card text-ink"
                    : "self-end rounded-br-md bg-pine text-white"
                }`}
              >
                <span className="sr-only">
                  {b.sender === "agent" ? "Care team: " : "You: "}
                </span>
                {b.text}
              </li>
            ))}
            {typing && (
              <li
                className="flex items-center gap-1.5 self-start rounded-bubble rounded-bl-md bg-card px-4 py-3.5 shadow-card"
                aria-label="Care team is typing"
              >
                <span className="typing-dot size-2 rounded-full bg-ink-soft" />
                <span className="typing-dot size-2 rounded-full bg-ink-soft" />
                <span className="typing-dot size-2 rounded-full bg-ink-soft" />
              </li>
            )}
          </ol>
          {loadError && (
            <p className="mt-4 rounded-xl bg-card px-4 py-3 text-center text-sm text-ink-soft shadow-card">
              We couldn&rsquo;t load your check-in. Please refresh to try again.
            </p>
          )}
        </div>

        {/* Answer chips */}
        {showChips && (
          <div className="flex gap-2 px-4 pb-2" role="group" aria-label="Quick answers">
            {["Yes", "No", "A little"].map((chip) => (
              <button
                key={chip}
                type="button"
                onClick={() => void send(chip)}
                className="flex-1 rounded-full border-2 border-pine/30 bg-card px-4 py-2.5 text-[16px] font-semibold text-pine transition-colors hover:border-pine hover:bg-pine-soft active:bg-pine-soft"
              >
                {chip}
              </button>
            ))}
          </div>
        )}

        {/* Composer */}
        <form onSubmit={onSubmit} className="flex items-end gap-2 px-4 pb-4 pt-1">
          <label htmlFor="chat-input" className="sr-only">
            Type your message
          </label>
          <input
            id="chat-input"
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type how you're feeling…"
            autoComplete="off"
            className="min-w-0 flex-1 rounded-full border border-line bg-card px-4 py-3 text-[17px] text-ink placeholder:text-ink-soft/70"
          />
          <button
            type="submit"
            disabled={!input.trim() || typing}
            aria-label="Send message"
            className="flex size-12 shrink-0 items-center justify-center rounded-full bg-pine text-white shadow-card transition-colors hover:bg-pine-deep disabled:opacity-40"
          >
            <svg aria-hidden width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path
                d="M3 10h13M11 4.5 16.5 10 11 15.5"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        </form>
      </div>
      <MockBadge />
    </div>
  );
}
