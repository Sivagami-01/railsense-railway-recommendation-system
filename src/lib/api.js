/**
 * API Client Library for Train Recommendation & Delay Prediction Backend
 * Base URL defaults to http://localhost:8000, overridable via VITE_API_BASE_URL.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

async function handleResponse(response) {
  if (!response.ok) {
    let errorDetail = `HTTP Error ${response.status}: ${response.statusText}`;
    try {
      const data = await response.json();
      if (data && data.detail) {
        errorDetail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
      }
    } catch {
      // Fallback to text status if response is not JSON
    }
    throw new Error(errorDetail);
  }
  return response.json();
}

export async function getHealth() {
  try {
    const res = await fetch(`${BASE_URL}/api/health`);
    return await handleResponse(res);
  } catch (err) {
    return { status: 'error', mongodb_connected: false, message: err.message };
  }
}

export async function searchStations(query) {
  if (!query || !query.trim()) return [];
  const encoded = encodeURIComponent(query.trim());
  const res = await fetch(`${BASE_URL}/api/stations/search?query=${encoded}`);
  return handleResponse(res);
}

export async function getRecommendations(payload) {
  const res = await fetch(`${BASE_URL}/api/recommendations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return handleResponse(res);
}

export async function predictDelay(payload) {
  const res = await fetch(`${BASE_URL}/api/predict-delay`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return handleResponse(res);
}

export async function getTrainDetails(trainNumber) {
  if (!trainNumber) throw new Error('Train number is required');
  const encoded = encodeURIComponent(String(trainNumber).trim());
  const res = await fetch(`${BASE_URL}/api/trains/${encoded}`);
  return handleResponse(res);
}
