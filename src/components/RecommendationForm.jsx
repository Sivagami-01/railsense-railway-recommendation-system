import React, { useState, useMemo, useRef, useEffect } from 'react';
import StationAutocomplete from './StationAutocomplete';
import { trainCatalog } from '../data/trainCatalog';

const demoPresets = [
  {
    label: 'South → South',
    source: { code: 'MAS', name: 'CHENNAI CENTRAL' },
    dest: { code: 'CBE', name: 'COIMBATORE JN' },
    scheduledTime: '2026-11-15T07:45',
    delayMinutes: 75,
    waitTolerance: 25,
  },
  {
    label: 'South → North',
    source: { code: 'SBC', name: 'BENGALURU CITY' },
    dest: { code: 'NDLS', name: 'NEW DELHI' },
    scheduledTime: '2026-11-15T18:10',
    delayMinutes: 150,
    waitTolerance: 35,
  },
  {
    label: 'North → North',
    source: { code: 'JAT', name: 'JAMMU TAWI' },
    dest: { code: 'UHP', name: 'UDHAMPUR' },
    scheduledTime: '2026-11-15T06:30',
    delayMinutes: 120,
    waitTolerance: 30,
  },
  {
    label: 'North → South',
    source: { code: 'NDLS', name: 'NEW DELHI' },
    dest: { code: 'MAS', name: 'CHENNAI CENTRAL' },
    scheduledTime: '2026-11-15T19:00',
    delayMinutes: 180,
    waitTolerance: 40,
  },
  {
    label: 'No result demo',
    source: { code: 'BCT', name: 'MUMBAI CENTRAL' },
    dest: { code: 'LTT', name: 'LOTTI' },
    scheduledTime: '2026-11-15T15:00',
    delayMinutes: 120,
    waitTolerance: 30,
  },
];

