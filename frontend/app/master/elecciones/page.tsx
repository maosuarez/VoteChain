import { ElectionsList } from "@/components/master/ElectionsList";
import { MasterShell } from "@/components/master/MasterShell";

export const metadata = { title: "Elecciones · VoteChain" };

export default function Page() {
  return <MasterShell><ElectionsList /></MasterShell>;
}
