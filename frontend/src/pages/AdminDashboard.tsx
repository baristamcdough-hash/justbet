import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';

function formatKES(amount: number): string {
  return `KES ${amount.toLocaleString('en-KE', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
}

interface DashboardStats {
  total_users: number;
  active_tickets: number;
  total_stakes_today: number;
  total_liability: number;
}

interface Liability {
  match_id: string;
  home_team: string;
  away_team: string;
  total_stakes: number;
  total_potential_payout: number;
  active_tickets: number;
}

export default function AdminDashboard() {
  const [tab, setTab] = useState<'dashboard' | 'create' | 'settle'>('dashboard');

  return (
    <div className="max-w-4xl mx-auto p-4">
      <h1 className="text-xl font-bold mb-4 text-accent-yellow">Admin Panel</h1>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 overflow-x-auto">
        {(['dashboard', 'create', 'settle'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 rounded-lg text-sm font-medium capitalize whitespace-nowrap ${
              tab === t
                ? 'bg-primary-600 text-white'
                : 'bg-dark-100 text-gray-300 hover:bg-dark-200'
            }`}
          >
            {t === 'create' ? 'Create Match' : t === 'settle' ? 'Settle Match' : t}
          </button>
        ))}
      </div>

      {tab === 'dashboard' && <DashboardTab />}
      {tab === 'create' && <CreateMatchTab />}
      {tab === 'settle' && <SettleTab />}
    </div>
  );
}

function DashboardTab() {
  const { data: stats } = useQuery<DashboardStats>({
    queryKey: ['admin-dashboard'],
    queryFn: async () => (await api.get('/api/admin/dashboard')).data,
  });

  const { data: liability } = useQuery<Liability[]>({
    queryKey: ['admin-liability'],
    queryFn: async () => (await api.get('/api/admin/liability')).data,
  });

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="Users" value={stats?.total_users || 0} />
        <StatCard label="Active Bets" value={stats?.active_tickets || 0} />
        <StatCard label="Total Stakes" value={formatKES(stats?.total_stakes_today || 0)} />
        <StatCard label="Liability" value={formatKES(stats?.total_liability || 0)} color="red" />
      </div>

      {/* Liability Table */}
      <div className="card overflow-hidden">
        <div className="bg-dark-200 px-4 py-3 border-b border-gray-700/50">
          <h3 className="font-semibold text-sm">Active Match Liability</h3>
        </div>
        <div className="divide-y divide-gray-700/30">
          {liability?.length === 0 && (
            <p className="p-4 text-gray-500 text-sm text-center">No active liability</p>
          )}
          {liability?.map((l) => (
            <div key={l.match_id} className="p-3 flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">{l.home_team} vs {l.away_team}</p>
                <p className="text-xs text-gray-500">{l.active_tickets} tickets</p>
              </div>
              <div className="text-right">
                <p className="text-sm font-bold text-red-400">
                  {formatKES(l.total_potential_payout)}
                </p>
                <p className="text-xs text-gray-500">
                  Stakes: {formatKES(l.total_stakes)}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: string | number; color?: string }) {
  return (
    <div className="card p-4 text-center">
      <p className="text-xs text-gray-400 mb-1">{label}</p>
      <p className={`text-lg font-bold ${color === 'red' ? 'text-red-400' : 'text-white'}`}>
        {value}
      </p>
    </div>
  );
}

function CreateMatchTab() {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    league_id: '',
    home_team: '',
    away_team: '',
    kickoff_time: '',
    home_odds: '2.00',
    draw_odds: '3.00',
    away_odds: '3.50',
  });
  const [leagueName, setLeagueName] = useState('');
  const [message, setMessage] = useState('');

  const { data: leagues } = useQuery<any[]>({
    queryKey: ['leagues'],
    queryFn: async () => (await api.get('/api/leagues')).data,
  });

  const createLeague = useMutation({
    mutationFn: (name: string) => api.post('/api/admin/leagues', { name, sport: 'football' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leagues'] });
      setLeagueName('');
      setMessage('League created!');
    },
  });

  const createMatch = useMutation({
    mutationFn: (data: any) => api.post('/api/admin/matches', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['matches'] });
      setMessage('Match created!');
      setForm({ ...form, home_team: '', away_team: '', kickoff_time: '' });
    },
    onError: (err: any) => setMessage(err.response?.data?.detail || 'Error'),
  });

  return (
    <div className="space-y-6">
      {message && <p className="text-sm text-primary-400 text-center">{message}</p>}

      {/* Create League */}
      <div className="card p-4">
        <h3 className="font-semibold mb-3">New League</h3>
        <div className="flex gap-2">
          <input
            value={leagueName}
            onChange={(e) => setLeagueName(e.target.value)}
            placeholder="League name"
            className="input-field flex-1"
          />
          <button
            onClick={() => createLeague.mutate(leagueName)}
            className="btn-primary"
          >
            Add
          </button>
        </div>
      </div>

      {/* Create Match */}
      <div className="card p-4">
        <h3 className="font-semibold mb-3">New Match</h3>
        <div className="space-y-3">
          <select
            value={form.league_id}
            onChange={(e) => setForm({ ...form, league_id: e.target.value })}
            className="input-field"
          >
            <option value="">Select League</option>
            {leagues?.map((l) => (
              <option key={l.id} value={l.id}>{l.name}</option>
            ))}
          </select>
          <input
            value={form.home_team}
            onChange={(e) => setForm({ ...form, home_team: e.target.value })}
            placeholder="Home Team"
            className="input-field"
          />
          <input
            value={form.away_team}
            onChange={(e) => setForm({ ...form, away_team: e.target.value })}
            placeholder="Away Team"
            className="input-field"
          />
          <input
            type="datetime-local"
            value={form.kickoff_time}
            onChange={(e) => setForm({ ...form, kickoff_time: e.target.value })}
            className="input-field"
          />
          <div className="grid grid-cols-3 gap-2">
            <input
              type="number"
              step="0.01"
              value={form.home_odds}
              onChange={(e) => setForm({ ...form, home_odds: e.target.value })}
              placeholder="Home odds"
              className="input-field text-center"
            />
            <input
              type="number"
              step="0.01"
              value={form.draw_odds}
              onChange={(e) => setForm({ ...form, draw_odds: e.target.value })}
              placeholder="Draw odds"
              className="input-field text-center"
            />
            <input
              type="number"
              step="0.01"
              value={form.away_odds}
              onChange={(e) => setForm({ ...form, away_odds: e.target.value })}
              placeholder="Away odds"
              className="input-field text-center"
            />
          </div>
          <button
            onClick={() =>
              createMatch.mutate({
                ...form,
                home_odds: parseFloat(form.home_odds),
                draw_odds: parseFloat(form.draw_odds),
                away_odds: parseFloat(form.away_odds),
              })
            }
            className="w-full btn-primary"
          >
            Create Match
          </button>
        </div>
      </div>
    </div>
  );
}

