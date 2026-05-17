export interface Odds {
  home: number;
  draw: number;
  away: number;
}

export interface Match {
  id: string;
  home_team: string;
  away_team: string;
  kickoff_time: string;
  status: 'upcoming' | 'live' | 'ended' | 'settled' | 'cancelled';
  home_score: number;
  away_score: number;
  odds: Odds;
}

export interface League {
  id: string;
  name: string;
  sport: string;
  country: string | null;
  matches: Match[];
}

export interface BetSelection {
  match_id: string;
  match_label: string; // "Team A vs Team B"
  market: 'home' | 'draw' | 'away';
  market_label: string; // "Home" / "Draw" / "Away"
  odds: number;
}

export interface Ticket {
  id: string;
  stake: number;
  total_odds: number;
  potential_win: number;
  status: 'active' | 'won' | 'lost' | 'void' | 'cashout';
  created_at: string;
  selections: TicketSelection[];
}

export interface TicketSelection {
  id: string;
  match_id: string;
  market: string;
  locked_odds: number;
  result: 'pending' | 'won' | 'lost' | 'void';
}

export interface Wallet {
  id: string;
  real_balance: number;
  bonus_balance: number;
  total_balance: number;
}

export interface Transaction {
  id: string;
  type: string;
  amount: number;
  balance_after: number;
  status: string;
  reference_id: string | null;
  created_at: string;
}

export interface User {
  id: string;
  phone: string;
  role: 'punter' | 'admin';
  created_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface OddsUpdate {
  type: 'odds_update' | 'odds_snapshot';
  match_id: string;
  timestamp?: string;
  odds: Odds;
  previous?: Odds;
}
