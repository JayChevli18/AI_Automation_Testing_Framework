export type InterpretedAction =
  | "goto"
  | "hover"
  | "click"
  | "fill"
  | "assert_visible"
  | "assert_text"
  | "wait"
  | "unknown";

export type InterpretedStep = {
  action: InterpretedAction;
  target: string;
  value: string | null;
  value_key: string | null;
  assertion: Record<string, unknown> | null;
  confidence: number;
  missing_value: boolean;
  notes: string | null;
};

export type InterpretedStepRecord = {
  step_index: number;
  raw_step: string;
  interpreted: InterpretedStep | null;
  interpretation_error: Record<string, string> | null;
};

export type InterpretedCaseRecord = {
  test_case_id: string;
  test_case_name: string;
  module: string;
  steps: InterpretedStepRecord[];
};

export type InterpretedStepsReadPayload = {
  success: boolean;
  run_id: string;
  interpreted_steps: InterpretedCaseRecord[];
  revision: number | null;
};

export type InterpretedStepsPatchResponse = {
  success: boolean;
  run_id: string;
  patched_test_case_ids: string[];
  revision: number | null;
  message: string;
};