function SettleTab() {
  const queryClient = useQueryClient();
  const [matchId, setMatchId] = useState('');
  const [homeScore, setHomeScore] = useState('0');
  const [awayScore, setAwayScore] = useState('0');
  const [message, setMessage] = useState('');

  const { data: liability } = useQuery<any[]>({
    queryKey: ['admin-liability'],
    queryFn: async () => (await api.get('/api/admin/liability')).data,
  });

  const settleMutation = useMutation({
    mutationFn: (data: { matchId: string; home_score: number; away_score: number }) =>
      api.post(`/api/admin/matches/${data.matchId}/settle`, {
        home_score: data.home_score,
        away_score: data.away_score,
      }),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['admin-liability'] });
      queryClient.invalidateQueries({ queryKey: ['admin-dashboard'] });
      setMessage(`Settled! Result: ${res.data.score} (${res.data.result})`);
    },
    onError: (err: any) => setMessage(err.response?.data?.detail || 'Settlement failed'),
  });

  return (
    <div className="space-y-6">
      {message && <p className="text-sm text-primary-400 text-center">{message}</p>}

      <div className="card p-4">
        <h3 className="font-semibold mb-3">Settle Match</h3>
        <div className="space-y-3">
          <select
            value={matchId}
            onChange={(e) => setMatchId(e.target.value)}
            className="input-field"
          >
            <option value="">Select Match</option>
            {liability?.map((l) => (
              <option key={l.match_id} value={l.match_id}>
                {l.home_team} vs {l.away_team}
              </option>
            ))}
          </select>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-400">Home Score</label>
              <input
                type="number"
                min="0"
                value={homeScore}
                onChange={(e) => setHomeScore(e.target.value)}
                className="input-field text-center"
              />
            </div>
            <div>
              <label className="text-xs text-gray-400">Away Score</label>
              <input
                type="number"
                min="0"
                value={awayScore}
                onChange={(e) => setAwayScore(e.target.value)}
                className="input-field text-center"
              />
            </div>
          </div>
          <button
            onClick={() =>
              settleMutation.mutate({
                matchId,
                home_score: parseInt(homeScore),
                away_score: parseInt(awayScore),
              })
            }
            disabled={!matchId || settleMutation.isPending}
            className="w-full bg-accent-yellow hover:bg-yellow-600 text-black font-semibold py-2 px-4 rounded-lg disabled:opacity-50"
          >
            {settleMutation.isPending ? 'Settling...' : 'Settle Match'}
          </button>
        </div>
      </div>
    </div>
  );
}
