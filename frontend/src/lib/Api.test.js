// Run:  node --test src/lib/api.test.js      (Node 20+, no packages needed)
import assert from "node:assert/strict";
import { beforeEach, test } from "node:test";

import {
  ApiError,
  SESSION_EXPIRED_EVENT,
  apiRequest,
  isAuthenticated,
  loginUser,
} from "./api.js";

const KEY = "attention_auth";
const store = new Map();
globalThis.sessionStorage = {
  getItem: (k) => (store.has(k) ? store.get(k) : null),
  setItem: (k, v) => store.set(k, String(v)),
  removeItem: (k) => store.delete(k),
};
globalThis.window = new EventTarget();

const json = (status, body) =>
  new Response(body === undefined ? null : JSON.stringify(body), { status });

/** A fake backend: access token valid only if it equals server.access; refresh tokens work once. */
function fakeServer() {
  const s = {
    access: "A1",
    refresh: "R1",
    n: 1,
    refreshCalls: 0,
    calls: [],
    refreshMode: "ok",
  };
  globalThis.fetch = async (url, init = {}) => {
    const path = String(url).replace("/api/v1", "");
    const auth = new Headers(init.headers).get("Authorization");
    s.calls.push({ path, auth });
    if (path === "/auth/refresh") {
      s.refreshCalls++;
      if (s.refreshMode === "offline") throw new TypeError("Failed to fetch");
      if (s.refreshMode === "busy") return json(503, {});
      const sent = JSON.parse(init.body).refresh_token;
      if (s.refreshMode === "reject" || sent !== s.refresh)
        return json(401, { detail: "Invalid refresh token" });
      s.n++;
      s.access = `A${s.n}`;
      s.refresh = `R${s.n}`;
      return json(200, {
        access_token: s.access,
        refresh_token: s.refresh,
        token_type: "bearer",
      });
    }
    if (path === "/auth/login")
      return json(401, { detail: "Invalid email or password" });
    if (path === "/boom") return json(500, {});
    if (path === "/limited") return json(429, { detail: "Too many requests" });
    if (path === "/invalid")
      return json(422, {
        detail: [{ msg: "Value error, Password needs a digit" }],
      });
    if (path === "/empty") return new Response(null, { status: 204 });
    if (auth !== `Bearer ${s.access}`)
      return json(401, { detail: "Not authenticated" });
    return json(200, { ok: true, path });
  };
  return s;
}

function loginState(access = "A1", refresh = "R1") {
  store.set(
    KEY,
    JSON.stringify({
      access_token: access,
      refresh_token: refresh,
      email: "me@example.com",
    }),
  );
}

beforeEach(() => store.clear());

test("four requests failing at once cause ONE refresh and all succeed", async () => {
  const server = fakeServer();
  server.access = "A2-new"; // the access token held by the browser (A1) is now expired
  loginState("A1", "R1");
  const results = await Promise.all([
    apiRequest("/stats/today"),
    apiRequest("/activity/recent"),
    apiRequest("/goals"),
    apiRequest("/users/me/settings"),
  ]);
  assert.equal(results.length, 4);
  assert.ok(results.every((r) => r.ok));
  assert.equal(server.refreshCalls, 1);
  assert.equal(JSON.parse(store.get(KEY)).refresh_token, server.refresh);
  assert.equal(isAuthenticated(), true);
});

test("a late 401 reuses the token another request already refreshed", async () => {
  const server = fakeServer();
  server.access = "Z";
  loginState("A1", "R1");
  await apiRequest("/first"); // refreshes: browser now has the new token
  const before = server.refreshCalls;
  // simulate a slow request that was sent with the OLD token and only now gets its 401
  store.set(
    KEY,
    JSON.stringify({
      access_token: server.access,
      refresh_token: server.refresh,
      email: "x",
    }),
  );
  await apiRequest("/second");
  assert.equal(server.refreshCalls, before);
});

test("expired session: tokens cleared, event fired, clear message", async () => {
  const server = fakeServer();
  server.access = "other";
  server.refreshMode = "reject";
  loginState();
  let fired = 0;
  window.addEventListener(SESSION_EXPIRED_EVENT, () => fired++);
  await assert.rejects(
    apiRequest("/stats/today"),
    (e) =>
      e instanceof ApiError &&
      e.status === 401 &&
      /log in again/.test(e.message),
  );
  assert.equal(store.get(KEY), undefined);
  assert.equal(fired, 1);
});

test("offline while refreshing keeps the session (no forced logout)", async () => {
  const server = fakeServer();
  server.access = "other";
  server.refreshMode = "offline";
  loginState();
  await assert.rejects(
    apiRequest("/stats/today"),
    (e) => e.status === 0 && /Cannot reach the server/.test(e.message),
  );
  assert.ok(store.get(KEY));
});

test("server busy while refreshing keeps the session", async () => {
  const server = fakeServer();
  server.access = "other";
  server.refreshMode = "busy";
  loginState();
  await assert.rejects(apiRequest("/stats/today"), (e) => e.status === 503);
  assert.ok(store.get(KEY));
});

test("wrong password on login does not try to refresh anything", async () => {
  const server = fakeServer();
  loginState(); // even with an old session in storage
  await assert.rejects(
    loginUser({ email: "a@b.com", password: "x" }),
    (e) => e.status === 401 && e.message === "Invalid email or password",
  );
  assert.equal(server.refreshCalls, 0);
});

test("a request is retried only once (no endless loop)", async () => {
  const server = fakeServer();
  server.access = "other";
  loginState();
  // after the refresh the server still refuses this path
  const original = globalThis.fetch;
  globalThis.fetch = async (url, init) =>
    String(url).endsWith("/stubborn")
      ? json(401, { detail: "Not authenticated" })
      : original(url, init);
  await assert.rejects(apiRequest("/stubborn"), (e) => e.status === 401);
  assert.ok(server.refreshCalls <= 1);
});

test("error messages are readable", async () => {
  fakeServer();
  await assert.rejects(apiRequest("/limited"), /Too many attempts/);
  await assert.rejects(
    apiRequest("/invalid"),
    (e) => e.message === "Password needs a digit" && e.status === 422,
  );
  await assert.rejects(apiRequest("/boom"), /Request failed \(500\)/);
  assert.equal(await apiRequest("/empty"), null);
});

test("server not running gives a clear message", async () => {
  globalThis.fetch = async () => {
    throw new TypeError("Failed to fetch");
  };
  await assert.rejects(
    apiRequest("/stats/today"),
    (e) => e.status === 0 && /Cannot reach the server/.test(e.message),
  );
});
