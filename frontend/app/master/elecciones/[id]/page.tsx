import { ElectionDetail } from "@/components/master/ElectionDetail";
import { MasterShell } from "@/components/master/MasterShell";

export const metadata = { title: "Elección · VoteChain" };

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <MasterShell><ElectionDetail id={decodeURIComponent(id)} /></MasterShell>;
}
