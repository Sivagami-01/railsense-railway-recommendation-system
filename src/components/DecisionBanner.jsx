import React from 'react';

export default function DecisionBanner({ recommendationData, loading, scheduledTimeStr }) {
  if (loading) {
    return (
      <div className="bg-[#0F172A] border border-[#2DD4BF]/30 rounded-xl p-4 mb-6 flex items-center space-x-3 animate-pulse">
        <div className="w-5 h-5 border-2 border-[#2DD4BF] border-t-transparent rounded-full animate-spin"></div>
        <div>
          <h4 className="text-sm font-semibold text-[#2DD4BF]">Searching Optimal Alternatives...</h4>
          <p className="text-xs text-[#94A3B8]">Analyzing direct and multi-hop transfer routes across Indian Railways network</p>
        </div>
      </div>
    );
  }

  if (!recommendationData) return null;

  const { decision, level, delayed_arrival_time, reason, alternatives } = recommendationData;

  const formatIsoDisplay = (isoStr) => {
    if (!isoStr) return '';
    try {
      const dt = new Date(isoStr);
      return dt.toLocaleString('en-IN', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: true
      });
    } catch {
      return isoStr;
    }
  };

  if (decision === 'continue_with_booked_train') {
    return (
      <div className="bg-emerald-950/40 border border-emerald-500/40 rounded-xl p-4.5 mb-6 text-emerald-200 flex items-start space-x-3.5">
        <div className="p-2 bg-emerald-900/60 rounded-lg text-emerald-400 mt-0.5">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <h3 className="text-base font-bold text-emerald-300">Continue With Your Booked Train</h3>
            <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-900/80 text-emerald-300 border border-emerald-700/50">
              No Action Needed
            </span>
          </div>
          <p className="text-xs text-emerald-300/80 mt-1">
            {reason || 'The expected delay is within your acceptable wait tolerance.'}
          </p>
          {delayed_arrival_time && (
            <div className="mt-2 text-xs font-mono text-emerald-400 bg-emerald-950/60 px-3 py-1.5 rounded inline-block border border-emerald-800/40">
              Expected Arrival: <span className="tabular-nums font-bold">{formatIsoDisplay(delayed_arrival_time)}</span>
            </div>
          )}
        </div>
      </div>
    );
  }

  if (decision === 'no_alternative_available') {
    return (
      <div className="bg-amber-950/40 border border-amber-500/40 rounded-xl p-4.5 mb-6 text-amber-200 flex items-start space-x-3.5">
        <div className="p-2 bg-amber-900/60 rounded-lg text-amber-400 mt-0.5">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>
        <div>
          <h3 className="text-base font-bold text-amber-300">No Alternative Options Found</h3>
          <p className="text-xs text-amber-300/80 mt-1">
            {reason || 'No qualifying direct or multi-hop trains operate strictly within the delay window.'}
          </p>
          {delayed_arrival_time && (
            <div className="mt-2 text-xs font-mono text-amber-400 bg-amber-950/60 px-3 py-1.5 rounded inline-block border border-amber-800/40">
              Delayed Arrival Window Target: <span className="tabular-nums font-bold">{formatIsoDisplay(delayed_arrival_time)}</span>
            </div>
          )}
        </div>
      </div>
    );
  }

  if (decision === 'alternative_found') {
    return (
      <div className="bg-[#0F172A] border border-[#2DD4BF]/40 rounded-xl p-4.5 mb-6 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 bg-[#2DD4BF]/10 rounded-lg text-[#2DD4BF] border border-[#2DD4BF]/30">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-base font-bold text-[#F8FAFC]">Alternative Trains Available</h3>
              <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-[#2DD4BF]/20 text-[#2DD4BF] border border-[#2DD4BF]/40">
                Level {level} Recommendation
              </span>
            </div>
            <p className="text-xs text-[#94A3B8] mt-0.5">
              Found {alternatives ? alternatives.length : 0} qualifying option(s) sorted by duration.
            </p>
          </div>
        </div>
        {delayed_arrival_time && (
          <div className="hidden sm:block text-right">
            <span className="text-[10px] uppercase tracking-wider text-[#94A3B8] block">New Delayed Arrival Target</span>
            <span className="text-xs font-mono font-bold text-[#38BDF8] tabular-nums">
              {formatIsoDisplay(delayed_arrival_time)}
            </span>
          </div>
        )}
      </div>
    );
  }

  return null;
}