export default function RecommendationForm({ onSubmit, loading }) {
  const [sourceStation, setSourceStation] = useState({ code: 'JAT', name: 'JAMMU TAWI' });
  const [destStation, setDestStation] = useState({ code: 'UHP', name: 'UDHAMPUR' });
  const [bookedTrainInfo, setBookedTrainInfo] = useState({ number: '12445', name: 'Uttar Sampark Kranti Express' });
  const [trainQuery, setTrainQuery] = useState('12445 - Uttar Sampark Kranti Express');
  const [trainOpen, setTrainOpen] = useState(false);
  const trainRef = useRef(null);

  const [scheduledDate, setScheduledDate] = useState('2026-11-15');
  const [scheduledTime, setScheduledTime] = useState('06:30');
  const [delayMinutes, setDelayMinutes] = useState(120);
  const [waitTolerance, setWaitTolerance] = useState(30);

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
    if (!search) return trainCatalog;

    return trainCatalog.filter((train) => {
      const haystack = `${train.number} ${train.name} ${train.type}`.toLowerCase();
      return haystack.includes(search);
    });
  }, [trainQuery]);

  const loadPreset = (preset) => {
    setSourceStation(preset.source);
    setDestStation(preset.dest);

    if (preset.scheduledTime && preset.scheduledTime.includes('T')) {
      const [datePart, timePart] = preset.scheduledTime.split('T');
      setScheduledDate(datePart);
      setScheduledTime(timePart.slice(0, 5));
    } else {
      setScheduledDate('2026-11-15');
      setScheduledTime('06:30');
    }

    setDelayMinutes(preset.delayMinutes);
    setWaitTolerance(preset.waitTolerance);
  };

  const handleTrainSelect = (train) => {
    const value = `${train.number} - ${train.name}`;
    setBookedTrainInfo({ number: train.number, name: train.name });
    setTrainQuery(value);
    setTrainOpen(false);
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    const srcCode = typeof sourceStation === 'object' ? sourceStation.code : sourceStation;
    const dstCode = typeof destStation === 'object' ? destStation.code : destStation;

    if (!srcCode || !dstCode) {
      alert('Please select valid source and destination stations.');
      return;
    }

    if (!scheduledDate || !scheduledTime) {
      alert('Please choose a valid scheduled date and time.');
      return;
    }

    const isoScheduledTime = `${scheduledDate}T${scheduledTime}:00`;

    const payload = {
      source_code: srcCode.toUpperCase().trim(),
      destination_code: dstCode.toUpperCase().trim(),
      scheduled_time: isoScheduledTime,
      delay_minutes: Number(delayMinutes),
      wait_tolerance_minutes: Number(waitTolerance),
      booked_train_number: bookedTrainInfo.number || ''
    };

    onSubmit(payload);
  };

  return (
    <form onSubmit={handleSubmit} className="bg-[#111827] border border-slate-800 rounded-xl p-5 mb-6 shadow-xl">
      <div className="flex items-center justify-between pb-3 mb-4 border-b border-slate-800">
        <h2 className="text-base font-bold text-[#F8FAFC] flex items-center space-x-2">
          <span className="text-[#2DD4BF]">🚆</span>
          <span>Journey & Delay Configuration</span>
        </h2>
        <span className="text-[11px] font-mono text-[#94A3B8] bg-slate-900 px-2 py-1 rounded border border-slate-800">
          3-Level Recommendation Engine
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        <StationAutocomplete
          label="Source Station"
          placeholder="e.g. JAT or Jammu Tawi"
          value={sourceStation}
          onChange={(code, obj) => setSourceStation(obj || code)}
          required
        />

        <StationAutocomplete
          label="Destination Station"
          placeholder="e.g. UHP or Udhampur"
          value={destStation}
          onChange={(code, obj) => setDestStation(obj || code)}
          required
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
        <div ref={trainRef} className="relative">
          <label className="block text-xs font-medium uppercase tracking-wider text-[#94A3B8] mb-1.5">
            Booked Train (Optional)
          </label>
          <input
            type="text"
            value={trainQuery}
            onFocus={() => setTrainOpen(true)}
            onChange={(e) => {
              const value = e.target.value;
              setTrainQuery(value);
              setTrainOpen(true);
              setBookedTrainInfo({ number: '', name: value });
            }}
            placeholder="e.g. 12445 Uttar Sampark Kranti"
            className="w-full bg-[#0B1120] border border-slate-800 rounded-lg px-3.5 py-2.5 text-sm text-[#F8FAFC] placeholder-slate-500 focus:outline-none focus:border-[#2DD4BF] transition-colors"
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
          <label className="block text-xs font-medium uppercase tracking-wider text-[#94A3B8] mb-1.5">
            Scheduled Date & Time <span className="text-[#2DD4BF]">*</span>
          </label>
          <div className="grid grid-cols-2 gap-2">
            <div className="relative">
              <input
                type="date"
                value={scheduledDate}
                onChange={(e) => setScheduledDate(e.target.value)}
                required
                className="w-full bg-[#0B1120] border border-slate-800 rounded-lg px-3.5 py-2.5 text-sm text-[#F8FAFC] focus:outline-none focus:border-[#2DD4BF] transition-colors font-mono tabular-nums"
              />
            </div>
            <div className="relative">
              <input
                type="time"
                value={scheduledTime}
                onChange={(e) => setScheduledTime(e.target.value)}
                required
                className="w-full bg-[#0B1120] border border-slate-800 rounded-lg px-3.5 py-2.5 text-sm text-[#F8FAFC] focus:outline-none focus:border-[#2DD4BF] transition-colors font-mono tabular-nums"
              />
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="block text-xs font-medium uppercase tracking-wider text-[#94A3B8] mb-1.5">
              Delay (mins) <span className="text-[#2DD4BF]">*</span>
            </label>
            <input
              type="number"
              min="0"
              value={delayMinutes}
              onChange={(e) => setDelayMinutes(e.target.value)}
              required
              className="w-full bg-[#0B1120] border border-slate-800 rounded-lg px-3 py-2.5 text-sm text-[#F8FAFC] font-mono tabular-nums focus:outline-none focus:border-[#2DD4BF]"
            />
          </div>

          <div>
            <label className="block text-xs font-medium uppercase tracking-wider text-[#94A3B8] mb-1.5">
              Tolerance (m) <span className="text-[#2DD4BF]">*</span>
            </label>
            <input
              type="number"
              min="0"
              value={waitTolerance}
              onChange={(e) => setWaitTolerance(e.target.value)}
              required
              className="w-full bg-[#0B1120] border border-slate-800 rounded-lg px-3 py-2.5 text-sm text-[#F8FAFC] font-mono tabular-nums focus:outline-none focus:border-[#2DD4BF]"
            />
          </div>
        </div>
      </div>

      <div className="mb-4 flex flex-wrap gap-2">
        {demoPresets.map((preset) => (
          <button
            key={preset.label}
            type="button"
            onClick={() => loadPreset(preset)}
            className="rounded-full border border-[#2DD4BF]/40 bg-[#0B1120] px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-[#2DD4BF] transition hover:bg-[#2DD4BF]/10"
          >
            {preset.label}
          </button>
        ))}
      </div>

      <button
        type="submit"
        disabled={loading}
        className="w-full bg-[#2DD4BF] hover:bg-[#26b8a5] text-[#0B1120] font-bold text-sm py-3 px-4 rounded-lg shadow-md transition-all flex items-center justify-center space-x-2 cursor-pointer disabled:opacity-50"
      >
        {loading ? (
          <>
            <div className="w-4 h-4 border-2 border-[#0B1120] border-t-transparent rounded-full animate-spin"></div>
            <span>Finding Alternatives...</span>
          </>
        ) : (
          <>
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <span>Find Alternative Trains</span>
          </>
        )}
      </button>
    </form>
  );
}
