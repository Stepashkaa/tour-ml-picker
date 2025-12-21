import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/api";

export default function Register() {
  const nav = useNavigate();
  const [name, setName] = useState("User One");
  const [email, setEmail] = useState("user1@mail.com");
  const [password, setPassword] = useState("1234");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await api.post("/api/auth/register", { name, email, password });
      nav("/login");
    } catch (err) {
      setError(err?.response?.data?.detail || "Register failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="center">
      <div className="card">
        <h2>Регистрация</h2>
        <div className="sub">Создай аккаунт для бронирований</div>

        <form onSubmit={onSubmit}>
          <div style={{ marginBottom: 12 }}>
            <label>Имя</label>
            <input value={name} onChange={(e) => setName(e.target.value)} />
          </div>

          <div style={{ marginBottom: 12 }}>
            <label>Email</label>
            <input value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>

          <div style={{ marginBottom: 12 }}>
            <label>Пароль</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>

          <button className="btn btn-primary" type="submit" disabled={loading} style={{ width: "100%" }}>
            {loading ? "Создаём..." : "Создать аккаунт"}
          </button>

          {error && <div className="error">{error}</div>}
        </form>

        <div className="hr" />

        <div className="small">
          Уже есть аккаунт? <Link to="/login">Войти</Link>
        </div>
      </div>
    </div>
  );
}
