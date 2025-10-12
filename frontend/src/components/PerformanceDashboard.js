import React, { useEffect, useState } from "react";
import axios from "axios";
import {
  PieChart, Pie, Cell, BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from "recharts";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const COLORS = {
  success: '#10b981',
  failed: '#ef4444',
  pending: '#f59e0b',
  long: '#3b82f6',
  short: '#8b5cf6'
};

const PerformanceDashboard = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadDashboardData();
    const interval = setInterval(loadDashboardData, 60000); // 60 saniyede bir güncelle
    return () => clearInterval(interval);
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const res = await axios.get(`${API}/performance-dashboard`);
      setData(res.data);
      setError(null);
    } catch (e) {
      console.error("Dashboard yükleme hatası:", e);
      setError("Dashboard verileri yüklenemedi");
    } finally {
      setLoading(false);
    }
  };

  if (loading && !data) {
    return (
      <div className="dashboard-loading">
        <div className="spinner"></div>
        <p>Dashboard yükleniyor...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="dashboard-error">
        <p>❌ {error}</p>
        <button className="btn btn-primary" onClick={loadDashboardData}>
          🔄 Yeniden Dene
        </button>
      </div>
    );
  }

  if (!data || !data.summary) {
    return (
      <div className="dashboard-error">
        <p>⚠️ Dashboard verisi bulunamadı</p>
      </div>
    );
  }

  const { summary, top_profitable, monthly_signals, coin_performance, signal_type_distribution } = data;

  // Başarı oranı için pasta grafiği verisi
  const successPieData = [
    { name: 'Başarılı', value: summary.successful_signals, color: COLORS.success },
    { name: 'Başarısız', value: summary.failed_signals, color: COLORS.failed },
    { name: 'Beklemede', value: summary.pending_signals, color: COLORS.pending }
  ].filter(item => item.value > 0);

  // Signal type dağılımı
  const signalTypeData = signal_type_distribution.map(st => ({
    name: st.type,
    count: st.count,
    color: st.type === 'LONG' ? COLORS.long : COLORS.short
  }));

  return (
    <div className="dashboard-container">
      <div className="dashboard-header">
        <h2>📊 Performance Dashboard</h2>
        <button className="btn btn-small" onClick={loadDashboardData}>
          🔄 Yenile
        </button>
      </div>

      {/* Summary Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon">📈</div>
          <div className="stat-content">
            <p className="stat-label">Toplam Sinyal</p>
            <p className="stat-value">{summary.total_signals}</p>
          </div>
        </div>

        <div className="stat-card success">
          <div className="stat-icon">✅</div>
          <div className="stat-content">
            <p className="stat-label">Başarılı</p>
            <p className="stat-value">{summary.successful_signals}</p>
          </div>
        </div>

        <div className="stat-card failed">
          <div className="stat-icon">❌</div>
          <div className="stat-content">
            <p className="stat-label">Başarısız</p>
            <p className="stat-value">{summary.failed_signals}</p>
          </div>
        </div>

        <div className="stat-card pending">
          <div className="stat-icon">⏳</div>
          <div className="stat-content">
            <p className="stat-label">Beklemede</p>
            <p className="stat-value">{summary.pending_signals}</p>
          </div>
        </div>

        <div className="stat-card rate">
          <div className="stat-icon">🎯</div>
          <div className="stat-content">
            <p className="stat-label">Başarı Oranı</p>
            <p className="stat-value">{summary.success_rate}%</p>
          </div>
        </div>

        <div className="stat-card gain">
          <div className="stat-icon">💰</div>
          <div className="stat-content">
            <p className="stat-label">Max Kazanç</p>
            <p className="stat-value">{summary.max_gain}%</p>
          </div>
        </div>

        <div className="stat-card loss">
          <div className="stat-icon">📉</div>
          <div className="stat-content">
            <p className="stat-label">Max Kayıp</p>
            <p className="stat-value">{summary.max_loss}%</p>
          </div>
        </div>

        <div className="stat-card avg">
          <div className="stat-icon">📊</div>
          <div className="stat-content">
            <p className="stat-label">Ort. Getiri</p>
            <p className="stat-value">{summary.avg_reward}%</p>
          </div>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="charts-grid">
        {/* Başarı Oranı Pasta Grafiği */}
        {successPieData.length > 0 && (
          <div className="chart-card">
            <h3>🎯 Sinyal Durumu Dağılımı</h3>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={successPieData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {successPieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Signal Type Dağılımı */}
        {signalTypeData.length > 0 && (
          <div className="chart-card">
            <h3>📊 LONG vs SHORT Dağılımı</h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={signalTypeData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="count" fill={COLORS.long}>
                  {signalTypeData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Aylık Sinyaller */}
      {monthly_signals.length > 0 && (
        <div className="chart-card full-width">
          <h3>📅 Aylık Sinyal Dağılımı</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={monthly_signals}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="count" stroke={COLORS.long} strokeWidth={2} name="Sinyal Sayısı" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Top 5 Kazançlı Sinyaller */}
      {top_profitable.length > 0 && (
        <div className="chart-card full-width">
          <h3>🏆 Top 5 Kazançlı Sinyal</h3>
          <div className="top-signals-table">
            <table>
              <thead>
                <tr>
                  <th>Coin</th>
                  <th>Yön</th>
                  <th>Kazanç %</th>
                  <th>Güvenilirlik</th>
                  <th>Zaman Dilimi</th>
                  <th>Tarih</th>
                </tr>
              </thead>
              <tbody>
                {top_profitable.map((signal) => (
                  <tr key={signal.id}>
                    <td className="coin-name">{signal.coin}</td>
                    <td>
                      <span className={`signal-badge ${signal.signal_type.toLowerCase()}`}>
                        {signal.signal_type === 'LONG' ? '📈 LONG' : '📉 SHORT'}
                      </span>
                    </td>
                    <td className="reward-value">+{signal.reward}%</td>
                    <td>{signal.probability}%</td>
                    <td>{signal.timeframe}</td>
                    <td>{signal.created_at ? new Date(signal.created_at).toLocaleDateString('tr-TR') : '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Coin Performans Tablosu */}
      {coin_performance.length > 0 && (
        <div className="chart-card full-width">
          <h3>🪙 Coin Bazlı Performans (Top 10)</h3>
          <div className="coin-performance-table">
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
                    <td className="coin-name">{cp.coin}</td>
                    <td>{cp.total_signals}</td>
                    <td>{cp.successful}</td>
                    <td>
                      <div className="success-rate-bar">
                        <div 
                          className="success-rate-fill" 
                          style={{ width: `${cp.success_rate}%` }}
                        ></div>
                        <span className="success-rate-text">{cp.success_rate}%</span>
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

export default PerformanceDashboard;
