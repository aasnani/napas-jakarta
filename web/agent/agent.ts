import { defineAgent } from "eve";
import { createNapasModel } from "./model";

export default defineAgent({
  defaultTools: false,
  model: createNapasModel(),
});
