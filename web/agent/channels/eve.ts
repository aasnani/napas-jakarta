import { eveChannel } from "eve/channels/eve";
import { localDev, none } from "eve/channels/auth";

export default eveChannel({
  auth: [
    localDev(),
    // Napas is intentionally a public, no-login experience.
    none(),
  ],
  // The product accepts text questions only. Reject direct file-part requests
  // at Eve's channel boundary as well as hiding attachment controls in the UI.
  uploadPolicy: "disabled",
});
