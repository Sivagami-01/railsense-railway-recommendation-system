import React, { useState, useEffect } from 'react';
import { getHealth, getRecommendations } from './lib/api';
import RecommendationForm from './components/RecommendationForm';
import DecisionBanner from './components/DecisionBanner';
import AlternativeCard from './components/AlternativeCard';
import DelayPredictionPanel from './components/DelayPredictionPanel';

export default function App() {
  const [healthStatus, setHealthStatus] = useState({ status: 'checking', mongodb_connected: false });
  const [loading, setLoading] = useState(false);
  const [recommendationResult, setRecommendationResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  // Check API health status on mount
  useEffect(() => {
    async function checkHealth() {
      const res = await getHealth();
      setHealthStatus(res);
    }
    checkHealth();
  }, []);

  const handleRecommendationSubmit = async (payload) => {
    setErrorMsg(null);

    // Requirement 2: If delay_minutes <= wait_tolerance_minutes, do NOT call API
    if (payload.delay_minutes <= payload.wait_tolerance_minutes) {
      setRecommendationResult({
        decision: 'continue_with_booked_train',
        reason: `Expected delay of ${payload.delay_minutes} mins is within user wait tolerance of ${payload.wait_tolerance_minutes} mins.`,
        delayed_arrival_time: payload.scheduled_time,
        alternatives: []
      });
      return;
    }

    setLoading(true);
    setRecommendationResult(null);

    try {
      const requestPayload = {
        ...payload,
        current_time: new Date().toISOString(),
      };
      const res = await getRecommendations(requestPayload);
      setRecommendationResult(res);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to fetch recommendations from backend API');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0B1120] text-[#F8FAFC] pb-12">
      {/* Top Navigation / Header Bar */}
      <header className="bg-[#0F172A] border-b border-slate-800 sticky top-0 z-40 shadow-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-[#2DD4BF]/10 text-[#2DD4BF] border border-[#2DD4BF]/30 rounded-lg">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            </div>
            <div>
              <h1 className="text-lg font-bold text-[#F8FAFC] tracking-tight">
                Indian Railways Delay & Alternative Engine
              </h1>
              <p className="text-xs text-[#94A3B8]">
                Hierarchical 3-Level Recommendation & ML Delay Prediction System
              </p>
            </div>
          </div>

          {/* Health Status Indicator */}
          <div className="flex items-center space-x-2">
            <div className={`w-2.5 h-2.5 rounded-full ${healthStatus.mongodb_connected ? 'bg-[#4ADE80] animate-pulse' : 'bg-red-500'}`}></div>
            <span className="text-xs font-mono text-[#94A3B8]">
              {healthStatus.mongodb_connected ? 'MongoDB Live' : 'API Connecting...'}
            </span>
          </div>
        </div>
      </header>

      {/* Main Container Layout */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          
          {/* Main Content Area (Form + Results) */}
          <div className="lg:col-span-8 space-y-6 lg:order-1">
            
            {/* Search Form */}
            <RecommendationForm
              onSubmit={handleRecommendationSubmit}
              loading={loading}
            />

            {/* Error Alert Box */}
            {errorMsg && (
              <div className="bg-red-950/40 border border-red-500/40 rounded-xl p-4 text-sm text-red-300 flex items-center justify-between">
                <div>
                  <strong className="font-bold">API Connection Error: </strong>
                  <span>{errorMsg}</span>
                </div>
                <button
                  onClick={() => setErrorMsg(null)}
                  className="text-xs font-bold text-red-400 hover:text-red-200 ml-4 cursor-pointer"
                >
                  Dismiss
                </button>
              </div>
            )}

            {/* Decision Status Banner */}
            <DecisionBanner
              recommendationData={recommendationResult}
              loading={loading}
            />

            {/* Alternative Cards List */}
            {recommendationResult && recommendationResult.alternatives && recommendationResult.alternatives.length > 0 && (
              <div className="space-y-4">
                <h3 className="text-sm font-bold uppercase tracking-wider text-[#94A3B8]">
                  Available Alternative Routes ({recommendationResult.alternatives.length})
                </h3>
                {recommendationResult.alternatives.map((option, idx) => (
                  <AlternativeCard
                    key={idx}
                    option={option}
                    level={recommendationResult.level}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Right Sidebar Area (ML Delay Prediction Panel) */}
          <div className="lg:col-span-4 space-y-6 lg:order-2">
            <DelayPredictionPanel
              onFindAlternativesTrigger={handleRecommendationSubmit}
            />

            {/* Quick System Info Card */}
            <div className="bg-[#0F172A] border border-slate-800/80 rounded-xl p-4 text-xs space-y-2 text-[#94A3B8]">
              <h4 className="font-bold text-[#F8FAFC] flex items-center space-x-1.5">
                <span>ℹ️</span>
                <span>Recommendation Hierarchy</span>
              </h4>
              <ul className="space-y-1.5 list-disc list-inside">
                <li><strong className="text-[#2DD4BF]">Level 1:</strong> Express, Superfast, Vande Bharat, Rajdhani, Shatabdi</li>
                <li><strong className="text-[#38BDF8]">Level 2:</strong> DEMU, MEMU, Passenger, Local Trains</li>
                <li><strong className="text-[#FBBF24]">Level 3:</strong> 2-Leg Multi-Hop Transfers (with Layover Guard)</li>
              </ul>
            </div>
          </div>

        </div>
      </main>
    </div>
  );
}
