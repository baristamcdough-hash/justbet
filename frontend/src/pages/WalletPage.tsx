import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import { Wallet, Transaction } from '../types';

export default function WalletPage() {
  const queryClient = useQueryClient();
  const [depositAmount, setDepositAmount] = useState('');
  const [withdrawAmount, setWithdrawAmount] = useState('');
  const [phone, setPhone] = useState('');
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const { data: wallet, isLoading } = useQuery<Wallet>({
    queryKey: ['wallet'],
    queryFn: async () => (await api.get('/api/wallet')).data,
  });

  const { data: transactions } = useQuery<Transaction[]>({
    queryKey: ['transactions'],
    queryFn: async () => (await api.get('/api/wallet/transactions')).data,
  });

  const depositMutation = useMutation({
    mutationFn: (data: { amount: number; phone: string }) =>
      api.post('/api/wallet/deposit', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wallet'] });
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      setMessage({ type: 'success', text: 'Deposit successful!' });
      setDepositAmount('');
    },
    onError: (err: any) => {
      setMessage({ type: 'error', text: err.response?.data?.detail || 'Deposit failed' });
    },
  });

  const withdrawMutation = useMutation({
    mutationFn: (data: { amount: number; phone: string }) =>
      api.post('/api/wallet/withdraw', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wallet'] });
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      setMessage({ type: 'success', text: 'Withdrawal initiated!' });
      setWithdrawAmount('');
    },
    onError: (err: any) => {
      setMessage({ type: 'error', text: err.response?.data?.detail || 'Withdrawal failed' });
    },
  });

  if (isLoading) {
    return <div className="p-4 text-center text-gray-400">Loading wallet...</div>;
  }

  return (
    <div className="max-w-lg mx-auto p-4 space-y-6">
      {/* Balance Card */}
      <div className="card p-6 text-center">
        <p className="text-sm text-gray-400 mb-1">Total Balance</p>
        <p className="text-4xl font-black text-primary-400">
          KES {wallet?.total_balance.toFixed(2)}
        </p>
        <div className="flex justify-center gap-6 mt-3 text-sm">
          <div>
            <span className="text-gray-400">Real: </span>
            <span className="font-medium">KES {wallet?.real_balance.toFixed(2)}</span>
          </div>
          <div>
            <span className="text-gray-400">Bonus: </span>
            <span className="font-medium text-accent-yellow">
              KES {wallet?.bonus_balance.toFixed(2)}
            </span>
          </div>
        </div>
      </div>

      {/* Message */}
      {message && (
        <div
          className={`text-sm text-center px-4 py-2 rounded-lg ${
            message.type === 'success'
              ? 'bg-green-500/20 text-green-400'
              : 'bg-red-500/20 text-red-400'
          }`}
        >
          {message.text}
        </div>
      )}

      {/* Deposit */}
      <div className="card p-4">
        <h3 className="font-semibold mb-3">Deposit (M-Pesa)</h3>
        <div className="space-y-3">
          <input
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="M-Pesa Phone Number"
            className="input-field"
          />
          <input
            type="number"
            value={depositAmount}
            onChange={(e) => setDepositAmount(e.target.value)}
            placeholder="Amount (KES)"
            className="input-field"
            min="10"
          />
          <button
            onClick={() =>
              depositMutation.mutate({ amount: Number(depositAmount), phone })
            }
            disabled={depositMutation.isPending || !depositAmount}
            className="w-full btn-primary disabled:opacity-50"
          >
            {depositMutation.isPending ? 'Processing...' : 'Deposit'}
          </button>
        </div>
      </div>

      {/* Withdraw */}
      <div className="card p-4">
        <h3 className="font-semibold mb-3">Withdraw</h3>
        <div className="space-y-3">
          <input
            type="number"
            value={withdrawAmount}
            onChange={(e) => setWithdrawAmount(e.target.value)}
            placeholder="Amount (KES)"
            className="input-field"
            min="10"
          />
          <button
            onClick={() =>
              withdrawMutation.mutate({ amount: Number(withdrawAmount), phone })
            }
            disabled={withdrawMutation.isPending || !withdrawAmount}
            className="w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-2 px-4 rounded-lg disabled:opacity-50"
          >
            {withdrawMutation.isPending ? 'Processing...' : 'Withdraw'}
          </button>
        </div>
      </div>

      {/* Transaction History */}
      <div className="card p-4">
        <h3 className="font-semibold mb-3">Recent Transactions</h3>
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {transactions?.length === 0 && (
            <p className="text-gray-500 text-sm text-center">No transactions yet</p>
          )}
          {transactions?.map((tx) => (
            <div
              key={tx.id}
              className="flex items-center justify-between bg-dark-400 rounded-lg p-3"
            >
              <div>
                <p className="text-sm font-medium capitalize">
                  {tx.type.replace('_', ' ')}
                </p>
                <p className="text-xs text-gray-500">
                  {new Date(tx.created_at).toLocaleDateString()}
                </p>
              </div>
              <span
                className={`font-bold text-sm ${
                  tx.amount > 0 ? 'text-green-400' : 'text-red-400'
                }`}
              >
                {tx.amount > 0 ? '+' : ''}
                {tx.amount.toFixed(2)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
