import { describe, expect, it } from "vitest";
import { parseCandidates, parseEmails, slugify, validValues } from "@/lib/csv";

describe("csv lists", () => {
  it("slugifies names", () => {
    expect(slugify("María Núñez-Pérez")).toBe("maria-nunez-perez");
    expect(slugify("¡¿?!")).toBe("");
  });

  it("candidates: skips header and blanks, flags duplicates, empty ids and existing ones", () => {
    const rows = parseCandidates("nombre\nAna Ruiz\n\nAna Ruiz\n???\nLuis,Ingeniería\nCarla", ["carla"]);
    expect(rows.map((r) => r.error ?? "ok")).toEqual([
      "ok", "Candidato repetido", "Nombre no válido", "ok", "Candidato repetido",
    ]);
    expect(validValues(rows)).toEqual([
      { id: "ana-ruiz", name: "Ana Ruiz" },
      { id: "luis", name: "Luis" },
    ]);
    expect(rows[1].line).toBe(4);
  });

  it("emails: lowercases, flags invalid and duplicates", () => {
    const rows = parseEmails("correo\nA@x.edu\na@X.edu\nmal\nb@x.edu;nota");
    expect(rows.map((r) => r.error ?? "ok")).toEqual([
      "ok", "Correo repetido", "Correo con formato inválido", "ok",
    ]);
    expect(validValues(rows)).toEqual(["a@x.edu", "b@x.edu"]);
  });
});
