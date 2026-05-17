import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { BetSelection } from '../types';

interface BetSlipState {
  selections: BetSelection[];
  stake: number;
  isOpen: boolean;

  // Actions
  addSelection: (selection: BetSelection) => void;
  removeSelection: (matchId: string) => void;
  toggleSelection: (selection: BetSelection) => void;
  setStake: (stake: number) => void;
  clearSlip: () => void;
  setOpen: (open: boolean) => void;

  // Computed
  totalOdds: () => number;
  potentialWin: () => number;
  selectionCount: () => number;
  isSelected: (matchId: string, market: string) => boolean;
}

export const useBetSlipStore = create<BetSlipState>()(
  persist(
    (set, get) => ({
      selections: [],
      stake: 0,
      isOpen: false,

      addSelection: (selection) => {
        set((state) => {
          // Remove existing selection for same match (only one market per match)
          const filtered = state.selections.filter(
            (s) => s.match_id !== selection.match_id
          );
          return { selections: [...filtered, selection] };
        });
      },

      removeSelection: (matchId) => {
        set((state) => ({
          selections: state.selections.filter((s) => s.match_id !== matchId),
        }));
      },

      toggleSelection: (selection) => {
        const state = get();
        const existing = state.selections.find(
          (s) => s.match_id === selection.match_id && s.market === selection.market
        );
        if (existing) {
          state.removeSelection(selection.match_id);
        } else {
          state.addSelection(selection);
        }
      },

      setStake: (stake) => set({ stake }),

      clearSlip: () => set({ selections: [], stake: 0 }),

      setOpen: (open) => set({ isOpen: open }),

      totalOdds: () => {
        const { selections } = get();
        if (selections.length === 0) return 0;
        return selections.reduce((acc, s) => acc * s.odds, 1);
      },

      potentialWin: () => {
        const { stake } = get();
        const totalOdds = get().totalOdds();
        return stake * totalOdds;
      },

      selectionCount: () => get().selections.length,

      isSelected: (matchId, market) => {
        return get().selections.some(
          (s) => s.match_id === matchId && s.market === market
        );
      },
    }),
    {
      name: 'justbet-slip',
      partialize: (state) => ({
        selections: state.selections,
        stake: state.stake,
      }),
    }
  )
);
