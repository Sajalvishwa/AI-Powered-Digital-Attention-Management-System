import { app, BrowserWindow, ipcMain } from "electron";
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const isDev = !app.isPackaged;

const projectRoot = path.resolve(__dirname, "../..");
const agentDirectory = path.join(projectRoot, "desktop-agent");

// Backend address. For a hosted backend change this to its https origin and set
// VITE_API_BASE_URL in frontend/.env.production to match before building.
const API_ORIGIN = "http://127.0.0.1:8000";

// Development: run the agent from its Python venv.
// Installed app: run the PyInstaller build that electron-builder copied to
// <resources>/agent.
function resolveAgentLaunch(extraArgs) {
  if (app.isPackaged) {
    const exe = path.join(
      process.resourcesPath,
      "agent",
      "attention-agent.exe",
    );
    return {
      command: exe,
      args: extraArgs,
      cwd: path.dirname(exe),
      required: exe,
    };
  }

  const python = path.join(agentDirectory, "venv", "Scripts", "python.exe");
  return {
    command: python,
    args: ["-u", "-m", "app.main", ...extraArgs],
    cwd: agentDirectory,
    required: python,
  };
}

// The agent reads this to find the backend (overrides config.toml).
const agentEnv = {
  ...process.env,
  ATTENTION_API_BASE_URL: `${API_ORIGIN}/api/v1`,
};

const agentDataDirectory = path.join(app.getPath("appData"), "AttentionAgent");

const agentLogFile = path.join(agentDataDirectory, "electron-agent.log");

// The Python agent watches for this file and shuts down cleanly when it appears.
const stopFlagFile = path.join(agentDataDirectory, "stop.flag");

let mainWindow = null;
let agentProcess = null;
let agentStopping = false;
let agentError = "";
let isQuitting = false;

function writeAgentLog(message) {
  const timestamp = new Date().toISOString();
  const line = `[${timestamp}] ${message}\n`;

  try {
    fs.mkdirSync(agentDataDirectory, { recursive: true });
    fs.appendFileSync(agentLogFile, line, "utf8");
  } catch (error) {
    console.error("Could not write agent log:", error);
  }
}

function isAgentRunning() {
  return Boolean(
    agentProcess &&
    agentProcess.exitCode === null &&
    agentProcess.signalCode === null,
  );
}

function waitForExit(ms = 10000) {
  return new Promise((resolve) => {
    const startedAt = Date.now();
    const id = setInterval(() => {
      if (!isAgentRunning() || Date.now() - startedAt > ms) {
        clearInterval(id);
        resolve();
      }
    }, 200);
  });
}

async function isBackendReachable() {
  try {
    const response = await fetch(`${API_ORIGIN}/health`, {
      signal: AbortSignal.timeout(2000),
    });

    return response.ok;
  } catch {
    return false;
  }
}

async function getAgentStatus() {
  const backendReachable = await isBackendReachable();

  return {
    supported: true,
    running: isAgentRunning() && !agentStopping,
    backendReachable,
    stopping: agentStopping,
    error: agentError,
  };
}

function startAgentProcess() {
  if (isAgentRunning()) {
    return { started: false };
  }

  agentError = "";
  agentStopping = false;

  const launch = resolveAgentLaunch([]);

  if (!fs.existsSync(launch.required)) {
    agentError = `Agent not found: ${launch.required}`;
    writeAgentLog(agentError);
    return { started: false, error: agentError };
  }

  let logFd;

  try {
    fs.mkdirSync(agentDataDirectory, { recursive: true });

    // Remove a stale stop request from an earlier run.
    try {
      fs.unlinkSync(stopFlagFile);
    } catch {
      // No stale flag.
    }

    logFd = fs.openSync(agentLogFile, "a");

    const child = spawn(launch.command, launch.args, {
      cwd: launch.cwd,
      env: agentEnv,
      windowsHide: true,
      detached: false,
      stdio: ["ignore", logFd, logFd],
    });

    agentProcess = child;
    writeAgentLog(`Agent process launched. PID: ${child.pid ?? "unknown"}`);

    child.once("error", (error) => {
      agentError = `Agent launch failed: ${error.message}`;
      writeAgentLog(agentError);

      if (agentProcess === child) {
        agentProcess = null;
        agentStopping = false;
      }
    });

    child.once("exit", (code, signal) => {
      writeAgentLog(`Agent exited. Code: ${code}; signal: ${signal ?? "none"}`);

      if (agentProcess === child) {
        agentProcess = null;
        agentStopping = false;

        if (code !== 0 && code !== null) {
          agentError = `Agent exited with code ${code}. Check ${agentLogFile}`;
        } else if (signal && !isQuitting) {
          agentError = `Agent stopped (${signal}).`;
        }
      }

      if (isQuitting) {
        app.quit();
      }
    });

    return { started: true };
  } catch (error) {
    agentError = `Could not start agent: ${error.message}`;
    writeAgentLog(agentError);

    return { started: false, error: agentError };
  } finally {
    if (logFd !== undefined) {
      try {
        fs.closeSync(logFd);
      } catch {
        // The child process has its own inherited log handles.
      }
    }
  }
}

