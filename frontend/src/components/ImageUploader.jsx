import { useRef } from "react";

export default function ImageUploader({ onFileSelected, isLoading }) {
  const inputRef = useRef(null);

  return (
    <div
      className="border-2 border-dashed border-gray-300 rounded-lg p-10 text-center cursor-pointer hover:border-blue-400 transition"
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => {
        e.preventDefault();
        const file = e.dataTransfer.files?.[0];
        if (file) onFileSelected(file);
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => e.target.files?.[0] && onFileSelected(e.target.files[0])}
      />
      {isLoading ? (
        <p className="text-blue-600 font-medium">Analizando imagen...</p>
      ) : (
        <>
          <p className="text-gray-600 font-medium">Arrastra una foto del pavimento aquí</p>
          <p className="text-gray-400 text-sm mt-1">o haz clic para seleccionar un archivo</p>
        </>
      )}
    </div>
  );
}