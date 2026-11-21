import React, { useState, useMemo, useRef, useEffect } from 'react';
import { predictDelay, getTrainDetails } from '../lib/api';
import { trainCatalog } from '../data/trainCatalog';

const allTrains = [...trainCatalog].sort((a, b) => a.name.localeCompare(b.name));

export default function DelayPredictionPanel({ onFindAlternativesTrigger }) {
  const [trainNumber, setTrainNumber] = useState('04601');
  const [trainQuery, setTrainQuery] = useState('04601 - Superfast Express');
  const [trainOpen, setTrainOpen] = useState(false);
  const trainRef = useRef(null);
  const [futureDate, setFutureDate] = useState('2026-11-15');
  const [loading, setLoading] = useState(false);
  const [prediction, setPrediction] = useState(null);
  const [error, setError] = useState(null);
  const [triggerLoading, setTriggerLoading] = useState(false);

  useEffect(() => {
    function onClickOutside(event) {
      if (trainRef.current && !trainRef.current.contains(event.target)) {
        setTrainOpen(false);
      }
    }
    document.addEventListener('mousedown', onClickOutside);
    return () => document.removeEventListener('mousedown', onClickOutside);
  }, []);

  const filteredTrains = useMemo(() => {
    const search = (trainQuery || '').trim().toLowerCase();
    if (!search) return allTrains;

    return allTrains.filter((train) => {
      const haystack = `${train.number} ${train.name} ${train.type}`.toLowerCase();
      return haystack.includes(search);
    });
  }, [trainQuery]);

  const handleTrainSelect = (train) => {
    setTrainNumber(train.number);
    setTrainQuery(`${train.number} - ${train.name}`);
    setTrainOpen(false);
  };

  const handlePredict = async (e) => {
    e.preventDefault();
    if (!trainNumber || !futureDate) return;

    setLoading(true);
    setError(null);
    setPrediction(null);

    try {
      const res = await predictDelay({
        train_number: trainNumber.trim(),
        future_date: futureDate.trim()
      });
      setPrediction(res);
    } catch (err) {
      setError(err.message || 'Failed to compute delay prediction');
    } finally {
      setLoading(false);
    }
  };

  const handleTriggerAlternatives = async () => {
    if (!prediction) return;

    setTriggerLoading(true);
    try {
      const trainDoc = await getTrainDetails(prediction.train_number);

      const sourceCode = trainDoc.source ? trainDoc.source.code : 'JAT';
      const destCode = trainDoc.destination ? trainDoc.destination.code : 'UHP';

      let depTime = '10:40:00';
      if (trainDoc.completeOrderedRoute && trainDoc.completeOrderedRoute.length > 0) {
        depTime = trainDoc.completeOrderedRoute[0].departureTime || '10:40:00';
      }

      const scheduledTimeIso = `${prediction.future_date}T${depTime}`;
      const range = prediction.predicted_delay_range_minutes || [60, 120];
      const midpointDelay = Math.round((range[0] + range[1]) / 2);

      const payload = {
        source_code: sourceCode,
        destination_code: destCode,
        scheduled_time: scheduledTimeIso,
        delay_minutes: midpointDelay,
        wait_tolerance_minutes: 30,
        current_time: new Date().toISOString(),
        booked_train_number: prediction.train_number,
      };

      onFindAlternativesTrigger(payload);
    } catch (err) {
      alert(`Error triggering alternative search: ${err.message}`);
    } finally {
      setTriggerLoading(false);
    }
  };

  return (
    <div className="bg-[#111827] border border-slate-800 rounded-xl p-5 shadow-xl">
      <div className="flex items-center space-x-2 pb-3 mb-4 border-b border-slate-800">
        <span className="text-[#38BDF8]">🔮</span>
        <h3 className="text-sm font-bold text-[#F8FAFC]">Future Date Delay Prediction</h3>
      </div>

      <form onSubmit={handlePredict} className="space-y-3.5 mb-4">
        <div ref={trainRef} className="relative">
          <label className="block text-[11px] font-medium uppercase tracking-wider text-[#94A3B8] mb-1">
            Train Number
          </label>
          <input
            type="text"
            value={trainQuery}
            onFocus={() => setTrainOpen(true)}
            onChange={(e) => {
              const value = e.target.value;
              setTrainQuery(value);
              setTrainOpen(true);
              setTrainNumber('');
            }}
            placeholder="e.g. 04601 or 12445"
            required
            className="w-full bg-[#0B1120] border border-slate-800 rounded-lg px-3 py-2 text-sm text-[#F8FAFC] font-mono tabular-nums focus:outline-none focus:border-[#38BDF8]"
          />

          {trainOpen && (
            <div className="absolute z-50 mt-1 w-full rounded-lg border border-slate-700 bg-[#0F172A] shadow-2xl overflow-hidden">
              <div className="max-h-72 overflow-y-auto">
                {filteredTrains.length > 0 ? filteredTrains.map((train) => (
                  <button
                    key={train.number}
                    type="button"
                    onClick={() => handleTrainSelect(train)}
                    className="flex w-full items-center justify-between gap-2 border-b border-slate-800/70 px-3 py-2 text-left hover:bg-[#111827]"
                  >
                    <div className="min-w-0">
                      <div className="font-mono text-[11px] font-bold text-[#38BDF8]">{train.number}</div>
                      <div className="truncate text-sm text-[#F8FAFC]">{train.name}</div>
                    </div>
                    <span className="rounded border border-[#2DD4BF]/30 bg-[#2DD4BF]/10 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-[#2DD4BF]">
                      {train.type || 'Train'}
                    </span>
                  </button>
                )) : (
                  <div className="px-3 py-3 text-xs text-slate-400">No trains found</div>
                )}
              </div>
            </div>
          )}
        </div>

        <div>
          <label className="block text-[11px] font-medium uppercase tracking-wider text-[#94A3B8] mb-1">
            Future Date
          </label>
          <input
            type="date"
            value={futureDate}
            onChange={(e) => setFutureDate(e.target.value)}
            required
            className="w-full bg-[#0B1120] border border-slate-800 rounded-lg px-3 py-2 text-sm text-[#F8FAFC] font-mono tabular-nums focus:outline-none focus:border-[#38BDF8]"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-[#38BDF8] hover:bg-[#0284c7] text-[#0B1120] font-bold text-xs py-2.5 px-3 rounded-lg transition-all flex items-center justify-center space-x-1.5 cursor-pointer disabled:opacity-50"
        >
          {loading ? (
            <>
              <div className="w-3.5 h-3.5 border-2 border-[#0B1120] border-t-transparent rounded-full animate-spin"></div>
              <span>Predicting ML Delay...</span>
            </>
          ) : (
            <span>Predict Future Delay</span>
          )}
        </button>
      </form>

      {error && (
        <div className="bg-red-950/40 border border-red-500/40 rounded-lg p-3 text-xs text-red-300">
          {error}
        </div>
      )}

      {prediction && (
        <div className="bg-[#0F172A] border border-slate-800 rounded-lg p-4 space-y-3">
          <div className="border-b border-slate-800/80 pb-2">
            <h4 className="text-xs font-bold text-[#F8FAFC]">{prediction.train_name}</h4>
            <span className="text-[10px] font-mono text-[#94A3B8]">
              Train #{prediction.train_number} • {prediction.future_date}
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-xs text-[#94A3B8]">Delay Probability:</span>
            <span className={`text-sm font-mono font-bold px-2 py-0.5 rounded ${
              prediction.delay_probability_pct >= 50
                ? 'bg-amber-500/20 text-[#FBBF24] border border-amber-500/40'
                : 'bg-emerald-500/20 text-[#4ADE80] border border-emerald-500/40'
            }`}>
              {prediction.delay_probability_pct}%
            </span>
          </div>

          <div className="flex items-center justify-between text-xs">
            <span className="text-[#94A3B8]">Predicted Delay Range:</span>
            <span className="font-mono font-bold text-[#F8FAFC] tabular-nums">
              {prediction.predicted_delay_range_minutes[0]} – {prediction.predicted_delay_range_minutes[1]} mins
            </span>
          </div>

          <p className="text-[11px] text-slate-400 italic bg-slate-900/80 p-2 rounded border border-slate-800/60">
            "{prediction.confidence_note}"
          </p>

          {prediction.delay_probability_pct >= 50 && (
            <button
              onClick={handleTriggerAlternatives}
              disabled={triggerLoading}
              className="w-full mt-2 bg-[#2DD4BF]/20 hover:bg-[#2DD4BF]/30 text-[#2DD4BF] border border-[#2DD4BF]/40 font-bold text-xs py-2 px-3 rounded-lg transition-all flex items-center justify-center space-x-1.5 cursor-pointer disabled:opacity-50"
            >
              {triggerLoading ? (
                <span>Fetching Train Schedule & Searching...</span>
              ) : (
                <>
                  <span>⚡ Find Reliable Alternatives</span>
                </>
              )}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
