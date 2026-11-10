import { Suspense } from "react";
import { BallotStep } from "@/components/voter/BallotStep";

export const metadata = { title: "Papeleta · VoteChain" };

export default function Page() {
  return <Suspense><BallotStep /></Suspense>;
}
