type DiffViewerProps = {
  diff: string;
};

export function DiffViewer({ diff }: DiffViewerProps) {
  return (
    <section className="panel">
      <div className="panel__header">
        <h2>Diff Snapshot</h2>
      </div>
      <pre className="diff-viewer">{diff || "No diff snapshot saved."}</pre>
    </section>
  );
}
