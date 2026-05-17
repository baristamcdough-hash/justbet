import { useState } from 'react';
import { useBetSlipStore } from '../stores/betSlipStore';
import { useAuthStore } from '../stores/authStore';
import api from '../services/api';

/** Format KES with thousand separators */
function formatKES(amount: number): string {
  return `KES ${amount.toLocaleString('en-KE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export default function BetSlip() {
  const {
    selections, stake, isOpen,
    setStake, removeSelection, clearSlip, setOpen,
    totalOdds, potentialWin, selectionCount,
  } = useBetSlipStore();

  const { isAuthenticated } = useAuthStore();
  const [isPlacing, setIsPlacing] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const count = selectionCount();

  const handlePlaceBet = async () => {
    if (!isAuthenticated) {
      setMessage({ type: 'error', text: 'Please login to place a bet' });
      return;
    }
    if (stake < 50) {
      setMessage({ type: 'error', text: 'Minimum stake is KES 50' });
      return;
    }
    if (stake > 500000) {
      setMessage({ type: 'error', text: 'Maximum stake is KES 500,000' });
      return;
    }

    setIsPlacing(true);
    setMessage(null);

    try {
      await api.post('/api/tickets', {
        selections: selections.map((s) => ({
          match_id: s.match_id,
          market: s.market,
          odds: s.odds,
        })),
        stake,
      });
      setMessage({ type: 'success', text: 'Bet placed successfully!' });
      clearSlip();
    } catch (err: any) {
      setMessage({
        type: 'error',
        text: err.response?.data?.detail || 'Failed to place bet',
      });
    } finally {
      setIsPlacing(false);
    }
  };

  // Mobile floating badge
  if (!isOpen && count > 0) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-4 right-4 md:hidden bg-primary-600 text-white rounded-full w-14 h-14 flex items-center justify-center shadow-xl z-50 animate-bounce"
      >
        <span className="font-bold">{count}</span>
      </button>
    );
  }

  if (count === 0 && !isOpen) return null;

  return (
    <>
      {/* Mobile Drawer */}
      <div
        className={`fixed inset-x-0 bottom-0 md:hidden z-50 transition-transform duration-300 ${
          isOpen ? 'translate-y-0' : 'translate-y-full'
        }`}
      >
        <div className="bg-dark-300 border-t border-gray-700 rounded-t-2xl max-h-[70vh] overflow-y-auto">
          <SlipContent
            selections={selections} stake={stake} setStake={setStake}
            removeSelection={removeSelection} totalOdds={totalOdds()}
            potentialWin={potentialWin()} onPlace={handlePlaceBet}
            isPlacing={isPlacing} message={message}
            onClose={() => setOpen(false)} onClear={clearSlip}
          />
        </div>
      </div>

      {/* Desktop Sidebar */}
      <div className="hidden md:block w-80 shrink-0">
        <div className="sticky top-4 card overflow-hidden">
          <SlipContent
            selections={selections} stake={stake} setStake={setStake}
            removeSelection={removeSelection} totalOdds={totalOdds()}
            potentialWin={potentialWin()} onPlace={handlePlaceBet}
            isPlacing={isPlacing} message={message} onClear={clearSlip}
          />
        </div>
      </div>

      {/* Mobile overlay */}
      {isOpen && (
        <div className="fixed inset-0 bg-black/50 z-40 md:hidden" onClick={() => setOpen(false)} />
      )}
    </>
  );
}

interface SlipContentProps {
  selections: any[];
  stake: number;
  setStake: (s: number) => void;
  removeSelection: (id: string) => void;
  totalOdds: number;
  potentialWin: number;
  onPlace: () => void;
  isPlacing: boolean;
  message: { type: string; text: string } | null;
  onClose?: () => void;
  onClear: () => void;
}

function SlipContent({
  selections, stake, setStake, removeSelection,
  totalOdds, potentialWin, onPlace, isPlacing, message, onClose, onClear,
}: SlipContentProps) {
  return (
    <div className="p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-bold text-lg">
          Bet Slip <span className="text-primary-400">({selections.length})</span>
        </h3>
        <div className="flex gap-2">
          <button onClick={onClear} className="text-xs text-gray-400 hover:text-white">Clear</button>
          {onClose && (
            <button onClick={onClose} className="text-gray-400 hover:text-white text-lg">✕</button>
          )}
        </div>
      </div>

      {/* Selections */}
      <div className="space-y-2 mb-4 max-h-48 overflow-y-auto">
        {selections.map((sel) => (
          <div key={sel.match_id} className="flex items-center justify-between bg-dark-400 rounded-lg p-2">
            <div className="flex-1 min-w-0">
              <p className="text-xs text-gray-400 truncate">{sel.match_label}</p>
              <p className="text-sm font-medium">{sel.market_label}</p>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-primary-400 font-bold text-sm">{sel.odds.toFixed(2)}</span>
              <button onClick={() => removeSelection(sel.match_id)} className="text-gray-500 hover:text-red-400 text-xs">✕</button>
            </div>
          </div>
        ))}
      </div>

      {/* Total Odds */}
      <div className="flex justify-between text-sm mb-3 px-1">
        <span className="text-gray-400">Total Odds</span>
        <span className="font-bold text-primary-400">{totalOdds.toFixed(2)}</span>
      </div>

      {/* Stake Input (KES) */}
      <div className="mb-3">
        <div className="relative">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 font-medium text-sm">KES</span>
          <input
            type="number"
            min="50"
            max="500000"
            placeholder="Min 50"
            value={stake || ''}
            onChange={(e) => setStake(Number(e.target.value))}
            className="input-field pl-12 text-center text-lg font-bold"
            inputMode="numeric"
          />
        </div>
        {/* Quick stake buttons */}
        <div className="grid grid-cols-4 gap-1 mt-2">
          {[50, 100, 500, 1000].map((amt) => (
            <button
              key={amt}
              onClick={() => setStake(amt)}
              className="text-xs bg-dark-100 hover:bg-dark-200 border border-gray-700 rounded py-1.5 font-medium"
            >
              {amt}
            </button>
          ))}
        </div>
      </div>

      {/* Potential Win */}
      <div className="flex justify-between text-sm mb-4 px-1">
        <span className="text-gray-400">Potential Win</span>
        <span className="font-bold text-accent-yellow text-lg">{formatKES(potentialWin)}</span>
      </div>

      {/* Message */}
      {message && (
        <div className={`text-sm text-center mb-3 px-3 py-2 rounded ${
          message.type === 'success' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
        }`}>
          {message.text}
        </div>
      )}

      {/* Place Bet */}
      <button
        onClick={onPlace}
        disabled={isPlacing || selections.length === 0 || stake < 50}
        className="w-full btn-primary py-3 text-lg disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isPlacing ? 'Placing...' : `Place Bet — ${formatKES(stake || 0)}`}
      </button>
    </div>
  );
}
