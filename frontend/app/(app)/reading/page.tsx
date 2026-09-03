// "use client";
// import { useEffect, useRef, useState } from "react";
// import { BookOpen, Check, Flame, Gauge, X, Zap } from "lucide-react";
// import { RequireAuth } from "@/components/RequireAuth";
// import { StepGuide } from "@/components/StepGuide";
// import { useToast } from "@/components/Toast";
// import { ChoiceOption,
//   Badge, EmptyState, ErrorNote, GapMeter, PageHeader, Section, Skeleton,
// } from "@/components/ui";
// import {
//   ApiError, readingApi,
//   type ReadingPassageRow, type ReadingQuestion,
//   type ReadingResult, type ReadingStart,
// } from "@/lib/api";
// import { useData } from "@/lib/useData";
// import { FullscreenPrompt } from "@/components/FullscreenPrompt";
// import { useProctoring } from "@/lib/proctoring";
// import { CameraPreview } from "@/components/proctoring/CameraPreview";

// export default function ReadingPage() {
//   return (
//     <RequireAuth roles={["student"]}>
//       <Reading />
//     </RequireAuth>
//   );
// }

// type Stage = "intro" | "browse" | "read" | "answer" | "marked";

// const KIND_LABEL: Record<string, string> = {
//   email: "Email",
//   notice: "Notice",
//   report: "Report",
//   article: "Article",
//   instructions: "Instructions",
// };

// /** Reading practice: comprehension and rate, measured separately.
//  *
//  *  The passage is taken away before the questions appear. Leaving it up would
//  *  turn this into a search task — find the sentence with the keyword in it —
//  *  which is a real skill but not the one being claimed, and it would make the
//  *  rate measure meaningless because nobody would need to finish reading.
//  */
// function Reading() {
//   const { toast } = useToast();
//   const { data, loading, error, reload } = useData(() => readingApi.passages());
//   const proctoring = useProctoring();

//   const [stage, setStage] = useState<Stage>("intro");
//   const [session, setSession] = useState<ReadingStart | null>(null);
//   const [questions, setQuestions] = useState<ReadingQuestion[]>([]);
//   const [answers, setAnswers] = useState<Record<string, number | null>>({});
//   const [result, setResult] = useState<ReadingResult | null>(null);
//   const [problem, setProblem] = useState("");
//   const [busy, setBusy] = useState(false);

//   // Set when the passage is put on screen, read when it is taken away.
//   const openedAt = useRef<number>(0);
//   const readMs = useRef<number>(0);

//   async function begin(passage: ReadingPassageRow) {
//     setProblem("");
//     setBusy(true);
//     try {
//       const started = await readingApi.start(passage.id);
//       setSession(started);
//       setQuestions([]);
//       setAnswers({});
//       setResult(null);
//       openedAt.current = Date.now();
//       setStage("read");
//     } catch (err) {
//       setProblem(err instanceof ApiError ? err.detail : "Could not open that passage");
//     } finally {
//       setBusy(false);
//     }
//   }

//   async function finishedReading() {
//     if (!session) return;
//     readMs.current = Date.now() - openedAt.current;
//     setBusy(true);
//     try {
//       setQuestions(await readingApi.questions(session.attempt_id));
//       setStage("answer");
//     } catch (err) {
//       const msg = err instanceof ApiError ? err.detail : "Could not load the questions";
//       setProblem(msg);
//       toast("error", msg);
//     } finally {
//       setBusy(false);
//     }
//   }

//   async function submit() {
//     if (!session) return;
//     setBusy(true);
//     try {
//       setResult(await readingApi.submit(session.attempt_id, {
//         answers: questions.map((q) => ({
//           item_id: q.id, selected_index: answers[q.id] ?? null,
//         })),
//         read_ms: readMs.current,
//       }));
//       toast("success", "Answers submitted successfully");
//       setStage("marked");
//       reload();
//     } catch (err) {
//       const msg = err instanceof ApiError ? err.detail : "Could not submit";
//       setProblem(msg);
//       toast("error", msg);
//     } finally {
//       setBusy(false);
//     }
//   }

