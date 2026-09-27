import { getUiCopy, type Language } from "./i18n.ts";

export function localizeChatError(message: string | undefined, language: Language): string | undefined {
  if (!message) return undefined;
  if (/cancel|abort/i.test(message)) return getUiCopy(language).chat.unableToCancel;
  if (/model|gemini|network|fetch|timeout|request|provider|quota|rate limit|429|502|503/i.test(message)) {
    return getUiCopy(language).chat.modelUnavailable;
  }
  return getUiCopy(language).chat.requestFailedDetail;
}
