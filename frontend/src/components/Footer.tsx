export default function Footer() {
  return (
    <footer className="bg-dark-400 border-t border-gray-700/50 py-4 mt-auto">
      <div className="max-w-7xl mx-auto px-4 text-center">
        <p className="text-xs text-gray-500">
          Built by <span className="text-primary-400 font-semibold">P.o.Riot</span> | Credits{' '}
          <span className="text-primary-400 font-semibold">P.o.Riot</span>
        </p>
        <p className="text-xs text-gray-600 mt-1">
          JustBet &copy; {new Date().getFullYear()} — Gamble Responsibly
        </p>
      </div>
    </footer>
  );
}