//   // Auto-start with a random passage after fullscreen prompt
//   useEffect(() => {
//     if (data && data.length > 0 && stage === "browse" && !session && !busy) {
//       setBusy(true);
//       const random = data[Math.floor(Math.random() * data.length)];
//       begin(random);
//     }
//   }, [data, stage, session, busy]); // eslint-disable-line react-hooks/exhaustive-deps

//   // Request camera when practice starts
//   useEffect(() => {
//     if (stage !== "intro" && !proctoring.state.cameraActive) {
//       proctoring.requestCamera();
//     }
//   }, [stage]);

//   if (stage === "intro") {
//     return <FullscreenPrompt onStart={() => setStage("browse")} />;
//   }

//   if (loading) return <Skeleton rows={5} />;
//   if (error) return <ErrorNote message={error} />;

//   // ------------------------------------------------------------------ read --
//   if (stage === "read" && session) {
//     return (
//       <>
//         <PageHeader
//           title={session.title}
//           sub={`${KIND_LABEL[session.kind] ?? session.kind} · ${session.word_count} words · ${session.question_count} questions afterwards`}
//         />
//         <div className="ds-card p-3 mb-3 text-[11px] text-muted leading-relaxed">
//           Read it once, at your normal pace. The passage is taken away before
//           the questions — you are not meant to look things up, and the time you
//           spend here is measured.
//         </div>
//         <Section>
//           <div className="text-sm leading-loose whitespace-pre-line max-w-[65ch]">
//             {session.body}
//           </div>
//         </Section>
//         {problem && <div className="mt-4"><ErrorNote message={problem} /></div>}
//         <button onClick={finishedReading} disabled={busy}
//                 className="btn btn-primary w-full ds-focus mt-4">
//           {busy ? "Loading…" : "I have finished reading — show the questions"}
//         </button>
//       </>
//     );
//   }

//   // ---------------------------------------------------------------- answer --
//   if (stage === "answer" && session) {
//     const answered = questions.filter((q) => answers[q.id] != null).length;
//     return (
//       <>
//         <CameraPreview
//           videoRef={proctoring.videoRef}
//           faceCount={proctoring.state.faceCount}
//           strikes={proctoring.state.strikes}
//           isFocused={proctoring.state.isFocused}
//         />
//         <PageHeader title={session.title}
//                     sub="Choose one answer for each question. The passage is no longer available." />

//         <div className="ds-card p-3 mb-4 flex items-center gap-3">
//           <div className="flex gap-1.5">
//             {questions.map((q) => (
//               <span key={q.id} className="rounded-full" style={{
//                 width: 9, height: 9,
//                 background: answers[q.id] != null ? "var(--primary)" : "var(--surface-2)",
//                 border: answers[q.id] != null ? "none" : "1.5px solid var(--border)",
//               }} />
//             ))}
//           </div>
//           <span className="text-xs font-semibold">
//             {answered} of {questions.length} answered
//           </span>
//         </div>

//         <div className="space-y-3">
//           {questions.map((q, n) => {
//             const done = answers[q.id] != null;
//             return (
//               <Section key={q.id}>
//                 <div className="flex items-start gap-2 mb-3">
//                   <span className="shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-[11px] font-bold mt-0.5"
//                         style={done ? { background: "var(--primary)", color: "var(--on-primary, #fff)" }
//                                     : { background: "var(--surface-2)", color: "var(--muted)" }}>
//                     {done ? <Check size={12} /> : n + 1}
//                   </span>
//                   <div className="text-sm font-semibold">{q.stem}</div>
//                 </div>
//                 <div className="space-y-2">
//                   {q.options.map((opt, i) => (
//                     <ChoiceOption key={i} label={opt} index={i}
//                                   selected={answers[q.id] === i}
//                                   onSelect={() => setAnswers((a) => ({ ...a, [q.id]: i }))} />
//                   ))}
//                 </div>
//               </Section>
//             );
//           })}
//         </div>
//         {problem && <div className="mt-4"><ErrorNote message={problem} /></div>}
//         <button onClick={submit} disabled={busy || answered === 0}
//                 className="btn btn-primary w-full ds-focus mt-4">
//           {busy ? "Marking…"
//                 : answered < questions.length
//                   ? `Submit — ${questions.length - answered} still unanswered`
//                   : "Submit answers"}
//         </button>
//       </>
//     );
//   }

