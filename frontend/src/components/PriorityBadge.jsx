const PRIORITY_STYLES = {
  alta: "bg-red-100 text-red-800 border-red-300",
  media: "bg-amber-100 text-amber-800 border-amber-300",
  baja: "bg-green-100 text-green-800 border-green-300",
};

export default function PriorityBadge({ level }) {
  const normalized = (level || "").toLowerCase();
  const style = PRIORITY_STYLES[normalized] || "bg-gray-100 text-gray-800 border-gray-300";

  return (
    <span className={`inline-block px-3 py-1 rounded-full border text-sm font-semibold uppercase tracking-wide ${style}`}>
      Prioridad {level}
    </span>
  );
}