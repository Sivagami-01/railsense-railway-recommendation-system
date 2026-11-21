import React from 'react';
import { stationList } from '../data/stations';

const stationNameMap = Object.fromEntries(
  stationList.map((station) => [String(station.code).toUpperCase(), station.name])
);

export default function AlternativeCard({ option, level }) {
  const formatDuration = (mins) => {
    if (!mins && mins !== 0) return '';
    const hrs = Math.floor(mins / 60);
    const m = mins % 60;
    if (hrs === 0) return `${m}m`;
    return m > 0 ? `${hrs}h ${m}m` : `${hrs}h`;
  };

  const formatStationCode = (code) => {
    if (!code) return '';
    const upper = String(code).toUpperCase();
    const name = stationNameMap[upper];
    return name ? `${upper} - ${name}` : upper;
  };

  // Level 3 Multi-hop Card Rendering
  if (level === 3 || option.leg1 || option.leg2) {
    const leg1 = option.leg1 || {};
    const leg2 = option.leg2 || {};
    const transfer = option.transferStation || {};
    const transferCode = typeof transfer === 'string' ? transfer : transfer.code || 'TRANS';
    const transferName = typeof transfer === 'object' ? transfer.name : '';

    return (
      <div className="bg-[#111827] border border-slate-800 hover:border-slate-700 rounded-xl p-5 mb-4 shadow-lg transition-all">
        {/* Card Top Level Badge & Transfer Overview */}
        <div className="flex flex-wrap items-center justify-between gap-2 mb-4 pb-3 border-b border-slate-800/80">
          <div className="flex items-center space-x-2.5">
            <span className="text-xs font-bold px-2.5 py-1 rounded bg-amber-500/10 text-[#FBBF24] border border-amber-500/30 uppercase tracking-wider">
              Level 3 • 2-Leg Transfer
            </span>
            <span className="text-xs font-medium text-[#38BDF8] bg-sky-950/50 px-2.5 py-1 rounded border border-sky-800/40">
              Transfer at {formatStationCode(transferCode)} {transferName && `(${transferName})`}
            </span>
          </div>
          <div className="text-xs font-mono font-bold text-[#2DD4BF] bg-[#2DD4BF]/10 px-3 py-1 rounded border border-[#2DD4BF]/30 tabular-nums">
            Total Duration: {formatDuration(option.totalDurationMinutes)} ({option.totalDurationMinutes} mins)
          </div>
        </div>

        {/* LEG 1 DETAIL */}
        <div className="bg-[#0F172A] rounded-lg p-4 mb-3 border border-slate-800/70">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center space-x-2">
              <span className="text-xs font-mono font-bold text-[#2DD4BF] bg-[#2DD4BF]/10 px-2 py-0.5 rounded border border-[#2DD4BF]/20">
                Leg 1
              </span>
              <h4 className="text-sm font-bold text-[#F8FAFC]">
                {leg1.trainNumber} - {leg1.trainName}
              </h4>
              <span className="text-[10px] text-[#94A3B8] px-1.5 py-0.5 bg-slate-800 rounded">
                {leg1.type}
              </span>
            </div>
            <span className="text-xs font-mono text-[#94A3B8] tabular-nums">
              {leg1.departureTime} → {leg1.arrivalTime} ({formatDuration(leg1.durationMinutes)})
            </span>
          </div>

          {/* Station Sequence Route Path */}
          {leg1.stationSequence && leg1.stationSequence.length > 0 && (
            <div className="mt-2 text-xs font-mono text-[#94A3B8] flex items-center space-x-1.5 overflow-x-auto py-1.5 scrollbar-thin">
              <span className="text-[10px] text-slate-500 uppercase tracking-wider mr-1">Route:</span>
              {leg1.stationSequence.map((code, idx) => (
                <React.Fragment key={idx}>
                  <span className={`px-1.5 py-0.5 rounded text-[11px] ${idx === 0 || idx === leg1.stationSequence.length - 1 ? 'bg-sky-950 text-[#38BDF8] font-bold border border-sky-800/40' : 'bg-slate-900 text-slate-300'}`}>
                    {formatStationCode(code)}
                  </span>
                  {idx < leg1.stationSequence.length - 1 && (
                    <span className="text-slate-600">→</span>
                  )}
                </React.Fragment>
              ))}
            </div>
          )}

          {/* Leg 1 Class Seat Availability */}
          {leg1.seatAvailability && (
            <div className="mt-3 flex flex-wrap gap-2 pt-2 border-t border-slate-800/50">
              <span className="text-[10px] uppercase text-slate-400 font-semibold self-center mr-1">Seats:</span>
              {Object.entries(leg1.seatAvailability).map(([cls, count]) => (
                <div key={cls} className="bg-slate-900 border border-slate-800 px-2.5 py-1 rounded text-xs flex items-center space-x-1.5">
                  <span className="font-bold text-slate-400">{cls}:</span>
                  <span className={`font-mono font-bold tabular-nums ${count > 0 ? 'text-[#4ADE80]' : 'text-slate-500'}`}>
                    {count}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* CONNECTION LAYOVER BADGE */}
        <div className="relative my-2.5 flex items-center justify-center">
          <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-dashed border-amber-500/40"></div></div>
          <div className="relative bg-amber-950/80 text-amber-300 border border-amber-500/40 text-xs px-3 py-1 rounded-full font-mono font-medium flex items-center space-x-1.5 shadow-md">
            <span>🔄 Transfer at <strong className="text-amber-200">{transferCode}</strong></span>
            <span>•</span>
            <span className="tabular-nums font-bold">Layover: {formatDuration(option.layoverMinutes)}</span>
          </div>
        </div>

        {/* LEG 2 DETAIL */}
        <div className="bg-[#0F172A] rounded-lg p-4 border border-slate-800/70">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center space-x-2">
              <span className="text-xs font-mono font-bold text-[#38BDF8] bg-sky-950/40 px-2 py-0.5 rounded border border-sky-800/30">
                Leg 2
              </span>
              <h4 className="text-sm font-bold text-[#F8FAFC]">
                {leg2.trainNumber} - {leg2.trainName}
              </h4>
              <span className="text-[10px] text-[#94A3B8] px-1.5 py-0.5 bg-slate-800 rounded">
                {leg2.type}
              </span>
            </div>
            <span className="text-xs font-mono text-[#94A3B8] tabular-nums">
              {leg2.departureTime} → {leg2.arrivalTime} ({formatDuration(leg2.durationMinutes)})
            </span>
          </div>

          {/* Station Sequence Route Path */}
          {leg2.stationSequence && leg2.stationSequence.length > 0 && (
            <div className="mt-2 text-xs font-mono text-[#94A3B8] flex items-center space-x-1.5 overflow-x-auto py-1.5 scrollbar-thin">
              <span className="text-[10px] text-slate-500 uppercase tracking-wider mr-1">Route:</span>
              {leg2.stationSequence.map((code, idx) => (
                <React.Fragment key={idx}>
                  <span className={`px-1.5 py-0.5 rounded text-[11px] ${idx === 0 || idx === leg2.stationSequence.length - 1 ? 'bg-sky-950 text-[#38BDF8] font-bold border border-sky-800/40' : 'bg-slate-900 text-slate-300'}`}>
                    {formatStationCode(code)}
                  </span>
                  {idx < leg2.stationSequence.length - 1 && (
                    <span className="text-slate-600">→</span>
                  )}
                </React.Fragment>
              ))}
            </div>
          )}

          {/* Leg 2 Class Seat Availability */}
          {leg2.seatAvailability && (
            <div className="mt-3 flex flex-wrap gap-2 pt-2 border-t border-slate-800/50">
              <span className="text-[10px] uppercase text-slate-400 font-semibold self-center mr-1">Seats:</span>
              {Object.entries(leg2.seatAvailability).map(([cls, count]) => (
                <div key={cls} className="bg-slate-900 border border-slate-800 px-2.5 py-1 rounded text-xs flex items-center space-x-1.5">
                  <span className="font-bold text-slate-400">{cls}:</span>
                  <span className={`font-mono font-bold tabular-nums ${count > 0 ? 'text-[#4ADE80]' : 'text-slate-500'}`}>
                    {count}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  // Direct Train Card (Level 1 & Level 2)
  const isLvl1 = option.level === 1 || level === 1;

  return (
    <div className="bg-[#111827] border border-slate-800 hover:border-slate-700 rounded-xl p-5 mb-4 shadow-lg transition-all">
      {/* Header & Level Badge */}
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <div className="flex items-center space-x-2.5">
          <span className={`text-xs font-bold px-2.5 py-1 rounded uppercase tracking-wider ${
            isLvl1 
              ? 'bg-[#2DD4BF]/10 text-[#2DD4BF] border border-[#2DD4BF]/30' 
              : 'bg-sky-500/10 text-[#38BDF8] border border-sky-500/30'
          }`}>
            {isLvl1 ? 'Level 1 • Express / Premium' : 'Level 2 • Local / Passenger / DEMU'}
          </span>
          <span className="text-xs font-semibold text-slate-400 bg-slate-800 px-2 py-0.5 rounded">
            {option.type}
          </span>
        </div>
        <div className="text-xs font-mono font-bold text-[#2DD4BF] bg-[#2DD4BF]/10 px-3 py-1 rounded border border-[#2DD4BF]/20 tabular-nums">
          Duration: {formatDuration(option.durationMinutes)}
        </div>
      </div>

      {/* Train Info */}
      <div className="mb-3">
        <h3 className="text-base font-bold text-[#F8FAFC]">
          {option.trainNumber} - {option.trainName}
        </h3>
        <div className="flex items-center space-x-3 mt-1.5 text-xs text-[#94A3B8] font-mono tabular-nums">
          <span>Departs: <strong className="text-[#F8FAFC]">{option.departureTime}</strong></span>
          <span>•</span>
          <span>Arrives: <strong className="text-[#F8FAFC]">{option.arrivalTime}</strong></span>
        </div>
      </div>

      {/* Station Sequence Route Path */}
      {option.stationSequence && option.stationSequence.length > 0 && (
        <div className="my-3 bg-[#0F172A] p-2.5 rounded-lg border border-slate-800/60">
          <div className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider mb-1.5">
            Station Sequence Route Path:
          </div>
          <div className="text-xs font-mono text-[#94A3B8] flex items-center space-x-1.5 overflow-x-auto pb-1 scrollbar-thin">
            {option.stationSequence.map((code, idx) => (
              <React.Fragment key={idx}>
                <span className={`px-2 py-0.5 rounded text-xs ${
                  idx === 0 || idx === option.stationSequence.length - 1 
                    ? 'bg-sky-950 text-[#38BDF8] font-bold border border-sky-800/50' 
                    : 'bg-slate-900 text-slate-300'
                }`}>
                  {formatStationCode(code)}
                </span>
                {idx < option.stationSequence.length - 1 && (
                  <span className="text-slate-600">→</span>
                )}
              </React.Fragment>
            ))}
          </div>
        </div>
      )}

      {/* Class Seat Availability Grid */}
      {option.seatAvailability && (
        <div className="mt-3 pt-3 border-t border-slate-800/70">
          <div className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider mb-2">
            Class Seat Availability:
          </div>
          <div className="flex flex-wrap gap-2">
            {Object.entries(option.seatAvailability).map(([cls, count]) => (
              <div 
                key={cls}
                className="bg-[#0F172A] border border-slate-800 px-3 py-1.5 rounded-lg text-xs flex items-center space-x-2"
              >
                <span className="font-bold text-slate-400">{cls}</span>
                <span className={`font-mono font-bold tabular-nums ${count > 0 ? 'text-[#4ADE80]' : 'text-slate-500'}`}>
                  {count > 0 ? `${count} seats` : '0 seats'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
