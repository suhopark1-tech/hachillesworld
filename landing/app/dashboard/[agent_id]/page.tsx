import AgentDetailClient from './AgentDetailClient';

interface Props {
  params: { agent_id: string };
}

export default function AgentDetailPage({ params }: Props) {
  return <AgentDetailClient agentId={params.agent_id} />;
}
