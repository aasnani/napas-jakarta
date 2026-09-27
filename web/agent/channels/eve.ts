import { eveChannel } from "eve/channels/eve";
import { localDev, none } from "eve/channels/auth";

export default eveChannel({
  auth: [
    localDev(),
    // Napas is intentionally a public, no-login experience.
    none(),
  ],
});
