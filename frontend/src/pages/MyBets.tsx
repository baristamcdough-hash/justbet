import { useQuery } from '@tanstack/react-query';
import api from '../services/api';
import { Ticket } from '../types';

function formatKES(amount: number): string {
  return `KES ${amount.toLocaleString('en-KE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

const statusColors: Record<string, string> = {
  active: 'bg-blue-500/20 text-blue-400',
  won: 'bg-green-500/20 text-green-400',
  lost: 'bg-red-500/20 text-red-400',
  void: 'bg-gray-500/20 text-gray-400',
};

export default function MyBets() {
  const { data: tickets, isLoading } = useQuery<Ticket[]>({
    queryKey: ['tickets'],
    queryFn: async () => (await api.get('/api/tickets')).data,
  });

  if (isLoading) {
    return <div className="p-4 text-center text-gray-400">Loading bets...</div>;
  }

  return (
    <div className="max-w-lg mx-auto p-4">
      <h1 className="text-xl font-bold mb-4">My Bets</h1>

      {tickets?.length === 0 && (
        <div className="card p-8 text-center text-gray-400">
          <p>No bets placed yet</p>
          <p className="text-sm mt-1">Select odds from the match grid to start</p>
        </div>
      )}

      <div className="space-y-3">
        {tickets?.map((ticket) => (
          <div key={ticket.id} className="card p-4">
            <div className="flex items-center justify-between mb-3">
              <span
                className={`text-xs font-semibold px-2 py-0.5 rounded-full uppercase ${
                  statusColors[ticket.status] || statusColors.void
                }`}
              >
                {ticket.status}
              </span>
              <span className="text-xs text-gray-500">
                {new Date(ticket.created_at).toLocaleDateString('en-KE')}
              </span>
            </div>

            {/* Selections */}
            <div className="space-y-1 mb-3">
              {ticket.selections.map((sel) => (
                <div key={sel.id} className="flex items-center justify-between text-sm">
                  <span className="text-gray-300 capitalize">{sel.market}</span>
                  <span className="font-medium">{sel.locked_odds.toFixed(2)}</span>
                </div>
              ))}
            </div>

            {/* Summary */}
            <div className="border-t border-gray-700/50 pt-2 flex items-center justify-between text-sm">
              <div>
                <span className="text-gray-400">Stake: </span>
                <span className="font-medium">{formatKES(ticket.stake)}</span>
              </div>
              <div>
                <span className="text-gray-400">Win: </span>
                <span className="font-bold text-accent-yellow">
                  {formatKES(ticket.potential_win)}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
