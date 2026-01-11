import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/api";
import { logout } from "../auth/auth";

export default function Tours() {
  const nav = useNavigate();

  const [city, setCity] = useState("Rome");
  const [maxPrice, setMaxPrice] = useState("");
  const [durationDays, setDurationDays] = useState("");
  const [tourType, setTourType] = useState("");
  const [season, setSeason] = useState("");

  const [items, setItems] = useState([]);
  const [error, setError] = useState(null);

  const [loading, setLoading] = useState(false);

  const [trainStatus, setTrainStatus] = useState(null);
  const [trainLoading, setTrainLoading] = useState(false);

  const [seedStatus, setSeedStatus] = useState(null);
  const [seedLoading, setSeedLoading] = useState(false);

  async function search() {
    setError(null);
    setLoading(true);
    try {
      const payload = {
        city,
        max_price: maxPrice ? parseInt(maxPrice) : null,
        duration_days: durationDays ? parseInt(durationDays) : null,
        tour_type: tourType || null,
        season: season || null,
        limit: 20,
      };
      const res = await api.post("/api/tours/search", payload);
      setItems(res.data);
    } catch (err) {
      setError(err?.response?.data?.detail || "Search failed");
    } finally {
      setLoading(false);
    }
  }

  async function trainModel() {
    setTrainStatus(null);
    setTrainLoading(true);
    try {
      const res = await api.post("/api/ml/train");
      setTrainStatus(JSON.stringify(res.data, null, 2));
      await search();
    } catch (err) {
      setTrainStatus(err?.response?.data?.detail || "Train failed");
    } finally {
      setTrainLoading(false);
    }
  }

  async function seedData() {
    setSeedStatus(null);
    setSeedLoading(true);
    try {
      // 5 users, много событий
      const res = await api.post(
        "/api/dev/seed?users_count=5&tours_count=120&views_per_user=80&books_per_user=20"
      );
      setSeedStatus(JSON.stringify(res.data, null, 2));
    } catch (err) {
      setSeedStatus(err?.response?.data?.detail || "Seed failed");
    } finally {
      setSeedLoading(false);
    }
  }

  useEffect(() => {
    search();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function onLogout() {
    logout();
    nav("/login");
  }

  return (
    <div className="container">
      <div className="hrow" style={{ marginBottom: 12 }}>
        <div>
          <h2>Подбор туров</h2>
          <div className="sub">ML-ранжирование выдачи по параметрам тура и фильтрам</div>
        </div>

        <div className="row">
          <Link className="btn btn-ghost" to="/bookings">Мои бронирования</Link>
          <button className="btn" onClick={onLogout}>Выйти</button>
        </div>

        <Link className="btn btn-ghost" to="/ml">ML Report</Link>
      </div>

      <div className="card">
        <div className="grid">
          <div>
            <label>Город</label>
            <select value={city} onChange={(e) => setCity(e.target.value)}>
              <option value="Rome">Rome</option>
              <option value="Paris">Paris</option>
              <option value="Barcelona">Barcelona</option>
              <option value="Prague">Prague</option>
              <option value="Vienna">Vienna</option>
              <option value="Berlin">Berlin</option>
            </select>
          </div>

          <div>
            <label>Макс. бюджет</label>
            <input value={maxPrice} onChange={(e) => setMaxPrice(e.target.value)} placeholder="например 120000" />
          </div>

          <div>
            <label>Длительность (дней)</label>
            <input value={durationDays} onChange={(e) => setDurationDays(e.target.value)} placeholder="например 7" />
          </div>

          <div>
            <label>Тип отдыха</label>
            <select value={tourType} onChange={(e) => setTourType(e.target.value)}>
              <option value="">не важно</option>
              <option value="relax">relax</option>
              <option value="excursion">excursion</option>
              <option value="beach">beach</option>
            </select>
          </div>

          <div>
            <label>Сезон</label>
            <select value={season} onChange={(e) => setSeason(e.target.value)}>
              <option value="">не важно</option>
              <option value="summer">summer</option>
              <option value="winter">winter</option>
              <option value="all">all</option>
            </select>
          </div>
        </div>

        <div className="row">
          <button className="btn btn-primary" onClick={search} disabled={loading}>
            {loading ? "Поиск..." : "Подобрать"}
          </button>

          <button className="btn btn-success" onClick={seedData} disabled={seedLoading}>
            {seedLoading ? "Генерация..." : "Seed (данные)"}
          </button>

          <button className="btn btn-success" onClick={trainModel} disabled={trainLoading}>
            {trainLoading ? "Обучение..." : "Train ML"}
          </button>

          <span className="badge">топ-20</span>
        </div>

        {error && <div className="error">{error}</div>}

        {seedStatus && (
          <div className="small" style={{ marginTop: 10 }}>
            <b>Seed result:</b>{"\n"}{seedStatus}
          </div>
        )}

        {trainStatus && (
          <div className="small" style={{ marginTop: 10 }}>
            <b>Train result:</b>{"\n"}{trainStatus}
          </div>
        )}
      </div>

      <div className="card">
        {items.length === 0 && !loading && <div className="small">Ничего не найдено</div>}

        {items.map((t) => (
          <div key={t.id} className="card" style={{ background: "rgba(255,255,255,0.04)" }}>
            <div className="hrow">
              <div>
                <div className="tourTitle">{t.city} • {t.tour_type}</div>
                <div className="tourMeta">
                  {t.duration_days} дней • сезон: {t.season} • рейтинг: {t.rating}
                </div>
              </div>

              <div style={{ textAlign: "right" }}>
                <div><b>{t.price}</b></div>
                <div className="small">ML-score: {t.ml_score != null ? t.ml_score.toFixed(4) : "-"}</div>
              </div>
            </div>

            <div className="row">
              <Link className="btn btn-primary" to={`/tours/${t.id}`}>Подробнее</Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
