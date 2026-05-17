import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import { Wallet, Transaction } from '../types';

/** Format KES with thousand separators */
function formatKES(amount: number): string {
  return `KES ${amount.toLocaleString('en-KE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export default function WalletPage() {
  const queryClient = useQueryClient();
  const [depositAmount, setDepositAmount] = useState('');
  const [withdrawAmount, setWithdrawAmount] = useState('');
  const [phone, setPhone] = useState('');
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [mpesaStatus, setMpesaStatus] = useState<'idle' | 'pending' | 'done'>('idle');

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
    onMutate: () => {
      setMpesaStatus('pending');
      setMessage({ type: 'success', text: 'Please enter your M-Pesa PIN on your phone...' });
    },
    onSuccess: (res) => {
      // Simulate M-Pesa confirmation delay
      setTimeout(() => {
        setMpesaStatus('done');
        queryClient.invalidateQueries({ queryKey: ['wallet'] });
        queryClient.invalidateQueries({ queryKey: ['transactions'] });
        setMessage({
          type: 'success',
          text: `Deposit confirmed! ${formatKES(res.data.amount)} added to your wallet.`,
        });
        setDepositAmount('');
        setTimeout(() => setMpesaStatus('idle'), 3000);
      }, 2000);
    },
    onError: (err: any) => {
      setMpesaStatus('idle');
      setMessage({ type: 'error', text: err.response?.data?.detail || 'Deposit failed' });
    },
  });

  const withdrawMutation = useMutation({
    mutationFn: (data: { amount: number; phone: string }) =>
      api.post('/api/wallet/withdraw', data),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['wallet'] });
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      setMessage({ type: 'success', text: res.data.message });
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
        <p className="text-3xl md:text-4xl font-black text-primary-400">
          {formatKES(wallet?.total_balance || 0)}
        </p>
        <div className="flex justify-center gap-6 mt-3 text-sm">
          <div>
            <span className="text-gray-400">Real: </span>
            <span className="font-medium">{formatKES(wallet?.real_balance || 0)}</span>
          </div>
          <div>
            <span className="text-gray-400">Bonus: </span>
            <span className="font-medium text-accent-yellow">
              {formatKES(wallet?.bonus_balance || 0)}
            </span>
          </div>
        </div>
      </div>

      {/* Message */}
      {message && (
        <div
          className={`text-sm text-center px-4 py-3 rounded-lg ${
            message.type === 'success'
              ? 'bg-green-500/20 text-green-400'
              : 'bg-red-500/20 text-red-400'
          }`}
        >
          {mpesaStatus === 'pending' && (
            <div className="flex items-center justify-center gap-2 mb-1">
              <div className="w-4 h-4 border-2 border-green-400 border-t-transparent rounded-full animate-spin" />
              <span className="font-medium">M-Pesa Processing...</span>
            </div>
          )}
          {message.text}
        </div>
      )}

      {/* Deposit via M-Pesa */}
      <div className="card p-4">
        <h3 className="font-semibold mb-1">Deposit via M-Pesa</h3>
        <p className="text-xs text-gray-500 mb-3">Min KES 100 · Max KES 150,000</p>
        <div className="space-y-3">
          <input
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="M-Pesa Number (07XXXXXXXX)"
            className="input-field"
            inputMode="tel"
          />
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 font-medium">
              KES
            </span>
            <input
              type="number"
              value={depositAmount}
              onChange={(e) => setDepositAmount(e.target.value)}
              placeholder="Amount"
              className="input-field pl-14"
              min="100"
              max="150000"
              inputMode="numeric"
            />
          </div>
          {/* Quick amounts */}
          <div className="grid grid-cols-4 gap-2">
            {[100, 500, 1000, 5000].map((amt) => (
              <button
                key={amt}
                onClick={() => setDepositAmount(String(amt))}
                className="text-xs bg-dark-100 hover:bg-dark-200 border border-gray-600 rounded py-2 font-medium"
              >
                {amt.toLocaleString()}
              </button>
            ))}
          </div>
          <button
            onClick={() =>
              depositMutation.mutate({ amount: Number(depositAmount), phone })
            }
            disabled={depositMutation.isPending || !depositAmount || !phone || mpesaStatus === 'pending'}
            className="w-full btn-primary disabled:opacity-50"
          >
            {mpesaStatus === 'pending' ? 'Waiting for M-Pesa PIN...' : 'Deposit via M-Pesa'}
          </button>
        </div>
      </div>

      {/* Withdraw */}
      <div className="card p-4">
        <h3 className="font-semibold mb-1">Withdraw to M-Pesa</h3>
        <p className="text-xs text-gray-500 mb-3">Min KES 100 · Max KES 70,000</p>
        <div className="space-y-3">
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 font-medium">
              KES
            </span>
            <input
              type="number"
              value={withdrawAmount}
              onChange={(e) => setWithdrawAmount(e.target.value)}
              placeholder="Amount"
              className="input-field pl-14"
              min="100"
              max="70000"
              inputMode="numeric"
            />
          </div>
          <button
            onClick={() =>
              withdrawMutation.mutate({ amount: Number(withdrawAmount), phone })
            }
            disabled={withdrawMutation.isPending || !withdrawAmount || !phone}
            className="w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-2 px-4 rounded-lg disabled:opacity-50"
          >
            {withdrawMutation.isPending ? 'Processing...' : 'Withdraw to M-Pesa'}
          </button>
        </div>
      </div>

      {/* Transaction History */}
      <div className="card p-4">
        <h3 className="font-semibold mb-3">Transaction History</h3>
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {transactions?.length === 0 && (
            <p className="text-gray-500 text-sm text-center py-4">No transactions yet</p>
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
                  {new Date(tx.created_at).toLocaleDateString('en-KE')}
                </p>
              </div>
              <span
                className={`font-bold text-sm ${
                  tx.amount > 0 ? 'text-green-400' : 'text-red-400'
                }`}
              >
                {tx.amount > 0 ? '+' : ''}KES {Math.abs(tx.amount).toLocaleString('en-KE', { minimumFractionDigits: 2 })}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