function stopAgentProcess() {
  if (!isAgentRunning()) {
    agentStopping = false;
    return { stopped: true };
  }

  const child = agentProcess;
  agentStopping = true;

  try {
    // Graceful stop: the agent sees this file, flushes the last session,
    // does a final sync and exits on its own.
    fs.mkdirSync(agentDataDirectory, { recursive: true });
    fs.writeFileSync(stopFlagFile, "stop", "utf8");

    writeAgentLog("Stop requested (stop.flag written).");

    // Fallback: force-kill only if the agent does not exit in time.
    setTimeout(() => {
      if (child.exitCode === null && child.signalCode === null) {
        writeAgentLog("Agent did not stop in time; killing it.");
        child.kill();
      }
    }, 10000);

    return { stopped: true, stopping: true };
  } catch (error) {
    agentStopping = false;
    agentError = `Could not stop agent: ${error.message}`;
    writeAgentLog(agentError);

    return { stopped: false, error: agentError };
  }
}

// Run "python -m app.main <command>" (login / logout) and wait for it to finish.
// Credentials are passed through stdin only, never as arguments and never logged.
function runAgentCommand(command, stdinText = "") {
  return new Promise((resolve) => {
    const extraArgs = [command];
    if (command === "login") extraArgs.push("--show-password");

    const launch = resolveAgentLaunch(extraArgs);

    if (!fs.existsSync(launch.required)) {
      resolve({ ok: false, error: `Agent not found: ${launch.required}` });
      return;
    }

    let child;
    try {
      child = spawn(launch.command, launch.args, {
        cwd: launch.cwd,
        env: agentEnv,
        windowsHide: true,
        stdio: ["pipe", "ignore", "ignore"],
      });
    } catch (error) {
      resolve({ ok: false, error: error.message });
      return;
    }

    const timer = setTimeout(() => {
      child.kill();
      resolve({ ok: false, error: "Agent command timed out" });
    }, 20000);

    child.once("error", (error) => {
      clearTimeout(timer);
      resolve({ ok: false, error: error.message });
    });

    child.once("close", (code) => {
      clearTimeout(timer);
      resolve({
        ok: code === 0,
        error: code === 0 ? "" : `Agent ${command} failed`,
      });
    });

    child.stdin.on("error", () => {
      // Process ended before reading stdin; "close" reports the result.
    });
    if (stdinText) child.stdin.write(stdinText);
    child.stdin.end();
  });
}

ipcMain.handle("agent:status", async () => {
  return getAgentStatus();
});

ipcMain.handle("agent:start", async () => {
  if (!isAgentRunning()) {
    const result = startAgentProcess();

    if (!result.started) {
      return {
        ...(await getAgentStatus()),
        ok: false,
        error: result.error || agentError,
      };
    }

    // Allow the Python process to initialize.
    await new Promise((resolve) => setTimeout(resolve, 700));
  }

  const status = await getAgentStatus();

  return {
    ...status,
    ok: status.running,
    error: agentError || status.error,
  };
});

ipcMain.handle("agent:stop", async () => {
  const result = stopAgentProcess();

  // Wait until the agent has flushed and synced, then report the real status.
  await waitForExit();

  return {
    ...(await getAgentStatus()),
    ok: result.stopped,
    stopping: false,
    error: result.error || agentError,
  };
});

ipcMain.handle("agent:login", async (_event, creds) => {
  const email = creds?.email;
  const password = creds?.password;

  if (typeof email !== "string" || typeof password !== "string") {
    return { ok: false, error: "Invalid credentials" };
  }
  if (/[\r\n]/.test(email) || /[\r\n]/.test(password)) {
    return { ok: false, error: "Invalid credentials" };
  }

  return runAgentCommand("login", `${email}\n${password}\n`);
});

ipcMain.handle("agent:logout", async () => {
  return runAgentCommand("logout");
});

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1000,
    minHeight: 650,
    title: "Attention - Focus Workspace",
    backgroundColor: "#101713",
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
  });

  if (isDev) {
    mainWindow.loadURL("http://localhost:5173");
  } else {
    mainWindow.loadFile(path.join(__dirname, "../dist/index.html"));
  }
}

app.whenReady().then(() => {
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("before-quit", (event) => {
  if (isQuitting) {
    return;
  }

  if (isAgentRunning()) {
    event.preventDefault();
    isQuitting = true;
    stopAgentProcess();

    // The exit handler calls app.quit() once the agent has stopped
    // (or after the fallback kill).
    return;
  }

  isQuitting = true;
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
