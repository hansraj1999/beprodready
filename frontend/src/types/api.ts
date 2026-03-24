export type GraphSummary = {
  id: string;
  name: string;
  description: string | null;
  updated_at: string;
};

export type GraphRead = {
  id: string;
  owner_id: string;
  name: string;
  description: string | null;
  nodes: Record<string, unknown>[];
  edges: Record<string, unknown>[];
  created_at: string;
  updated_at: string;
};

export type EvaluateResponse = {
  score: number;
  strengths: string[];
  weaknesses: string[];
  questions: string[];
};

export type InterviewStartResponse = {
  session_id: string;
  message: string;
  first_question: string;
  turn: number;
};

export type AnswerEvaluation = {
  score: number;
  feedback: string;
  strengths: string[];
  improvements: string[];
};

export type InterviewRespondResponse = {
  session_id: string;
  evaluation: AnswerEvaluation;
  follow_up_questions: string[];
  next_question: string;
  turn: number;
};
