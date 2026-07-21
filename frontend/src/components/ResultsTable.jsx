export default function ResultsTable({ detections }) {
  return (
    <table className="w-full text-sm text-left border-collapse">
      <thead>
        <tr className="border-b border-gray-200 text-gray-500 uppercase text-xs">
          <th className="py-2 pr-4">Tipo de daño</th>
          <th className="py-2 pr-4">Confianza</th>
          <th className="py-2 pr-4">% Superficie</th>
        </tr>
      </thead>
      <tbody>
        {detections.map((det, i) => (
          <tr key={i} className="border-b border-gray-100">
            <td className="py-2 pr-4 font-medium capitalize">{det.clase.replace(/_/g, " ")}</td>
            <td className="py-2 pr-4">{(det.confianza * 100).toFixed(0)}%</td>
            <td className="py-2 pr-4">{det.superficie_pct.toFixed(1)}%</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}