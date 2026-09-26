import { defineAgent } from "eve";
import { anthropic } from "eve/models/anthropic";

export default defineAgent({
  model: anthropic(process.env.NAPAS_AGENT_MODEL),
});
