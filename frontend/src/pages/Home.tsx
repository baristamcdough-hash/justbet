import MatchGrid from '../components/MatchGrid';
import BetSlip from '../components/BetSlip';

export default function Home() {
  return (
    <div className="flex gap-4 max-w-7xl mx-auto">
      {/* Main Content */}
      <div className="flex-1 min-w-0">
        <MatchGrid />
      </div>

      {/* Desktop Bet Slip Sidebar */}
      <BetSlip />
    </div>
  );
}
