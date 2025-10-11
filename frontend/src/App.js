import React, { useEffect, useState } from "react";
import "@/App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [config, setConfig] = useState({
    threshold: 75,
    selected_coins: [],
    max_concurrent_coins: 20
  });
  const [signals, setSignals] = useState([]);
  const [adminToken, setAdminToken] = useState("cryptobot_admin_2024");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [activeTab, setActiveTab] = useState("panel");
  const [newCoin, setNewCoin] = useState("");
  
  // Available coins - now dynamic
  const availableCoins = ["BTC", "ETH", "BNB", "SOL", "ADA", "XRP", "DOGE", "DOT", "MATIC", "AVAX", "LINK", "UNI", "ARB", "OP", "SUI"];

  useEffect(() => {
    loadConfig();
    loadSignals();
    const interval = setInterval(loadSignals, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const loadConfig = async () => {
    try {
      const res = await axios.get(`${API}/config`);
      setConfig(res.data);
    } catch (e) {
      console.error("Config yükleme hatası:", e);
    }
  };

  const loadSignals = async () => {
    try {
      const res = await axios.get(`${API}/signals?limit=20`);
      setSignals(res.data.signals || []);
    } catch (e) {
      console.error("Sinyal yükleme hatası:", e);
    }
  };

  const saveConfig = async () => {
    setLoading(true);
    setMessage("");
    try {
      await axios.post(`${API}/config`, {
        threshold: parseInt(config.threshold),
        selected_coins: config.selected_coins,
        max_concurrent_coins: parseInt(config.max_concurrent_coins)
      }, {
        headers: { "x-admin-token": adminToken }
      });
      setMessage("✅ Ayarlar kaydedildi!");
      await loadConfig();
    } catch (e) {
      setMessage("❌ Kaydetme hatası: " + (e.response?.data?.detail || e.message));
    }
    setLoading(false);
  };

  const testTelegram = async () => {
    setLoading(true);
    setMessage("");
    try {
      const res = await axios.post(`${API}/test_telegram`, {}, {
        headers: { "x-admin-token": adminToken }
      });
      setMessage("✅ " + res.data.detail);
    } catch (e) {
      setMessage("❌ Telegram testi başarısız: " + (e.response?.data?.detail || e.message));
    }
    setLoading(false);
  };

  const analyzeNow = async () => {
    setLoading(true);
    setMessage("");
    try {
      const res = await axios.post(`${API}/analyze_now`, {}, {
        headers: { "x-admin-token": adminToken }
      });
      setMessage("✅ " + res.data.message);
      setTimeout(loadSignals, 5000);
    } catch (e) {
      setMessage("❌ Analiz hatası: " + (e.response?.data?.detail || e.message));
    }
    setLoading(false);
  };

  const toggleCoin = (coin) => {
    const selected = config.selected_coins || [];
    const newSelected = selected.includes(coin)
      ? selected.filter(c => c !== coin)
      : [...selected, coin];
    setConfig({ ...config, selected_coins: newSelected });
  };

  const removeCoin = (coin) => {
    const selected = config.selected_coins || [];
    setConfig({ ...config, selected_coins: selected.filter(c => c !== coin) });
  };

  const addNewCoin = () => {
    const coin = newCoin.trim().toUpperCase();
    if (!coin) {
      setMessage("⚠️ Lütfen coin sembolü girin");
      return;
    }
    const selected = config.selected_coins || [];
    if (selected.includes(coin)) {
      setMessage("⚠️ Bu coin zaten listede");
      return;
    }
    setConfig({ ...config, selected_coins: [...selected, coin] });
    setNewCoin("");
    setMessage("✅ " + coin + " eklendi");
  };

  return (
    <div className="app-container">
      <header className="header">
        <h1>📊 MM TRADING BOT PRO</h1>
        <p className="subtitle">CoinMarketCap & Telegram Entegrasyonlu</p>
      </header>

      <div className="tabs">
        <button 
          className={`tab ${activeTab === 'panel' ? 'active' : ''}`}
          onClick={() => setActiveTab('panel')}
        >
          ⚙️ Panel
        </button>
        <button 
          className={`tab ${activeTab === 'signals' ? 'active' : ''}`}
          onClick={() => setActiveTab('signals')}
        >
          📊 Sinyaller
        </button>
      </div>

      <div className="content">
        {activeTab === 'panel' && (
          <div className="panel-section">
            <div className="card">
              <h3>🔐 Admin Token</h3>
              <input
                type="password"
                className="input"
                value={adminToken}
                onChange={(e) => setAdminToken(e.target.value)}
                placeholder="Admin token girin"
              />
            </div>

            <div className="card">
              <h3>📈 Sinyal Ayarları</h3>
              <div className="form-group">
                <label>Eşik Değeri (%)</label>
                <input
                  type="number"
                  className="input"
                  value={config.threshold}
                  onChange={(e) => setConfig({...config, threshold: e.target.value})}
                  min="0"
                  max="100"
                />
                <small>Sadece %{config.threshold} ve üzeri sinyaller gönderilir</small>
              </div>

              <div className="form-group">
                <label>Maksimum Eşzamanlı Coin</label>
                <input
                  type="number"
                  className="input"
                  value={config.max_concurrent_coins}
                  onChange={(e) => setConfig({...config, max_concurrent_coins: e.target.value})}
                  min="1"
                  max="50"
                />
              </div>
            </div>

            <div className="card">
              <h3>🪙 Coin Seçimi ({config.selected_coins?.length || 0})</h3>
              <div className="coin-grid">
                {availableCoins.map(coin => (
                  <button
                    key={coin}
                    className={`coin-btn ${config.selected_coins?.includes(coin) ? 'selected' : ''}`}
                    onClick={() => toggleCoin(coin)}
                  >
                    {coin}
                  </button>
                ))}
              </div>
            </div>

            <div className="button-group">
              <button className="btn btn-primary" onClick={saveConfig} disabled={loading}>
                {loading ? '⏳ Kaydediliyor...' : '💾 Ayarları Kaydet'}
              </button>
              <button className="btn btn-secondary" onClick={testTelegram} disabled={loading}>
                {loading ? '⏳ Test ediliyor...' : '📱 Telegram Test'}
              </button>
              <button className="btn btn-success" onClick={analyzeNow} disabled={loading}>
                {loading ? '⏳ Analiz ediliyor...' : '🔍 Şimdi Analiz Et'}
              </button>
            </div>

            {message && (
              <div className={`message ${message.includes('✅') ? 'success' : 'error'}`}>
                {message}
              </div>
            )}
          </div>
        )}

        {activeTab === 'signals' && (
          <div className="signals-section">
            <div className="card">
              <div className="signals-header">
                <h3>📊 Son Sinyaller</h3>
                <button className="btn btn-small" onClick={loadSignals}>🔄 Yenile</button>
              </div>
              
              {signals.length === 0 ? (
                <p className="no-data">Henüz sinyal yok. Bot otomatik olarak her 60 saniyede analiz yapıyor.</p>
              ) : (
                <div className="signals-list">
                  {signals.map(signal => (
                    <div key={signal.id} className="signal-card">
                      <div className="signal-header">
                        <span className="signal-coin">{signal.coin}</span>
                        <span className={`signal-type ${signal.signal_type?.toLowerCase()}`}>
                          {signal.signal_type === 'LONG' ? '📈 LONG' : '📉 SHORT'}
                        </span>
                      </div>
                      <div className="signal-body">
                        <div className="signal-row">
                          <span>Güvenilirlik:</span>
                          <strong>{signal.probability?.toFixed(2)}%</strong>
                        </div>
                        <div className="signal-row">
                          <span>Eşik:</span>
                          <span>{signal.threshold_used}%</span>
                        </div>
                        <div className="signal-row">
                          <span>Zaman Dilimi:</span>
                          <span>{signal.timeframe}</span>
                        </div>
                        {signal.features?.price && (
                          <div className="signal-row">
                            <span>Fiyat:</span>
                            <strong>${signal.features.price?.toFixed(4)}</strong>
                          </div>
                        )}
                        <div className="signal-time">
                          {new Date(signal.created_at).toLocaleString('tr-TR')}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <footer className="footer">
        <p>🤖 Kripto Bot v1.0 | CoinMarketCap & Telegram</p>
      </footer>
    </div>
  );
}

export default App;