//   // ---------------------------------------------------------------- marked --
//   if (stage === "marked" && result) {
//     return (
//       <>
//         <PageHeader
//           title={`${result.correct} of ${result.total} correct`}
//           sub={result.title}
//           action={
//             <button onClick={() => { setStage("browse"); setResult(null); }}
//                     className="btn btn-primary btn-sm ds-focus">
//               Another passage
//             </button>
//           }
//         />

//         {/* Two numbers, side by side and never merged. Fast with poor
//             comprehension is skimming; slow with good comprehension is a
//             different problem with a different fix, and one blended score
//             would make those look identical. */}
//         <div className="grid sm:grid-cols-2 gap-3 mb-4">
//           <div className="ds-card p-4">
//             <div className="text-[11px] font-semibold uppercase tracking-wide text-muted">
//               Comprehension
//             </div>
//             <div className="text-2xl font-bold mt-2" style={{ color: "var(--primary)" }}>
//               {result.score}
//             </div>
//             <div className="text-[11px] text-muted mt-1">out of 80 · {result.band}</div>
//           </div>
//           <div className="ds-card p-4">
//             <div className="text-[11px] font-semibold uppercase tracking-wide text-muted flex items-center gap-1.5">
//               <Gauge size={11} /> Reading rate
//             </div>
//             <div className="text-2xl font-bold mt-2" style={{ color: "var(--secondary)" }}>
//               {result.words_per_minute ?? "—"}
//               {result.words_per_minute != null && (
//                 <span className="text-xs font-normal text-muted ml-1">wpm</span>
//               )}
//             </div>
//             <div className="text-[11px] text-muted mt-1">
//               {result.word_count} words
//             </div>
//           </div>
//         </div>

//         <div className="ds-card p-3 mb-4 text-xs leading-relaxed">
//           {result.rate_note}
//         </div>

//         <div className="ds-card p-4 mb-4 flex items-center gap-4 flex-wrap">
//           <span className="flex items-center gap-1.5 text-sm font-bold"
//                 style={{ color: "var(--primary)" }}>
//             <Zap size={15} /> +{result.xp_awarded} XP
//           </span>
//           {result.day_counted_now ? (
//             <span className="flex items-center gap-1.5 text-sm font-bold"
//                   style={{ color: "var(--rag-green)" }}>
//               <Flame size={15} /> Day {result.streak_current} — today is counted
//             </span>
//           ) : result.streak_current > 0 && (
//             <span className="flex items-center gap-1.5 text-xs text-muted">
//               <Flame size={13} /> {result.streak_current}-day streak
//             </span>
//           )}
//         </div>

//         <Section title="Every question, with the reasoning" className="mb-4">
//           <div className="space-y-2">
//             {result.items.map((row) => (
//               <div key={row.item_id} className="ds-inset p-3">
//                 <div className="flex items-start gap-2">
//                   {row.is_correct
//                     ? <Check size={13} className="shrink-0 mt-0.5" style={{ color: "var(--rag-green)" }} />
//                     : <X size={13} className="shrink-0 mt-0.5" style={{ color: "var(--rag-red)" }} />}
//                   <div className="flex-1">
//                     <div className="text-xs font-semibold">{row.stem}</div>
//                     {!row.is_correct && (
//                       <div className="text-[11px] text-muted mt-1">
//                         You chose:{" "}
//                         {row.selected_index != null ? row.options[row.selected_index] : "nothing"}
//                         {" · "}Answer: {row.options[row.correct_index]}
//                       </div>
//                     )}
//                     <p className="text-[11px] text-muted mt-1.5 leading-relaxed">
//                       {row.explanation}
//                     </p>
//                   </div>
//                 </div>
//               </div>
//             ))}
//           </div>
//         </Section>

//         <Section title="The passage again">
//           <div className="text-xs text-muted leading-loose whitespace-pre-line max-w-[65ch]">
//             {result.body}
//           </div>
//         </Section>
//       </>
//     );
//   }

//   // ---------------------------------------------------------------- browse --
//   return (
//     <>
//       <PageHeader
//         title="Reading"
//         sub="Workplace text — emails, notices, reports. Comprehension and reading speed, measured separately."
//       />

