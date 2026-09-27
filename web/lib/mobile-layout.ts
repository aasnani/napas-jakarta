export const MOBILE_DEFAULT_SURFACE = "assistant" as const;

export function toggleMobileMapOverlay(isOpen: boolean): boolean {
  return !isOpen;
}
