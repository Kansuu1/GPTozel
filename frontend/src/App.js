import React, { useEffect, useState } from "react";
import "@/App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [config, setConfig] = useState({
    threshold: 75,
    selected_coins: [],
    timeframe: "24h",
    max_concurrent_coins: 20,
    cmc_api_key: ""
  });
  const [signals, setSignals] = useState([]);
  const [adminToken, setAdminToken] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [activeTab, setActiveTab] = useState("panel");
  const [newCoin, setNewCoin] = useState("");

  // Load admin token from localStorage on mount
  useEffect(() => {
    const loadToken = () => {
      try {
        const savedToken = localStorage.getItem("admin_token");
        if (savedToken) {
          setAdminToken(savedToken);
          console.log("✅ Token yüklendi:", savedToken);
        } else {
          console.log("⚠️ localStorage'da token yok");
        }
      } catch (e) {
        console.error("Token yükleme hatası:", e);
      }
    };
    loadToken();
  }, []);
  
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
      // API key maskelenmiş gelirse göster
      if (res.data.cmc_api_key === "*****") {
        res.data.cmc_api_key = "*****";
      }
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
    if (!adminToken) {
      setMessage("❌ Lütfen Admin Token girin!");
      return;
    }
    
    setLoading(true);
    setMessage("");
    try {
      // Save token to localStorage
      localStorage.setItem("admin_token", adminToken);
      
      await axios.post(`${API}/config`, {
        threshold: parseInt(config.threshold),
        selected_coins: config.selected_coins,
        timeframe: config.timeframe,
        max_concurrent_coins: parseInt(config.max_concurrent_coins),
        cmc_api_key: config.cmc_api_key || undefined
      }, {
        headers: { "x-admin-token": adminToken }
      });
      setMessage("✅ Ayarlar kaydedildi!");
      await loadConfig();
    } catch (e) {
      if (e.response?.status === 403) {
        setMessage("❌ Yanlış admin token!");
        localStorage.removeItem("admin_token");
      } else {
        setMessage("❌ Kaydetme hatası: " + (e.response?.data?.detail || e.message));
      }
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

  const deleteSignal = async (signalId) => {
    if (!window.confirm("Bu sinyali silmek istediğinizden emin misiniz?")) return;
    
    try {
      await axios.delete(`${API}/signals/${signalId}`, {
        headers: { "x-admin-token": adminToken }
      });
      setMessage("✅ Sinyal silindi");
      loadSignals();
    } catch (e) {
      setMessage("❌ Silme hatası: " + (e.response?.data?.detail || e.message));
    }
  };

  const clearAllSignals = async () => {
    if (!window.confirm("TÜM SİNYALLERİ silmek istediğinizden emin misiniz? Bu işlem geri alınamaz!")) return;
    
    setLoading(true);
    try {
      const res = await axios.post(`${API}/signals/clear_all`, {}, {
        headers: { "x-admin-token": adminToken }
      });
      setMessage("✅ " + res.data.message);
      loadSignals();
    } catch (e) {
      setMessage("❌ Silme hatası: " + (e.response?.data?.detail || e.message));
    }
    setLoading(false);
  };

  const clearFailedSignals = async () => {
    if (!window.confirm("Başarısız sinyalleri silmek istediğinizden emin misiniz?")) return;
    
    setLoading(true);
    try {
      const res = await axios.post(`${API}/signals/clear_failed`, {}, {
        headers: { "x-admin-token": adminToken }
      });
      setMessage("✅ " + res.data.message);
      loadSignals();
    } catch (e) {
      setMessage("❌ Silme hatası: " + (e.response?.data?.detail || e.message));
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
              <h3>🔐 Yetkilendirme</h3>
              
              <div className="form-group">
                <label>Admin Token</label>
                <div className="token-input-group">
                  <input
                    type="password"
                    className="input"
                    value={adminToken}
                    onChange={(e) => setAdminToken(e.target.value)}
                    placeholder="Admin token (örn: mmkansu)"
                  />
                  {adminToken && (
                    <button 
                      className="btn btn-small btn-secondary"
                      onClick={() => {
                        localStorage.removeItem("admin_token");
                        setAdminToken("");
                        setMessage("🔓 Admin token temizlendi");
                      }}
                    >
                      🗑
                    </button>
                  )}
                </div>
                <small>
                  {adminToken ? "✅ Token kaydedildi" : "⚠️ İlk kullanımda token girin"}
                </small>
              </div>

              <div className="form-group">
                <label>📊 CoinMarketCap API Key</label>
                <div className="token-input-group">
                  <input
                    type="text"
                    className="input"
                    value={config.cmc_api_key || ""}
                    onChange={(e) => setConfig({...config, cmc_api_key: e.target.value})}
                    placeholder="API Key (örn: ad7e6f5c-...)"
                    readOnly={config.cmc_api_key === "*****"}
                  />
                  {config.cmc_api_key && config.cmc_api_key === "*****" && (
                    <button 
                      className="btn btn-small btn-warning"
                      onClick={() => setConfig({...config, cmc_api_key: ""})}
                    >
                      ✏️ Değiştir
                    </button>
                  )}
                  {config.cmc_api_key && config.cmc_api_key !== "*****" && (
                    <button 
                      className="btn btn-small btn-info"
                      onClick={() => {
                        const input = document.querySelector('input[placeholder*="API Key"]');
                        input.type = input.type === 'password' ? 'text' : 'password';
                      }}
                    >
                      👁
                    </button>
                  )}
                </div>
                <small>
                  {config.cmc_api_key === "*****" 
                    ? "🔒 Mevcut API Key kullanılıyor (Değiştirmek için ✏️ tıklayın)" 
                    : config.cmc_api_key 
                      ? "✅ API Key ayarlanacak" 
                      : "💡 CMC Pro plan için yeni API key girebilirsiniz"}
                </small>
              </div>
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
                <label>⏱ Zaman Dilimi</label>
                <select
                  className="input"
                  value={config.timeframe}
                  onChange={(e) => setConfig({...config, timeframe: e.target.value})}
                >
                  <option value="15m">15 Dakika (15m)</option>
                  <option value="1h">1 Saat (1h)</option>
                  <option value="4h">4 Saat (4h)</option>
                  <option value="12h">12 Saat (12h)</option>
                  <option value="24h">24 Saat (1 Gün)</option>
                  <option value="7d">7 Gün (1 Hafta)</option>
                  <option value="30d">30 Gün (1 Ay)</option>
                </select>
                <small>Seçilen zaman dilimine göre analiz yapılır</small>
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
              <h3>🪙 Coin Yönetimi</h3>
              
              <div className="add-coin-section">
                <label>Yeni Coin Ekle</label>
                <div className="add-coin-input">
                  <input
                    type="text"
                    className="input"
                    value={newCoin}
                    onChange={(e) => setNewCoin(e.target.value)}
                    placeholder="Örn: SHIB, PEPE, FLOKI"
                    onKeyPress={(e) => e.key === 'Enter' && addNewCoin()}
                  />
                  <button className="btn btn-add" onClick={addNewCoin}>
                    ➕ Ekle
                  </button>
                </div>
              </div>

              <div className="selected-coins-section">
                <label>Seçili Coinler ({config.selected_coins?.length || 0})</label>
                <div className="selected-coins-list">
                  {config.selected_coins && config.selected_coins.length > 0 ? (
                    config.selected_coins.map(coin => (
                      <div key={coin} className="selected-coin-item">
                        <span className="coin-name">{coin}</span>
                        <button 
                          className="remove-btn"
                          onClick={() => removeCoin(coin)}
                          title="Kaldır"
                        >
                          ✕
                        </button>
                      </div>
                    ))
                  ) : (
                    <p className="no-coins">Henüz coin seçilmedi. Aşağıdan coin ekleyin veya hızlı seçim yapın.</p>
                  )}
                </div>
              </div>

              <div className="quick-select-section">
                <label>Hızlı Seçim</label>
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
                <div className="signals-actions">
                  <button className="btn btn-small" onClick={loadSignals}>🔄 Yenile</button>
                  <button className="btn btn-small btn-danger" onClick={clearFailedSignals} disabled={loading}>
                    🗑 Başarısızları Sil
                  </button>
                  <button className="btn btn-small btn-danger-outline" onClick={clearAllSignals} disabled={loading}>
                    ⚠️ Tümünü Sil
                  </button>
                </div>
              </div>
              
              {signals.length === 0 ? (
                <p className="no-data">Henüz sinyal yok. Bot otomatik olarak her 60 saniyede analiz yapıyor.</p>
              ) : (
                <div className="signals-list">
                  {signals.map(signal => (
                    <div key={signal.id} className="signal-card">
                      <div className="signal-header">
                        <div className="signal-header-left">
                          <span className="signal-coin">{signal.coin}</span>
                          <span className={`signal-type ${signal.signal_type?.toLowerCase()}`}>
                            {signal.signal_type === 'LONG' ? '📈 LONG' : '📉 SHORT'}
                          </span>
                        </div>
                        <button 
                          className="delete-signal-btn"
                          onClick={() => deleteSignal(signal.id)}
                          title="Sinyali sil"
                        >
                          🗑
                        </button>
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
                            <span>Giriş Fiyatı:</span>
                            <strong>${signal.features.price?.toFixed(4)}</strong>
                          </div>
                        )}
                        {signal.tp && (
                          <div className="signal-row tp">
                            <span>🎯 Take Profit:</span>
                            <strong className="tp-value">${signal.tp?.toFixed(4)}</strong>
                          </div>
                        )}
                        {signal.stop_loss && (
                          <div className="signal-row sl">
                            <span>🛡 Stop Loss:</span>
                            <strong className="sl-value">${signal.stop_loss?.toFixed(4)}</strong>
                          </div>
                        )}
                        <div className="signal-time">
                          {signal.created_at ? new Date(signal.created_at).toLocaleString('tr-TR', {
                            timeZone: 'Europe/Istanbul',
                            year: 'numeric',
                            month: '2-digit',
                            day: '2-digit',
                            hour: '2-digit',
                            minute: '2-digit'
                          }) : 'Bilinmiyor'}
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
        <p>📊 MM TRADING BOT PRO v1.0 | CoinMarketCap & Telegram</p>
      </footer>
    </div>
  );
}

export default App;