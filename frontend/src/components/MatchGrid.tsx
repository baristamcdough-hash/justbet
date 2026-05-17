import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useMemo } from 'react';
import api from '../services/api';
import { League, OddsUpdate } from '../types';
import { useBetSlipStore } from '../stores/betSlipStore';
import { useWebSocket } from '../hooks/useWebSocket';
import OddsCell from './OddsCell';

export default function MatchGrid() {
  const queryClient = useQueryClient();
  const { toggleSelection, isSelected } = useBetSlipStore();

  const { data: leagues, isLoading } = useQuery<League[]>({
    queryKey: ['matches'],
    queryFn: async () => {
      const res = await api.get('/api/matches');
      return res.data;
    },
  });

  const matchIds = useMemo(
    () => leagues?.flatMap((l) => l.matches.map((m) => m.id)) || [],
    [leagues]
  );

  const handleOddsUpdate = useCallback(
    (data: OddsUpdate) => {
      if (data.type === 'odds_update' || data.type === 'odds_snapshot') {
        queryClient.setQueryData<League[]>(['matches'], (old) => {
          if (!old) return old;
          return old.map((league) => ({
            ...league,
            matches: league.matches.map((match) =>
              match.id === data.match_id
                ? { ...match, odds: data.odds }
                : match
            ),
          }));
        });
      }
    },
    [queryClient]
  );

  useWebSocket(matchIds, handleOddsUpdate);

  if (isLoading) {
    return (
      <div className="space-y-4 p-4">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="card p-4 animate-pulse">
            <div className="h-4 bg-dark-100 rounded w-1/3 mb-3"></div>
            <div className="space-y-2">
              <div className="h-12 bg-dark-100 rounded"></div>
              <div className="h-12 bg-dark-100 rounded"></div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (!leagues || leagues.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">
        <p>No matches available</p>
      </div>
    );
  }

  return (
    <div className="space-y-4 p-3 md:p-4">
      {leagues.map((league) => (
        <div key={league.id} className="card overflow-hidden">
          {/* League Header */}
          <div className="bg-dark-200 px-3 py-2 border-b border-gray-700/50">
            <h3 className="text-xs font-semibold text-primary-400 uppercase tracking-wide">
              {league.country && <span className="mr-1">{league.country} —</span>}
              {league.name}
            </h3>
          </div>

          {/* Matches */}
          <div className="divide-y divide-gray-700/30">
            {league.matches.map((match) => (
              <div key={match.id} className="p-3">
                {/* Match Info */}
                <div className="flex items-center justify-between mb-2">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">
                      {match.home_team}
                    </p>
                    <p className="text-sm text-gray-400 truncate">
                      {match.away_team}
                    </p>
                  </div>
                  <div className="text-right ml-2">
                    {match.status === 'live' ? (
                      <span className="text-xs bg-red-500/20 text-red-400 px-2 py-0.5 rounded-full font-medium">
                        LIVE {match.home_score}-{match.away_score}
                      </span>
                    ) : (
                      <span className="text-xs text-gray-500">
                        {new Date(match.kickoff_time).toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                    )}
                  </div>
                </div>

                {/* Odds Row */}
                <div className="grid grid-cols-3 gap-2">
                  <OddsCell
                    odds={match.odds.home}
                    label="1"
                    isSelected={isSelected(match.id, 'home')}
                    onClick={() =>
                      toggleSelection({
                        match_id: match.id,
                        match_label: `${match.home_team} vs ${match.away_team}`,
                        market: 'home',
                        market_label: match.home_team,
                        odds: match.odds.home,
                      })
                    }
                  />
                  <OddsCell
                    odds={match.odds.draw}
                    label="X"
                    isSelected={isSelected(match.id, 'draw')}
                    onClick={() =>
                      toggleSelection({
                        match_id: match.id,
                        match_label: `${match.home_team} vs ${match.away_team}`,
                        market: 'draw',
                        market_label: 'Draw',
                        odds: match.odds.draw,
                      })
                    }
                  />
                  <OddsCell
                    odds={match.odds.away}
                    label="2"
                    isSelected={isSelected(match.id, 'away')}
                    onClick={() =>
                      toggleSelection({
                        match_id: match.id,
                        match_label: `${match.home_team} vs ${match.away_team}`,
                        market: 'away',
                        market_label: match.away_team,
                        odds: match.odds.away,
                      })
                    }
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
