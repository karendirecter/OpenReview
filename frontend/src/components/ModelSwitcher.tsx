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
        <div>
          <p className="panel__eyebrow">Execution tools</p>
          <h2>Model Replay</h2>
        </div>
        <span className="panel__meta">{models.length} models</span>
      </div>
      <div className="model-switcher__controls">
        <label className="field">
          <span className="field__label">Replay model</span>
          <select value={selectedModel} onChange={(event) => onChange(event.target.value)}>
            {models.map((model) => (
              <option key={model} value={model}>
                {model}
              </option>
            ))}
          </select>
        </label>
        <button type="button" className="button" onClick={onReplay} disabled={loading || !selectedModel}>
          {loading ? "Replaying..." : "Replay run"}
        </button>
      </div>
    </section>
  );
}