//       <StepGuide
//         active={1}
//         steps={[
//           { label: "Pick a passage", detail: "Workplace text — emails, notices, reports." },
//           { label: "Read it", detail: "Your reading time is measured, so read normally." },
//           { label: "Answer the questions", detail: "The passage stays on screen while you answer." },
//           { label: "See your marks", detail: "Comprehension and speed, scored separately." },
//         ]}
//       />

//       {problem && <div className="mb-4"><ErrorNote message={problem} /></div>}

//       {!data || data.length === 0 ? (
//         <EmptyState icon={BookOpen} title="No passages yet"
//                     desc="The reading bank is empty for this institution." />
//       ) : (
//         <div className="grid md:grid-cols-2 gap-3">
//           {data.map((p) => (
//             <button key={p.id} onClick={() => begin(p)} disabled={busy}
//                     className="ds-card p-4 text-left hover:bg-surface2 transition-colors ds-focus">
//               <div className="flex items-start justify-between gap-2">
//                 <div className="text-sm font-bold">{p.title}</div>
//                 {p.best_score != null && (
//                   <Badge tone="var(--rag-green)">best {p.best_score}</Badge>
//                 )}
//               </div>
//               <div className="text-[11px] text-muted mt-1">
//                 {KIND_LABEL[p.kind] ?? p.kind} · {p.word_count} words ·{" "}
//                 {p.question_count} questions
//               </div>
//               {p.best_score != null && (
//                 <div className="mt-2.5"><GapMeter percent={((p.best_score - 20) / 60) * 100} /></div>
//               )}
//             </button>
//           ))}
//         </div>
//       )}

//       <Section title="What this measures" className="mt-4">
//         <p className="text-xs text-muted leading-relaxed">
//           Comprehension — following a passage and answering about what it meant.
//           Several of these bury a qualification: a sentence early on that a
//           later sentence narrows or reverses. Skimmers miss those reliably,
//           which is the point of measuring speed alongside understanding rather
//           than instead of it.
//         </p>
//         <p className="text-xs text-muted leading-relaxed mt-2">
//           The rate is timed on your device, from the passage appearing to you
//           saying you have finished. It is a practice measure, not an
//           invigilated one — a rate too fast to be real is flagged rather than
//           scored.
//         </p>
//       </Section>
//     </>
//   );
// }
"use client";
import { useEffect, useRef, useState } from "react";
import { BookOpen, Check, Flame, Gauge, Loader2, X, Zap } from "lucide-react";
import { RequireAuth } from "@/components/RequireAuth";
import { useToast } from "@/components/Toast";
import {
  ErrorNote, GapMeter, PageHeader, Section,
} from "@/components/ui";
import {
  ApiError, readingApi,
  type ReadingQuestion,
  type ReadingResult, type ReadingStart,
} from "@/lib/api";
import { FullscreenPrompt } from "@/components/FullscreenPrompt";
import ProctorCamera from "@/app/proctoring/ProctorCamera";

export default function ReadingPage() {
  return (
    <RequireAuth roles={["student"]}>
      <Reading />
    </RequireAuth>
  );
}

type Stage = "intro" | "select" | "loading" | "read" | "answer" | "marked";

const KIND_LABEL: Record<string, string> = {
  email: "Email", notice: "Notice", report: "Report",
  article: "Article", instructions: "Instructions", general: "General",
  TCS: "TCS", Infosys: "Infosys", Wipro: "Wipro",
  Accenture: "Accenture", Cognizant: "Cognizant", HCL: "HCL",
  "Tech Mahindra": "Tech Mahindra", Capgemini: "Capgemini",
};

