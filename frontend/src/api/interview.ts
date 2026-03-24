import { requestJson } from "./client";
import type { InterviewRespondResponse, InterviewStartResponse } from "../types/api";

export function startInterview(token: string): Promise<InterviewStartResponse> {
  return requestJson<InterviewStartResponse>("/api/v1/interview/start", {
    method: "POST",
    token,
    body: JSON.stringify({}),
  });
}

export function respondInterview(
  token: string,
  sessionId: string,
  answer: string,
): Promise<InterviewRespondResponse> {
  return requestJson<InterviewRespondResponse>("/api/v1/interview/respond", {
    method: "POST",
    token,
    body: JSON.stringify({ session_id: sessionId, answer }),
  });
}
