type DiffViewerProps = {
  diff: string;
};

export function DiffViewer({ diff }: DiffViewerProps) {
  const lineCount = diff ? diff.split("\n").length : 0;

  return (
    <section className="panel">
      <div className="panel__header">
        <div>
          <p className="panel__eyebrow">Patch context</p>
          <h2>Diff Snapshot</h2>
        </div>
        <span className="panel__meta">{lineCount} lines</span>
      </div>
      <pre className="diff-viewer">{diff || "No diff snapshot saved."}</pre>
    </section>
  );
}