function Reading() {
  const { toast } = useToast();
  const { data, loading, error, reload } = useData(() => readingApi.passages());

  const [stage, setStage] = useState<Stage>("intro");
  const [session, setSession] = useState<ReadingStart | null>(null);
  const [questions, setQuestions] = useState<ReadingQuestion[]>([]);
  const [answers, setAnswers] = useState<Record<string, number | null>>({});
  const [result, setResult] = useState<ReadingResult | null>(null);
  const [problem, setProblem] = useState("");
  const [busy, setBusy] = useState(false);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [showInstructions, setShowInstructions] = useState(false);
  const [answerSeconds, setAnswerSeconds] = useState(0);
  const [difficulty, setDifficulty] = useState<DifficultyLevel>("");

  const openedAt = useRef<number>(0);
  const readMs = useRef<number>(0);

  // Auto-start: fetch a random passage with questions and begin immediately
  async function autoStart() {
    setStage("loading");
    setBusy(true);
    try {
      const started = await readingApi.random();
      // Mark this passage as attempted so it won't appear again today
      markAttempted("reading", started.passage_id);
      setSession(started);
      setQuestions([]);
      setAnswers({});
      setResult(null);
      setCurrentQuestionIndex(0);
      setAnswerSeconds(0);
      openedAt.current = Date.now();
      setExamMode(true);
      setStage("read");
    } catch (err) {
      setProblem(err instanceof ApiError ? err.detail : "No reading passages with questions available yet. Please try again later.");
      toast("error", err instanceof ApiError ? err.detail : "No passages available");
      setStage("intro");
    } finally {
      setBusy(false);
    }
  }

  async function finishedReading() {
    if (!session) return;
    readMs.current = Date.now() - openedAt.current;
    setBusy(true);
    try {
      setQuestions(await readingApi.questions(session.attempt_id));
      setStage("answer");
    } catch (err) {
      const msg = err instanceof ApiError ? err.detail : "Could not load the questions";
      setProblem(msg);
      toast("error", msg);
    } finally {
      setBusy(false);
    }
  }

  async function submit() {
    if (!session) return;
    setBusy(true);
    try {
      setResult(await readingApi.submit(session.attempt_id, {
        answers: questions.map((q) => ({
          item_id: q.id, selected_index: answers[q.id] ?? null,
        })),
        read_ms: readMs.current,
      }));
      toast("success", "Answers submitted successfully");
      proctoring.stopCamera();
      setExamMode(false);
      setStage("marked");
    } catch (err) {
      const msg = err instanceof ApiError ? err.detail : "Could not submit";
      setProblem(msg);
      toast("error", msg);
    } finally {
      setBusy(false);
    }
  }

  // Auto-start with a random passage after fullscreen prompt
  useEffect(() => {
    if (data && data.length > 0 && stage === "browse" && !session && !busy) {
      setBusy(true);
      const random = data[Math.floor(Math.random() * data.length)];
      begin(random);
    }
  }, [data, stage, session, busy]); // eslint-disable-line react-hooks/exhaustive-deps

  if (stage === "intro") {
    return <LevelSelect skill="reading" onSelect={(level) => { setDifficulty(level); setStage("select"); }} />;
  }

  if (stage === "select") {
    return <FullscreenPrompt onStart={autoStart} />;
  }

  if (stage === "loading") {
    return (
      <>
        <PageHeader title="Reading" sub="Loading passage…" />
        <div className="ds-card p-8 flex items-center justify-center gap-3">
          <Loader2 size={18} className="animate-spin text-muted" />
          <span className="text-xs text-muted">Selecting a random passage…</span>
        </div>
      </>
    );
  }

  // ------------------------------------------------------------------ read --
  if (stage === "read" && session) {
    return (
      <FullscreenGuard>
        <CameraPreview
          videoRef={proctoring.videoRef}
          faceCount={proctoring.state.faceCount}
          strikes={proctoring.state.strikes}
          isFocused={proctoring.state.isFocused}
        />
        <PageHeader
          title={session.title}
          sub={`${KIND_LABEL[session.kind] ?? session.kind} · ${session.word_count} words · ${session.question_count} questions afterwards`}
        />
        <div className="ds-card p-3 mb-3 text-[11px] text-muted leading-relaxed">
          Read it once, at your normal pace. The passage is taken away before
          the questions — you are not meant to look things up, and the time you
          spend here is measured.
        </div>
        <Section>
          <div className="text-sm leading-loose whitespace-pre-line max-w-[65ch]">
            {session.body}
          </div>
        </Section>
        {problem && <div className="mt-4"><ErrorNote message={problem} /></div>}
        <button onClick={finishedReading} disabled={busy}
                className="btn btn-primary w-full ds-focus mt-4">
          {busy ? "Loading…" : "I have finished reading — show the questions"}
        </button>
      </FullscreenGuard>
    );
  }

  // ---------------------------------------------------------------- answer --
  if (stage === "answer" && session) {
    const answered = questions.filter((q) => answers[q.id] != null).length;
    const currentQuestion = questions[currentQuestionIndex];
    const isCompany = session.kind !== "general" && session.kind !== "article" && session.kind !== "email" && session.kind !== "notice" && session.kind !== "report";
    const companyLabel = isCompany ? `${session.kind} Round` : "General";

    const questionStatuses: ExamQuestionStatus[] = questions.map((q, i) => ({
      id: q.id, index: i + 1, answered: answers[q.id] != null, selectedOption: answers[q.id] ?? null,
    }));

    const navigateForward = (newIndex: number) => {
      if (newIndex > currentQuestionIndex && newIndex < questions.length) {
        setCurrentQuestionIndex(newIndex);
      }
    };

    const answerQuestion = (choice: number | null) => {
      if (!currentQuestion) return;
      const updated = { ...answers, [currentQuestion.id]: choice };
      setAnswers(updated);
      if (currentQuestionIndex + 1 < questions.length) {
        setCurrentQuestionIndex(currentQuestionIndex + 1);
      }
    };

    const totalAnswerTime = 600;
    const remainingSeconds = Math.max(0, totalAnswerTime - answerSeconds);
    const remainingMinutes = Math.floor(remainingSeconds / 60);
    const remainingSecs = remainingSeconds % 60;

    return (
      <>
        <ProctorCamera
          sessionId={session.attempt_id}
          enabled
          examCompleted={stage === "marked"}
          onAutoEnd={submit}
        />

        <PageHeader title={session.title}
                    sub="Choose one answer for each question. The passage is no longer available." />

        <div className="flex items-center gap-3 mb-4">
          <span className="text-[11px] font-bold uppercase tracking-wider text-muted">
            Question {currentQuestionIndex + 1} of {questions.length}
          </span>
          <div className="flex-1" />
          <span className="text-xs text-muted">
            {answered} of {questions.length} answered
          </span>
        </div>

        {currentQuestion && (
          <Section>
            <div className="flex items-start gap-2 mb-3">
              <span className="shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-[11px] font-bold mt-0.5"
                    style={answers[currentQuestion.id] != null
                      ? { background: "var(--rag-green)", color: "#fff" }
                      : { background: "var(--surface-2)", color: "var(--muted)" }}>
                {answers[currentQuestion.id] != null ? <Check size={12} /> : currentQuestionIndex + 1}
              </span>
              <div className="text-sm font-semibold">{currentQuestion.stem}</div>
            </div>
            <div className="space-y-2">
              {currentQuestion.options.map((opt, i) => (
                <button
                  key={i}
                  onClick={() => answerQuestion(i)}
                  className="w-full flex items-center gap-3 text-left p-3 rounded-lg ds-focus transition-colors"
                  style={{
                    border: `1.5px solid ${answers[currentQuestion.id] === i ? "var(--primary)" : "var(--border)"}`,
                    background: answers[currentQuestion.id] === i
                      ? "color-mix(in srgb, var(--primary) 14%, var(--surface))"
                      : "var(--surface)",
                  }}
                >
                  <span className="shrink-0 rounded-full flex items-center justify-center"
                        style={{
                          width: 18, height: 18,
                          border: `2px solid ${answers[currentQuestion.id] === i ? "var(--primary)" : "var(--muted)"}`,
                        }}>
                    {answers[currentQuestion.id] === i && (
                      <span className="rounded-full" style={{ width: 8, height: 8, background: "var(--primary)" }} />
                    )}
                  </span>
                  <span className="text-sm leading-snug"
                        style={{ color: answers[currentQuestion.id] === i ? "var(--text)" : "var(--fg)",
                                 fontWeight: answers[currentQuestion.id] === i ? 600 : 400 }}>
                    <span className="text-muted mr-1.5">{String.fromCharCode(65 + i)}.</span>
                    {opt}
                  </span>
                </button>
              ))}
            </div>
          </Section>
        )}

        <div className="flex items-center justify-between mt-6 pt-4 border-t border-border">
          <button onClick={() => answerQuestion(null)} className="btn btn-ghost btn-sm ds-focus">
            Skip this one
          </button>
          {currentQuestionIndex + 1 === questions.length ? (
            <button onClick={submit} disabled={busy || answered === 0}
                    className="btn btn-primary ds-focus">
              {busy ? "Marking…"
                    : answered < questions.length
                      ? `Submit — ${questions.length - answered} still unanswered`
                      : "Submit answers"}
            </button>
          ) : (
            <div className="text-[10px] text-muted">
              Answer to proceed to next question
            </div>
          )}
        </div>
      </ExamSidebar>
      </FullscreenGuard>
    );
  }

  // ---------------------------------------------------------------- marked --
  if (stage === "marked" && result) {
    return (
      <>
        <PageHeader
          title={`${result.correct} of ${result.total} correct`}
          sub={result.title}
          action={
            <button onClick={() => autoStart()}
                    className="btn btn-primary btn-sm ds-focus">
              Another passage
            </button>
          }
        />

        <div className="grid sm:grid-cols-2 gap-3 mb-4">
          <div className="ds-card p-4">
            <div className="text-[11px] font-semibold uppercase tracking-wide text-muted">
              Comprehension
            </div>
            <div className="text-2xl font-bold mt-2" style={{ color: "var(--primary)" }}>
              {result.score}
            </div>
            <div className="text-[11px] text-muted mt-1">out of 100 · {result.band}</div>
          </div>
          <div className="ds-card p-4">
            <div className="text-[11px] font-semibold uppercase tracking-wide text-muted flex items-center gap-1.5">
              <Gauge size={11} /> Reading rate
            </div>
            <div className="text-2xl font-bold mt-2" style={{ color: "var(--secondary)" }}>
              {result.words_per_minute ?? "—"}
              {result.words_per_minute != null && (
                <span className="text-xs font-normal text-muted ml-1">wpm</span>
              )}
            </div>
            <div className="text-[11px] text-muted mt-1">
              {result.word_count} words
            </div>
          </div>
        </div>

        <div className="ds-card p-3 mb-4 text-xs leading-relaxed">
          {result.rate_note}
        </div>

        <div className="ds-card p-4 mb-4 flex items-center gap-4 flex-wrap">
          <span className="flex items-center gap-1.5 text-sm font-bold"
                style={{ color: "var(--primary)" }}>
            <Zap size={15} /> +{result.xp_awarded} XP
          </span>
          {result.day_counted_now ? (
            <span className="flex items-center gap-1.5 text-sm font-bold"
                  style={{ color: "var(--rag-green)" }}>
              <Flame size={15} /> Day {result.streak_current} — today is counted
            </span>
          ) : result.streak_current > 0 && (
            <span className="flex items-center gap-1.5 text-xs text-muted">
              <Flame size={13} /> {result.streak_current}-day streak
            </span>
          )}
        </div>

        {/* Review & Rating Card */}
        <ReviewCard attemptId={session?.attempt_id} label="reading" onNext={autoStart} onBack={() => { proctoring.stopCamera(); setStage("intro"); }} nextLabel="Next set →" />

        <Section title="Every question, with the reasoning" className="mb-4">
          <div className="space-y-2">
            {result.items.map((row) => (
              <div key={row.item_id} className="ds-inset p-3">
                <div className="flex items-start gap-2">
                  {row.is_correct
                    ? <Check size={13} className="shrink-0 mt-0.5" style={{ color: "var(--rag-green)" }} />
                    : <X size={13} className="shrink-0 mt-0.5" style={{ color: "var(--rag-red)" }} />}
                  <div className="flex-1">
                    <div className="text-xs font-semibold">{row.stem}</div>
                    {!row.is_correct && (
                      <div className="text-[11px] text-muted mt-1">
                        You chose:{" "}
                        {row.selected_index != null ? row.options[row.selected_index] : "nothing"}
                        {". "}Answer: {row.options[row.correct_index]}
                      </div>
                    )}
                    <p className="text-[11px] text-muted mt-1.5 leading-relaxed">
                      {row.explanation}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Section>

        <Section title="The passage again">
          <div className="text-xs text-muted leading-loose whitespace-pre-line max-w-[65ch]">
            {result.body}
          </div>
        </Section>
      </>
    );
  }

  return null;
}
