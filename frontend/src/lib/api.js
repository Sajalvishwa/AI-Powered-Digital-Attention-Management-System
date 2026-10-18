const API_BASE = import.meta.env?.VITE_API_BASE_URL || "/api/v1";

const TOKEN_KEY = "attention_auth";
export const SESSION_EXPIRED_EVENT = "attention:session-expired";
const NETWORK_MESSAGE = "Cannot reach the server. Is the backend running?";

export class ApiError extends Error {
  constructor(message, status = 0) {
    super(message);
    this.name = "ApiError";
    this.status = status; // 0 = server not reachable
  }
}

function getTokens() {
  try {
    return JSON.parse(sessionStorage.getItem(TOKEN_KEY) || "null");
  } catch {
    return null;
  }
}

function saveTokens(tokens) {
  sessionStorage.setItem(TOKEN_KEY, JSON.stringify(tokens));
}

export function clearAuth() {
  sessionStorage.removeItem(TOKEN_KEY);
}

async function readResponse(response) {
  if (response.status === 204) return null;

  const text = await response.text();
  let data = null;

  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: text };
    }
  }

  if (!response.ok) {
    const detail = data?.detail;
    let message;
    if (response.status === 429) {
      message = "Too many attempts. Please wait a minute and try again.";
    } else if (Array.isArray(detail)) {
      message =
        detail
          .map((item) => String(item.msg || "").replace(/^Value error, /, ""))
          .filter(Boolean)
          .join(", ") || "Please check your input.";
    } else if (typeof detail === "string") {
      message = detail;
    } else {
      message = `Request failed (${response.status})`;
    }
    throw new ApiError(message, response.status);
  }

  return data;
}

async function send(path, options, accessToken) {
  const headers = new Headers(options.headers || {});

  if (options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  const timeout =
    typeof AbortSignal !== "undefined" &&
    typeof AbortSignal.timeout === "function"
      ? AbortSignal.timeout(15000)
      : undefined;

  try {
    return await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
      signal: options.signal || timeout,
    });
  } catch {
    throw new ApiError(NETWORK_MESSAGE, 0);
  }
}

// ---------------------------------------------------------------------------
// Token refresh. The backend lets a refresh token be used ONCE; a second use is
// treated as theft and ALL tokens of the user are revoked (= random logout).
// So when several requests fail with 401 together, only ONE refresh call may be
// made, and the others wait for its result ("single flight").
// ---------------------------------------------------------------------------
let refreshPromise = null;

async function doRefresh() {
  const tokens = getTokens();
  if (!tokens?.refresh_token) return "expired";

  let response;
  try {
    response = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: tokens.refresh_token }),
    });
  } catch {
    return "offline"; // keep the session: the user is just offline
  }

  if (response.ok) {
    const refreshed = await response.json();
    saveTokens({ ...refreshed, email: tokens.email });
    return "ok";
  }
  if (response.status === 401) return "expired"; // the session is really over
  return "error"; // 429 / 5xx: temporary, keep the session
}

function refreshAccessToken() {
  if (!refreshPromise) {
    refreshPromise = doRefresh().finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

export async function apiRequest(path, options = {}, retry = true) {
  const tokens = getTokens();
  const usedToken = tokens?.access_token || null;
  const response = await send(path, options, usedToken);

  const isAuthCall = path.startsWith("/auth/");
  if (
    response.status === 401 &&
    retry &&
    !isAuthCall &&
    tokens?.refresh_token
  ) {
    // another request may already have refreshed while this one was in flight
    const current = getTokens();
    if (current?.access_token && current.access_token !== usedToken) {
      return apiRequest(path, options, false);
    }

    const result = await refreshAccessToken();
    if (result === "ok") return apiRequest(path, options, false);

    if (result === "expired") {
      clearAuth();
      window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
      throw new ApiError("Your session expired. Please log in again.", 401);
    }
    if (result === "offline") throw new ApiError(NETWORK_MESSAGE, 0);
    throw new ApiError(
      "The server is busy. Please try again in a moment.",
      503,
    );
  }

  return readResponse(response);
}

const jsonBody = (value) => JSON.stringify(value);

export async function registerUser({ name, email, password }) {
  return apiRequest("/auth/register", {
    method: "POST",
    body: jsonBody({ name, email, password }),
  });
}

export async function loginUser({ email, password }) {
  const tokens = await apiRequest("/auth/login", {
    method: "POST",
    body: jsonBody({ email, password }),
  });

  saveTokens({ ...tokens, email });
  return tokens;
}

export async function logoutUser() {
  const tokens = getTokens();

  try {
    if (tokens?.refresh_token) {
      await apiRequest(
        "/auth/logout",
        {
          method: "POST",
          body: jsonBody({ refresh_token: tokens.refresh_token }),
        },
        false,
      );
    }
  } finally {
    clearAuth();
  }
}

export function isAuthenticated() {
  return Boolean(getTokens()?.access_token);
}

export const getCurrentUser = () => apiRequest("/users/me");

export const updateProfile = (data) =>
  apiRequest("/users/me", {
    method: "PUT",
    body: jsonBody(data),
  });

export const getSettings = () => apiRequest("/users/me/settings");

export const updateSettings = (data) =>
  apiRequest("/users/me/settings", {
    method: "PUT",
    body: jsonBody(data),
  });

export const deleteMyData = () =>
  apiRequest("/users/me/data?confirm=true", { method: "DELETE" });

export const getTodayStats = () => apiRequest("/stats/today");

export const getRangeStats = (from, to) =>
  apiRequest(
    `/stats/range?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`,
  );

export const getRecentActivity = (limit = 20) =>
  apiRequest(`/activity/recent?limit=${limit}`);

export const startFocusSession = (planned_min, label = null) =>
  apiRequest("/focus-sessions", {
    method: "POST",
    body: jsonBody({ planned_min, label }),
  });

export const getActiveFocusSession = () => apiRequest("/focus-sessions/active");

export const updateFocusSession = (id, action, switch_count) =>
  apiRequest(`/focus-sessions/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: jsonBody({
      action,
      ...(switch_count === undefined ? {} : { switch_count }),
    }),
  });

export const getFocusSessions = (limit = 20, offset = 0) =>
  apiRequest(`/focus-sessions?limit=${limit}&offset=${offset}`);

export const getGoals = (active_only = false) =>
  apiRequest(`/goals?active_only=${active_only}`);

export const createGoal = (data) =>
  apiRequest("/goals", {
    method: "POST",
    body: jsonBody(data),
  });

export const updateGoal = (id, data) =>
  apiRequest(`/goals/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: jsonBody(data),
  });

export const deleteGoal = (id) =>
  apiRequest(`/goals/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
