import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/api";

export default function MyBookings() {
  const [items, setItems] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function load() {
    setError(null);
    setLoading(true);
    try {
      const res = await api.get("/api/bookings/my");
      setItems(res.data);
    } catch (err) {
      setError(err?.response?.data?.detail || "Load failed");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="container">
      <div className="row">
        <Link className="btn btn-ghost" to="/tours">← Назад</Link>
      </div>

      <div className="card">
        <h2>Мои бронирования</h2>
        <div className="sub">Список созданных броней</div>

        {error && <div className="error">{error}</div>}
        {loading && <div className="small">Загрузка...</div>}
        {items.length === 0 && !error && !loading && <div className="small">Пока нет бронирований</div>}
      </div>

      {items.map((b) => (
        <div key={b.id} className="card">
          <div className="hrow">
            <div>
              <div className="tourTitle">
                Booking #{b.id} • <span className="badge">{b.status}</span>
              </div>
              <div className="tourMeta">{new Date(b.created_at).toLocaleString()}</div>
            </div>
            <div style={{ textAlign: "right" }}>
              <div><b>{b.tour.city}</b></div>
              <div className="small">{b.tour.tour_type} • {b.tour.duration_days} дней</div>
              <div className="small">Цена: {b.tour.price}</div>
            </div>
          </div>

          <div className="row">
            <Link className="btn btn-primary" to={`/tours/${b.tour.id}`}>Открыть тур</Link>
          </div>
        </div>
      ))}
    </div>
  );
}
