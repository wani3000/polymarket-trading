"use client";

import { FormEvent, useEffect, useState } from "react";

import { apiRequest } from "../lib/api";

type NonceResponse = {
  wallet_address: string;
  nonce: string;
  message: string;
  expires_at: string;
};

type SessionResponse = {
  session?: string;
  token?: string;
  wallet_address: string;
  user_id?: string;
  expires_at: string;
};

type Bot = {
  id: string;
  name: string;
  mode: string;
  strategy_type: string;
  bankroll_limit: number;
  max_position_pct: number;
  max_open_positions: number;
  daily_loss_limit: number;
  status: string;
};

const SESSION_KEY = "polymarket-web-session";

export function Dashboard() {
  const [walletAddress, setWalletAddress] = useState("");
  const [message, setMessage] = useState("");
  const [signature, setSignature] = useState("");
  const [sessionToken, setSessionToken] = useState("");
  const [sessionInfo, setSessionInfo] = useState<SessionResponse | null>(null);
  const [bots, setBots] = useState<Bot[]>([]);
  const [status, setStatus] = useState("API not checked");
  const [error, setError] = useState("");
  const [botName, setBotName] = useState("Market Follow MVP");

  useEffect(() => {
    const saved = window.localStorage.getItem(SESSION_KEY);
    if (saved) {
      setSessionToken(saved);
    }
  }, []);

  async function checkHealth() {
    setError("");
    const data = await apiRequest<{ status: string }>("/health");
    setStatus(`API: ${data.status}`);
  }

  async function requestNonce(event: FormEvent) {
    event.preventDefault();
    setError("");
    const data = await apiRequest<NonceResponse>("/auth/nonce", {
      method: "POST",
      body: JSON.stringify({ wallet_address: walletAddress }),
    });
    setMessage(data.message);
  }

  async function verifySignature(event: FormEvent) {
    event.preventDefault();
    setError("");
    const data = await apiRequest<SessionResponse>("/auth/verify", {
      method: "POST",
      body: JSON.stringify({
        wallet_address: walletAddress,
        message,
        signature,
      }),
    });
    const token = data.session ?? "";
    setSessionToken(token);
    setSessionInfo(data);
    window.localStorage.setItem(SESSION_KEY, token);
  }

  async function loadSession() {
    if (!sessionToken) {
      setError("Missing session token.");
      return;
    }
    setError("");
    const data = await apiRequest<SessionResponse>("/auth/me", undefined, sessionToken);
    setSessionInfo(data);
  }

  async function loadBots() {
    if (!sessionToken) {
      setError("Missing session token.");
      return;
    }
    setError("");
    const data = await apiRequest<{ items: Bot[] }>("/bots", undefined, sessionToken);
    setBots(data.items);
  }

  async function createBot(event: FormEvent) {
    event.preventDefault();
    if (!sessionToken) {
      setError("Missing session token.");
      return;
    }
    setError("");
    await apiRequest(
      "/bots",
      {
        method: "POST",
        body: JSON.stringify({
          name: botName,
          mode: "paper",
          strategy_type: "market_follow",
          bankroll_limit: 1000,
          max_position_pct: 0.1,
          max_open_positions: 5,
          daily_loss_limit: 100,
        }),
      },
      sessionToken,
    );
    await loadBots();
  }

  async function startBot(botId: string) {
    if (!sessionToken) {
      setError("Missing session token.");
      return;
    }
    setError("");
    await apiRequest(`/bots/${botId}/start`, { method: "POST" }, sessionToken);
    await loadBots();
  }

  return (
    <main className="shell">
      <section className="hero">
        <span className="eyebrow">Dashboard Prototype</span>
        <h1>Wallet auth and bot control.</h1>
        <p>
          This page is the first web control surface for the new architecture.
          It is wired for nonce auth, session lookup, and paper bot creation
          against the FastAPI backend.
        </p>
        <div className="toolbar">
          <button className="cta secondary" onClick={checkHealth} type="button">
            Check API
          </button>
          <span className="status">{status}</span>
        </div>
        {error ? <p className="error">{error}</p> : null}
      </section>

      <section className="panel-grid">
        <article className="panel">
          <h2>1. Request nonce</h2>
          <form className="stack" onSubmit={requestNonce}>
            <input
              placeholder="0x wallet address"
              value={walletAddress}
              onChange={(event) => setWalletAddress(event.target.value)}
            />
            <button className="cta" type="submit">
              Issue nonce
            </button>
          </form>
          {message ? <pre className="code">{message}</pre> : null}
        </article>

        <article className="panel">
          <h2>2. Verify signature</h2>
          <form className="stack" onSubmit={verifySignature}>
            <textarea
              placeholder="Paste wallet signature"
              value={signature}
              onChange={(event) => setSignature(event.target.value)}
            />
            <button className="cta" type="submit">
              Verify
            </button>
          </form>
          {sessionToken ? <pre className="code">{sessionToken}</pre> : null}
        </article>

        <article className="panel">
          <h2>3. Session</h2>
          <div className="stack">
            <input
              placeholder="Bearer session token"
              value={sessionToken}
              onChange={(event) => setSessionToken(event.target.value)}
            />
            <button className="cta" type="button" onClick={loadSession}>
              Load session
            </button>
          </div>
          {sessionInfo ? (
            <pre className="code">{JSON.stringify(sessionInfo, null, 2)}</pre>
          ) : null}
        </article>
      </section>

      <section className="panel-grid">
        <article className="panel">
          <h2>Create paper bot</h2>
          <form className="stack" onSubmit={createBot}>
            <input
              placeholder="Bot name"
              value={botName}
              onChange={(event) => setBotName(event.target.value)}
            />
            <button className="cta" type="submit">
              Create bot
            </button>
          </form>
        </article>

        <article className="panel wide">
          <div className="split">
            <h2>Bots</h2>
            <button className="cta secondary" onClick={loadBots} type="button">
              Refresh
            </button>
          </div>
          <div className="stack">
            {bots.length === 0 ? <span className="muted">No bots yet.</span> : null}
            {bots.map((bot) => (
              <div className="botRow" key={bot.id}>
                <div>
                  <strong>{bot.name}</strong>
                  <div className="muted">
                    {bot.strategy_type} · {bot.mode} · {bot.status}
                  </div>
                </div>
                <button className="cta secondary" onClick={() => startBot(bot.id)} type="button">
                  Start
                </button>
              </div>
            ))}
          </div>
        </article>
      </section>
    </main>
  );
}
