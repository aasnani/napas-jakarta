import { spawn as nodeSpawn } from "node:child_process";
import { pathToFileURL } from "node:url";

const DEFAULT_EVE_PORT = "4274";

function childExitCode(code) {
  return typeof code === "number" && code > 0 ? code : 1;
}

function terminate(child) {
  if (child && child.exitCode === null && !child.killed) {
    child.kill("SIGTERM");
  }
}

export async function superviseProduction({
  env = process.env,
  signalSource = process,
  spawnProcess = nodeSpawn,
} = {}) {
  const evePort = env.EVE_NEXT_PRODUCTION_PORT ?? DEFAULT_EVE_PORT;
  const nextPort = env.PORT ?? "3000";
  const childEnv = {
    ...env,
    EVE_NEXT_PRODUCTION_ORIGIN:
      env.EVE_NEXT_PRODUCTION_ORIGIN ?? `http://127.0.0.1:${evePort}`,
  };

  const children = [
    spawnProcess(
      "./node_modules/.bin/eve",
      ["start", "--host", "127.0.0.1", "--port", evePort],
      { env: childEnv, stdio: "inherit" },
    ),
    spawnProcess(
      // Run Next directly: going through `npm run` keeps an extra idle Node
      // process (and its memory) alive for the life of the service.
      "./node_modules/.bin/next",
      ["start", "--hostname", "0.0.0.0", "--port", nextPort],
      { env: childEnv, stdio: "inherit" },
    ),
  ];

  let shuttingDown = false;
  let resultCode = 0;
  let resolveCompletion;
  const completion = new Promise((resolve) => {
    resolveCompletion = resolve;
  });
  let remaining = children.length;
  const exited = new Set();

  const finish = (code, exclude) => {
    if (shuttingDown) return;
    shuttingDown = true;
    resultCode = code;
    for (const child of children) {
      if (child !== exclude) terminate(child);
    }
  };

  const onExit = (child, code) => {
    if (exited.has(child)) return;
    exited.add(child);
    if (!shuttingDown) finish(childExitCode(code), child);
    remaining -= 1;
    if (remaining === 0) resolveCompletion(resultCode);
  };

  for (const child of children) {
    child.once("exit", (code) => onExit(child, code));
    child.once("error", () => onExit(child, 1));
  }

  const onSignal = () => {
    if (!shuttingDown) finish(0);
  };
  signalSource.on("SIGINT", onSignal);
  signalSource.on("SIGTERM", onSignal);

  try {
    return await completion;
  } finally {
    signalSource.off("SIGINT", onSignal);
    signalSource.off("SIGTERM", onSignal);
  }
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? "").href) {
  process.exitCode = await superviseProduction();
}
