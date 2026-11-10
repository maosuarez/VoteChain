import Link from "next/link";

export const metadata = { title: "VoteChain" };

export default function Home() {
  return (
    <main>
      <h1>VoteChain</h1>
      <p>Elecciones de reconocimiento de la Facultad de Ingeniería.</p>
      <p className="row">
        <Link className="btn primary" href="/votar">Votar</Link>
        <Link className="btn" href="/master">Administración</Link>
      </p>
    </main>
  );
}
