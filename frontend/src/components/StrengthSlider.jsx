export default function StrengthSlider({ value, onChange }) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium">Strength</label>
        <span className="text-sm font-mono text-[var(--color-primary)]">{value}%</span>
      </div>
      <input
        type="range"
        min={0}
        max={100}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full"
      />
      <div className="flex justify-between text-xs text-[var(--color-text-secondary)]">
        <span>Subtle</span>
        <span>Full</span>
      </div>
    </div>
  );
}
