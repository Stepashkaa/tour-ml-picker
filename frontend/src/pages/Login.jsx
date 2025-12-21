import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/api";
import { setToken } from "../auth/auth";

export default function Login() {
  const nav = useNavigate();
  const [email, setEmail] = useState("demo1@mail.com");
  const [password, setPassword] = useState("1234");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    // OAuth2PasswordRequestForm => x-www-form-urlencoded
    const form = new URLSearchParams();
    form.append("username", email);
    form.append("password", password);

    try {
      const res = await api.post("/api/auth/login", form, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });
      setToken(res.data.access_token);
      nav("/tours");
    } catch (err) {
      setError(err?.response?.data?.detail || "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="center">
      <div className="card">
        <h2>Вход</h2>
        <div className="sub">Авторизация для доступа к подбору туров и бронированиям</div>

        <form onSubmit={onSubmit}>
          <div style={{ marginBottom: 12 }}>
            <label>Email</label>
            <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="demo1@mail.com" />
          </div>

          <div style={{ marginBottom: 12 }}>
            <label>Пароль</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="1234" />
          </div>

          <button className="btn btn-primary" type="submit" disabled={loading} style={{ width: "100%" }}>
            {loading ? "Входим..." : "Войти"}
          </button>

          {error && <div className="error">{error}</div>}
        </form>

        <div className="hr" />

        <div className="small">
          Нет аккаунта? <Link to="/register">Регистрация</Link>
        </div>
      </div>
    </div>
  );
}
