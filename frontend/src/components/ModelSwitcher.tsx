type ModelSwitcherProps = {
  models: string[];
  selectedModel: string;
  loading?: boolean;
  onChange: (value: string) => void;
  onReplay: () => void;
};

export function ModelSwitcher({
  models,
  selectedModel,
  loading = false,
  onChange,
  onReplay
}: ModelSwitcherProps) {
  return (
    <section className="panel model-switcher">
      <div className="panel__header">
        <h2>Model Replay</h2>
      </div>
      <div className="model-switcher__controls">
        <select value={selectedModel} onChange={(event) => onChange(event.target.value)}>
          {models.map((model) => (
            <option key={model} value={model}>
              {model}
            </option>
          ))}
        </select>
        <button type="button" onClick={onReplay} disabled={loading}>
          {loading ? "Replaying..." : "Replay"}
        </button>
      </div>
    </section>
  );
}
