export default function Layout({ children }) {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <h1 className="text-xl font-bold text-gray-800">🛣️ RoadGuardian AI</h1>
        <p className="text-sm text-gray-500">Inspección automática del pavimento</p>
      </header>
      <main className="max-w-4xl mx-auto p-6">{children}</main>
    </div>
  );
}