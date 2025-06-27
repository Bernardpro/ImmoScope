import React, { useState, useEffect } from "react";
import "./TermsBySentiment.scss";

interface TermsBySentimentProps {
  /** Code INSEE de la commune sélectionnée */
  codeCommune: string;
}

/**
 * Réponse attendue de /comment/data/sentiment-terms
 * {
 *   "positive": ["calme", "vert", ...],
 *   "negative": ["sale", "bruyant", ...]
 * }
 */
interface SentimentTermsResponse {
  [sentiment: string]: string[];
}

/**
 * Les 5 mots les plus fréquents, réponse brute de /comment/data/top-terms
 * Exemple: ["calme", "après", "avantage", "bucolique", "calme"]
 */
type TopTermsResponse = string[];

const API_BASE =
  "https://api.homepedia.spectrum-app.cloud/comment/data";

/**
 * Composant affichant :
 * 1. Les mots les plus fréquents, tous sentiments confondus (top‑terms)
 * 2. Les mots positifs
 * 3. Les mots négatifs
 */
const TermsBySentiment: React.FC<TermsBySentimentProps> = ({ codeCommune }) => {
  const [terms, setTerms] = useState<{
    positive: string[];
    negative: string[];
    top: string[];
  }>({
    positive: [],
    negative: [],
    top: [],
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!codeCommune) return;

    const fetchTerms = async () => {
      setLoading(true);
      setError(null);

      try {
        // Appels parallèles : sentiment‑terms + top‑terms
        const [sentimentRes, topRes] = await Promise.all([
          fetch(`${API_BASE}/sentiment-terms?code=${codeCommune}`),
          fetch(`${API_BASE}/top-terms?code=${codeCommune}`),
        ]);

        if (!sentimentRes.ok || !topRes.ok) {
          throw new Error(
            `HTTP ${sentimentRes.status}/${topRes.status}`
          );
        }

        const sentimentData: SentimentTermsResponse =
          (await sentimentRes.json()) ?? {};
        const topData: TopTermsResponse = (await topRes.json()) ?? [];

        setTerms({
          positive: sentimentData.positive ?? [],
          negative: sentimentData.negative ?? [],
          top: topData,
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : "Erreur inconnue");
      } finally {
        setLoading(false);
      }
    };

    fetchTerms();
  }, [codeCommune]);

  if (loading)
    return <p className="text-sm italic">Chargement des mots‑clés…</p>;
  if (error)
    return (
      <div className="error-container">
        <p className="error-message">⚠️ {error} key words…</p>
      </div>
    );

  return (
    <div className="terms-card">
      {/* Top tokens */}
      <div className="terms-card__section">
        <h4 className="terms-card__title">Principaux mots</h4>
        <ul className="terms-card__list">
          {terms.top.length ? (
            terms.top.map((t) => (
              <li key={t} className="terms-card__list-item">
                {t}
              </li>
            ))
          ) : (
            <li className="terms-card__list-item terms-card__list-item--empty">
              Aucun mot pour cette zone
            </li>
          )}
        </ul>
      </div>

      {/* Positif */}
      <div className="terms-card__section">
        <h4 className="terms-card__title terms-card__title--positive">
          Positif
        </h4>
        <ul className="terms-card__list">
          {terms.positive.length ? (
            terms.positive.map((t) => (
              <li key={t} className="terms-card__list-item">
                {t}
              </li>
            ))
          ) : (
            <li className="terms-card__list-item terms-card__list-item--empty">
              Aucun mot pour cette zone
            </li>
          )}
        </ul>
      </div>

      {/* Négatif */}
      <div className="terms-card__section">
        <h4 className="terms-card__title terms-card__title--negative">
          Négatif
        </h4>
        <ul className="terms-card__list">
          {terms.negative.length ? (
            terms.negative.map((t) => (
              <li key={t} className="terms-card__list-item">
                {t}
              </li>
            ))
          ) : (
            <li className="terms-card__list-item terms-card__list-item--empty">
              Aucun mot pour cette zone
            </li>
          )}
        </ul>
      </div>
    </div>
  );
};

export default TermsBySentiment;
