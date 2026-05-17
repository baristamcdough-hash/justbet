import { Link, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { useBetSlipStore } from '../stores/betSlipStore';

export default function Navbar() {
  const { isAuthenticated, user, logout } = useAuthStore();
  const { selectionCount, setOpen } = useBetSlipStore();
  const navigate = useNavigate();
  const count = selectionCount();

  return (
    <nav className="bg-dark-300 border-b border-gray-700/50 sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center justify-between h-14">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2">
            <span className="text-xl font-black text-primary-400">JustBet</span>
          </Link>

          {/* Nav Items */}
          <div className="flex items-center gap-3">
            {/* Bet Slip Badge (mobile) */}
            {count > 0 && (
              <button
                onClick={() => setOpen(true)}
                className="md:hidden relative bg-dark-100 rounded-lg px-3 py-1.5"
              >
                <span className="text-sm font-medium">Slip</span>
                <span className="absolute -top-1 -right-1 bg-primary-500 text-white text-xs w-5 h-5 rounded-full flex items-center justify-center">
                  {count}
                </span>
              </button>
            )}

            {isAuthenticated ? (
              <div className="flex items-center gap-2">
                <Link
                  to="/wallet"
                  className="text-sm bg-dark-100 hover:bg-dark-200 px-3 py-1.5 rounded-lg border border-gray-600"
                >
                  Wallet
                </Link>
                <Link
                  to="/my-bets"
                  className="text-sm text-gray-300 hover:text-white hidden sm:block"
                >
                  My Bets
                </Link>
                {user?.role === 'admin' && (
                  <Link
                    to="/admin"
                    className="text-sm text-accent-yellow hover:text-yellow-300"
                  >
                    Admin
                  </Link>
                )}
                <button
                  onClick={() => { logout(); navigate('/'); }}
                  className="text-sm text-gray-400 hover:text-white"
                >
                  Logout
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Link to="/login" className="text-sm text-gray-300 hover:text-white">
                  Login
                </Link>
                <Link to="/register" className="btn-primary text-sm py-1.5 px-3">
                  Join
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}
