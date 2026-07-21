import { useState } from "react";
import Layout from "../components/Layout";
import ImageUploader from "../components/ImageUploader";
import DetectionCanvas from "../components/DetectionCanvas";
import ResultsTable from "../components/ResultsTable";
import PriorityBadge from "../components/PriorityBadge";
import { mockAnalysis } from "../mocks/mockAnalysis";

const USE_MOCK = true; // cambiar a false cuando conectemos el backend real

export default function Home() {
  const [imageUrl, setImageUrl] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleFileSelected(file) {
    setLoading(true);
    setError(null);
    setResult(null);
    setImageUrl(URL.createObjectURL(file));

    try {
      const data = USE_MOCK
        ? await new Promise((res) => setTimeout(() => res(mockAnalysis), 1200))
        : null; // aquí irá analyzeImage(file) cuando conectemos el backend real
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Layout>
      <ImageUploader onFileSelected={handleFileSelected} isLoading={loading} />

      {error && (
        <div className="mt-4 p-4 bg-red-50 text-red-700 rounded-lg border border-red-200">
          {error}
        </div>
      )}

      {result && imageUrl && (
        <div className="mt-8 space-y-6">
          <DetectionCanvas
            imageUrl={imageUrl}
            detections={result.detecciones}
            imgMeta={result.imagen}
          />

          <div className="flex items-center justify-between">
            <PriorityBadge level={result.veredicto.nivel_alerta} />
            <span className="text-sm text-gray-500">
              {result.total_detecciones} incidencia(s) detectada(s)
            </span>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <h2 className="font-semibold text-gray-800 mb-3">Resultados de detección</h2>
            <ResultsTable detections={result.detecciones} />
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <h2 className="font-semibold text-gray-800 mb-2">Acción recomendada</h2>
            <p className="text-gray-600 text-sm">{result.veredicto.accion}</p>
            <p className="text-gray-500 text-sm mt-1">{result.veredicto.detalles}</p>
          </div>

          {result.informe && (
            <div className="bg-white rounded-lg border border-gray-200 p-5">
              <h2 className="font-semibold text-gray-800 mb-2">Informe técnico</h2>
              <p className="text-gray-600 text-sm whitespace-pre-line">{result.informe}</p>
            </div>
          )}
        </div>
      )}
    </Layout>
  );
}