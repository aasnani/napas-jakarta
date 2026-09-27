export function shouldShowPendingThinking({
  isBusy,
  isResuming,
}: {
  readonly isBusy: boolean;
  readonly isResuming: boolean;
}): boolean {
  return isBusy || isResuming;
}

export function shouldShowSuggestedQuestions({
  hasAssistantAnswer,
  isBusy,
  isEmpty,
  isResuming,
}: {
  readonly hasAssistantAnswer: boolean;
  readonly isBusy: boolean;
  readonly isEmpty: boolean;
  readonly isResuming: boolean;
}): boolean {
  return isEmpty || (!isBusy && !isResuming && hasAssistantAnswer);
}
