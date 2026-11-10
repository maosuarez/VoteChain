// Line-based list parsing with per-row errors, for candidate and census previews.
export type Row<T> = { line: number; raw: string; value?: T; error?: string };

const EMAIL = /^[^\s@,;]+@[^\s@,;]+\.[^\s@,;]+$/;

/** First column of each non-empty line; a header row ("nombre", "correo", "email") is skipped. */
function firstColumns(text: string): { line: number; raw: string }[] {
  return text
    .split(/\r?\n/)
    .map((l, i) => ({ line: i + 1, raw: l.split(/[,;]/)[0].trim() }))
    .filter((r) => r.raw !== "" && !/^(nombre|correo|email|name)$/i.test(r.raw));
}

export function slugify(name: string): string {
  return name
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export type Candidate = { id: string; name: string };

/** `existingIds` are candidates already in the category. */
export function parseCandidates(text: string, existingIds: string[] = []): Row<Candidate>[] {
  const seen = new Set(existingIds);
  return firstColumns(text).map(({ line, raw }) => {
    const id = slugify(raw);
    if (!id) return { line, raw, error: "Nombre no válido" };
    if (seen.has(id)) return { line, raw, error: "Candidato repetido" };
    seen.add(id);
    return { line, raw, value: { id, name: raw } };
  });
}

export function parseEmails(text: string): Row<string>[] {
  const seen = new Set<string>();
  return firstColumns(text).map(({ line, raw }) => {
    const email = raw.toLowerCase();
    if (!EMAIL.test(email)) return { line, raw, error: "Correo con formato inválido" };
    if (seen.has(email)) return { line, raw, error: "Correo repetido" };
    seen.add(email);
    return { line, raw, value: email };
  });
}

export const validValues = <T,>(rows: Row<T>[]): T[] =>
  rows.flatMap((r) => (r.error === undefined && r.value !== undefined ? [r.value] : []));
