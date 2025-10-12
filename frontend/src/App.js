import React, { useEffect, useState } from "react";
import "@/App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [config, setConfig] = useState({
    threshold: 75,
    threshold_mode: "manual",
    use_coin_specific_settings: false,
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
  const [coinSettings, setCoinSettings] = useState([]);
  const [fetchIntervals, setFetchIntervals] = useState({});

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
    loadCoinSettings();
    loadFetchIntervals();
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

  const loadCoinSettings = async () => {
    try {
      const res = await axios.get(`${API}/coin-settings`);
      setCoinSettings(res.data.coin_settings || []);
    } catch (e) {
      console.error("Coin ayarları yükleme hatası:", e);
    }
  };

  const saveCoinSettings = async () => {
    if (!adminToken) {
      setMessage("❌ Lütfen Admin Token girin!");
      return;
    }

    setLoading(true);
    setMessage("");
    try {
      await axios.post(`${API}/coin-settings`, {
        coin_settings: coinSettings
      }, {
        headers: { "x-admin-token": adminToken }
      });
      setMessage("✅ Coin ayarları kaydedildi!");
      await loadCoinSettings();
    } catch (e) {
      setMessage("❌ Kaydetme hatası: " + (e.response?.data?.detail || e.message));
    }
    setLoading(false);
  };

  const updateCoinSetting = (coin, field, value) => {
    setCoinSettings(prevSettings => 
      prevSettings.map(cs => 
        cs.coin === coin ? { ...cs, [field]: value } : cs
      )
    );
  };

  const addCoinToSettings = () => {
    if (!newCoin.trim()) {
      setMessage("⚠️ Lütfen coin sembolü girin");
      return;
    }

    const coinSymbol = newCoin.trim().toUpperCase();
    
    // Coin zaten var mı kontrol et
    if (coinSettings.some(cs => cs.coin === coinSymbol)) {
      setMessage("⚠️ Bu coin zaten listede");
      return;
    }

    // Yeni coin ekle (varsayılan değerlerle)
    const newCoinSetting = {
      coin: coinSymbol,
      timeframe: config.timeframe || "24h",
      threshold: parseFloat(config.threshold) || 4.0,
      threshold_mode: config.threshold_mode || "dynamic",
      active: true
    };

    setCoinSettings([...coinSettings, newCoinSetting]);
    setNewCoin("");
    setMessage(`✅ ${coinSymbol} eklendi - ayarları yapıp kaydedin`);
  };

  const removeCoinFromSettings = (coin) => {
    if (window.confirm(`${coin} coin'ini listeden kaldırmak istediğinize emin misiniz?`)) {
      setCoinSettings(coinSettings.filter(cs => cs.coin !== coin));
      setMessage(`✅ ${coin} listeden kaldırıldı - değişiklikleri kaydedin`);
    }
  };

  const loadFetchIntervals = async () => {
    try {
      const res = await axios.get(`${API}/fetch-intervals`);
      setFetchIntervals(res.data.fetch_intervals || {});
    } catch (e) {
      console.error("Fetch intervals yükleme hatası:", e);
    }
  };

  const saveFetchIntervals = async () => {
    if (!adminToken) {
      setMessage("❌ Lütfen Admin Token girin!");
      return;
    }

    setLoading(true);
    setMessage("");
    try {
      const response = await axios.post(`${API}/fetch-intervals`, {
        intervals: fetchIntervals
      }, {
        headers: { "x-admin-token": adminToken }
      });
      setMessage("✅ " + response.data.message);
    } catch (e) {
      setMessage("❌ Kaydetme hatası: " + (e.response?.data?.detail || e.message));
    }
    setLoading(false);
  };

  const restartBackend = async () => {
    if (!adminToken) {
      setMessage("❌ Lütfen Admin Token girin!");
      return;
    }

    if (!window.confirm("Backend'i yeniden başlatmak istediğinize emin misiniz? Bu işlem 5-10 saniye sürebilir.")) {
      return;
    }

    setLoading(true);
    setMessage("🔄 Backend yeniden başlatılıyor...");
    
    try {
      await axios.post(`${API}/restart`, {}, {
        headers: { "x-admin-token": adminToken },
        timeout: 30000
      });
      setMessage("✅ Backend başarıyla yeniden başlatıldı!");
      
      // 5 saniye sonra config'i yeniden yükle
      setTimeout(() => {
        loadConfig();
        loadCoinSettings();
        loadFetchIntervals();
        setMessage("✅ Ayarlar güncellendi!");
      }, 5000);
      
    } catch (e) {
      setMessage("⚠️ Backend restart edildi, sayfa yenileniyor...");
      setTimeout(() => window.location.reload(), 3000);
    }
    
    setLoading(false);
  };

  const updateFetchInterval = (timeframe, minutes) => {
    setFetchIntervals(prev => ({
      ...prev,
      [timeframe]: parseInt(minutes) || 1
    }));
  };

  const resetToDefaults = () => {
    const defaults = {
      "15m": 1,
      "1h": 2,
      "4h": 5,
      "12h": 10,
      "24h": 15,
      "7d": 30,
      "30d": 60
    };
    setFetchIntervals(defaults);
    setMessage("✅ Varsayılan değerler yüklendi");
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
        threshold_mode: config.threshold_mode,
        use_coin_specific_settings: config.use_coin_specific_settings,
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

  // Dashboard Component
  const DashboardSection = () => {
    const [dashData, setDashData] = useState(null);
    const [dashLoading, setDashLoading] = useState(true);

    useEffect(() => {
      loadDashboard();
      const interval = setInterval(loadDashboard, 60000);
      return () => clearInterval(interval);
    }, []);

    const loadDashboard = async () => {
      try {
        setDashLoading(true);
        const res = await axios.get(`${API}/performance-dashboard`);
        setDashData(res.data);
      } catch (e) {
        console.error("Dashboard yükleme hatası:", e);
      } finally {
        setDashLoading(false);
      }
    };

    if (dashLoading && !dashData) {
      return <div className="dashboard-loading"><p>📊 Dashboard yükleniyor...</p></div>;
    }

    if (!dashData || !dashData.summary) {
      return <div className="dashboard-error"><p>⚠️ Dashboard verisi yüklenemedi</p></div>;
    }

    const { summary, top_profitable, coin_performance } = dashData;

    return (
      <div className="dashboard-section">
        <div className="card">
          <h3>📊 Performance Dashboard</h3>
          
          <div className="stats-grid-simple">
            <div className="stat-card-simple">
              <div className="stat-label">Toplam Sinyal</div>
              <div className="stat-value">{summary.total_signals}</div>
            </div>
            <div className="stat-card-simple success">
              <div className="stat-label">Başarılı</div>
              <div className="stat-value">{summary.successful_signals}</div>
            </div>
            <div className="stat-card-simple failed">
              <div className="stat-label">Başarısız</div>
              <div className="stat-value">{summary.failed_signals}</div>
            </div>
            <div className="stat-card-simple pending">
              <div className="stat-label">Beklemede</div>
              <div className="stat-value">{summary.pending_signals}</div>
            </div>
            <div className="stat-card-simple rate">
              <div className="stat-label">Başarı Oranı</div>
              <div className="stat-value">{summary.success_rate}%</div>
            </div>
            <div className="stat-card-simple gain">
              <div className="stat-label">Max Kazanç</div>
              <div className="stat-value">{summary.max_gain}%</div>
            </div>
            <div className="stat-card-simple loss">
              <div className="stat-label">Max Kayıp</div>
              <div className="stat-value">{summary.max_loss}%</div>
            </div>
            <div className="stat-card-simple avg">
              <div className="stat-label">Ort. Getiri</div>
              <div className="stat-value">{summary.avg_reward}%</div>
            </div>
          </div>
        </div>

        {top_profitable && top_profitable.length > 0 && (
          <div className="card">
            <h3>🏆 Top 5 Kazançlı Sinyal</h3>
            <div className="dashboard-table">
              <table>
                <thead>
                  <tr>
                    <th>Coin</th>
                    <th>Yön</th>
                    <th>Kazanç %</th>
                    <th>Güvenilirlik</th>
                    <th>Tarih</th>
                  </tr>
                </thead>
                <tbody>
                  {top_profitable.map((sig, idx) => (
                    <tr key={idx}>
                      <td><strong>{sig.coin}</strong></td>
                      <td>
                        <span className={`signal-type ${sig.signal_type?.toLowerCase()}`}>
                          {sig.signal_type === 'LONG' ? '📈 LONG' : '📉 SHORT'}
                        </span>
                      </td>
                      <td className="gain-text">+{sig.reward}%</td>
                      <td>{sig.probability}%</td>
                      <td>{sig.created_at ? new Date(sig.created_at).toLocaleDateString('tr-TR') : '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {coin_performance && coin_performance.length > 0 && (
          <div className="card">
            <h3>🪙 Coin Performansı (Top 10)</h3>
            <div className="dashboard-table">
              <table>
                <thead>
                  <tr>
                    <th>Coin</th>
                    <th>Toplam Sinyal</th>
                    <th>Başarılı</th>
                    <th>Başarı Oranı</th>
                  </tr>
                </thead>
                <tbody>
                  {coin_performance.map((cp, idx) => (
                    <tr key={idx}>
                      <td><strong>{cp.coin}</strong></td>
                      <td>{cp.total_signals}</td>
                      <td>{cp.successful}</td>
                      <td>
                        <div className="progress-bar">
                          <div className="progress-fill" style={{ width: `${cp.success_rate}%` }}></div>
                          <span className="progress-text">{cp.success_rate}%</span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    );
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
        <button 
          className={`tab ${activeTab === 'dashboard' ? 'active' : ''}`}
          onClick={() => setActiveTab('dashboard')}
        >
          📈 Dashboard
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
                <label className="toggle-label">
                  <input
                    type="checkbox"
                    checked={config.use_coin_specific_settings}
                    onChange={(e) => setConfig({...config, use_coin_specific_settings: e.target.checked})}
                    className="toggle-checkbox"
                  />
                  <span className="toggle-text">
                    {config.use_coin_specific_settings ? '✅ Coin Başına Özel Ayarlar Aktif' : '⚙️ Global Ayarlar Aktif'}
                  </span>
                </label>
                {config.use_coin_specific_settings && (
                  <div className="info-box">
                    ⚙️ Coin başına özel ayarlar aktif — global ayarlar devre dışı bırakıldı.
                  </div>
                )}
              </div>

              <div className="form-group">
                <label>🎯 Eşik Tipi</label>
                <select
                  className="input"
                  value={config.threshold_mode}
                  onChange={(e) => setConfig({...config, threshold_mode: e.target.value})}
                  disabled={config.use_coin_specific_settings}
                >
                  <option value="manual">Manuel (Sabit Eşik)</option>
                  <option value="dynamic">Dinamik (Otomatik Eşik)</option>
                </select>
                <small>
                  {config.threshold_mode === 'dynamic' 
                    ? '🤖 Volatiliteye göre otomatik eşik hesaplanır' 
                    : '👤 Manuel olarak belirlediğiniz eşik kullanılır'}
                </small>
              </div>

              <div className="form-group">
                <label>Eşik Değeri (%)  {config.threshold_mode === 'dynamic' && '(Referans)'}</label>
                <input
                  type="number"
                  className="input"
                  value={config.threshold}
                  onChange={(e) => setConfig({...config, threshold: e.target.value})}
                  min="0"
                  max="100"
                  disabled={config.threshold_mode === 'dynamic' || config.use_coin_specific_settings}
                />
                <small>
                  {config.threshold_mode === 'dynamic' 
                    ? '⚙️ Dinamik modda bu değer referans olarak kullanılır' 
                    : `Sadece %${config.threshold} ve üzeri sinyaller gönderilir`}
                </small>
              </div>

              <div className="form-group">
                <label>⏱ Zaman Dilimi</label>
                <select
                  className="input"
                  value={config.timeframe}
                  onChange={(e) => setConfig({...config, timeframe: e.target.value})}
                  disabled={config.use_coin_specific_settings}
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



            <div className="card">
              <h3>⏱ Veri Çekme Sıklığı</h3>
              <p className="card-description">
                Her timeframe için ne sıklıkla veri çekileceğini ayarlayın
              </p>

              <div className="intervals-grid">
                {Object.entries(fetchIntervals).map(([timeframe, minutes]) => (
                  <div key={timeframe} className="interval-item">
                    <label className="interval-label">
                      <span className="timeframe-badge">{timeframe}</span>
                      <input
                        type="number"
                        className="input-interval"
                        value={minutes}
                        onChange={(e) => updateFetchInterval(timeframe, e.target.value)}
                        min="1"
                        max="120"
                      />
                      <span className="interval-unit">dakika</span>
                    </label>
                  </div>
                ))}
              </div>

              <div className="interval-info">
                <p>💡 <strong>Önerilen Değerler:</strong></p>
                <ul>
                  <li>Kısa vade (15m, 1h): 1-2 dakika - Hızlı sinyaller</li>
                  <li>Orta vade (4h, 12h, 24h): 5-15 dakika - Dengeli</li>
                  <li>Uzun vade (7d, 30d): 30-60 dakika - API optimizasyonu</li>
                </ul>
              </div>

              <div className="button-group">
                <button className="btn btn-secondary" onClick={resetToDefaults}>
                  🔄 Varsayılanlara Dön
                </button>
                <button className="btn btn-primary" onClick={saveFetchIntervals} disabled={loading}>
                  {loading ? '⏳ Kaydediliyor...' : '💾 Sıklıkları Kaydet'}
                </button>
              </div>

              <div className="restart-section">
                <p className="restart-info">
                  ⚠️ <strong>Önemli:</strong> Interval veya coin ayarları değiştirdikten sonra, değişikliklerin uygulanması için backend'i yeniden başlatmanız gerekir.
                </p>
                <button className="btn btn-warning" onClick={restartBackend} disabled={loading}>
                  {loading ? '⏳ Başlatılıyor...' : '🔄 Backend\'i Yeniden Başlat'}
                </button>
              </div>
            </div>



            {config.use_coin_specific_settings && (
              <div className="card">
                <h3>⚙️ Coin Başına Özel Ayarlar</h3>
                <p className="card-description">
                  Her coin için ayrı timeframe, eşik ve mod ayarı yapabilirsiniz
                </p>

                {coinSettings.length > 0 && (
                  <div className="coin-status-summary">
                    <div className="status-item">
                      <span className="status-icon">✅</span>
                      <span>Aktif: <span className="status-count">{coinSettings.filter(cs => cs.active !== false).length}</span></span>
                    </div>
                    <div className="status-item">
                      <span className="status-icon">⏸️</span>
                      <span>Pasif: <span className="status-count">{coinSettings.filter(cs => cs.active === false).length}</span></span>
                    </div>
                    <div className="status-item">
                      <span className="status-icon">📊</span>
                      <span>Toplam: <span className="status-count">{coinSettings.length}</span></span>
                    </div>
                  </div>
                )}
                
                {coinSettings.length > 0 ? (
                <div className="coin-settings-table-wrapper">
                  <table className="coin-settings-table">
                    <thead>
                      <tr>
                        <th>Durum</th>
                        <th>Coin</th>
                        <th>Zaman Dilimi</th>
                        <th>Eşik (%)</th>
                        <th>Mod</th>
                        <th>İşlem</th>
                      </tr>
                    </thead>
                    <tbody>
                      {coinSettings.map((cs) => (
                        <tr key={cs.coin} className={!cs.active ? 'inactive-coin' : ''}>
                          <td className="status-cell">
                            <label className="toggle-switch-small">
                              <input
                                type="checkbox"
                                checked={cs.active !== false}
                                onChange={(e) => updateCoinSetting(cs.coin, 'active', e.target.checked)}
                              />
                              <span className="toggle-slider-small"></span>
                            </label>
                          </td>
                          <td className="coin-name-cell">
                            <strong>{cs.coin}</strong>
                            {!cs.active && <span className="inactive-badge">Pasif</span>}
                          </td>
                          <td>
                            <select
                              className="input-small"
                              value={cs.timeframe}
                              onChange={(e) => updateCoinSetting(cs.coin, 'timeframe', e.target.value)}
                            >
                              <option value="15m">15m</option>
                              <option value="1h">1h</option>
                              <option value="4h">4h</option>
                              <option value="12h">12h</option>
                              <option value="24h">24h</option>
                              <option value="7d">7d</option>
                              <option value="30d">30d</option>
                            </select>
                          </td>
                          <td>
                            <input
                              type="number"
                              className="input-small"
                              value={cs.threshold}
                              onChange={(e) => updateCoinSetting(cs.coin, 'threshold', parseFloat(e.target.value))}
                              min="0"
                              max="100"
                              step="0.5"
                              disabled={cs.threshold_mode === 'dynamic'}
                            />
                          </td>
                          <td>
                            <select
                              className="input-small"
                              value={cs.threshold_mode}
                              onChange={(e) => updateCoinSetting(cs.coin, 'threshold_mode', e.target.value)}
                            >
                              <option value="manual">Manuel</option>
                              <option value="dynamic">Dinamik</option>
                            </select>
                          </td>
                          <td>
                            <button
                              className="btn-delete-coin"
                              onClick={() => removeCoinFromSettings(cs.coin)}
                              title={`${cs.coin} sil`}
                            >
                              🗑️
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  <div className="add-coin-section">
                    <h4>➕ Yeni Coin Ekle</h4>
                    <div className="add-coin-input-group">
                      <input
                        type="text"
                        className="input"
                        placeholder="Örn: ADA, DOGE, XRP"
                        value={newCoin}
                        onChange={(e) => setNewCoin(e.target.value.toUpperCase())}
                        onKeyPress={(e) => {
                          if (e.key === 'Enter') {
                            addCoinToSettings();
                          }
                        }}
                      />
                      <button className="btn btn-success" onClick={addCoinToSettings}>
                        ➕ Ekle
                      </button>
                    </div>
                    <small className="help-text">
                      Yeni coin ekledikten sonra ayarlarını yapıp "Coin Ayarlarını Kaydet" butonuna basın
                    </small>
                  </div>
                </div>
              ) : (
                <p className="no-data">Coin ayarları yükleniyor...</p>
              )}

              <div className="button-group" style={{marginTop: '20px'}}>
                <button className="btn btn-primary" onClick={saveCoinSettings} disabled={loading}>
                  {loading ? '⏳ Kaydediliyor...' : '💾 Coin Ayarlarını Kaydet'}
                </button>
              </div>
            </div>
            )}

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

        {activeTab === 'dashboard' && (
          <DashboardSection />
        )}
      </div>

      <footer className="footer">
        <p>📊 MM TRADING BOT PRO v1.0 | CoinMarketCap & Telegram</p>
      </footer>
    </div>
  );
}

export default App;