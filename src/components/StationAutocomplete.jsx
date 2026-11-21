import React, { useState, useEffect, useMemo, useRef } from 'react';
import { stationList } from '../data/stations';

const allStations = [...stationList].sort((a, b) => a.name.localeCompare(b.name));

const normalizeStationText = (value = '') => value.toUpperCase().replace(/[^A-Z0-9]/g, '');

const aliasMap = {
  'CHENNAICENTRAL': 'MAS',
  'MGRCHENNAICENTRAL': 'MAS',
  'CHENNAIEGMORE': 'MS',
  'CHENNAIBEACH': 'MSB',
  'CHENNAIBEACHJN': 'MSB',
};

export default function StationAutocomplete({
  label,
  placeholder,
  value,
  onChange,
  required = false
}) {
  const [query, setQuery] = useState(value ? value.code || value : '');
  const [isOpen, setIsOpen] = useState(false);
  const wrapperRef = useRef(null);

  useEffect(() => {
    if (typeof value === 'object' && value !== null) {
      setQuery(value.code ? `${value.code} - ${value.name}` : '');
    } else if (typeof value === 'string') {
      setQuery(value);
    }
  }, [value]);

  useEffect(() => {
    function handleClickOutside(event) {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const filteredOptions = useMemo(() => {
    const search = (query || '').trim();
    const normalizedSearch = normalizeStationText(search);
    if (!normalizedSearch) return allStations;

    return allStations.filter((station) => {
      const normalizedCode = normalizeStationText(station.code);
      const normalizedName = normalizeStationText(station.name);
      const combined = normalizeStationText(`${station.code} ${station.name}`);
      const aliasMatch = aliasMap[normalizedSearch] === station.code;

      return aliasMatch || normalizedCode.includes(normalizedSearch) || normalizedName.includes(normalizedSearch) || combined.includes(normalizedSearch);
    });
  }, [query]);

  const handleInputChange = (e) => {
    const rawValue = e.target.value;
    setQuery(rawValue);
    setIsOpen(true);

    if (!rawValue || !rawValue.trim()) {
      onChange('', null);
      return;
    }

    onChange('', null);
  };

  const handleSelect = (station) => {
    setQuery(`${station.code} - ${station.name}`);
    setIsOpen(false);
    onChange(station.code, station);
  };

  return (
    <div className="relative w-full" ref={wrapperRef}>
      {label && (
        <label className="block text-xs font-medium uppercase tracking-wider text-[#94A3B8] mb-1.5">
          {label} {required && <span className="text-[#2DD4BF]">*</span>}
        </label>
      )}

      <input
        type="text"
        value={query}
        onFocus={() => setIsOpen(true)}
        onChange={handleInputChange}
        placeholder={placeholder || 'e.g. JAT or Jammu Tawi'}
        required={required}
        className="w-full bg-[#0B1120] border border-slate-800 rounded-lg px-3.5 py-2.5 text-sm text-[#F8FAFC] placeholder-slate-500 focus:outline-none focus:border-[#2DD4BF] transition-colors"
      />

      {isOpen && (
        <div className="absolute z-50 mt-1 w-full rounded-lg border border-slate-700 bg-[#0F172A] shadow-2xl overflow-hidden">
          <div className="max-h-72 overflow-y-auto">
            {filteredOptions.length > 0 ? (
              filteredOptions.map((station) => (
                <button
                  key={station.code}
                  type="button"
                  onClick={() => handleSelect(station)}
                  className="flex w-full items-center justify-between gap-3 border-b border-slate-800/70 px-3 py-2 text-left text-sm hover:bg-[#111827]"
                >
                  <div className="flex min-w-0 items-center gap-2">
                    <span className="rounded border border-sky-700 bg-sky-950/40 px-1.5 py-0.5 font-mono text-[11px] font-bold text-[#38BDF8]">
                      {station.code}
                    </span>
                    <span className="truncate text-[#F8FAFC]">{station.name}</span>
                  </div>
                </button>
              ))
            ) : (
              <div className="px-3 py-3 text-xs text-slate-400">No stations found</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
