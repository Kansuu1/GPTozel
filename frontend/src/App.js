import React, { useEffect, useState } from "react";
import "@/App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Fiyat formatlama fonksiyonu (küçük sayılar için)
function formatPrice(price) {
  if (!price || price === 0) return "$0.0000";
  
  // Çok küçük sayılar için bilimsel notasyon
  if (price < 0.000001) {
    return `$${price.toExponential(4)}`;
  }
  
  // 0.0001'den küçükse 8 ondalık
  if (price < 0.0001) {
    return `$${price.toFixed(8)}`;
  }
  
  // 0.01'den küçükse 6 ondalık
  if (price < 0.01) {
    return `$${price.toFixed(6)}`;
  }
  
  // 1'den küçükse 4 ondalık
  if (price < 1) {
    return `$${price.toFixed(4)}`;
  }
  
  // 1'den büyükse 2 ondalık
  return `$${price.toFixed(2)}`;
}

function App() {
  const [config, setConfig] = useState({
    threshold: 75,
    threshold_mode: "manual",
    use_coin_specific_settings: true, // Coin başına özel ayarlar varsayılan olarak aktif
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
  const [selectedCoinFilter, setSelectedCoinFilter] = useState(""); // Sinyal filtreleme için
  
  // Signal Performance Tracking
  const [selectedStatus, setSelectedStatus] = useState("all"); // all | active | hit_tp | hit_sl | expired
  const [selectedCoins, setSelectedCoins] = useState([]); // Multi-select coins
  const [signalStats, setSignalStats] = useState(null);
  const [coinSettings, setCoinSettings] = useState([]);
  const [fetchIntervals, setFetchIntervals] = useState({});
  const [indicators, setIndicators] = useState({});  // RSI/MACD göstergeleri
  const [alarms, setAlarms] = useState([]);  // Fiyat alarmları
  const [alarmsActive, setAlarmsActive] = useState(() => {
    // localStorage'dan alarm durumunu yükle
    const saved = localStorage.getItem('alarmsActive');
    return saved ? JSON.parse(saved) : true; // Varsayılan: aktif
  });
  const [chartData, setChartData] = useState(null);  // Signal grafik verileri
  const [telegramConfig, setTelegramConfig] = useState({
    telegram_token: "",
    telegram_chat_id: ""
  });
  const [manualPrices, setManualPrices] = useState({});  // Manuel fiyat override'ları
  const [newManualPrice, setNewManualPrice] = useState({ coin: "", price: "" });
  const [darkMode, setDarkMode] = useState(() => {
    // localStorage'dan dark mode tercihini yükle
    const saved = localStorage.getItem('darkMode');
    return saved ? JSON.parse(saved) : false;
  });
  const [coinDropdownOpen, setCoinDropdownOpen] = useState(false); // Coin dropdown açık/kapalı
  const [signalLimit, setSignalLimit] = useState(100); // Gösterilecek sinyal sayısı
  const [historicalDays, setHistoricalDays] = useState(30); // Geçmiş veri gün sayısı
  const [historicalInterval, setHistoricalInterval] = useState('1h'); // Geçmiş veri interval
  const [historicalImportResult, setHistoricalImportResult] = useState(null); // İçe aktarma sonucu
  const [globalFeatureFlag, setGlobalFeatureFlag] = useState(false); // Global feature flag (master switch)

  // Dark mode değiştiğinde localStorage'a kaydet ve body'ye class ekle
  useEffect(() => {
    localStorage.setItem('darkMode', JSON.stringify(darkMode));
    if (darkMode) {
      document.body.classList.add('dark-mode');
    } else {
      document.body.classList.remove('dark-mode');
    }
  }, [darkMode]);

  // Alarms active durumunu localStorage'a kaydet
  useEffect(() => {
    localStorage.setItem('alarmsActive', JSON.stringify(alarmsActive));
  }, [alarmsActive]);
  
  // Signal tracking - her 5 dakikada bir otomatik kontrol
  useEffect(() => {
    if (activeTab === 'signals' && adminToken) {
      loadSignalStats();
      
      // İlk tracking
      trackSignals();
      
      // 5 dakikada bir otomatik tracking
      const interval = setInterval(() => {
        trackSignals();
      }, 5 * 60 * 1000); // 5 dakika
      
      return () => clearInterval(interval);
    }
  }, [activeTab, adminToken]);
  
  // Filtre değiştiğinde sinyalleri yeniden yükle
  useEffect(() => {
    if (activeTab === 'signals') {
      loadSignals();
    }
  }, [selectedStatus, selectedCoins, signalLimit, activeTab]);

  // Dropdown dışına tıklanınca kapat
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (coinDropdownOpen && !event.target.closest('.coin-dropdown-container')) {
        setCoinDropdownOpen(false);
      }
      
      // Signal management menu
      const signalMenu = document.getElementById('signal-management-menu');
      if (signalMenu && signalMenu.style.display === 'block' && 
          !event.target.closest('#signal-management-menu') && 
          !event.target.textContent.includes('Yönet')) {
        signalMenu.style.display = 'none';
      }
    };
    
    if (coinDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    } else {
      document.addEventListener('mousedown', handleClickOutside);
    }
    
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [coinDropdownOpen]);

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
    loadAlarms();
    loadChartData();
    loadManualPrices();
    
    // 10 dakikada bir yenile
    const signalInterval = setInterval(loadSignals, 600000); // 10 minutes
    const coinInterval = setInterval(loadCoinSettings, 600000); // 10 minutes
    const alarmInterval = setInterval(loadAlarms, 600000); // 10 minutes
    
    return () => {
      clearInterval(signalInterval);
      clearInterval(coinInterval);
      clearInterval(alarmInterval);
    };
  }, []);

  const loadConfig = async () => {
    try {
      const res = await axios.get(`${API}/config`);
      // API key maskelenmiş gelirse göster
      if (res.data.cmc_api_key === "*****") {
        res.data.cmc_api_key = "*****";
      }
      setConfig(res.data);
      
      // Telegram ayarlarını da yükle
      setTelegramConfig({
        telegram_token: res.data.telegram_token || "",
        telegram_chat_id: res.data.telegram_chat_id || ""
      });
    } catch (e) {
      console.error("Config yükleme hatası:", e);
    }
  };

  const loadSignals = async (coin = null) => {
    try {
      // Filtreleri oluştur
      let url = `${API}/signals?limit=${signalLimit}`;
      
      // Status filtresi
      if (selectedStatus && selectedStatus !== 'all') {
        url += `&status=${selectedStatus}`;
      }
      
      // Coin filtresi
      if (selectedCoins.length > 0) {
        url += `&coins=${selectedCoins.join(',')}`;
      } else if (coin) {
        url += `&coin=${coin}`;
      } else if (selectedCoinFilter) {
        url += `&coin=${selectedCoinFilter}`;
      }
      
      const res = await axios.get(url);
      setSignals(res.data.signals || []);
    } catch (e) {
      console.error("Sinyal yükleme hatası:", e);
    }
  };
  
  const loadSignalStats = async () => {
    try {
      const res = await axios.get(`${API}/signals/statistics`);
      setSignalStats(res.data);
    } catch (e) {
      console.error("İstatistik yükleme hatası:", e);
    }
  };
  
  const trackSignals = async () => {
    if (!adminToken) {
      setMessage("❌ Admin token gerekli!");
      return;
    }
    
    setLoading(true);
    try {
      const res = await axios.post(`${API}/signals/track`, {}, {
        headers: { "x-admin-token": adminToken }
      });
      setMessage(`✅ ${res.data.message}`);
      await loadSignals();
      await loadSignalStats();
    } catch (e) {
      setMessage("❌ Tracking hatası: " + (e.response?.data?.detail || e.message));
    }
    setLoading(false);
  };
  
  const deleteSingleSignal = async (signalId) => {
    if (!adminToken) {
      setMessage("❌ Admin token gerekli!");
      return;
    }
    
    if (!window.confirm("Bu sinyali silmek istediğinizden emin misiniz?")) {
      return;
    }
    
    try {
      await axios.delete(`${API}/signals/${signalId}`, {
        headers: { "x-admin-token": adminToken }
      });
      setMessage("✅ Sinyal silindi!");
      await loadSignals();
      await loadSignalStats();
    } catch (e) {
      setMessage("❌ Silme hatası: " + (e.response?.data?.detail || e.message));
    }
  };

  const loadCoinSettings = async () => {
    try {
      const res = await axios.get(`${API}/coin-settings`);
      const settings = res.data.coin_settings || [];
      setCoinSettings(settings);
      
      // SADECE ACTIVE coinler için göstergeleri yükle
      const activeCoins = settings.filter(cs => cs.status === 'active');
      activeCoins.forEach(cs => {
        loadIndicators(cs.coin);
      });
      
      // Passive coinlerin indicator state'ini temizle
      const passiveCoins = settings.filter(cs => cs.status === 'passive');
      setIndicators(prev => {
        const newIndicators = {...prev};
        passiveCoins.forEach(cs => {
          delete newIndicators[cs.coin];
        });
        return newIndicators;
      });
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

  const saveSingleCoinSetting = async (coin) => {
    if (!adminToken) {
      setMessage("❌ Lütfen Admin Token girin!");
      return;
    }

    const coinSetting = coinSettings.find(cs => cs.coin === coin);
    if (!coinSetting) {
      setMessage("❌ Coin ayarları bulunamadı!");
      return;
    }

    setLoading(true);
    setMessage("");
    try {
      await axios.post(`${API}/update-coin`, coinSetting, {
        headers: { "x-admin-token": adminToken }
      });
      setMessage(`✅ ${coin} ayarları kaydedildi!`);
      await loadCoinSettings();
      
      // 3 saniye sonra mesajı temizle
      setTimeout(() => setMessage(""), 3000);
    } catch (e) {
      setMessage(`❌ ${coin} kaydetme hatası: ` + (e.response?.data?.detail || e.message));
    }
    setLoading(false);
  };

  const updateCoinSetting = async (coin, field, value) => {
    setCoinSettings(prevSettings => 
      prevSettings.map(cs => {
        if (cs.coin === coin) {
          const updated = { ...cs, [field]: value };
          
          // Status değişikliğinde active alanını da güncelle (backward compatibility)
          if (field === 'status') {
            updated.active = value === 'active';
          }
          
          return updated;
        }
        return cs;
      })
    );

    // Dinamik moda geçildiğinde veya timeframe değiştiğinde threshold'u hesapla
    const coinSetting = coinSettings.find(cs => cs.coin === coin);
    
    if (field === 'threshold_mode' && value === 'dynamic') {
      // Modu dinamik yaptık, threshold hesapla
      await updateDynamicThreshold(coin, coinSetting?.timeframe || '24h');
    } else if (field === 'timeframe' && coinSetting?.threshold_mode === 'dynamic') {
      // Timeframe değişti ve mod dinamik, threshold hesapla
      await updateDynamicThreshold(coin, value);
    }
  };

  const toggleAllCoins = async () => {
    // Tüm coinlerin aktif mi kontrol et
    const allActive = coinSettings.every(cs => cs.status === 'active');
    const newStatus = allActive ? 'passive' : 'active';
    
    // Tüm coinleri yeni status'e çevir
    setCoinSettings(prevSettings => 
      prevSettings.map(cs => ({
        ...cs,
        status: newStatus,
        active: newStatus === 'active'
      }))
    );
    
    setMessage(allActive ? '⏸️ Tüm coinler pasif yapıldı' : '✅ Tüm coinler aktif yapıldı');
  };

  const toggleGlobalFeatureFlag = async () => {
    const newValue = !globalFeatureFlag;
    setGlobalFeatureFlag(newValue);
    
    try {
      await axios.post(`${API}/feature-flags/toggle`, {
        flag: 'enable_candle_interval_analysis',
        enabled: newValue
      }, {
        headers: { "x-admin-token": adminToken }
      });
      
      setMessage(newValue ? '🔧 Candle Interval Analysis AÇILDI' : '🔧 Candle Interval Analysis KAPATILDI');
    } catch (e) {
      setMessage("❌ Feature flag hatası: " + (e.response?.data?.detail || e.message));
      setGlobalFeatureFlag(!newValue); // Rollback
    }
  };

  const toggleCoinFeatureFlag = async (coin) => {
    if (!adminToken) {
      setMessage("❌ Lütfen Admin Token girin!");
      return;
    }
    
    const currentSetting = coinSettings.find(cs => cs.coin === coin);
    const newValue = !currentSetting?.candle_analysis_enabled;
    
    // State'i güncelle ve güncel state'i al
    setCoinSettings(prevSettings => {
      const updatedSettings = prevSettings.map(cs =>
        cs.coin === coin
          ? { ...cs, candle_analysis_enabled: newValue }
          : cs
      );
      
      // State güncellendikten hemen sonra backend'e kaydet
      const updatedCoinSetting = updatedSettings.find(cs => cs.coin === coin);
      
      // Backend'e kaydet (async)
      setLoading(true);
      axios.post(`${API}/coin-settings`, {
        coin_settings: [updatedCoinSetting]
      }, {
        headers: { "x-admin-token": adminToken }
      }).then(() => {
        setMessage(newValue ? `🟢 ${coin}: Candle analizi aktif` : `🔴 ${coin}: Candle analizi pasif`);
        setLoading(false);
      }).catch(e => {
        setMessage(`❌ ${coin}: Kaydetme hatası - ${e.response?.data?.detail || e.message}`);
        setLoading(false);
        // Rollback
        setCoinSettings(prevSettings =>
          prevSettings.map(cs =>
            cs.coin === coin
              ? { ...cs, candle_analysis_enabled: !newValue }
              : cs
          )
        );
      });
      
      return updatedSettings;
    });
  };

  const updateDynamicThreshold = async (coin, timeframe) => {
    try {
      const res = await axios.get(`${API}/calculate-threshold`, {
        params: { coin, timeframe }
      });
      
      if (res.data.threshold) {
        // Hesaplanan threshold'u coin setting'e uygula
        setCoinSettings(prevSettings => 
          prevSettings.map(cs => 
            cs.coin === coin ? { ...cs, threshold: res.data.threshold } : cs
          )
        );
      }
    } catch (e) {
      console.error('Threshold hesaplama hatası:', e);
    }
  };

  const addCoinToSettings = async () => {
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

    const timeframe = config.timeframe || "24h";
    const thresholdMode = config.threshold_mode || "dynamic";
    let threshold = parseFloat(config.threshold) || 4.0;

    // Eğer dinamik modsa, threshold'u hesapla
    if (thresholdMode === "dynamic") {
      setMessage(`⏳ ${coinSymbol} için dinamik eşik hesaplanıyor...`);
      try {
        const res = await axios.get(`${API}/calculate-threshold`, {
          params: { coin: coinSymbol, timeframe }
        });
        if (res.data.threshold) {
          threshold = res.data.threshold;
        }
      } catch (e) {
        console.error('Threshold hesaplama hatası:', e);
      }
    }

    // Yeni coin ekle
    const newCoinSetting = {
      coin: coinSymbol,
      timeframe: timeframe,
      threshold: threshold,
      threshold_mode: thresholdMode,
      active: true,
      fetch_interval_minutes: 2,
      status: "active"
    };

    setCoinSettings([...coinSettings, newCoinSetting]);
    setNewCoin("");
    setMessage(`✅ ${coinSymbol} eklendi (Eşik: ${threshold}%, Interval: 2dk) - ayarları yapıp kaydedin`);
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

  const toggleAlarms = async (enabled) => {
    if (!adminToken) {
      setMessage("❌ Lütfen Admin Token girin!");
      setAlarmsActive(!enabled); // Geri al
      return;
    }

    try {
      await axios.post(`${API}/alarms/toggle`, {
        enabled: enabled
      }, {
        headers: { "x-admin-token": adminToken }
      });
      
      const statusText = enabled ? 'aktif' : 'pasif';
      setMessage(`✅ Alarm sistemi ${statusText}`);
      console.log(`🔔 Alarm sistemi ${statusText}`);
    } catch (e) {
      setMessage("❌ Alarm toggle hatası: " + (e.response?.data?.detail || e.message));
      setAlarmsActive(!enabled); // Hata durumunda geri al
    }
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

  // Yeni fonksiyonlar: Alarmlar, Göstergeler, Grafik verileri
  const loadAlarms = async () => {
    try {
      const res = await axios.get(`${API}/alarms`);
      setAlarms(res.data.alarms || []);
      
      // Backend'den alarm durumunu yükle
      if (res.data.alarms_enabled !== undefined) {
        setAlarmsActive(res.data.alarms_enabled);
      }
    } catch (e) {
      console.error("Alarmlar yükleme hatası:", e);
    }
  };

  const loadIndicators = async (symbol) => {
    try {
      const res = await axios.get(`${API}/indicators/${symbol}`);
      setIndicators(prev => ({
        ...prev,
        [symbol]: res.data.indicators
      }));
    } catch (e) {
      console.error(`[${symbol}] Göstergeler yükleme hatası:`, e);
    }
  };

  const loadChartData = async (days = 7) => {
    try {
      const res = await axios.get(`${API}/signals/chart?days=${days}`);
      setChartData(res.data);
    } catch (e) {
      console.error("Grafik verileri yükleme hatası:", e);
    }
  };

  const loadManualPrices = async () => {
    try {
      const res = await axios.get(`${API}/manual-prices`);
      setManualPrices(res.data.manual_prices || {});
    } catch (e) {
      console.error("Manuel fiyatlar yükleme hatası:", e);
    }
  };

  const addManualPrice = async () => {
    if (!adminToken) {
      setMessage("❌ Lütfen Admin Token girin!");
      return;
    }

    if (!newManualPrice.coin || !newManualPrice.price) {
      setMessage("❌ Lütfen coin ve fiyat girin!");
      return;
    }

    const price = parseFloat(newManualPrice.price);
    if (isNaN(price) || price <= 0) {
      setMessage("❌ Geçerli bir fiyat girin!");
      return;
    }

    setLoading(true);
    try {
      await axios.post(`${API}/manual-price?coin=${newManualPrice.coin.toUpperCase()}&price=${price}`, {}, {
        headers: { "x-admin-token": adminToken }
      });
      setMessage(`✅ ${newManualPrice.coin.toUpperCase()} için manuel fiyat belirlendi: $${price}`);
      setNewManualPrice({ coin: "", price: "" });
      await loadManualPrices();
    } catch (e) {
      setMessage("❌ Hata: " + (e.response?.data?.detail || e.message));
    }
    setLoading(false);
  };

  const removeManualPrice = async (coin) => {
    if (!adminToken) {
      setMessage("❌ Lütfen Admin Token girin!");
      return;
    }

    setLoading(true);
    try {
      await axios.delete(`${API}/manual-price/${coin}`, {
        headers: { "x-admin-token": adminToken }
      });
      setMessage(`✅ ${coin} manuel fiyatı kaldırıldı`);
      await loadManualPrices();
    } catch (e) {
      setMessage("❌ Hata: " + (e.response?.data?.detail || e.message));
    }
    setLoading(false);
  };

  const saveTelegramConfig = async () => {
    if (!adminToken) {
      setMessage("❌ Lütfen Admin Token girin!");
      return;
    }

    if (!telegramConfig.telegram_token || !telegramConfig.telegram_chat_id) {
      setMessage("❌ Lütfen tüm alanları doldurun!");
      return;
    }

    setLoading(true);
    setMessage("");
    try {
      await axios.post(`${API}/config`, {
        telegram_token: telegramConfig.telegram_token,
        telegram_chat_id: telegramConfig.telegram_chat_id
      }, {
        headers: { "x-admin-token": adminToken }
      });
      setMessage("✅ Telegram ayarları kaydedildi!");
      await loadConfig();
    } catch (e) {
      setMessage("❌ Kaydetme hatası: " + (e.response?.data?.detail || e.message));
    }
    setLoading(false);
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
    if (!window.confirm("Başarısız ve süresi dolmuş sinyalleri silmek istediğinizden emin misiniz?")) return;
    
    setLoading(true);
    try {
      // Yeni bulk delete endpoint'ini kullan
      const res = await axios.delete(`${API}/signals/bulk?status=hit_sl,expired`, {
        headers: { "x-admin-token": adminToken }
      });
      setMessage(`✅ ${res.data.deleted_count} sinyal silindi`);
      loadSignals();
      loadSignalStats();
    } catch (e) {
      setMessage("❌ Silme hatası: " + (e.response?.data?.detail || e.message));
    }
    setLoading(false);
  };

  const exportSignals = async (type = 'all') => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/signals/export?type=${type}`, {
        responseType: 'json'
      });
      
      // JSON'u dosya olarak indir
      const data = response.data;
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      
      // Dosya adı
      const date = new Date().toISOString().split('T')[0].replace(/-/g, '');
      a.download = `signals_${type}_${date}.json`;
      
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      
      setMessage(`✅ ${data.count} sinyal indirildi (${type})`);
      
      // Dropdown'u kapat
      document.getElementById('signal-management-menu').style.display = 'none';
    } catch (e) {
      setMessage("❌ İndirme hatası: " + (e.response?.data?.detail || e.message));
    } finally {
      setLoading(false);
    }
  };

  const importSignals = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    
    if (!window.confirm(`${file.name} dosyasını yüklemek istediğinize emin misiniz?`)) {
      event.target.value = ''; // Reset file input
      return;
    }
    
    setLoading(true);
    try {
      // Dosyayı oku
      const text = await file.text();
      const data = JSON.parse(text);
      
      // Backend'e gönder
      const res = await axios.post(`${API}/signals/import`, data, {
        headers: { 
          "x-admin-token": adminToken,
          "Content-Type": "application/json"
        }
      });
      
      setMessage(`✅ ${res.data.imported} sinyal yüklendi, ${res.data.skipped} atlandı`);
      loadSignals();
      loadSignalStats();
      
      // Dropdown'u kapat
      document.getElementById('signal-management-menu').style.display = 'none';
    } catch (e) {
      if (e instanceof SyntaxError) {
        setMessage("❌ Geçersiz JSON dosyası");
      } else {
        setMessage("❌ Yükleme hatası: " + (e.response?.data?.detail || e.message));
      }
    } finally {
      setLoading(false);
      event.target.value = ''; // Reset file input
    }
  };

  const importHistoricalData = async () => {
    if (!coinSettings || coinSettings.length === 0) {
      setMessage("❌ Önce coin eklemelisiniz");
      return;
    }
    
    const activeCoins = coinSettings
      .filter(cs => cs.status === 'active')
      .map(cs => cs.coin);
    
    if (activeCoins.length === 0) {
      setMessage("❌ Aktif coin bulunamadı");
      return;
    }
    
    if (!window.confirm(`${activeCoins.length} aktif coin için ${historicalDays} günlük geçmiş veri çekilecek. Bu işlem birkaç dakika sürebilir. Devam edilsin mi?`)) {
      return;
    }
    
    setLoading(true);
    setHistoricalImportResult(null);
    setMessage("⏳ Geçmiş veriler çekiliyor, lütfen bekleyin...");
    
    try {
      const res = await axios.post(`${API}/historical/import`, {
        coins: activeCoins,
        days: historicalDays,
        interval: historicalInterval
      }, {
        headers: { "x-admin-token": adminToken }
      });
      
      setHistoricalImportResult(res.data.results);
      
      // Başarı mesajı
      const successCount = Object.values(res.data.results).filter(r => r.status === 'success').length;
      const totalImported = Object.values(res.data.results)
        .filter(r => r.status === 'success')
        .reduce((sum, r) => sum + r.imported, 0);
      
      setMessage(`✅ ${successCount} coin için ${totalImported} yeni veri eklendi!`);
      
      // Coin settings'i yenile (son güncelleme zamanı değişecek)
      loadCoinSettings();
      
    } catch (e) {
      setMessage("❌ İçe aktarma hatası: " + (e.response?.data?.detail || e.message));
      setHistoricalImportResult(null);
    } finally {
      setLoading(false);
    }
  };

  const clearCoinSignals = async () => {
    if (!selectedCoinFilter) {
      setMessage("⚠️ Lütfen silmek için bir coin seçin");
      return;
    }

    if (!window.confirm(`${selectedCoinFilter} coin'inin TÜM sinyallerini silmek istediğinizden emin misiniz?`)) return;
    
    setLoading(true);
    try {
      const res = await axios.post(`${API}/signals/clear_by_coin`, 
        { coin: selectedCoinFilter },
        { headers: { "x-admin-token": adminToken } }
      );
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
        <div className="header-content">
          <div className="header-title">
            <h1>📊 MM TRADING BOT PRO</h1>
            <p className="subtitle">CoinMarketCap & Telegram Entegrasyonlu</p>
          </div>
          <button 
            className="dark-mode-toggle"
            onClick={() => setDarkMode(!darkMode)}
            title={darkMode ? 'Açık moda geç' : 'Karanlık moda geç'}
          >
            {darkMode ? '☀️' : '🌙'}
          </button>
        </div>
      </header>

      <div className="tabs">
        <button 
          className={`tab ${activeTab === 'panel' ? 'active' : ''}`}
          onClick={() => setActiveTab('panel')}
        >
          ⚙️ Panel
        </button>
        <button 
          className={`tab ${activeTab === 'telegram' ? 'active' : ''}`}
          onClick={() => setActiveTab('telegram')}
        >
          💬 Telegram
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
                    placeholder="Admin token'ı girin"
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

            {/* Geçmiş Veri İçe Aktarma */}
            <div className="card">
              <h3>📥 Geçmiş Veri İçe Aktar</h3>
              <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
                Golden Cross/Death Cross için 200 veri noktası gereklidir. Geçmiş verileri içe aktararak hemen kullanmaya başlayabilirsiniz.
              </p>
              
              <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-end', flexWrap: 'wrap' }}>
                <div style={{ flex: 1, minWidth: '200px' }}>
                  <label>Gün Sayısı</label>
                  <select 
                    className="input"
                    value={historicalDays}
                    onChange={(e) => setHistoricalDays(parseInt(e.target.value))}
                  >
                    <option value="7">7 Gün (~168 veri)</option>
                    <option value="14">14 Gün (~336 veri)</option>
                    <option value="30">30 Gün (~720 veri) ⭐</option>
                    <option value="60">60 Gün (~1440 veri)</option>
                    <option value="90">90 Gün (~2160 veri)</option>
                    <option value="180">180 Gün (~4320 veri)</option>
                    <option value="365">365 Gün (~8760 veri)</option>
                    <option value="720">720 Gün (~17280 veri)</option>
                  </select>
                </div>
                
                <div style={{ flex: 1, minWidth: '200px' }}>
                  <label>Interval</label>
                  <select 
                    className="input"
                    value={historicalInterval}
                    onChange={(e) => setHistoricalInterval(e.target.value)}
                  >
                    <option value="15m">15 Dakika (Çok Detaylı)</option>
                    <option value="30m">30 Dakika (Detaylı)</option>
                    <option value="1h">1 Saat ⭐</option>
                    <option value="4h">4 Saat</option>
                    <option value="6h">6 Saat</option>
                    <option value="12h">12 Saat</option>
                    <option value="24h">24 Saat (Günlük)</option>
                  </select>
                </div>
                
                <button 
                  className="btn"
                  onClick={importHistoricalData}
                  disabled={loading}
                  style={{ minWidth: '150px' }}
                >
                  {loading ? '⏳ Yükleniyor...' : '📥 Veri İçe Aktar'}
                </button>
              </div>
              
              {historicalImportResult && (
                <div style={{ 
                  marginTop: '1rem', 
                  padding: '1rem', 
                  backgroundColor: 'var(--bg-secondary)', 
                  borderRadius: '8px',
                  fontSize: '0.9rem'
                }}>
                  <strong>📊 İçe Aktarma Sonucu:</strong>
                  <ul style={{ marginTop: '0.5rem', paddingLeft: '1.5rem' }}>
                    {Object.entries(historicalImportResult).map(([coin, result]) => (
                      <li key={coin}>
                        <strong>{coin}:</strong> {
                          result.status === 'success' 
                            ? `✅ ${result.imported} yeni, ${result.skipped} mevcut (${result.total} toplam)`
                            : `❌ ${result.message}`
                        }
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>



            <div className="card">
              {/* Header with Toggle */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <div>
                  <h3 style={{ margin: 0 }}>⚙️ Coin Başına Özel Ayarlar</h3>
                  <p className="card-description" style={{ margin: '0.25rem 0 0 0' }}>
                    Her coin için ayrı timeframe, eşik ve mod ayarı yapabilirsiniz
                  </p>
                </div>
                
                {/* Toggle ve Gösterge */}
                {coinSettings.length > 0 && (
                  <div style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    gap: '1rem',
                    padding: '0.75rem 1rem',
                    backgroundColor: 'var(--bg-secondary)',
                    borderRadius: '8px',
                    border: '1px solid var(--border-color)'
                  }}>
                    {/* Renk Göstergesi */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                        <div style={{ 
                          width: '10px', 
                          height: '10px', 
                          borderRadius: '50%', 
                          backgroundColor: '#10b981' 
                        }}></div>
                        <span style={{ fontSize: '0.85rem', fontWeight: '600', color: '#10b981' }}>
                          {coinSettings.filter(cs => cs.status === 'active').length}
                        </span>
                      </div>
                      
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                        <div style={{ 
                          width: '10px', 
                          height: '10px', 
                          borderRadius: '50%', 
                          backgroundColor: '#6b7280' 
                        }}></div>
                        <span style={{ fontSize: '0.85rem', fontWeight: '600', color: '#6b7280' }}>
                          {coinSettings.filter(cs => cs.status === 'passive').length}
                        </span>
                      </div>
                    </div>
                    
                    {/* Status Toggle Butonu */}
                    <div style={{ 
                      display: 'flex', 
                      flexDirection: 'column', 
                      alignItems: 'center',
                      gap: '0.25rem',
                      marginRight: '1rem',
                      paddingRight: '1rem',
                      borderRight: '1px solid var(--border-color)'
                    }}>
                      <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: '500' }}>
                        Tümü
                      </span>
                      <button
                        onClick={toggleAllCoins}
                        className={`status-toggle-modern ${coinSettings.filter(cs => cs.status === 'active').length === coinSettings.length ? 'active' : ''}`}
                        title={coinSettings.filter(cs => cs.status === 'active').length === coinSettings.length ? 'Tümünü Pasif Yap' : 'Tümünü Aktif Yap'}
                      >
                        <span className="toggle-slider-modern"></span>
                      </button>
                    </div>

                    {/* Feature Flag Toggle Butonu */}
                    <div style={{ 
                      display: 'flex', 
                      flexDirection: 'column', 
                      alignItems: 'center',
                      gap: '0.25rem'
                    }}>
                      <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: '500' }}>
                        🔧 Candle
                      </span>
                      <button
                        onClick={toggleGlobalFeatureFlag}
                        className={`status-toggle-modern ${globalFeatureFlag ? 'active' : ''}`}
                        title={globalFeatureFlag ? 'Candle Interval Analysis: Açık' : 'Candle Interval Analysis: Kapalı'}
                      >
                        <span className="toggle-slider-modern"></span>
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* Coin Ekleme Bölümü */}
                <div style={{ 
                  marginBottom: '1.5rem', 
                  padding: '1rem', 
                  backgroundColor: 'var(--bg-secondary)', 
                  borderRadius: '8px',
                  border: '1px solid var(--border-color)'
                }}>
                  <label style={{ fontWeight: '600', marginBottom: '0.5rem', display: 'block' }}>➕ Yeni Coin Ekle</label>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <input
                      type="text"
                      className="input"
                      value={newCoin}
                      onChange={(e) => setNewCoin(e.target.value)}
                      placeholder="Örn: SHIB, PEPE, FLOKI"
                      onKeyPress={(e) => e.key === 'Enter' && addNewCoin()}
                      style={{ flex: 1 }}
                    />
                    <button className="btn btn-add" onClick={addNewCoin} style={{ whiteSpace: 'nowrap' }}>
                      ➕ Ekle
                    </button>
                  </div>
                </div>

                {coinSettings.length > 0 ? (
                <>
                <div className="coin-settings-grid">
                  {coinSettings.map((cs) => {
                    const isActive = cs.status === 'active' || (cs.active !== false && !cs.status);
                    return (
                      <div key={cs.coin} className={`coin-card ${!isActive ? 'coin-card-inactive' : 'coin-card-active'}`}>
                        {/* Header with Coin Name and Status */}
                        <div className="coin-card-header">
                          <div className="coin-card-title">
                            <h4>{cs.coin}</h4>
                            <span className={`status-badge ${isActive ? 'status-active' : 'status-passive'}`}>
                              {isActive ? '🟢 Active' : '⚫ Passive'}
                            </span>
                          </div>
                          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                            {/* Feature Flag Indicator */}
                            <div style={{ 
                              display: 'flex', 
                              flexDirection: 'column', 
                              alignItems: 'center',
                              gap: '0.2rem'
                            }}>
                              <button
                                onClick={() => toggleCoinFeatureFlag(cs.coin)}
                                style={{
                                  background: 'none',
                                  border: 'none',
                                  cursor: 'pointer',
                                  padding: '4px',
                                  fontSize: '1.3rem',
                                  transition: 'transform 0.2s',
                                  opacity: isActive ? 1 : 0.3
                                }}
                                onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.2)'}
                                onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
                                title={
                                  globalFeatureFlag 
                                    ? 'Global: Aktif (Tüm coinler için candle analizi açık)' 
                                    : cs.candle_analysis_enabled 
                                      ? 'Coin: Aktif (Global kapalı olsa da bu coin için açık)' 
                                      : 'Kapalı (Hem global hem coin kapalı)'
                                }
                                disabled={!isActive}
                              >
                                {globalFeatureFlag || cs.candle_analysis_enabled ? '🟢' : '🔴'}
                              </button>
                              <span style={{ fontSize: '0.6rem', color: 'var(--text-secondary)' }}>
                                Candle
                              </span>
                            </div>
                            
                            {/* Status Toggle */}
                            <button 
                              className={`status-toggle-modern ${isActive ? 'active' : 'passive'}`}
                              onClick={() => updateCoinSetting(cs.coin, 'status', isActive ? 'passive' : 'active')}
                              title={isActive ? 'Pasife al' : 'Aktif et'}
                            >
                              <span className="toggle-slider-modern"></span>
                            </button>
                          </div>
                        </div>

                        {/* Fetch Interval Section */}
                        <div className="coin-card-section interval-section">
                          <div className="section-label">
                            <span className="label-icon">⏱️</span>
                            <span>Veri Çekme Sıklığı</span>
                          </div>
                          <div className="interval-control">
                            <input
                              type="number"
                              className="interval-input-modern"
                              value={cs.fetch_interval_minutes || 2}
                              onChange={(e) => updateCoinSetting(cs.coin, 'fetch_interval_minutes', parseInt(e.target.value))}
                              min="1"
                              max="1440"
                              step="1"
                              disabled={!isActive}
                            />
                            <span className="interval-unit">dakika</span>
                          </div>
                          {isActive && cs.time_ago && (
                            <div className="last-update-info">
                              <span className="update-icon">📡</span>
                              <span className="update-text">{cs.time_ago}</span>
                            </div>
                          )}
                        </div>

                        {/* Göstergeler */}
                        {isActive && indicators[cs.coin] && (
                          <div className="coin-card-section border-t border-gray-200 dark:border-gray-700 pt-3">
                            {/* Combined Signal Strength */}
                            {indicators[cs.coin].signal_strength && (
                              <div className="mb-3 p-2 rounded" style={{ backgroundColor: 'var(--bg-secondary)' }}>
                                <div className="flex items-center justify-between mb-1">
                                  <span className="text-xs font-semibold text-gray-600 dark:text-gray-400">📊 Sinyal Gücü</span>
                                  <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                                    indicators[cs.coin].signal_strength.direction === 'BULLISH' ? 'bg-green-600 text-white' :
                                    indicators[cs.coin].signal_strength.direction === 'BEARISH' ? 'bg-red-600 text-white' :
                                    'bg-gray-600 text-white'
                                  }`}>
                                    {indicators[cs.coin].signal_strength.direction}
                                  </span>
                                </div>
                                <div className="flex items-center gap-2">
                                  <div className="flex-1 h-2 bg-gray-300 dark:bg-gray-700 rounded-full overflow-hidden">
                                    <div 
                                      className={`h-full ${
                                        indicators[cs.coin].signal_strength.level === 'VERY_STRONG' ? 'bg-green-600' :
                                        indicators[cs.coin].signal_strength.level === 'STRONG' ? 'bg-green-500' :
                                        indicators[cs.coin].signal_strength.level === 'MODERATE' ? 'bg-yellow-500' :
                                        indicators[cs.coin].signal_strength.level === 'WEAK' ? 'bg-orange-500' :
                                        'bg-red-500'
                                      }`}
                                      style={{ width: `${indicators[cs.coin].signal_strength.score}%` }}
                                    />
                                  </div>
                                  <span className="text-xs font-bold">{indicators[cs.coin].signal_strength.score}/100</span>
                                </div>
                                <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                                  {indicators[cs.coin].signal_strength.level} 
                                  ({indicators[cs.coin].signal_strength.bullish_count}📈 / {indicators[cs.coin].signal_strength.bearish_count}📉)
                                </div>
                              </div>
                            )}
                            
                            {/* Kısa Vadeli EMA */}
                            <div className="flex gap-2 items-center flex-wrap mb-2">
                              {indicators[cs.coin].rsi && (
                                <span className={`px-2 py-1 rounded text-xs font-medium ${
                                  indicators[cs.coin].rsi_signal === 'OVERSOLD' ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300' :
                                  indicators[cs.coin].rsi_signal === 'OVERBOUGHT' ? 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300' :
                                  'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300'
                                }`}>
                                  RSI: {indicators[cs.coin].rsi.toFixed(1)}
                                </span>
                              )}
                              {indicators[cs.coin].macd_signal && (
                                <span className={`px-2 py-1 rounded text-xs font-medium ${
                                  indicators[cs.coin].macd_signal === 'BULLISH' ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300' :
                                  indicators[cs.coin].macd_signal === 'BEARISH' ? 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300' :
                                  'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300'
                                }`}>
                                  MACD: {indicators[cs.coin].macd_signal}
                                </span>
                              )}
                              {indicators[cs.coin].volatility && (
                                <span className="px-2 py-1 rounded text-xs font-medium bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300">
                                  📊 Vol: {indicators[cs.coin].volatility.toFixed(1)}%
                                </span>
                              )}
                            </div>
                            
                            {/* EMA Değerleri */}
                            <div className="flex gap-2 items-center flex-wrap">
                              {indicators[cs.coin].ema9 && indicators[cs.coin].ema21 && (
                                <span className={`px-2 py-1 rounded text-xs font-medium ${
                                  indicators[cs.coin].ema_signal === 'BULLISH' ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300' :
                                  indicators[cs.coin].ema_signal === 'BEARISH' ? 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300' :
                                  'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
                                }`}>
                                  EMA9/21: {indicators[cs.coin].ema9.toFixed(2)} / {indicators[cs.coin].ema21.toFixed(2)} 
                                  {indicators[cs.coin].ema_signal === 'BULLISH' ? ' 📈' : 
                                   indicators[cs.coin].ema_signal === 'BEARISH' ? ' 📉' : ' ➡️'}
                                </span>
                              )}
                              {indicators[cs.coin].ema50 && indicators[cs.coin].ema200 && (
                                <span className={`px-2 py-1 rounded text-xs font-medium ${
                                  indicators[cs.coin].ema_cross === 'GOLDEN_CROSS' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200' :
                                  indicators[cs.coin].ema_cross === 'DEATH_CROSS' ? 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200' :
                                  'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
                                }`}>
                                  {indicators[cs.coin].ema_cross === 'GOLDEN_CROSS' ? '🌟 Golden Cross' :
                                   indicators[cs.coin].ema_cross === 'DEATH_CROSS' ? '💀 Death Cross' :
                                   `EMA50/200: ${indicators[cs.coin].ema50.toFixed(0)}/${indicators[cs.coin].ema200.toFixed(0)}`}
                                </span>
                              )}
                            </div>
                          </div>
                        )}

                        {/* Timeframe and Mode */}
                        <div className="coin-card-section">
                          <div className="section-label">
                            <span className="label-icon">📊</span>
                            <span>Analiz Ayarları</span>
                          </div>
                          
                          {/* Adaptive Timeframe Toggle */}
                          <div className="mb-3 p-2 rounded" style={{ backgroundColor: 'var(--bg-secondary)' }}>
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <span className="text-sm font-medium">🎯 Adaptive Timeframe</span>
                                <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                                  cs.adaptive_timeframe_enabled ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300' :
                                  'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300'
                                }`}>
                                  {cs.adaptive_timeframe_enabled ? '✅ Aktif' : '⏸️ Pasif'}
                                </span>
                              </div>
                              <button
                                onClick={() => updateCoinSetting(cs.coin, 'adaptive_timeframe_enabled', !cs.adaptive_timeframe_enabled)}
                                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 ${
                                  cs.adaptive_timeframe_enabled 
                                    ? 'bg-green-600 focus:ring-green-500' 
                                    : 'bg-gray-400 focus:ring-gray-400'
                                }`}
                                disabled={!isActive}
                              >
                                <span
                                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                                    cs.adaptive_timeframe_enabled ? 'translate-x-6' : 'translate-x-1'
                                  }`}
                                />
                              </button>
                            </div>
                            {cs.adaptive_timeframe_enabled && (
                              <div className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                                ℹ️ Volatiliteye göre otomatik timeframe seçimi aktif
                              </div>
                            )}
                          </div>

                          <div className="settings-row">
                            <div className="setting-item">
                              <label>📊 Analiz Zaman Dilimi {cs.adaptive_timeframe_enabled && '(Manuel Ayar)'}</label>
                              <select
                                className="select-modern"
                                value={cs.timeframe}
                                onChange={(e) => updateCoinSetting(cs.coin, 'timeframe', e.target.value)}
                                disabled={cs.adaptive_timeframe_enabled}
                              >
                                <option value="15m">15 dakika</option>
                                <option value="30m">30 dakika</option>
                                <option value="1h">1 saat</option>
                                <option value="4h">4 saat</option>
                                <option value="6h">6 saat</option>
                                <option value="12h">12 saat</option>
                                <option value="24h">24 saat</option>
                                <option value="7d">7 gün</option>
                                <option value="30d">30 gün</option>
                                <option value="60d">60 gün</option>
                                <option value="90d">90 gün</option>
                                <option value="180d">180 gün</option>
                                <option value="365d">365 gün (1 yıl)</option>
                                <option value="720d">720 gün (2 yıl)</option>
                              </select>
                              {cs.adaptive_timeframe_enabled && (
                                <div className="text-xs text-blue-600 dark:text-blue-400 mt-1">
                                  🤖 Otomatik seçiliyor
                                </div>
                              )}
                            </div>
                            <div className="setting-item">
                              <label>Eşik Modu</label>
                              <select
                                className="select-modern"
                                value={cs.threshold_mode}
                                onChange={(e) => updateCoinSetting(cs.coin, 'threshold_mode', e.target.value)}
                              >
                                <option value="manual">Manuel</option>
                                <option value="dynamic">Dinamik 🤖</option>
                              </select>
                            </div>
                          </div>
                        </div>

                        {/* Threshold */}
                        <div className="coin-card-section">
                          <div className="section-label">
                            <span className="label-icon">🎯</span>
                            <span>Eşik Değeri</span>
                          </div>
                          <div className="threshold-control">
                            <input
                              type="number"
                              className="threshold-input-modern"
                              value={cs.threshold}
                              onChange={(e) => updateCoinSetting(cs.coin, 'threshold', parseFloat(e.target.value))}
                              min="0"
                              max="100"
                              step="0.5"
                              disabled={cs.threshold_mode === 'dynamic'}
                            />
                            <span className="threshold-unit">%</span>
                          </div>
                        </div>

                        {/* Action Buttons */}
                        <div className="flex gap-2 mt-3">
                          <button
                            className="btn-save-modern flex-1"
                            onClick={() => saveSingleCoinSetting(cs.coin)}
                            title={`${cs.coin} ayarlarını kaydet`}
                            disabled={loading}
                          >
                            💾 Kaydet
                          </button>
                          <button
                            className="btn-delete-modern"
                            onClick={() => removeCoinFromSettings(cs.coin)}
                            title={`${cs.coin} sil`}
                          >
                            🗑️ Sil
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>

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
                </>
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
                  <button className="btn btn-small" onClick={() => loadSignals()}>🔄 Yenile</button>
                  <button className="btn btn-small btn-danger" onClick={clearFailedSignals} disabled={loading}>
                    🗑 Başarısızları Sil
                  </button>
                  <button className="btn btn-small btn-danger-outline" onClick={clearAllSignals} disabled={loading}>
                    ⚠️ Tümünü Sil
                  </button>
                </div>
              </div>

              {/* Filtreleme ve İstatistikler */}
              <div className="signal-filters" style={{ padding: '1rem', borderBottom: '1px solid var(--border-color)', background: 'var(--bg-secondary)' }}>
                {/* İstatistik Kartı */}
                {signalStats && (
                  <div className="signal-stats-card mb-3" style={{ background: 'var(--bg-primary)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '1rem' }}>
                      <div className="stat-item">
                        <div className="stat-label text-xs text-gray-500">Toplam</div>
                        <div className="stat-value text-sm font-bold">{signalStats.total}</div>
                      </div>
                      <div className="stat-item">
                        <div className="stat-label text-xs text-gray-500">Aktif</div>
                        <div className="stat-value text-sm font-bold text-blue-600">{signalStats.active}</div>
                      </div>
                      <div className="stat-item">
                        <div className="stat-label text-xs text-gray-500">TP Hit</div>
                        <div className="stat-value text-sm font-bold text-green-600">{signalStats.hit_tp}</div>
                      </div>
                      <div className="stat-item">
                        <div className="stat-label text-xs text-gray-500">SL Hit</div>
                        <div className="stat-value text-sm font-bold text-red-600">{signalStats.hit_sl}</div>
                      </div>
                      <div className="stat-item">
                        <div className="stat-label text-xs text-gray-500">Win Rate</div>
                        <div className="stat-value text-sm font-bold">{signalStats.win_rate}%</div>
                      </div>
                      <div className="stat-item">
                        <div className="stat-label text-xs text-gray-500">Avg P/L</div>
                        <div className={`stat-value text-sm font-bold ${signalStats.avg_profit_loss >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {signalStats.avg_profit_loss >= 0 ? '+' : ''}{signalStats.avg_profit_loss}%
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Filtreler */}
                <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'center' }}>
                  {/* Status Filtresi */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <label style={{ fontWeight: '500', fontSize: '0.9rem' }}>🎯 Durum:</label>
                    <select 
                      value={selectedStatus} 
                      onChange={(e) => setSelectedStatus(e.target.value)}
                      className="filter-select"
                      style={{ 
                        padding: '0.4rem 0.8rem', 
                        borderRadius: '6px', 
                        border: '1px solid var(--border-color)',
                        backgroundColor: 'var(--bg-primary)',
                        color: 'var(--text-primary)',
                        fontSize: '0.9rem'
                      }}
                    >
                      <option value="all">Tümü</option>
                      <option value="active">Aktif</option>
                      <option value="hit_tp">TP Hit ✅</option>
                      <option value="hit_sl">SL Hit 🛑</option>
                      <option value="expired">Expired ⏰</option>
                    </select>
                  </div>

                  {/* Coin Multi-Select Dropdown */}
                  <div style={{ position: 'relative', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <label style={{ fontWeight: '500', fontSize: '0.9rem' }}>🪙 Coinler:</label>
                    <div className="coin-dropdown-container" style={{ position: 'relative' }}>
                      <button
                        onClick={() => setCoinDropdownOpen(!coinDropdownOpen)}
                        className="filter-select"
                        style={{ 
                          padding: '0.4rem 2rem 0.4rem 0.8rem', 
                          borderRadius: '6px', 
                          border: '1px solid var(--border-color)',
                          backgroundColor: 'var(--bg-primary)',
                          color: 'var(--text-primary)',
                          fontSize: '0.9rem',
                          cursor: 'pointer',
                          minWidth: '150px',
                          textAlign: 'left',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.5rem'
                        }}
                      >
                        <span>
                          {selectedCoins.length === 0 ? 'Tümü' : `${selectedCoins.length} coin seçili`}
                        </span>
                        <span style={{ 
                          position: 'absolute', 
                          right: '0.5rem',
                          transition: 'transform 0.2s',
                          transform: coinDropdownOpen ? 'rotate(180deg)' : 'rotate(0deg)'
                        }}>▼</span>
                      </button>
                      
                      {coinDropdownOpen && (
                        <div style={{
                          position: 'absolute',
                          top: 'calc(100% + 4px)',
                          left: 0,
                          minWidth: '200px',
                          maxHeight: '300px',
                          overflowY: 'auto',
                          backgroundColor: 'var(--bg-primary)',
                          border: '1px solid var(--border-color)',
                          borderRadius: '8px',
                          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
                          zIndex: 1000,
                          padding: '0.5rem'
                        }}>
                          {/* Tümünü Seç/Kaldır */}
                          <div style={{
                            padding: '0.5rem',
                            borderBottom: '1px solid var(--border-color)',
                            marginBottom: '0.5rem'
                          }}>
                            <button
                              onClick={() => {
                                if (selectedCoins.length === coinSettings.length) {
                                  setSelectedCoins([]);
                                } else {
                                  setSelectedCoins(coinSettings.map(cs => cs.coin));
                                }
                              }}
                              style={{
                                fontSize: '0.85rem',
                                padding: '0.3rem 0.6rem',
                                backgroundColor: 'var(--accent-color)',
                                color: 'white',
                                border: 'none',
                                borderRadius: '4px',
                                cursor: 'pointer',
                                width: '100%'
                              }}
                            >
                              {selectedCoins.length === coinSettings.length ? '❌ Tümünü Kaldır' : '✅ Tümünü Seç'}
                            </button>
                          </div>
                          
                          {/* Coin Listesi */}
                          {coinSettings.map(cs => (
                            <label 
                              key={cs.coin} 
                              style={{ 
                                display: 'flex', 
                                alignItems: 'center', 
                                gap: '0.5rem', 
                                cursor: 'pointer',
                                padding: '0.5rem',
                                borderRadius: '4px',
                                transition: 'background-color 0.2s',
                                backgroundColor: selectedCoins.includes(cs.coin) ? 'var(--hover-color)' : 'transparent'
                              }}
                              onMouseEnter={(e) => {
                                if (!selectedCoins.includes(cs.coin)) {
                                  e.currentTarget.style.backgroundColor = 'var(--hover-color-light)';
                                }
                              }}
                              onMouseLeave={(e) => {
                                if (!selectedCoins.includes(cs.coin)) {
                                  e.currentTarget.style.backgroundColor = 'transparent';
                                }
                              }}
                            >
                              <input
                                type="checkbox"
                                checked={selectedCoins.includes(cs.coin)}
                                onChange={(e) => {
                                  if (e.target.checked) {
                                    setSelectedCoins([...selectedCoins, cs.coin]);
                                  } else {
                                    setSelectedCoins(selectedCoins.filter(c => c !== cs.coin));
                                  }
                                }}
                                style={{ cursor: 'pointer' }}
                              />
                              <span className="text-sm font-medium">{cs.coin}</span>
                              <span className="text-xs" style={{ 
                                marginLeft: 'auto',
                                padding: '0.1rem 0.4rem',
                                borderRadius: '4px',
                                backgroundColor: cs.status === 'active' ? '#10b981' : '#6b7280',
                                color: 'white'
                              }}>
                                {cs.status === 'active' ? '🟢' : '⚫'}
                              </span>
                            </label>
                          ))}
                          
                          {coinSettings.length === 0 && (
                            <div style={{ 
                              padding: '1rem', 
                              textAlign: 'center', 
                              color: 'var(--text-secondary)',
                              fontSize: '0.85rem'
                            }}>
                              Henüz coin eklenmemiş
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Limit Seçici */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <label style={{ fontWeight: '500', fontSize: '0.9rem' }}>📊 Göster:</label>
                    <select 
                      value={signalLimit} 
                      onChange={(e) => setSignalLimit(parseInt(e.target.value))}
                      className="filter-select"
                      style={{ 
                        padding: '0.4rem 0.8rem', 
                        borderRadius: '6px', 
                        border: '1px solid var(--border-color)',
                        backgroundColor: 'var(--bg-primary)',
                        color: 'var(--text-primary)',
                        fontSize: '0.9rem'
                      }}
                    >
                      <option value="50">50 Sinyal</option>
                      <option value="100">100 Sinyal</option>
                      <option value="200">200 Sinyal</option>
                      <option value="500">500 Sinyal</option>
                      <option value="1000">Tümü</option>
                    </select>
                  </div>

                  {/* Actions */}
                  <div style={{ marginLeft: 'auto', display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                    {/* Sinyal Yönetimi Dropdown */}
                    <div style={{ position: 'relative' }}>
                      <button 
                        className="btn btn-small"
                        onClick={() => {
                          const menu = document.getElementById('signal-management-menu');
                          menu.style.display = menu.style.display === 'block' ? 'none' : 'block';
                        }}
                        disabled={loading}
                      >
                        📋 Yönet ▼
                      </button>
                      <div 
                        id="signal-management-menu"
                        style={{
                          display: 'none',
                          position: 'absolute',
                          top: 'calc(100% + 4px)',
                          right: 0,
                          minWidth: '220px',
                          backgroundColor: 'var(--bg-primary)',
                          border: '1px solid var(--border-color)',
                          borderRadius: '8px',
                          boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                          zIndex: 1000,
                          padding: '0.5rem'
                        }}
                      >
                        <button 
                          className="dropdown-item"
                          onClick={() => exportSignals('all')}
                          style={{
                            width: '100%',
                            padding: '0.5rem',
                            textAlign: 'left',
                            border: 'none',
                            background: 'transparent',
                            cursor: 'pointer',
                            borderRadius: '4px',
                            fontSize: '0.9rem'
                          }}
                          onMouseEnter={(e) => e.target.style.backgroundColor = 'var(--hover-color)'}
                          onMouseLeave={(e) => e.target.style.backgroundColor = 'transparent'}
                        >
                          📥 Toplu İndir (Tümü)
                        </button>
                        <button 
                          className="dropdown-item"
                          onClick={() => exportSignals('hit_tp')}
                          style={{
                            width: '100%',
                            padding: '0.5rem',
                            textAlign: 'left',
                            border: 'none',
                            background: 'transparent',
                            cursor: 'pointer',
                            borderRadius: '4px',
                            fontSize: '0.9rem'
                          }}
                          onMouseEnter={(e) => e.target.style.backgroundColor = 'var(--hover-color)'}
                          onMouseLeave={(e) => e.target.style.backgroundColor = 'transparent'}
                        >
                          📈 Başarılı Sinyaller
                        </button>
                        <button 
                          className="dropdown-item"
                          onClick={() => document.getElementById('import-file-input').click()}
                          style={{
                            width: '100%',
                            padding: '0.5rem',
                            textAlign: 'left',
                            border: 'none',
                            background: 'transparent',
                            cursor: 'pointer',
                            borderRadius: '4px',
                            fontSize: '0.9rem'
                          }}
                          onMouseEnter={(e) => e.target.style.backgroundColor = 'var(--hover-color)'}
                          onMouseLeave={(e) => e.target.style.backgroundColor = 'transparent'}
                        >
                          📤 Sinyal Yükle
                        </button>
                        <hr style={{ margin: '0.5rem 0', border: 'none', borderTop: '1px solid var(--border-color)' }} />
                        <button 
                          className="dropdown-item"
                          onClick={clearFailedSignals}
                          style={{
                            width: '100%',
                            padding: '0.5rem',
                            textAlign: 'left',
                            border: 'none',
                            background: 'transparent',
                            cursor: 'pointer',
                            borderRadius: '4px',
                            fontSize: '0.9rem',
                            color: '#ef4444'
                          }}
                          onMouseEnter={(e) => e.target.style.backgroundColor = 'var(--hover-color)'}
                          onMouseLeave={(e) => e.target.style.backgroundColor = 'transparent'}
                        >
                          🗑 Başarısızları Temizle
                        </button>
                      </div>
                      {/* Hidden file input for import */}
                      <input 
                        id="import-file-input"
                        type="file"
                        accept=".json"
                        style={{ display: 'none' }}
                        onChange={importSignals}
                      />
                    </div>
                    
                    <button className="btn btn-small" onClick={trackSignals} disabled={loading}>
                      🔄 Track Signals
                    </button>
                    <button className="btn btn-small btn-danger-outline" onClick={clearAllSignals} disabled={loading}>
                      🗑 Tümünü Sil
                    </button>
                  </div>
                </div>

                {/* Sonuç sayısı */}
                <div style={{ marginTop: '0.5rem', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                  📊 {signals.length} sinyal görüntüleniyor
                </div>
              </div>
              
              {signals.length === 0 ? (
                <p className="no-data">Henüz sinyal yok. Bot otomatik olarak her 60 saniyede analiz yapıyor.</p>
              ) : (
                <div className="signals-list">
                  {signals.map(signal => (
                    <div key={signal.id} className="signal-card">
                      <div className="signal-header">
                        <div className="signal-coin-name">{signal.coin}</div>
                        <div className={`signal-type ${signal.signal_type?.toLowerCase()}`}>
                          {signal.signal_type === 'LONG' ? '📈 LONG' : '📉 SHORT'}
                        </div>
                        
                        {/* Status Badge */}
                        <div className={`signal-status-badge ${signal.signal_status || 'active'}`}>
                          {signal.signal_status === 'hit_tp' && '✅ TP Hit'}
                          {signal.signal_status === 'hit_sl' && '🛑 SL Hit'}
                          {signal.signal_status === 'expired' && '⏰ Expired'}
                          {(!signal.signal_status || signal.signal_status === 'active') && '🔵 Active'}
                        </div>
                        
                        {/* Profit/Loss */}
                        {signal.profit_loss_percent !== undefined && signal.profit_loss_percent !== 0 && (
                          <div className={`profit-loss-badge ${signal.profit_loss_percent >= 0 ? 'profit' : 'loss'}`}>
                            {signal.profit_loss_percent >= 0 ? '+' : ''}{signal.profit_loss_percent?.toFixed(2)}%
                          </div>
                        )}
                        
                        <button 
                          className="signal-delete-btn-mini" 
                          onClick={() => deleteSingleSignal(signal.id)}
                          title="Sinyali sil"
                        >
                          🗑️
                        </button>
                      </div>
                      <div className="signal-body">
                        {/* Combined Signal Strength Gauge */}
                        {signal.signal_strength && (
                          <div className="signal-strength-section mb-3">
                            <div className="flex justify-between items-center mb-1">
                              <span className="text-sm font-semibold text-gray-600 dark:text-gray-400">📊 Signal Strength</span>
                              <span className="text-sm font-bold">{signal.signal_strength.score?.toFixed(0)}%</span>
                            </div>
                            <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                              <div 
                                className={`h-full transition-all ${
                                  signal.signal_strength.score >= 80 ? 'bg-green-500' :
                                  signal.signal_strength.score >= 60 ? 'bg-yellow-500' :
                                  'bg-red-500'
                                }`}
                                style={{ width: `${signal.signal_strength.score}%` }}
                              />
                            </div>
                            <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                              {signal.signal_strength.level} - {signal.signal_strength.direction}
                            </div>
                          </div>
                        )}

                        <div className="signal-row">
                          <span>Güvenilirlik:</span>
                          <strong>{signal.probability?.toFixed(2)}%</strong>
                        </div>
                        
                        {/* Indicators Summary - Hover Tooltip */}
                        {(signal.rsi || signal.macd_signal || signal.ema_signal) && (
                          <div className="signal-row" title={`RSI: ${signal.rsi?.toFixed(1) || 'N/A'}, MACD: ${signal.macd_signal || 'N/A'}, EMA: ${signal.ema_signal || 'N/A'}`}>
                            <span>🧠 Göstergeler:</span>
                            <div className="flex gap-1">
                              {signal.rsi && (
                                <span className={`px-2 py-0.5 rounded text-xs ${
                                  signal.rsi_signal === 'OVERSOLD' ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300' :
                                  signal.rsi_signal === 'OVERBOUGHT' ? 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300' :
                                  'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300'
                                }`}>
                                  RSI
                                </span>
                              )}
                              {signal.macd_signal && (
                                <span className={`px-2 py-0.5 rounded text-xs ${
                                  signal.macd_signal === 'BULLISH' ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300' :
                                  signal.macd_signal === 'BEARISH' ? 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300' :
                                  'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300'
                                }`}>
                                  MACD
                                </span>
                              )}
                              {signal.ema_signal && (
                                <span className={`px-2 py-0.5 rounded text-xs ${
                                  signal.ema_signal === 'BULLISH' ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300' :
                                  signal.ema_signal === 'BEARISH' ? 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300' :
                                  'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
                                }`}>
                                  EMA
                                </span>
                              )}
                            </div>
                          </div>
                        )}

                        {/* Golden/Death Cross */}
                        {signal.ema_cross && signal.ema_cross !== 'NEUTRAL' && (
                          <div className="signal-row">
                            <span>📈 Trend:</span>
                            <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                              signal.ema_cross === 'GOLDEN_CROSS' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200' :
                              'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200'
                            }`}>
                              {signal.ema_cross === 'GOLDEN_CROSS' ? '🌟 Golden Cross' : '💀 Death Cross'}
                            </span>
                          </div>
                        )}

                        {/* Adaptive Timeframe */}
                        <div className="signal-row">
                          <span>⏱ Timeframe:</span>
                          <div className="flex items-center gap-2">
                            <span>{signal.timeframe}</span>
                            {signal.adaptive_timeframe_enabled && (
                              <span className="px-2 py-0.5 rounded text-xs bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300">
                                ⚙️ Adaptive
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Trend Weight */}
                        {signal.trend_weight && signal.trend_weight !== 0 && (
                          <div className="signal-row">
                            <span>⚖️ Trend Ağırlığı:</span>
                            <div className="flex items-center gap-2">
                              <span className={signal.trend_weight > 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}>
                                {signal.trend_weight > 0 ? '+' : ''}{signal.trend_weight.toFixed(0)}%
                              </span>
                              <div className="h-2 w-16 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                                <div 
                                  className={signal.trend_weight > 0 ? 'bg-green-500 h-full' : 'bg-red-500 h-full'}
                                  style={{ width: `${Math.abs(signal.trend_weight) / 15 * 100}%` }}
                                />
                              </div>
                            </div>
                          </div>
                        )}

                        {signal.features?.price && (
                          <div className="signal-row">
                            <span>💰 Giriş:</span>
                            <strong>{formatPrice(signal.features.price)}</strong>
                          </div>
                        )}
                        {signal.tp && (
                          <div className="signal-row tp">
                            <span>🎯 TP:</span>
                            <strong className="tp-value">{formatPrice(signal.tp)}</strong>
                          </div>
                        )}
                        {signal.stop_loss && (
                          <div className="signal-row sl">
                            <span>🛡 SL:</span>
                            <strong className="sl-value">{formatPrice(signal.stop_loss)}</strong>
                          </div>
                        )}
                        <div className="signal-time">
                          {signal.created_at ? new Date(signal.created_at).toLocaleString('tr-TR', {
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

        {activeTab === 'telegram' && (
          <div className="telegram-section">
            <div className="card">
              <h3>💬 Telegram Entegrasyon Ayarları</h3>
              <p className="card-description">
                Telegram bot token ve chat ID'nizi buradan yönetebilirsiniz
              </p>

              <div className="space-y-4 mt-6">
                {/* Bot Token */}
                <div className="form-group">
                  <label className="block text-sm font-medium mb-2">
                    🤖 Telegram Bot Token
                  </label>
                  <input
                    type="text"
                    className="input-modern w-full"
                    placeholder="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
                    value={telegramConfig.telegram_token}
                    onChange={(e) => setTelegramConfig({
                      ...telegramConfig,
                      telegram_token: e.target.value
                    })}
                  />
                  <small className="text-gray-600 dark:text-gray-400 mt-1 block">
                    Bot token'ınızı <a href="https://t.me/BotFather" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">@BotFather</a>'dan alabilirsiniz
                  </small>
                </div>

                {/* Chat ID */}
                <div className="form-group">
                  <label className="block text-sm font-medium mb-2">
                    💬 Telegram Chat ID
                  </label>
                  <input
                    type="text"
                    className="input-modern w-full"
                    placeholder="-1001234567890"
                    value={telegramConfig.telegram_chat_id}
                    onChange={(e) => setTelegramConfig({
                      ...telegramConfig,
                      telegram_chat_id: e.target.value
                    })}
                  />
                  <small className="text-gray-600 dark:text-gray-400 mt-1 block">
                    Chat ID'nizi <a href="https://t.me/userinfobot" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">@userinfobot</a> ile öğrenebilirsiniz
                  </small>
                </div>

                {/* Mevcut Ayarlar Göster */}
                {config.telegram_token && (
                  <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                    <div className="text-sm space-y-2">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">🤖 Bot Token:</span>
                        <code className="bg-white dark:bg-gray-800 px-2 py-1 rounded text-xs">
                          {config.telegram_token === '*****' ? '*****' : config.telegram_token.substring(0, 20) + '...'}
                        </code>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium">💬 Chat ID:</span>
                        <code className="bg-white dark:bg-gray-800 px-2 py-1 rounded text-xs">
                          {config.telegram_chat_id}
                        </code>
                      </div>
                    </div>
                  </div>
                )}

                {/* Action Buttons */}
                <div className="flex gap-3 flex-wrap">
                  <button
                    className="btn btn-primary"
                    onClick={saveTelegramConfig}
                    disabled={loading}
                  >
                    {loading ? '⏳ Kaydediliyor...' : '💾 Kaydet'}
                  </button>

                  <button
                    className="btn btn-secondary"
                    onClick={testTelegram}
                    disabled={loading}
                  >
                    {loading ? '⏳ Test ediliyor...' : '🔔 Test Bildirimi Gönder'}
                  </button>
                </div>

                {/* Info Box */}
                <div className="info-box mt-4">
                  <h4 className="font-medium mb-2">ℹ️ Nasıl Kullanılır?</h4>
                  <ol className="list-decimal list-inside space-y-1 text-sm">
                    <li>Telegram'da <a href="https://t.me/BotFather" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">@BotFather</a> botunu açın</li>
                    <li>/newbot komutu ile yeni bot oluşturun</li>
                    <li>Size verilen token'ı yukarıdaki alana yapıştırın</li>
                    <li>Botunuzu bir gruba ekleyin veya direkt mesaj gönderin</li>
                    <li><a href="https://t.me/userinfobot" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">@userinfobot</a> ile Chat ID'nizi öğrenin</li>
                    <li>Chat ID'yi yukarıdaki alana girin ve kaydedin</li>
                    <li>"Test Bildirimi Gönder" butonu ile test edin</li>
                  </ol>
                </div>
              </div>
            </div>

            {/* Manuel Fiyat Yönetimi */}
            <div className="card mt-6">
              <h3>💲 Manuel Fiyat Yönetimi</h3>
              <p className="card-description">
                Belirli coinler için manuel fiyat belirleyerek API fiyatlarını override edebilirsiniz
              </p>

              <div className="space-y-4 mt-6">
                {/* Yeni Manuel Fiyat Ekle */}
                <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                  <h4 className="font-medium mb-3">Yeni Manuel Fiyat Ekle</h4>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <input
                      type="text"
                      className="input-modern"
                      placeholder="Coin (örn: COAI)"
                      value={newManualPrice.coin}
                      onChange={(e) => setNewManualPrice({...newManualPrice, coin: e.target.value.toUpperCase()})}
                    />
                    <input
                      type="number"
                      step="0.0001"
                      className="input-modern"
                      placeholder="Fiyat (örn: 10.8)"
                      value={newManualPrice.price}
                      onChange={(e) => setNewManualPrice({...newManualPrice, price: e.target.value})}
                    />
                    <button
                      className="btn btn-primary"
                      onClick={addManualPrice}
                      disabled={loading}
                    >
                      {loading ? '⏳ Kaydediliyor...' : '💾 Ekle'}
                    </button>
                  </div>
                  <small className="text-gray-600 dark:text-gray-400 mt-2 block">
                    ℹ️ Manuel fiyat, tüm API fiyatlarından (CMC, CoinGecko, DexScreener) önceliklidir
                  </small>
                </div>

                {/* Mevcut Manuel Fiyatlar */}
                {Object.keys(manualPrices).length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                      <thead className="bg-gray-50 dark:bg-gray-800">
                        <tr>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                            Coin
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                            Manuel Fiyat
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                            Durum
                          </th>
                          <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                            İşlem
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
                        {Object.entries(manualPrices).map(([coin, price]) => (
                          <tr key={coin}>
                            <td className="px-4 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-gray-100">
                              {coin}
                            </td>
                            <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-700 dark:text-gray-300">
                              <span className="font-mono">${price.toFixed(4)}</span>
                            </td>
                            <td className="px-4 py-4 whitespace-nowrap text-sm">
                              <span className="px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300">
                                📌 Aktif
                              </span>
                            </td>
                            <td className="px-4 py-4 whitespace-nowrap text-right text-sm">
                              <button
                                className="text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300"
                                onClick={() => removeManualPrice(coin)}
                                disabled={loading}
                              >
                                🗑️ Kaldır
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                    <p>📭 Henüz manuel fiyat yok</p>
                    <p className="text-sm mt-2">Yukarıdaki formu kullanarak ekleyebilirsiniz</p>
                  </div>
                )}
              </div>
            </div>

            {/* Alarmlar Kartı */}
            <div className="card mt-6">
              <div className="flex items-center justify-between mb-2">
                <h3>🔔 Aktif Fiyat Alarmları</h3>
                <div className="flex items-center gap-3">
                  <span className={`text-sm font-medium ${alarmsActive ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                    {alarmsActive ? '✅ Aktif' : '⛔ Pasif'}
                  </span>
                  <button
                    onClick={() => {
                      const newValue = !alarmsActive;
                      setAlarmsActive(newValue);
                      toggleAlarms(newValue);
                    }}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 ${
                      alarmsActive 
                        ? 'bg-green-600 focus:ring-green-500' 
                        : 'bg-red-600 focus:ring-red-500'
                    }`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        alarmsActive ? 'translate-x-6' : 'translate-x-1'
                      }`}
                    />
                  </button>
                </div>
              </div>
              <p className="card-description">
                Sinyal üretildiğinde otomatik oluşturulan fiyat alarmları
              </p>

              {alarms.length > 0 ? (
                <div className="overflow-x-auto mt-4">
                  <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                    <thead className="bg-gray-50 dark:bg-gray-800">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                          Coin
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                          Alarm Tipi
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                          Hedef Fiyat
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                          Sinyal
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                          Durum
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
                      {alarms.map((alarm) => (
                        <tr key={alarm._id}>
                          <td className="px-4 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-gray-100">
                            {alarm.coin}
                          </td>
                          <td className="px-4 py-4 whitespace-nowrap text-sm">
                            <span className={`px-2 py-1 rounded text-xs font-medium ${
                              alarm.alarm_type === 'tp' ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300' :
                              alarm.alarm_type === 'sl' ? 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300' :
                              'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
                            }`}>
                              {alarm.alarm_type === 'tp' ? '🎯 TP (Kar Al)' :
                               alarm.alarm_type === 'sl' ? '🛑 SL (Zarar Kes)' :
                               '📌 Giriş'}
                            </span>
                          </td>
                          <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-700 dark:text-gray-300">
                            ${alarm.target_price.toFixed(4)}
                          </td>
                          <td className="px-4 py-4 whitespace-nowrap text-sm">
                            <span className={`px-2 py-1 rounded text-xs font-medium ${
                              alarm.signal_type === 'LONG' ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300' :
                              'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
                            }`}>
                              {alarm.signal_type}
                            </span>
                          </td>
                          <td className="px-4 py-4 whitespace-nowrap text-sm">
                            <span className="text-yellow-600 dark:text-yellow-400">
                              ⏳ Bekliyor
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                  <p>📭 Henüz aktif alarm yok</p>
                  <p className="text-sm mt-2">Sinyal üretildiğinde otomatik olarak alarm oluşturulacak</p>
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