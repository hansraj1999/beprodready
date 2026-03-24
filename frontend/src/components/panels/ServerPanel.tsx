import { useState } from "react";
import { useAuth } from "../../auth/AuthContext";
import { ApiError } from "../../api/errors";
import { respondInterview } from "../../api/interview";
import type { EvaluateResponse, InterviewRespondResponse } from "../../types/api";

export type InterviewState = {
  sessionId: string;
  opening: string;
  currentQuestion: string;
  turn: number;
  transcript: { role: "assistant" | "user"; text: string }[];
};

type Props = {
  evaluation: EvaluateResponse | null;
  interview: InterviewState | null;
  onInterviewUpdate: (next: InterviewState | null) => void;
  onInterviewReset: () => void;
  onApiError: (message: string | null) => void;
};

function appendEvaluation(lines: string[], r: InterviewRespondResponse) {
  const ev = r.evaluation;
  lines.push(`Score: ${ev.score}`);
  if (ev.feedback) lines.push(ev.feedback);
  if (ev.strengths.length) lines.push(`Strengths: ${ev.strengths.join("; ")}`);
  if (ev.improvements.length) lines.push(`Improve: ${ev.improvements.join("; ")}`);
  if (r.follow_up_questions.length) {
    lines.push(`Follow-ups: ${r.follow_up_questions.join(" | ")}`);
  }
}

export function ServerPanel({
  evaluation,
  interview,
  onInterviewUpdate,
  onInterviewReset,
  onApiError,
}: Props) {
  const { getIdToken } = useAuth();
  const [answer, setAnswer] = useState("");
  const [busy, setBusy] = useState(false);

  const onSubmitAnswer = () => {
    if (!interview || !answer.trim()) return;
    onApiError(null);
    setBusy(true);
    void (async () => {
      try {
        const token = await getIdToken();
        if (!token) throw new Error("Sign in to continue the interview");
        const r = await respondInterview(token, interview.sessionId, answer.trim());
        const transcript = [
          ...interview.transcript,
          { role: "user" as const, text: answer.trim() },
        ];
        const feedbackLines: string[] = [];
        appendEvaluation(feedbackLines, r);
        transcript.push({ role: "assistant", text: feedbackLines.join("\n") });
        if (r.next_question) {
          transcript.push({ role: "assistant", text: r.next_question });
        }
        onInterviewUpdate({
          sessionId: r.session_id,
          opening: interview.opening,
          currentQuestion: r.next_question || interview.currentQuestion,
          turn: r.turn,
          transcript,
        });
        setAnswer("");
      } catch (e) {
        onApiError(
          e instanceof ApiError
            ? e.message
            : e instanceof Error
              ? e.message
              : "Interview request failed",
        );
      } finally {
        setBusy(false);
      }
    })();
  };

  return (
    <section className="server-panel">
      <h2 className="server-panel__title">AI feedback</h2>

      <div className="server-panel__block">
        <h3 className="server-panel__subtitle">Evaluation</h3>
        {!evaluation ? (
          <p className="server-panel__empty">Run Evaluate on the toolbar to see scores and suggestions.</p>
        ) : (
          <div className="server-panel__eval">
            <div className="server-panel__score">Score: {evaluation.score} / 100</div>
            <ul className="server-panel__list">
              {evaluation.strengths.map((s) => (
                <li key={`s-${s}`}>
                  <strong>+</strong> {s}
                </li>
              ))}
              {evaluation.weaknesses.map((w) => (
                <li key={`w-${w}`}>
                  <strong>−</strong> {w}
                </li>
              ))}
            </ul>
            {evaluation.questions.length > 0 ? (
              <div className="server-panel__questions">
                <span className="server-panel__label">Questions</span>
                <ul className="server-panel__list">
                  {evaluation.questions.map((q) => (
                    <li key={q}>{q}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        )}
      </div>

      <div className="server-panel__block">
        <div className="server-panel__interview-head">
          <h3 className="server-panel__subtitle">Interview</h3>
          {interview ? (
            <button type="button" className="toolbar__btn" onClick={onInterviewReset}>
              End session
            </button>
          ) : null}
        </div>
        {!interview ? (
          <p className="server-panel__empty">Start Interview from the toolbar to open a session.</p>
        ) : (
          <div className="server-panel__interview">
            <div className="server-panel__transcript">
              {interview.transcript.map((line, i) => (
                <p key={`${i}-${line.role}`} className={`server-panel__line server-panel__line--${line.role}`}>
                  {line.text}
                </p>
              ))}
            </div>
            <label className="server-panel__answer-label">
              Your answer
              <textarea
                className="server-panel__textarea"
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                rows={4}
                disabled={busy}
                placeholder="Type your answer…"
              />
            </label>
            <button
              type="button"
              className="toolbar__btn toolbar__btn--primary"
              disabled={busy || !answer.trim()}
              onClick={() => void onSubmitAnswer()}
            >
              Send answer
            </button>
          </div>
        )}
      </div>
    </section>
  );
}

/** Build initial transcript from start response */
export function interviewStateFromStart(r: {
  message: string;
  first_question: string;
  session_id: string;
  turn: number;
}): InterviewState {
  return {
    sessionId: r.session_id,
    opening: r.message,
    currentQuestion: r.first_question,
    turn: r.turn,
    transcript: [
      { role: "assistant", text: r.message },
      { role: "assistant", text: r.first_question },
    ],
  };
}
