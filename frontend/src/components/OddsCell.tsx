import { useState, useEffect } from 'react';

interface OddsCellProps {
  odds: number;
  previousOdds?: number;
  label: string;
  isSelected: boolean;
  onClick: () => void;
}

export default function OddsCell({ odds, previousOdds, label, isSelected, onClick }: OddsCellProps) {
  const [flash, setFlash] = useState<'up' | 'down' | null>(null);

  useEffect(() => {
    if (previousOdds !== undefined && previousOdds !== odds) {
      setFlash(odds > previousOdds ? 'up' : 'down');
      const timer = setTimeout(() => setFlash(null), 600);
      return () => clearTimeout(timer);
    }
  }, [odds, previousOdds]);

  return (
    <button
      onClick={onClick}
      className={`odds-cell relative ${
        isSelected ? 'odds-cell-selected' : 'odds-cell-default'
      } ${flash === 'up' ? 'animate-flash-green' : ''} ${
        flash === 'down' ? 'animate-flash-red' : ''
      }`}
    >
      <div className="flex flex-col items-center gap-0.5">
        <span className="text-[10px] text-gray-400 uppercase">{label}</span>
        <span className="text-sm font-bold">{odds.toFixed(2)}</span>
      </div>
      {flash === 'up' && (
        <span className="absolute -top-1 -right-1 text-green-400 text-xs">▲</span>
      )}
      {flash === 'down' && (
        <span className="absolute -top-1 -right-1 text-red-400 text-xs">▼</span>
      )}
    </button>
  );
}
