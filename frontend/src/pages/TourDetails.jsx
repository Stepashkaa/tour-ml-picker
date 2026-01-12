import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api/api";

export default function TourDetails() {
  const { id } = useParams();
  const nav = useNavigate();

  const [tour, setTour] = useState(null);
  const [error, setError] = useState(null);
  const [bookingLoading, setBookingLoading] = useState(false);

  useEffect(() => {
    async function load() {
      setError(null);
      try {
        const res = await api.get(`/api/tours/${id}`);
        setTour(res.data);

        // VIEW событие
        const searchId = localStorage.getItem("last_search_id");
        await api.post("/api/events/view", {
          tour_id: parseInt(id),
          search_id: searchId ? parseInt(searchId) : null,
        });
      } catch (err) {
        setError(err?.response?.data?.detail || "Load failed");
      }
    }
    load();
  }, [id]);

  async function book() {
    setBookingLoading(true);
    setError(null);
    try {
      const searchId = localStorage.getItem("last_search_id");
      await api.post("/api/bookings", {
        tour_id: parseInt(id),
        search_id: searchId ? parseInt(searchId) : null,
      });
      nav("/bookings");
    } catch (err) {
      setError(err?.response?.data?.detail || "Booking failed");
    } finally {
      setBookingLoading(false);
    }
  }

  return (
    <div className="container">
      <div className="row">
        <Link className="btn btn-ghost" to="/tours">← Назад</Link>
      </div>

      <div className="card">
        <h2>Карточка тура</h2>
        <div className="sub">Детальная информация и бронирование</div>

        {error && <div className="error">{error}</div>}
        {!tour && !error && <div className="small">Загрузка...</div>}

        {tour && (
          <>
            <div className="kv">
              <div className="small">Город</div><div><b>{tour.city}</b></div>
              <div className="small">Цена</div><div><b>{tour.price}</b></div>
              <div className="small">Длительность</div><div><b>{tour.duration_days}</b> дней</div>
              <div className="small">Рейтинг</div><div><b>{tour.rating}</b></div>
              <div className="small">Сезон</div><div><b>{tour.season}</b></div>
              <div className="small">Тип</div><div><b>{tour.tour_type}</b></div>
            </div>

            <div className="hr" />

            <div className="small"><b>Описание:</b></div>
            <div style={{ marginTop: 6 }}>{tour.description}</div>

            <div className="row">
              <button className="btn btn-success" onClick={book} disabled={bookingLoading}>
                {bookingLoading ? "Бронируем..." : "Забронировать"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
