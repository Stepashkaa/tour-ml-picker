import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/api";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
  LineChart, Line,
} from "recharts";

export default function MlReport() {
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);

  async function load() {
    setError(null);
    try {
      const res = await api.get("/api/ml/report");
      setReport(res.data);
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to load report");
    }
  }

  useEffect(() => {
    load();
  }, []);

  const m = report?.metrics;

  const metricsData = useMemo(() => {
    if (!m) return [];
    const keys = ["roc_auc", "pr_auc", "accuracy", "precision", "recall", "f1"];
    return keys.map((k) => ({ name: k.toUpperCase(), value: Number(m[k] ?? 0) }));
  }, [m]);

  const classData = useMemo(() => {
    if (!report?.labels) return [];
    const c0 = report.labels.count_0 ?? 0;
    const c1 = report.labels.count_1 ?? 0;
    return [
      { name: "VIEW (0)", value: c0 },
      { name: "BOOK (1)", value: c1 },
    ];
  }, [report]);

  const bookRate = useMemo(() => {
    const c0 = report?.labels?.count_0 ?? 0;
    const c1 = report?.labels?.count_1 ?? 0;
    const total = c0 + c1;
    return total ? (c1 / total) : 0;
  }, [report]);

  const derivedData = useMemo(() => {
    const d = m?.derived;
    if (!d) return [];
    const items = [
      ["SPEC (TNR)", d.tnr_specificity],
      ["FPR", d.fpr],
      ["FNR", d.fnr],
      ["BAL ACC", d.balanced_accuracy],
      ["MCC", d.mcc],
    ];
    return items.map(([name, value]) => ({ name, value: Number(value ?? 0) }));
  }, [m]);

  const splitData = useMemo(() => {
    if (!report) return [];
    return [
      { name: "TRAIN", value: Number(report.train_samples ?? 0) },
      { name: "TEST", value: Number(report.test_samples ?? 0) },
      { name: "TOTAL", value: Number(report.samples_total ?? 0) },
    ];
  }, [report]);

  const cmBars = useMemo(() => {
    const cm = m?.confusion_matrix;
    if (!cm || !Array.isArray(cm) || cm.length !== 2) return [];
    const tn = Number(cm[0]?.[0] ?? 0);
    const fp = Number(cm[0]?.[1] ?? 0);
    const fn = Number(cm[1]?.[0] ?? 0);
    const tp = Number(cm[1]?.[1] ?? 0);

    return [
      { name: "TN", value: tn },
      { name: "FP", value: fp },
      { name: "FN", value: fn },
      { name: "TP", value: tp },
    ];
  }, [m]);

  const rocData = useMemo(() => {
    const pts = m?.roc_curve;
    if (!Array.isArray(pts)) return [];
    return pts.map((p) => ({
      fpr: Number(p.fpr ?? 0),
      tpr: Number(p.tpr ?? 0),
    }));
  }, [m]);

  const prData = useMemo(() => {
    const pts = m?.pr_curve;
    if (!Array.isArray(pts)) return [];
    return pts.map((p) => ({
      recall: Number(p.recall ?? 0),
      precision: Number(p.precision ?? 0),
    }));
  }, [m]);

  const best = m?.best_threshold;

  const thresholdCurve = useMemo(() => {
    const curve = best?.curve;
    if (!Array.isArray(curve)) return [];
    return curve.map((p) => ({
      ...p,
      threshold: Number(p.threshold.toFixed(2)),
    }));
  }, [best]);

  return (
    <div className="container">
      <div className="row">
        <Link className="btn btn-ghost" to="/tours">← Назад</Link>
        <button className="btn" onClick={load}>Обновить</button>
      </div>

      <div className="card">
        <h2>ML Report</h2>
        <div className="sub">Визуализация качества модели и данных обучения</div>

        {error && <div className="error">{error}</div>}
        {!report && !error && <div className="small">Загрузка...</div>}

        {report && (
          <>
            <div className="row">
              <span className="badge">samples: {report.samples_total}</span>
              <span className="badge">train: {report.train_samples}</span>
              <span className="badge">test: {report.test_samples}</span>
              <span className="badge">BOOK share: {(bookRate * 100).toFixed(1)}%</span>
              <span className="badge">time: {report.timestamp_utc}</span>
              <span className="badge">threshold: {m?.threshold}</span>
              {best?.threshold != null && <span className="badge">best thr: {best.threshold}</span>}
            </div>

            <div className="hr" />

            {/* Метрики качества (основные) */}
            <div className="card" style={{ background: "rgba(255,255,255,0.04)" }}>
              <div className="tourTitle">Основные метрики</div>
              <div className="tourMeta">ROC-AUC / PR-AUC / Accuracy / Precision / Recall / F1</div>

              <div style={{ height: 260, marginTop: 10 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={metricsData}>
                    <XAxis dataKey="name" />
                    <YAxis domain={[0, 1]} />
                    <Tooltip />
                    <Bar dataKey="value" />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="small">
                LogLoss: {m?.logloss?.toFixed?.(4) ?? m?.logloss} •{" "}
                Brier: {m?.brier?.toFixed?.(4) ?? m?.brier} •{" "}
                F1_macro: {m?.f1_macro?.toFixed?.(4) ?? m?.f1_macro} •{" "}
                F1_weighted: {m?.f1_weighted?.toFixed?.(4) ?? m?.f1_weighted}
              </div>
            </div>

            {rocData.length > 0 && (
              <div className="card" style={{ background: "rgba(255,255,255,0.04)" }}>
                <div className="tourTitle">ROC-кривая (TPR vs FPR)</div>
                <div className="tourMeta">
                  Визуализация ROC-AUC (качество разделения классов при разных порогах)
                </div>

                <div style={{ height: 280, marginTop: 10 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={rocData}>
                      <XAxis dataKey="fpr" />
                      <YAxis domain={[0, 1]} />
                      <Tooltip />
                      <Legend />
                      <Line type="monotone" dataKey="tpr" name="TPR (Recall)" dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>

                <div className="small">
                  ROC-AUC: {m?.roc_auc?.toFixed?.(4) ?? m?.roc_auc}. Чем ближе к 1 — тем лучше различаются BOOK и VIEW.
                </div>
              </div>
            )}

            {prData.length > 0 && (
              <div className="card" style={{ background: "rgba(255,255,255,0.04)" }}>
                <div className="tourTitle">Precision–Recall кривая</div>
                <div className="tourMeta">
                  Важна при дисбалансе классов (BOOK встречается реже)
                </div>

                <div style={{ height: 280, marginTop: 10 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={prData}>
                      <XAxis dataKey="recall" />
                      <YAxis domain={[0, 1]} />
                      <Tooltip />
                      <Legend />
                      <Line type="monotone" dataKey="precision" name="Precision" dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>

                <div className="small">
                  PR-AUC: {m?.pr_auc?.toFixed?.(4) ?? m?.pr_auc}. Показывает компромисс точности и полноты для класса BOOK.
                </div>
              </div>
            )}

            {splitData.length > 0 && (
              <div className="card" style={{ background: "rgba(255,255,255,0.04)" }}>
                <div className="tourTitle">Разбиение датасета (train/test)</div>

                <div style={{ height: 260, marginTop: 10 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={splitData}>
                      <XAxis dataKey="name" />
                      <YAxis />
                      <Tooltip />
                      <Bar dataKey="value" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                <div className="small">
                </div>
              </div>
            )}

            {/* Derived metrics */}
            {derivedData.length > 0 && (
              <div className="card" style={{ background: "rgba(255,255,255,0.04)" }}>
                <div className="tourTitle">Метрики ошибок и устойчивости (из Confusion Matrix)</div>
                <div className="tourMeta">Specificity / FPR / FNR / Balanced Accuracy / MCC</div>

                <div style={{ height: 260, marginTop: 10 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={derivedData}>
                      <XAxis dataKey="name" />
                      <YAxis domain={[-1, 1]} />
                      <Tooltip />
                      <Bar dataKey="value" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                <div className="small">
                  Specificity (TNR) — насколько хорошо модель распознаёт VIEW (0). MCC — хорош при дисбалансе.
                </div>
              </div>
            )}

            {/* Баланс классов */}
            <div className="card" style={{ background: "rgba(255,255,255,0.04)" }}>
              <div className="tourTitle">Баланс классов (VIEW vs BOOK)</div>
              <div className="tourMeta">Сколько событий каждого типа было в датасете</div>

              <div style={{ height: 260, marginTop: 10 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={classData}
                      dataKey="value"
                      nameKey="name"
                      outerRadius={90}
                      label
                    >
                      {classData.map((_, idx) => (
                        <Cell key={idx} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              <div className="small">
                VIEW={report.labels?.count_0} • BOOK={report.labels?.count_1} • BOOK share={(bookRate * 100).toFixed(1)}%
              </div>
            </div>

            {/* Сравнение порогов */}
            {best && (
              <div className="card" style={{ background: "rgba(255,255,255,0.04)" }}>
                <div className="tourTitle">Сравнение порога 0.5 и лучшего порога</div>
                <div className="tourMeta">Для дисбаланса классов порог 0.5 часто не оптимален</div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginTop: 12 }}>
                  <div className="card" style={{ background: "rgba(0,0,0,0.20)" }}>
                    <div className="small"><b>Threshold = 0.5</b></div>
                    <div className="small">Precision: {m?.precision?.toFixed?.(4) ?? m?.precision}</div>
                    <div className="small">Recall: {m?.recall?.toFixed?.(4) ?? m?.recall}</div>
                    <div className="small">F1: {m?.f1?.toFixed?.(4) ?? m?.f1}</div>
                  </div>

                  <div className="card" style={{ background: "rgba(0,0,0,0.20)" }}>
                    <div className="small"><b>Best threshold = {best.threshold}</b></div>
                    <div className="small">Precision: {best.precision?.toFixed?.(4) ?? best.precision}</div>
                    <div className="small">Recall: {best.recall?.toFixed?.(4) ?? best.recall}</div>
                    <div className="small">F1: {best.f1?.toFixed?.(4) ?? best.f1}</div>
                  </div>
                </div>
              </div>
            )}

            {thresholdCurve.length > 0 && (
              <div className="card" style={{ background: "rgba(255,255,255,0.04)" }}>
                <div className="tourTitle">Метрики в зависимости от threshold</div>
                <div className="tourMeta">
                  Как меняются Precision / Recall / F1 при изменении порога классификации
                </div>

                <div style={{ height: 300, marginTop: 10 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={thresholdCurve}>
                      <XAxis dataKey="threshold" />
                      <YAxis domain={[0, 1]} />
                      <Tooltip />
                      <Legend />
                      <Line type="monotone" dataKey="precision" name="Precision" dot={false} />
                      <Line type="monotone" dataKey="recall" name="Recall" dot={false} />
                      <Line type="monotone" dataKey="f1" name="F1" dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}

            {cmBars.length > 0 && (
              <div className="card" style={{ background: "rgba(255,255,255,0.04)" }}>
                <div className="tourTitle">Ошибки классификации (TN / FP / FN / TP)</div>
                <div className="tourMeta">Визуализация confusion matrix при threshold={m?.threshold}</div>

                <div style={{ height: 260, marginTop: 10 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={cmBars}>
                      <XAxis dataKey="name" />
                      <YAxis />
                      <Tooltip />
                      <Bar dataKey="value" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                <div className="small">
                  FP — ложные “BOOK”, FN — пропущенные “BOOK”.
                </div>
              </div>
            )}

            {/* Confusion matrix */}
            <div className="card" style={{ background: "rgba(255,255,255,0.04)" }}>
              <div className="tourTitle">Confusion Matrix</div>
              <div className="tourMeta">[[TN, FP], [FN, TP]] при threshold={m?.threshold}</div>

              {!m?.confusion_matrix && <div className="small">Нет данных</div>}

              {m?.confusion_matrix && (
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginTop: 12 }}>
                  <div className="card" style={{ background: "rgba(0,0,0,0.20)" }}>
                    <div className="small">TN (правильные 0)</div>
                    <div className="tourTitle">{m.confusion_matrix[0][0]}</div>
                  </div>
                  <div className="card" style={{ background: "rgba(0,0,0,0.20)" }}>
                    <div className="small">FP (ложные 1)</div>
                    <div className="tourTitle">{m.confusion_matrix[0][1]}</div>
                  </div>
                  <div className="card" style={{ background: "rgba(0,0,0,0.20)" }}>
                    <div className="small">FN (пропущенные 1)</div>
                    <div className="tourTitle">{m.confusion_matrix[1][0]}</div>
                  </div>
                  <div className="card" style={{ background: "rgba(0,0,0,0.20)" }}>
                    <div className="small">TP (правильные 1)</div>
                    <div className="tourTitle">{m.confusion_matrix[1][1]}</div>
                  </div>
                </div>
              )}
            </div>

            <div className="small">
              <b>Notes:</b> {report.notes}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
