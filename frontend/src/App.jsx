// App.jsx
import React, { useState } from 'react'
import { MapPin, Clock, DollarSign, TrendingUp, Bus, Train, Car, Navigation, Star } from 'lucide-react'
import './index.css'

export default function App() {
  const [origin, setOrigin] = useState('')
  const [destination, setDestination] = useState('')
  const [preferredTime, setPreferredTime] = useState('')
  const [modePrefs, setModePrefs] = useState({bus:true, metro:true, rideshare:true, taxi:true})
  const [tripId, setTripId] = useState(null)
  const [recs, setRecs] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [useML, setUseML] = useState(true)
  const [usedModelIndicator, setUsedModelIndicator] = useState(null)
  const [showFeedback, setShowFeedback] = useState(null)
  const [rating, setRating] = useState(5)
  const [comment, setComment] = useState('')
  const [showMap, setShowMap] = useState(false)
  const [selectedRoute, setSelectedRoute] = useState(null)
  const [mapData, setMapData] = useState(null)
  const [loadingMap, setLoadingMap] = useState(false)
  const apiBase = 'http://127.0.0.1:8000/api'

  const getModeIcon = (mode) => {
    const iconProps = { size: 24 }
    switch(mode) {
      case 'Bus': return <Bus {...iconProps} />
      case 'Metro': return <Train {...iconProps} />
      case 'RideShare': return <Car {...iconProps} />
      case 'Taxi': return <Navigation {...iconProps} />
      default: return <MapPin {...iconProps} />
    }
  }

  const formatTime = (minutes) => {
    if (minutes < 60) {
      return `${minutes} minutes`
    }
    const hours = Math.floor(minutes / 60)
    const mins = minutes % 60
    if (mins === 0) {
      return `${hours} ${hours === 1 ? 'hour' : 'hours'}`
    }
    return `${hours} ${hours === 1 ? 'hour' : 'hours'} ${mins} minutes`
  }

  async function createTrip() {
    if (!origin || !destination) {
      setError('Please enter both origin and destination')
      return
    }
    setError('')
    setLoading(true)
    try {
      const resp = await fetch(`${apiBase}/trip_requests/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          origin, 
          destination, 
          preferred_time: preferredTime, 
          mode_preferences: Object.keys(modePrefs).filter(k=>modePrefs[k]).join(',') 
        })
      })
      const data = await resp.json()
      if (resp.ok) {
        setTripId(data.id)
        await fetchRecs(data.id)
      } else {
        setError('Error creating trip: ' + (data.detail || JSON.stringify(data)))
        setRecs([])
      }
    } catch (err) {
      setError('Network error: ' + String(err))
    } finally {
      setLoading(false)
    }
  }

  async function fetchRecs(id) {
    setError('')
    setLoading(true)
    try {
      const resp = await fetch(`${apiBase}/recommendations/?trip_id=${id}&use_ml=${useML}`)
      const data = await resp.json()
      if (resp.ok) {
        setRecs(data.recommendations || [])
        if (data.used_model !== undefined) setUsedModelIndicator(data.used_model)
      } else {
        setError('Error fetching recommendations: ' + (data.detail || JSON.stringify(data)))
        setRecs([])
      }
    } catch (err) {
      setError('Network error: ' + String(err))
      setRecs([])
    } finally {
      setLoading(false)
    }
  }

  async function submitFeedback(r) {
    try {
      const resp = await fetch(`${apiBase}/feedback/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          trip_id: tripId, 
          mode: r.mode, 
          rating, 
          comment, 
          eta_minutes: r.eta_minutes, 
          cost: r.cost, 
          score: r.score 
        })
      })
      const data = await resp.json()
      if (resp.ok) {
        setShowFeedback(null)
        setRating(5)
        setComment('')
        alert('✅ Thanks! Your feedback helps improve recommendations.')
      } else {
        alert('Error saving feedback: ' + JSON.stringify(data))
      }
    } catch (err) {
      alert('Network error: ' + String(err))
    }
  }

  async function loadMapData(route) {
    setLoadingMap(true)
    try {
      const resp = await fetch(`${apiBase}/map-data/?trip_id=${tripId}&mode=${route.mode}`)
      const data = await resp.json()
      if (resp.ok) {
        setMapData(data)
        setSelectedRoute(route)
        setShowMap(true)
      } else {
        alert('Error loading map: ' + (data.error || 'Unknown error'))
      }
    } catch (err) {
      alert('Network error: ' + String(err))
    } finally {
      setLoadingMap(false)
    }
  }

  return (
    <div className="app-container">
      <div className="app-wrapper">
        
        {/* Header */}
        <header className="app-header">
          <div className="header-content">
            <div className="logo-icon">
              <MapPin size={32} />
            </div>
            <h1 className="app-title">TransitMate</h1>
          </div>
          <p className="app-subtitle">AI-powered transportation recommendations</p>
        </header>

        {/* Main Card */}
        <div className="main-card">
          <div className="card-content">
            
            {/* ML Toggle */}
            <div className="ml-toggle-section">
              <div className="toggle-left">
                <TrendingUp size={20} />
                <span className="toggle-label">AI Recommendations</span>
                <label className="toggle-switch">
                  <input 
                    type="checkbox" 
                    checked={useML} 
                    onChange={e => setUseML(e.target.checked)}
                  />
                  <span className="toggle-slider"></span>
                </label>
              </div>
              {usedModelIndicator !== null && (
                <span className={`model-badge ${usedModelIndicator ? 'ml-active' : 'heuristic'}`}>
                  {usedModelIndicator ? '🤖 ML Active' : '📊 Rule-Based'}
                </span>
              )}
            </div>

            {/* Search Form */}
            <div className="search-form">
              <div className="input-row">
                <div className="input-group">
                  <label className="input-label">
                    <MapPin size={16} className="label-icon green" />
                    From
                  </label>
                  <input 
                    className="input-field"
                    value={origin} 
                    onChange={e => setOrigin(e.target.value)} 
                    placeholder="e.g. Islamabad"
                  />
                </div>

                <div className="input-group">
                  <label className="input-label">
                    <MapPin size={16} className="label-icon red" />
                    To
                  </label>
                  <input 
                    className="input-field"
                    value={destination} 
                    onChange={e => setDestination(e.target.value)} 
                    placeholder="e.g. Lahore"
                  />
                </div>
              </div>

              <div className="time-submit-row">
                <div className="input-group">
                  <label className="input-label">
                    <Clock size={16} className="label-icon blue" />
                    Preferred Time
                  </label>
                  <input 
                    type="time" 
                    className="input-field"
                    value={preferredTime} 
                    onChange={e => setPreferredTime(e.target.value)} 
                  />
                </div>
                
                <button 
                  disabled={loading} 
                  onClick={createTrip}
                  className="submit-btn"
                >
                  {loading ? (
                    <>
                      <span className="spinner"></span>
                      Searching...
                    </>
                  ) : (
                    'Get Routes'
                  )}
                </button>
              </div>

              {/* Mode Preferences */}
              <div className="mode-prefs">
                <label className="mode-label">Transportation Modes</label>
                <div className="mode-buttons">
                  {Object.keys(modePrefs).map(key => (
                    <button 
                      key={key} 
                      type="button" 
                      onClick={() => setModePrefs(prev => ({...prev, [key]: !prev[key]}))}
                      className={`mode-btn ${modePrefs[key] ? 'active' : ''}`}
                    >
                      {key.charAt(0).toUpperCase() + key.slice(1)}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Error */}
            {error && (
              <div className="error-alert">
                <p>{error}</p>
              </div>
            )}
          </div>
        </div>

        {/* Recommendations Section */}
        <section className="recommendations-section">
          <h2 className="section-title">
            <div className="title-accent"></div>
            Your Routes
          </h2>
          
          {loading && (
            <div className="loading-state">
              <div className="loading-spinner"></div>
              <p>Finding best routes...</p>
            </div>
          )}

          {!loading && recs.length === 0 && (
            <div className="empty-state">
              <MapPin size={64} className="empty-icon" />
              <p>Enter your trip details to see recommendations</p>
            </div>
          )}

          <div className="recommendations-grid">
            {recs.map((r, i) => (
              <div key={i} className={`rec-card mode-${r.mode.toLowerCase()}`}>
                
                <div className="rec-header">
                  <div className="header-bg-icon">
                    {getModeIcon(r.mode)}
                  </div>
                  <div className="header-content">
                    <div className="header-top">
                      {getModeIcon(r.mode)}
                      <span className="score-badge">
                        {Math.round(r.score * 100)}%
                      </span>
                    </div>
                    <h3 className="mode-title">{r.mode}</h3>
                  </div>
                </div>

                <div className="rec-body">
                  <div className="rec-detail">
                    <Clock size={20} className="detail-icon" />
                    <span>{formatTime(r.eta_minutes)}</span>
                  </div>
                  <div className="rec-detail">
                    <DollarSign size={20} className="detail-icon" />
                    <span>Rs {r.cost.toFixed(2)}</span>
                  </div>

                  <div className="rec-actions">
                    <button 
                      onClick={() => navigator.clipboard?.writeText(`${origin} → ${destination} via ${r.mode}`)}
                      className="action-btn secondary"
                    >
                      Copy
                    </button>
                    <button 
                      onClick={() => loadMapData(r)}
                      className="action-btn secondary"
                      disabled={loadingMap}
                    >
                      {loadingMap ? 'Loading...' : 'Map'}
                    </button>
                    <button 
                      onClick={() => setShowFeedback(r)}
                      className="action-btn primary"
                    >
                      Rate
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Feedback Modal */}
        {showFeedback && (
          <div className="modal-overlay" onClick={() => setShowFeedback(null)}>
            <div className="modal-content" onClick={e => e.stopPropagation()}>
              <h3 className="modal-title">Rate {showFeedback.mode}</h3>
              
              <div className="rating-section">
                <label className="modal-label">Your Rating</label>
                <div className="star-rating">
                  {[1,2,3,4,5].map(star => (
                    <button
                      key={star}
                      onClick={() => setRating(star)}
                      className="star-btn"
                    >
                      <Star 
                        size={40}
                        className={star <= rating ? 'star-filled' : 'star-empty'}
                        fill={star <= rating ? 'currentColor' : 'none'}
                      />
                    </button>
                  ))}
                </div>
              </div>

              <div className="comment-section">
                <label className="modal-label">Comments (optional)</label>
                <textarea 
                  className="comment-textarea"
                  rows="3"
                  value={comment}
                  onChange={e => setComment(e.target.value)}
                  placeholder="Share your experience..."
                />
              </div>

              <div className="modal-actions">
                <button 
                  onClick={() => setShowFeedback(null)}
                  className="modal-btn cancel"
                >
                  Cancel
                </button>
                <button 
                  onClick={() => submitFeedback(showFeedback)}
                  className="modal-btn submit"
                >
                  Submit
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Map Modal */}
        {showMap && selectedRoute && mapData && (
          <div className="modal-overlay" onClick={() => setShowMap(false)}>
            <div className="map-modal-content" onClick={e => e.stopPropagation()}>
              <div className="map-modal-header">
                <h3 className="modal-title">
                  {origin} → {destination} via {selectedRoute.mode}
                </h3>
                <button 
                  onClick={() => setShowMap(false)}
                  className="map-close-btn"
                >
                  ✕
                </button>
              </div>
              <div className="map-container" id="route-map">
                <div className="map-info-box">
                  <h4>🚗 {selectedRoute.mode}</h4>
                  <p><strong>From:</strong> {origin}</p>
                  <p><strong>To:</strong> {destination}</p>
                  <p><strong>Distance:</strong> {(mapData.distance / 1000).toFixed(2)} km</p>
                  <p><strong>ETA:</strong> {formatTime(mapData.eta_minutes)}</p>
                  <p><strong>Cost:</strong> Rs {mapData.cost.toFixed(2)}</p>
                </div>
                <iframe
                  className="map-iframe"
                  srcDoc={mapData.html}
                  title="Route Map"
                  sandbox="allow-scripts"
                />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}