const cards = [
  {
    title: "Wallet session",
    body: "Nonce sign-in and wallet connection will live in the frontend and API boundary.",
  },
  {
    title: "Bot control",
    body: "Users will create a market-follow bot config, then start and stop runs from the dashboard.",
  },
  {
    title: "Worker runtime",
    body: "The Python worker keeps running after the browser closes and persists events, orders, and positions.",
  },
];

export default function HomePage() {
  return (
    <main className="shell">
      <section className="hero">
        <span className="eyebrow">Polymarket Web App MVP</span>
        <h1>Market-follow bot control surface.</h1>
        <p>
          This frontend is the new entry point for the wallet-connected product.
          The Python engine will move behind an API and worker boundary so users
          can configure, launch, and monitor automated runs from the web.
        </p>
        <a className="cta" href="/app">
          Open dashboard
        </a>
        <div className="grid">
          {cards.map((card) => (
            <article className="card" key={card.title}>
              <strong>{card.title}</strong>
              <span>{card.body}</span>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
