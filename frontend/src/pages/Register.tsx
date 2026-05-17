import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';

export default function Register() {
  const [phone, setPhone] = useState('');
  const [pin, setPin] = useState('');
  const [confirmPin, setConfirmPin] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { register } = useAuthStore();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (pin !== confirmPin) {
      setError('PINs do not match');
      return;
    }

    if (pin.length !== 4 || !/^\d{4}$/.test(pin)) {
      setError('PIN must be exactly 4 digits');
      return;
    }

    // Validate Kenyan phone
    const normalized = phone.replace(/\s/g, '');
    if (!/^(?:\+?254|0)7\d{8}$/.test(normalized)) {
      setError('Enter a valid Safaricom number (07XXXXXXXX)');
      return;
    }

    setLoading(true);

    try {
      await register(normalized, pin);
      navigate('/');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4">
      <div className="card w-full max-w-sm p-6">
        <h1 className="text-2xl font-bold text-center mb-2">Create Account</h1>
        <p className="text-center text-gray-400 text-sm mb-6">
          Register with your Safaricom number
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Phone Number</label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 text-sm">
                +254
              </span>
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="07XXXXXXXX"
                className="input-field pl-14"
                inputMode="tel"
                maxLength={13}
                required
              />
            </div>
            <p className="text-xs text-gray-500 mt-1">Safaricom number for M-Pesa deposits</p>
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">Create 4-Digit PIN</label>
            <input
              type="password"
              value={pin}
              onChange={(e) => {
                const val = e.target.value.replace(/\D/g, '').slice(0, 4);
                setPin(val);
              }}
              placeholder="••••"
              className="input-field text-center text-2xl tracking-[0.5em]"
              inputMode="numeric"
              maxLength={4}
              required
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">Confirm PIN</label>
            <input
              type="password"
              value={confirmPin}
              onChange={(e) => {
                const val = e.target.value.replace(/\D/g, '').slice(0, 4);
                setConfirmPin(val);
              }}
              placeholder="••••"
              className="input-field text-center text-2xl tracking-[0.5em]"
              inputMode="numeric"
              maxLength={4}
              required
            />
          </div>

          {error && (
            <p className="text-red-400 text-sm text-center">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading || pin.length !== 4}
            className="w-full btn-primary py-3 disabled:opacity-50"
          >
            {loading ? 'Creating...' : 'Register'}
          </button>
        </form>

        <p className="text-center text-sm text-gray-400 mt-4">
          Already have an account?{' '}
          <Link to="/login" className="text-primary-400 hover:underline">
            Login
          </Link>
        </p>
      </div>
    </div>
  );
}
